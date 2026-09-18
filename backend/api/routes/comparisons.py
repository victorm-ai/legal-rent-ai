"""Contract comparison API (RF-59–RF-62)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.middleware.auth import require_auth
from services.comparison_service import ComparisonError, ComparisonService
from services.contract_service import ContractAccessError, ContractNotFoundError

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


class CompareContractsRequest(BaseModel):
    base_contract_id: str
    compare_contract_id: str


class ComparisonChangeResponse(BaseModel):
    id: str
    change_type: str
    category: str | None = None
    description: str | None = None
    old_value: str | None = None
    new_value: str | None = None


class ComparisonRowResponse(BaseModel):
    item_key: str
    item_type: str
    original_value: str | None = None
    new_value: str | None = None
    change_type: str
    difference: str


class ComparisonResponse(BaseModel):
    id: str
    base_contract_id: str
    compare_contract_id: str
    summary: str | None = None
    risk_delta: str | None = None
    created_at: str
    changes: List[ComparisonChangeResponse] = []
    rows: List[ComparisonRowResponse] = []


def _comparison_to_response(comparison, changes, rows) -> ComparisonResponse:
    return ComparisonResponse(
        id=comparison.id,
        base_contract_id=comparison.base_contract_id,
        compare_contract_id=comparison.compare_contract_id,
        summary=comparison.summary,
        risk_delta=comparison.risk_delta,
        created_at=comparison.created_at.isoformat(),
        changes=[
            ComparisonChangeResponse(
                id=change.id,
                change_type=change.change_type,
                category=change.category,
                description=change.description,
                old_value=change.old_value,
                new_value=change.new_value,
            )
            for change in changes
        ],
        rows=[
            ComparisonRowResponse(
                item_key=row["item_key"],
                item_type=row["item_type"],
                original_value=row.get("original_value"),
                new_value=row.get("new_value"),
                change_type=row["change_type"],
                difference=row["difference"],
            )
            for row in rows
        ],
    )


@router.post("", response_model=ComparisonResponse, status_code=201)
async def compare_contracts(
    body: CompareContractsRequest,
    current_user: dict = Depends(require_auth),
):
    service = ComparisonService()
    try:
        comparison, changes, rows = service.compare_contracts(
            current_user,
            body.base_contract_id,
            body.compare_contract_id,
        )
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except ComparisonError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc

    return _comparison_to_response(comparison, changes, rows)


@router.get("/{comparison_id}", response_model=ComparisonResponse)
async def get_comparison(
    comparison_id: str,
    current_user: dict = Depends(require_auth),
):
    service = ComparisonService()
    try:
        comparison, changes, rows = service.get_comparison(current_user, comparison_id)
    except ComparisonError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return _comparison_to_response(comparison, changes, rows)
