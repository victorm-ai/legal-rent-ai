"""Contract analysis business logic (RF-52, RF-13, RF-10, RF-18, RF-37)."""

import json
import logging
from typing import List, Optional

from config.settings import Settings, get_settings
from data.analysis_dto import AnalysisDTO, ExtractedFieldDTO
from data.repositories.analysis_approval_repository import AnalysisApprovalRepository
from data.repositories.analysis_repository import AnalysisRepository
from data.repositories.clause_repository import ClauseRepository
from data.repositories.contract_document_repository import ContractDocumentRepository
from data.repositories.contract_party_repository import ContractPartyRepository
from data.repositories.contract_repository import ContractRepository
from data.repositories.extracted_field_repository import ExtractedFieldRepository
from data.repositories.finding_repository import FindingRepository
from data.repositories.finding_review_repository import FindingReviewRepository, VALID_VERDICTS
from domain.analysis_status import (
    InvalidAnalysisStatusTransitionError,
    assert_transition as assert_analysis_transition,
    validate_analysis_status_value,
)
from domain.contract_status import is_visible_to_lawyer
from domain.entities import Role
from ai.postprocess import resolve_clause_id, resolve_jurisdiction_value
from ai.runtime import AIRuntime
from guardrails.errors import GuardrailViolation
from llm.prompts import CONTRACT_ANALYSIS_PROMPT_ID
from services.contract_service import ContractAccessError, ContractNotFoundError, ALLOWED_PERSPECTIVES

logger = logging.getLogger(__name__)

ANALYSIS_DOCUMENT_SCOPES = {"original", "lawyer_revision"}
DEFAULT_ANALYSIS_DOCUMENT_SCOPE = "original"
EDITED_ANALYSIS_DOCUMENT_SCOPE = "lawyer_revision"


class AnalysisNotFoundError(Exception):
    def __init__(self, message: str = "Analysis not found"):
        super().__init__(message)
        self.message = message


