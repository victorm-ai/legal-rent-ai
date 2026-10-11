"""Public signing-schedule endpoints (JWT in query, no SPA login)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from auth.signing_schedule_token import SigningScheduleTokenService
from config.settings import get_settings
from data.repositories.contract_repository import ContractRepository
from domain.contract_status import is_contract_locked
from scheduling.availability import (
    DEFAULT_CLOSE_HOUR,
    DEFAULT_OPEN_HOUR,
    MEXICO_CITY,
    generate_signing_schedule_by_date,
)

router = APIRouter(prefix="/public/signing-schedule", tags=["signing-schedule"])


class SigningScheduleContextResponse(BaseModel):
    contract_id: str
    contract_title: str | None
    status: str
    timezone: str = "America/Mexico_City"
    slot_minutes: int
    open_hour: int
    close_hour: int
    days_ahead: int
    bookable_dates: list[str]
    slots_by_date: dict[str, list[str]]


class ConfirmSigningSlotRequest(BaseModel):
    slot_label: str = Field(min_length=3, max_length=200)


class ConfirmSigningSlotResponse(BaseModel):
    status: str
    slot_label: str
    message: str


def _verify_token(token: str) -> dict:
    payload = SigningScheduleTokenService().verify(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired scheduling token")
    return payload


@router.get("", response_model=SigningScheduleContextResponse)
async def get_signing_schedule_context(token: str = Query(..., min_length=10)):
    """Return contract metadata and simulated availability for the scheduling UI."""
    payload = _verify_token(token)
    contract_id = payload["contract_id"]
    settings = get_settings()
    contracts = ContractRepository(settings)
    contract = contracts.get_by_id(contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.user_id != payload["client_user_id"]:
        raise HTTPException(status_code=403, detail="Token does not match contract owner")
    if not is_contract_locked(contract.status):
        raise HTTPException(
            status_code=409,
            detail="Scheduling is available only after administrative closure",
        )

    slots_by_date = generate_signing_schedule_by_date(
        days_ahead=settings.signing_schedule_days_ahead,
        slot_minutes=settings.signing_schedule_slot_minutes,
        open_hour=DEFAULT_OPEN_HOUR,
        close_hour=DEFAULT_CLOSE_HOUR,
    )
    return SigningScheduleContextResponse(
        contract_id=contract_id,
        contract_title=contract.title,
        status=contract.status,
        timezone=str(MEXICO_CITY),
        slot_minutes=settings.signing_schedule_slot_minutes,
        open_hour=DEFAULT_OPEN_HOUR,
        close_hour=DEFAULT_CLOSE_HOUR,
        days_ahead=settings.signing_schedule_days_ahead,
        bookable_dates=sorted(slots_by_date.keys()),
        slots_by_date=slots_by_date,
    )


@router.post("/confirm", response_model=ConfirmSigningSlotResponse)
async def confirm_signing_slot(
    payload: ConfirmSigningSlotRequest,
    token: str = Query(..., min_length=10),
):
    """Simulate booking a slot (no persistence)."""
    ctx = _verify_token(token)
    contract = ContractRepository(get_settings()).get_by_id(ctx["contract_id"])
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.user_id != ctx["client_user_id"]:
        raise HTTPException(status_code=403, detail="Token does not match contract owner")
    if not is_contract_locked(contract.status):
        raise HTTPException(status_code=409, detail="Contract is not closed yet")

    return ConfirmSigningSlotResponse(
        status="confirmed",
        slot_label=payload.slot_label,
        message=(
            "Time slot recorded (simulated). Your lawyer will confirm the appointment "
            "for signing with the landlord."
        ),
    )
