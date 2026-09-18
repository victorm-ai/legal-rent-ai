"""Admin endpoints (RF-70)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import require_lawyer
from data.repositories.analysis_approval_repository import AnalysisApprovalRepository
from data.repositories.finding_review_repository import FindingReviewRepository
from config.settings import get_settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/feedback/export")
async def export_lawyer_feedback(_current_user: dict = Depends(require_lawyer)):
    """Export lawyer reviews and approvals for future model improvement (RF-70)."""
    settings = get_settings()
    reviews_repo = FindingReviewRepository(settings)
    approvals_repo = AnalysisApprovalRepository(settings)
    reviews = reviews_repo.list_all()
    approvals = approvals_repo.list_all()
    return {
        "finding_reviews": reviews,
        "analysis_approvals": approvals,
        "total_reviews": len(reviews),
        "total_approvals": len(approvals),
    }
