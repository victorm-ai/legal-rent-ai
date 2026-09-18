"""Contract comparison business logic (RF-59–RF-62)."""

from __future__ import annotations

from difflib import unified_diff

from config.settings import Settings, get_settings
from data.repositories.analysis_repository import AnalysisRepository
from data.repositories.clause_repository import ClauseRepository
from data.repositories.comparison_repository import ComparisonDTO, ComparisonRepository
from data.repositories.contract_repository import ContractRepository
from data.repositories.extracted_field_repository import ExtractedFieldRepository
from domain.contract_status import is_visible_to_lawyer
from domain.entities import Role
from services.contract_service import ContractAccessError, ContractNotFoundError

DEFAULT_ANALYSIS_DOCUMENT_SCOPE = "original"
EDITED_ANALYSIS_DOCUMENT_SCOPE = "lawyer_revision"


class ComparisonError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


_RISK_ORDINAL = {"low": 1, "medium": 2, "high": 3}


class ComparisonService:
    def __init__(
        self,
        comparison_repository: ComparisonRepository | None = None,
        contract_repository: ContractRepository | None = None,
        analysis_repository: AnalysisRepository | None = None,
        field_repository: ExtractedFieldRepository | None = None,
        clause_repository: ClauseRepository | None = None,
        settings: Settings | None = None,
    ):
        self._settings = settings or get_settings()
        self._comparisons = comparison_repository or ComparisonRepository(self._settings)
        self._contracts = contract_repository or ContractRepository(self._settings)
        self._analyses = analysis_repository or AnalysisRepository(self._settings)
        self._fields = field_repository or ExtractedFieldRepository(self._settings)
        self._clauses = clause_repository or ClauseRepository(self._settings)

    def compare_contracts(
        self,
        current_user: dict,
        base_contract_id: str,
        compare_contract_id: str,
    ) -> tuple[ComparisonDTO, list, list]:
        if base_contract_id == compare_contract_id:
            raise ComparisonError("Cannot compare a contract with itself")

        base = self._get_accessible_contract(current_user, base_contract_id)
        compare = self._get_accessible_contract(current_user, compare_contract_id)

        base_analysis = self._latest_completed_analysis(
            base_contract_id,
            base.perspective,
            DEFAULT_ANALYSIS_DOCUMENT_SCOPE,
        )
        compare_analysis = self._latest_completed_analysis(
            compare_contract_id,
            compare.perspective,
            DEFAULT_ANALYSIS_DOCUMENT_SCOPE,
        )
        if base_analysis is None or compare_analysis is None:
            raise ComparisonError(
                "Both contracts require a completed analysis for their upload perspective"
            )

        base_fields = {f.field_name: f.field_value for f in self._fields.list_by_analysis(base_analysis.id)}
        compare_fields = {
            f.field_name: f.field_value for f in self._fields.list_by_analysis(compare_analysis.id)
        }
        base_clauses = self._clauses.list_by_analysis(base_analysis.id)
        compare_clauses = self._clauses.list_by_analysis(compare_analysis.id)

        changes: list[dict] = []
        changes.extend(self._diff_fields(base_fields, compare_fields))
        changes.extend(self._diff_clauses(base_clauses, compare_clauses))

        risk_delta = self._compute_risk_delta(base_analysis.general_risk, compare_analysis.general_risk)
        summary = (
            f"Compared '{base.title or base_contract_id}' vs '{compare.title or compare_contract_id}': "
            f"{len(changes)} change(s) detected. Risk delta: {risk_delta or 'unchanged'}."
        )

        comparison = self._comparisons.create(
            base_contract_id=base_contract_id,
            compare_contract_id=compare_contract_id,
            created_by=current_user["user_id"],
            summary=summary,
            risk_delta=risk_delta,
            changes=changes,
        )
        rows = self._build_comparison_rows(base_fields, compare_fields, base_clauses, compare_clauses)
        persisted_changes = self._comparisons.list_changes(comparison.id)
        return comparison, persisted_changes, rows

    def compare_edited_revision(self, current_user: dict, contract_id: str) -> tuple[ComparisonDTO, list, list]:
        """Compare original vs lawyer-edited analyses for the same contract."""
        contract = self._get_accessible_contract(current_user, contract_id)
        base_analysis = self._latest_completed_analysis(
            contract_id,
            contract.perspective,
            DEFAULT_ANALYSIS_DOCUMENT_SCOPE,
        )
        if base_analysis is None:
            raise ComparisonError(
                "El contrato original debe estar analizado antes de comparar la versión editada."
            )

        compare_analysis = self._latest_completed_analysis(
            contract_id,
            contract.perspective,
            EDITED_ANALYSIS_DOCUMENT_SCOPE,
        )
        if compare_analysis is None:
            raise ComparisonError(
                "La versión editada aún no tiene análisis. Ejecute la comparación de nuevo tras completarlo."
            )

        return self._compare_analyses_for_contract(
            current_user=current_user,
            contract_id=contract_id,
            contract_title=contract.title,
            base_analysis=base_analysis,
            compare_analysis=compare_analysis,
            summary_prefix="Comparación contrato original vs versión editada",
        )

    def get_revision_comparison_context(self, contract_id: str) -> dict | None:
        """Return comparison table rows for LLM/chat context (same contract revision)."""
        comparison = self._comparisons.get_latest_self_comparison(contract_id)
        if comparison is None:
            return None
        rows = self._revision_comparison_rows(contract_id)
        return {
            "summary": comparison.summary,
            "risk_delta": comparison.risk_delta,
            "rows": [
                {
                    "item_key": row["item_key"],
                    "item_type": row["item_type"],
                    "original_value": row.get("original_value"),
                    "new_value": row.get("new_value"),
                    "difference": row.get("difference"),
                    "change_type": row.get("change_type"),
                }
                for row in rows
            ],
        }

    def get_latest_revision_comparison(
        self,
        current_user: dict,
        contract_id: str,
    ) -> tuple[ComparisonDTO, list, list] | None:
        self._get_accessible_contract(current_user, contract_id)
        comparison = self._comparisons.get_latest_self_comparison(contract_id)
        if comparison is None:
            return None
        changes = self._comparisons.list_changes(comparison.id)
        rows = self._revision_comparison_rows(contract_id)
        return comparison, changes, rows

    def get_comparison(self, current_user: dict, comparison_id: str) -> tuple[ComparisonDTO, list, list]:
        comparison = self._comparisons.get_by_id(comparison_id)
        if comparison is None:
            raise ComparisonError("Comparison not found")
        self._get_accessible_contract(current_user, comparison.base_contract_id)
        self._get_accessible_contract(current_user, comparison.compare_contract_id)
        changes = self._comparisons.list_changes(comparison_id)
        if comparison.base_contract_id == comparison.compare_contract_id:
            rows = self._revision_comparison_rows(comparison.base_contract_id)
        else:
            rows = self._rows_from_changes(changes)
        return comparison, changes, rows

    def _revision_comparison_rows(self, contract_id: str) -> list[dict]:
        contract = self._contracts.get_by_id(contract_id)
        if contract is None:
            return []
        base_analysis = self._latest_completed_analysis(
            contract_id,
            contract.perspective,
            DEFAULT_ANALYSIS_DOCUMENT_SCOPE,
        )
        compare_analysis = self._latest_completed_analysis(
            contract_id,
            contract.perspective,
            EDITED_ANALYSIS_DOCUMENT_SCOPE,
        )
        if base_analysis is None or compare_analysis is None:
            return []
        base_fields = {
            field.field_name: field.field_value for field in self._fields.list_by_analysis(base_analysis.id)
        }
        compare_fields = {
            field.field_name: field.field_value for field in self._fields.list_by_analysis(compare_analysis.id)
        }
        base_clauses = self._clauses.list_by_analysis(base_analysis.id)
        compare_clauses = self._clauses.list_by_analysis(compare_analysis.id)
        return self._build_comparison_rows(base_fields, compare_fields, base_clauses, compare_clauses)

    def _compare_analyses_for_contract(
        self,
        *,
        current_user: dict,
        contract_id: str,
        contract_title: str | None,
        base_analysis,
        compare_analysis,
        summary_prefix: str,
    ) -> tuple[ComparisonDTO, list, list]:
        base_fields = {
            field.field_name: field.field_value for field in self._fields.list_by_analysis(base_analysis.id)
        }
        compare_fields = {
            field.field_name: field.field_value for field in self._fields.list_by_analysis(compare_analysis.id)
        }
        base_clauses = self._clauses.list_by_analysis(base_analysis.id)
        compare_clauses = self._clauses.list_by_analysis(compare_analysis.id)

        changes: list[dict] = []
        changes.extend(self._diff_fields(base_fields, compare_fields))
        changes.extend(self._diff_clauses(base_clauses, compare_clauses))

        risk_delta = self._compute_risk_delta(base_analysis.general_risk, compare_analysis.general_risk)
        label = contract_title or contract_id
        summary = (
            f"{summary_prefix} '{label}': {len(changes)} cambio(s) detectado(s). "
            f"Delta de riesgo: {risk_delta or 'sin cambio'}."
        )

        comparison = self._comparisons.create(
            base_contract_id=contract_id,
            compare_contract_id=contract_id,
            created_by=current_user["user_id"],
            summary=summary,
            risk_delta=risk_delta,
            changes=changes,
        )
        rows = self._build_comparison_rows(base_fields, compare_fields, base_clauses, compare_clauses)
        persisted_changes = self._comparisons.list_changes(comparison.id)
        return comparison, persisted_changes, rows

    def _latest_completed_analysis(
        self,
        contract_id: str,
        perspective: str,
        document_scope: str = DEFAULT_ANALYSIS_DOCUMENT_SCOPE,
    ):
        analyses = self._analyses.list_by_contract(contract_id)
        completed = [
            analysis
            for analysis in analyses
            if analysis.perspective == perspective
            and (analysis.document_scope or DEFAULT_ANALYSIS_DOCUMENT_SCOPE) == document_scope
            and analysis.status in {"ai_generated", "pending_review", "reviewed", "approved"}
        ]
        return completed[0] if completed else None

    @staticmethod
    def _field_change_type(old: str | None, new: str | None) -> str:
        if old == new:
            return "unchanged"
        if old is None:
            return "added"
        if new is None:
            return "removed"
        return "modified"

    @staticmethod
    def _difference_summary(old: str | None, new: str | None) -> str:
        change_type = ComparisonService._field_change_type(old, new)
        if change_type == "unchanged":
            return "Sin cambio"
        if change_type == "added":
            return "Agregado en la versión editada"
        if change_type == "removed":
            return "Eliminado en la versión editada"
        return "Modificado"

    @classmethod
    def _build_comparison_rows(
        cls,
        base_fields: dict[str, str],
        compare_fields: dict[str, str],
        base_clauses,
        compare_clauses,
    ) -> list[dict]:
        rows: list[dict] = []
        for key in sorted(set(base_fields) | set(compare_fields)):
            old = base_fields.get(key)
            new = compare_fields.get(key)
            rows.append(
                {
                    "item_key": key,
                    "item_type": "field",
                    "original_value": old,
                    "new_value": new,
                    "change_type": cls._field_change_type(old, new),
                    "difference": cls._difference_summary(old, new),
                }
            )

        base_by_cat = {clause.category: clause for clause in base_clauses}
        compare_by_cat = {clause.category: clause for clause in compare_clauses}
        for category in sorted(set(base_by_cat) | set(compare_by_cat)):
            base_clause = base_by_cat.get(category)
            compare_clause = compare_by_cat.get(category)
            old = base_clause.text if base_clause else None
            new = compare_clause.text if compare_clause else None
            rows.append(
                {
                    "item_key": category,
                    "item_type": "clause",
                    "original_value": old,
                    "new_value": new,
                    "change_type": cls._field_change_type(old, new),
                    "difference": cls._difference_summary(old, new),
                }
            )
        return rows

    @staticmethod
    def _rows_from_changes(changes: list) -> list[dict]:
        rows: list[dict] = []
        for change in changes:
            category = change.category or "item"
            item_type = "clause" if category in {
                "object",
                "rent",
                "deposit",
                "term",
                "maintenance",
                "services",
                "sublease",
                "guarantees",
                "insurance",
                "renewal",
                "termination",
                "penalties",
                "liability",
                "jurisdiction",
                "other",
            } else "field"
            rows.append(
                {
                    "item_key": category,
                    "item_type": item_type,
                    "original_value": change.old_value,
                    "new_value": change.new_value,
                    "change_type": change.change_type,
                    "difference": ComparisonService._difference_summary(change.old_value, change.new_value),
                }
            )
        return rows

    @staticmethod
    def _diff_fields(base: dict, compare: dict) -> list[dict]:
        changes: list[dict] = []
        all_keys = sorted(set(base) | set(compare))
        for key in all_keys:
            old = base.get(key)
            new = compare.get(key)
            if old == new:
                continue
            if old is None:
                changes.append(
                    {
                        "change_type": "added",
                        "category": key,
                        "description": f"Field '{key}' added in compare version",
                        "old_value": None,
                        "new_value": new,
                    }
                )
            elif new is None:
                changes.append(
                    {
                        "change_type": "removed",
                        "category": key,
                        "description": f"Field '{key}' removed in compare version",
                        "old_value": old,
                        "new_value": None,
                    }
                )
            else:
                changes.append(
                    {
                        "change_type": "modified",
                        "category": key,
                        "description": f"Field '{key}' changed",
                        "old_value": old,
                        "new_value": new,
                    }
                )
        return changes

    @staticmethod
    def _diff_clauses(base_clauses, compare_clauses) -> list[dict]:
        changes: list[dict] = []
        base_by_cat = {c.category: c for c in base_clauses}
        compare_by_cat = {c.category: c for c in compare_clauses}
        all_cats = sorted(set(base_by_cat) | set(compare_by_cat))
        for category in all_cats:
            base_clause = base_by_cat.get(category)
            compare_clause = compare_by_cat.get(category)
            if base_clause is None and compare_clause is not None:
                changes.append(
                    {
                        "change_type": "added",
                        "category": category,
                        "description": f"Clause category '{category}' added",
                        "old_value": None,
                        "new_value": compare_clause.text[:500],
                    }
                )
            elif compare_clause is None and base_clause is not None:
                changes.append(
                    {
                        "change_type": "removed",
                        "category": category,
                        "description": f"Clause category '{category}' removed",
                        "old_value": base_clause.text[:500],
                        "new_value": None,
                    }
                )
            elif base_clause and compare_clause:
                if base_clause.text.strip() != compare_clause.text.strip():
                    diff_lines = list(
                        unified_diff(
                            base_clause.text.splitlines(),
                            compare_clause.text.splitlines(),
                            lineterm="",
                        )
                    )
                    changes.append(
                        {
                            "change_type": "modified",
                            "category": category,
                            "description": f"Clause '{category}' text changed",
                            "old_value": base_clause.text[:500],
                            "new_value": compare_clause.text[:500],
                        }
                    )
                    if diff_lines:
                        changes[-1]["description"] += f" ({len(diff_lines)} diff lines)"
        return changes

    @staticmethod
    def _compute_risk_delta(base_risk: str | None, compare_risk: str | None) -> str | None:
        if not base_risk or not compare_risk:
            return None
        base_ord = _RISK_ORDINAL.get(base_risk, 2)
        compare_ord = _RISK_ORDINAL.get(compare_risk, 2)
        if compare_ord > base_ord:
            return "high"
        if compare_ord < base_ord:
            return "low"
        return "medium"

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