class AnalysisPipelineError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AnalysisReviewError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AnalysisService:
    """Orchestrates contract analysis pipeline and persistence."""

    def __init__(
        self,
        analysis_repository: AnalysisRepository | None = None,
        field_repository: ExtractedFieldRepository | None = None,
        clause_repository: ClauseRepository | None = None,
        finding_repository: FindingRepository | None = None,
        finding_review_repository: FindingReviewRepository | None = None,
        analysis_approval_repository: AnalysisApprovalRepository | None = None,
        contract_repository: ContractRepository | None = None,
        document_repository: ContractDocumentRepository | None = None,
        party_repository: ContractPartyRepository | None = None,
        settings: Settings | None = None,
        ai_runtime: AIRuntime | None = None,
    ):
        self._settings = settings or get_settings()
        self._ai = ai_runtime or AIRuntime(self._settings)
        self._analyses = analysis_repository or AnalysisRepository(self._settings)
        self._fields = field_repository or ExtractedFieldRepository(self._settings)
        self._clauses = clause_repository or ClauseRepository(self._settings)
        self._findings = finding_repository or FindingRepository(self._settings)
        self._finding_reviews = finding_review_repository or FindingReviewRepository(self._settings)
        self._approvals = analysis_approval_repository or AnalysisApprovalRepository(self._settings)
        self._contracts = contract_repository or ContractRepository(self._settings)
        self._documents = document_repository or ContractDocumentRepository(self._settings)
        self._parties = party_repository or ContractPartyRepository(self._settings)

    def start_analysis(
        self,
        current_user: dict,
        contract_id: str,
        perspective: str,
        *,
        document_scope: str = DEFAULT_ANALYSIS_DOCUMENT_SCOPE,
        run_async: bool | None = None,
    ) -> AnalysisDTO:
        """Create an analysis record and run the pipeline (sync or async)."""
        normalized_perspective = perspective.strip().lower()
        if normalized_perspective not in ALLOWED_PERSPECTIVES:
            raise AnalysisPipelineError(
                f"Invalid perspective. Allowed values: {', '.join(sorted(ALLOWED_PERSPECTIVES))}"
            )
        normalized_scope = (document_scope or DEFAULT_ANALYSIS_DOCUMENT_SCOPE).strip().lower()
        if normalized_scope not in ANALYSIS_DOCUMENT_SCOPES:
            raise AnalysisPipelineError(
                f"Invalid document scope. Allowed values: {', '.join(sorted(ANALYSIS_DOCUMENT_SCOPES))}"
            )
        if current_user["role"] == Role.LAWYER:
            raise ContractAccessError("Lawyers cannot start contract analyses")

        contract = self._get_accessible_contract(current_user, contract_id)
        documents = self._documents.list_by_contract(contract_id)
        if not documents:
            raise AnalysisPipelineError("Contract has no documents to analyze")

        if normalized_scope == EDITED_ANALYSIS_DOCUMENT_SCOPE:
            has_revision = any(doc.document_type == "lawyer_revision" for doc in documents)
            if not has_revision:
                raise AnalysisPipelineError(
                    "No lawyer-edited contract version is available to analyze."
                )

        existing = self._analyses.get_by_contract_perspective_scope(
            contract_id,
            normalized_perspective,
            normalized_scope,
        )
        if existing and existing.status in {
            "ai_generated",
            "pending_review",
            "reviewed",
            "approved",
            "processing",
        }:
            scope_label = (
                "edited contract"
                if normalized_scope == EDITED_ANALYSIS_DOCUMENT_SCOPE
                else "original contract"
            )
            raise AnalysisPipelineError(
                f"An analysis for perspective '{normalized_perspective}' on the {scope_label} already exists."
            )

        if existing and existing.status == "failed":
            analysis = self._analyses.reset_for_retry(existing.id)
            if analysis is None:
                raise AnalysisPipelineError("Could not retry failed analysis")
        else:
            analysis = self._analyses.create(
                contract_id=contract_id,
                perspective=normalized_perspective,
                document_scope=normalized_scope,
                status="processing",
            )

        use_async = self._settings.analysis_async if run_async is None else run_async
        if use_async:
            return analysis

        try:
            self._run_pipeline(
                analysis,
                normalized_perspective,
                contract.title,
                document_scope=normalized_scope,
            )
        except Exception as exc:
            logger.exception("Analysis pipeline failed for %s", analysis.id)
            self._analyses.update_status(analysis.id, "failed")
            raise AnalysisPipelineError(str(exc)) from exc

        return self.get_analysis(current_user, analysis.id)

    def run_pipeline_for_analysis(self, analysis_id: str) -> None:
        """Execute pipeline for an existing processing record (background task)."""
        analysis = self._analyses.get_by_id(analysis_id)
        if analysis is None:
            return
        contract = self._contracts.get_by_id(analysis.contract_id)
        if contract is None:
            self._analyses.update_status(analysis_id, "failed")
            return
        try:
            self._run_pipeline(
                analysis,
                analysis.perspective,
                contract.title,
                document_scope=analysis.document_scope,
            )
        except Exception:
            logger.exception("Background analysis failed for %s", analysis_id)
            self._analyses.update_status(analysis_id, "failed")

    def _run_pipeline(
        self,
        analysis: AnalysisDTO,
        perspective: str,
        title: str | None,
        *,
        document_scope: str = DEFAULT_ANALYSIS_DOCUMENT_SCOPE,
    ) -> None:
        contract_text = self._documents.get_extracted_text_for_analysis_scope(
            analysis.contract_id,
            document_scope,
        )
        if not contract_text.strip():
            raise AnalysisPipelineError("No extracted text available for analysis")

        try:
            result = self._ai.analyze_contract(
                contract_text=contract_text,
                perspective=perspective,
                title=title,
            )
        except GuardrailViolation as exc:
            raise AnalysisPipelineError(exc.user_message) from exc

        field_records = [
            ExtractedFieldDTO(
                field_name=item["field_name"],
                field_value=str(item.get("field_value", "")),
                confidence=float(item.get("confidence", 0.7)),
                source_page=item.get("source_page"),
                source_clause=item.get("source_clause"),
                source_section=item.get("source_section"),
                source_text_snippet=item.get("source_text_snippet"),
            )
            for item in result.extracted_fields
            if item.get("field_name") and item.get("field_value")
        ]
        self._fields.replace_for_analysis(analysis.id, field_records)
        saved_clauses = self._clauses.replace_for_analysis(analysis.id, result.clauses)

        def clause_resolver(finding: dict) -> str | None:
            return resolve_clause_id(finding, saved_clauses)

        self._findings.replace_for_analysis(
            analysis.id,
            result.findings,
            clause_id_resolver=clause_resolver,
        )

        self._parties.replace_for_contract(
            analysis.contract_id,
            [{"field_name": f.field_name, "field_value": f.field_value, "confidence": f.confidence}
             for f in field_records],
        )

        jurisdiction_value = resolve_jurisdiction_value(
            [{"field_name": f.field_name, "field_value": f.field_value} for f in field_records],
            result.findings,
        )
        if jurisdiction_value:
            self._contracts.update_jurisdiction(analysis.contract_id, jurisdiction_value)
        else:
            self._contracts.clear_jurisdiction(analysis.contract_id)

        general_risk = result.general_risk if result.general_risk in {"low", "medium", "high"} else "medium"
        self._analyses.update_completed(
            analysis_id=analysis.id,
            status="ai_generated",
            summary_executive=result.summary_executive,
            general_risk=general_risk,
        )

        response_path = self._persist_raw_response(analysis.id, result)
        prompt_id = result.prompt_id or CONTRACT_ANALYSIS_PROMPT_ID
        self._analyses.log_llm_run(
            analysis_id=analysis.id,
            provider=result.provider,
            model=result.model,
            tokens_input=result.tokens_input,
            tokens_output=result.tokens_output,
            duration_ms=result.duration_ms,
            prompt_id=prompt_id,
            model_version=result.model or prompt_id,
            response_storage_path=response_path,
        )
        if result.duration_ms and result.duration_ms > self._settings.analysis_sla_ms:
            logger.warning(
                "Analysis %s exceeded SLA (%sms > %sms)",
                analysis.id,
                result.duration_ms,
                self._settings.analysis_sla_ms,
            )

    def _persist_raw_response(self, analysis_id: str, result) -> str | None:
        content = result.raw_response
        if not content:
            content = json.dumps(
                {
                    "extracted_fields": result.extracted_fields,
                    "clauses_count": len(result.clauses),
                    "findings_count": len(result.findings),
                    "general_risk": result.general_risk,
                    "provider": result.provider,
                    "model": result.model,
                },
                ensure_ascii=False,
                indent=2,
            )
        storage_dir = self._settings.llm_responses_path()
        file_path = storage_dir / f"{analysis_id}.json"
        file_path.write_text(content, encoding="utf-8")
        return str(file_path)

    def list_analyses(self, current_user: dict, contract_id: str) -> List[AnalysisDTO]:
        self._get_accessible_contract(current_user, contract_id)
        return self._analyses.list_by_contract(contract_id)

    def promote_analyses_for_contract_review(self, contract_id: str) -> int:
        """Queue AI-generated analyses for lawyer review when a contract enters in_review."""
        return self._analyses.promote_ai_generated_to_pending_review(contract_id)

    def update_analysis_status(
        self,
        current_user: dict,
        analysis_id: str,
        status: str,
    ) -> AnalysisDTO:
        analysis = self._analyses.get_by_id(analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError()

        self._get_accessible_contract(current_user, analysis.contract_id)
        validate_analysis_status_value(status)
        assert_analysis_transition(current_user["role"], analysis.status, status)

        updated = self._analyses.update_status(analysis_id, status)
        if updated is None:
            raise AnalysisNotFoundError()
        return updated

    def review_finding(
        self,
        current_user: dict,
        analysis_id: str,
        finding_id: str,
        verdict: str,
        notes: str | None = None,
    ):
        self._ensure_lawyer(current_user)

        analysis = self._analyses.get_by_id(analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError()

        self._get_accessible_contract(current_user, analysis.contract_id)

        if analysis.status not in {"pending_review", "reviewed", "approved"}:
            raise AnalysisReviewError(
                "Findings can only be reviewed while the analysis is pending review or later"
            )

        normalized_verdict = verdict.strip().lower()
        if normalized_verdict not in VALID_VERDICTS:
            raise AnalysisReviewError(
                f"Invalid verdict. Allowed values: {', '.join(sorted(VALID_VERDICTS))}"
            )

        finding = self._findings.get_by_id(finding_id)
        if finding is None or finding.analysis_id != analysis_id:
            raise AnalysisReviewError("Finding not found for this analysis")

        review = self._finding_reviews.upsert(
            finding_id=finding_id,
            lawyer_id=current_user["user_id"],
            verdict=normalized_verdict,
            notes=notes,
        )

        if analysis.status == "pending_review":
            self._analyses.update_status(analysis_id, "reviewed")

        return review

    def approve_analysis(
        self,
        current_user: dict,
        analysis_id: str,
        notes: str | None = None,
    ):
        self._ensure_lawyer(current_user)

        analysis = self._analyses.get_by_id(analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError()

        self._get_accessible_contract(current_user, analysis.contract_id)

        if analysis.status == "approved" or self._approvals.get_by_analysis(analysis_id) is not None:
            raise AnalysisReviewError("Analysis has already been approved")

        if analysis.status not in {"reviewed", "pending_review"}:
            raise AnalysisReviewError(
                "Analysis must be reviewed before it can be formally approved"
            )

        if analysis.status == "pending_review":
            assert_analysis_transition(current_user["role"], analysis.status, "reviewed")
            self._analyses.update_status(analysis_id, "reviewed")

        assert_analysis_transition(current_user["role"], "reviewed", "approved")
        self._analyses.update_status(analysis_id, "approved")

        return self._approvals.create(
            analysis_id=analysis_id,
            lawyer_id=current_user["user_id"],
            notes=notes,
        )

    def get_analysis(self, current_user: dict, analysis_id: str) -> AnalysisDTO:
        analysis = self._analyses.get_by_id(analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError()
        self._get_accessible_contract(current_user, analysis.contract_id)
        analysis.extracted_fields = self._fields.list_by_analysis(analysis_id)
        analysis.clauses = self._clauses.list_by_analysis(analysis_id)
        analysis.findings = self._findings.list_by_analysis(analysis_id)
        analysis.llm_metadata = self._analyses.get_latest_llm_metadata(analysis_id)
        analysis.finding_reviews = self._finding_reviews.map_by_finding_for_analysis(analysis_id)
        analysis.approval = self._approvals.get_by_analysis(analysis_id)
        return analysis

    def get_analysis_status(self, current_user: dict, analysis_id: str) -> AnalysisDTO:
        analysis = self._analyses.get_by_id(analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError()
        self._get_accessible_contract(current_user, analysis.contract_id)
        return analysis

    def _get_accessible_contract(self, current_user: dict, contract_id: str):
        contract = self._contracts.get_by_id(contract_id)
        if contract is None:
            raise ContractNotFoundError()
        role = current_user["role"]
        if role == Role.LAWYER:
            if not is_visible_to_lawyer(contract.status):
                raise ContractAccessError("Contract is not available for legal review")
            return contract
        if contract.user_id != current_user["user_id"]:
            raise ContractAccessError()
        return contract

    @staticmethod
    def _ensure_lawyer(current_user: dict) -> None:
        if current_user["role"] != Role.LAWYER:
            raise ContractAccessError("Only lawyers can perform this action")
