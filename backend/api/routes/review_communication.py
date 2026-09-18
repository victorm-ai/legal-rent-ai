"""Client–lawyer review communication routes (RF-50, RF-51)."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import require_auth
from api.schemas.delivery import ReviewMessageResponse, SendReviewMessageRequest
from services.analysis_service import AnalysisNotFoundError
from services.contract_service import ContractAccessError
from services.review_communication_service import (
    ReviewCommunicationError,
    ReviewCommunicationService,
)

router = APIRouter(tags=["review-communication"])


def _to_response(item) -> ReviewMessageResponse:
    return ReviewMessageResponse(
        id=item.id,
        analysis_id=item.analysis_id,
        user_id=item.user_id,
        author_name=item.author_name,
        author_email=item.author_email,
        author_role=item.author_role,
        content=item.content,
        created_at=item.created_at,
    )


@router.post(
    "/analyses/{analysis_id}/review-messages",
    response_model=ReviewMessageResponse,
    status_code=201,
)
async def send_review_message(
    analysis_id: str,
    body: SendReviewMessageRequest,
    current_user: dict = Depends(require_auth),
):
    service = ReviewCommunicationService()
    try:
        message = service.send_message(current_user, analysis_id, body.content)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except ReviewCommunicationError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    return _to_response(message)


@router.get(
    "/analyses/{analysis_id}/review-messages",
    response_model=List[ReviewMessageResponse],
)
async def list_review_messages(
    analysis_id: str,
    current_user: dict = Depends(require_auth),
):
    service = ReviewCommunicationService()
    try:
        items = service.list_messages(current_user, analysis_id)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    return [_to_response(item) for item in items]
