"""Report generation business logic (RF-46–RF-49)."""

from __future__ import annotations

import json
from pathlib import Path

from config.settings import Settings, get_settings
from data.delivery_dto import ReportDTO
from data.repositories.download_log_repository import DownloadLogRepository
from data.repositories.report_repository import ReportRepository
from domain.entities import Role
from report.pdf_generator import generate_pdf_report
from services.analysis_service import AnalysisNotFoundError, AnalysisService
from services.contract_service import ContractAccessError, ContractNotFoundError


class ReportNotFoundError(Exception):
    def __init__(self, message: str = "Report not found"):
        super().__init__(message)
        self.message = message


class ReportService:
    def __init__(
        self,
        analysis_service: AnalysisService | None = None,
        report_repository: ReportRepository | None = None,
        download_log_repository: DownloadLogRepository | None = None,
        settings: Settings | None = None,
    ):
        self._settings = settings or get_settings()
        self._analysis = analysis_service or AnalysisService(settings=self._settings)
        self._reports = report_repository or ReportRepository(self._settings)
        self._downloads = download_log_repository or DownloadLogRepository(self._settings)

    def generate_report(
        self,
        current_user: dict,
        analysis_id: str,
        format: str,
    ) -> ReportDTO:
        if format not in {"pdf", "json"}:
            raise ValueError("format must be pdf or json")

        analysis = self._analysis.get_analysis(current_user, analysis_id)
        if analysis.status not in {"ai_generated", "pending_review", "reviewed", "approved"}:
            raise ValueError("Analysis is not ready for reporting")

        contract = self._analysis._contracts.get_by_id(analysis.contract_id)
        payload = self._build_payload(analysis, contract.title if contract else None)

        storage_dir = self._settings.reports_path() / analysis_id
        storage_dir.mkdir(parents=True, exist_ok=True)

        if format == "json":
            file_name = f"report-{analysis_id}.json"
            file_path = storage_dir / file_name
            file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            file_name = f"report-{analysis_id}.pdf"
            file_path = storage_dir / file_name
            generate_pdf_report(payload, file_path)

        return self._reports.create(
            analysis_id=analysis_id,
            format=format,
            storage_path=str(file_path),
            generated_by=current_user["user_id"],
        )

    def list_reports(self, current_user: dict, analysis_id: str) -> list[ReportDTO]:
        self._analysis.get_analysis(current_user, analysis_id)
        return self._reports.list_by_analysis(analysis_id)

    def get_report_file(
        self,
        current_user: dict,
        report_id: str,
    ) -> tuple[Path, str, str]:
        report = self._reports.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError()

        self._analysis.get_analysis(current_user, report.analysis_id)

        path = Path(report.storage_path)
        if not path.exists():
            raise ReportNotFoundError("Report file missing on disk")

        self._downloads.log_download(current_user["user_id"], "report", report_id)

        media = "application/pdf" if report.format == "pdf" else "application/json"
        filename = path.name
        return path, media, filename

    @staticmethod
    def _build_payload(analysis, contract_title: str | None) -> dict:
        extracted = {
            field.field_name: {
                "value": field.field_value,
                "confidence": field.confidence,
                "requires_review": field.requires_review,
                "source": {
                    "page": field.source_page,
                    "clause": field.source_clause,
                    "section": field.source_section,
                    "text_snippet": field.source_text_snippet,
                }
                if any(
                    [
                        field.source_page,
                        field.source_clause,
                        field.source_section,
                        field.source_text_snippet,
                    ]
                )
                else None,
            }
            for field in analysis.extracted_fields
        }
        findings = [
            {
                "id": f.id,
                "finding_type": f.finding_type,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "recommendation": f.recommendation,
                "suggested_rewording": f.suggested_rewording,
                "evidence_text": f.evidence_text,
                "evidence_page": f.evidence_page,
                "source_law": f.source_law,
                "legal_basis": f.legal_basis,
                "legal_citations": [
                    {
                        "law_code": c.law_code,
                        "article": c.article,
                        "excerpt": c.excerpt,
                    }
                    for c in f.legal_citations
                ],
            }
            for f in analysis.findings
        ]
        clauses = [
            {
                "id": c.id,
                "category": c.category,
                "section": c.section,
                "page": c.page,
                "text": c.text[:500],
            }
            for c in analysis.clauses
        ]
        return {
            "meta": {
                "analysis_id": analysis.id,
                "contract_id": analysis.contract_id,
                "contract_title": contract_title,
                "general_risk": analysis.general_risk,
                "status": analysis.status,
                "generated_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
            },
            "summary_executive": analysis.summary_executive,
            "extracted_data": extracted,
            "findings": findings,
            "clauses": clauses,
            "llm_metadata": analysis.llm_metadata,
        }
