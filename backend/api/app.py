"""
Main FastAPI application for the contract analyzer.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from api.routes import create_router
from config.settings import get_settings
from app_logging.setup import configure_logging

configure_logging()


app = FastAPI(
    title="Legal Rent AI - Contract Analyzer MVP",
    description="API for lease contract analysis in Mexico",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "legal-rent-ai-api",
        "version": "0.1.0",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc),
        },
    )


app.include_router(create_router())


def _request_is_https(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    forwarded = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    return forwarded == "https"


@app.middleware("http")
async def optional_https_redirect(request: Request, call_next):
    settings = get_settings()
    if settings.force_https and not _request_is_https(request):
        url = request.url.replace(scheme="https")
        return RedirectResponse(url=str(url), status_code=307)
    return await call_next(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
