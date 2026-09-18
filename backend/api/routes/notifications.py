"""Notification routes (RF-50, RF-51)."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import require_auth
from api.schemas.delivery import NotificationResponse, NotifyLawyerRequest
from services.analysis_service import AnalysisNotFoundError
from services.contract_service import ContractAccessError
from services.notification_service import NotificationError, NotificationService

router = APIRouter(tags=["notifications"])


def _to_response(item) -> NotificationResponse:
    return NotificationResponse(
        id=item.id,
        analysis_id=item.analysis_id,
        lawyer_email=item.lawyer_email,
        decision=item.decision,
        status=item.status,
        sent_at=item.sent_at,
        created_at=item.created_at,
    )


@router.post(
    "/analyses/{analysis_id}/notifications",
    response_model=NotificationResponse,
    status_code=201,
)
async def notify_lawyer(
    analysis_id: str,
    body: NotifyLawyerRequest,
    current_user: dict = Depends(require_auth),
):
    service = NotificationService()
    try:
        notification = service.notify_lawyer(
            current_user,
            analysis_id,
            body.lawyer_email,
            body.decision,
        )
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except NotificationError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    return _to_response(notification)


@router.get("/analyses/{analysis_id}/notifications", response_model=List[NotificationResponse])
async def list_notifications(
    analysis_id: str,
    current_user: dict = Depends(require_auth),
):
    service = NotificationService()
    try:
        items = service.list_notifications(current_user, analysis_id)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    return [_to_response(item) for item in items]
