"""
API route registration.
"""

from fastapi import APIRouter

from api.routes.auth import router as auth_router
from api.routes.contracts import router as contracts_router
from api.routes.analyses import router as analyses_router
from api.routes.reports import router as reports_router
from api.routes.review_communication import router as review_communication_router
from api.routes.chat import router as chat_router
from api.routes.comparisons import router as comparisons_router
from api.routes.admin import router as admin_router
from api.routes.notifications import router as notifications_router
from api.routes.signing_schedule import router as signing_schedule_router


def create_router() -> APIRouter:
    """Create the main API router with all route modules."""
    router = APIRouter()
    router.include_router(auth_router)
    router.include_router(contracts_router)
    router.include_router(analyses_router)
    router.include_router(reports_router)
    router.include_router(review_communication_router)
    router.include_router(chat_router)
    router.include_router(comparisons_router)
    router.include_router(admin_router)
    router.include_router(notifications_router)
    router.include_router(signing_schedule_router)
    return router
