"""Report routes (RF-46–RF-49)."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from api.middleware.auth import require_auth
from api.schemas.delivery import GenerateReportRequest, ReportResponse
from services.analysis_service import AnalysisNotFoundError
from services.contract_service import ContractAccessError, ContractNotFoundError
from services.report_service import ReportNotFoundError, ReportService

router = APIRouter(tags=["reports"])


def _to_response(report) -> ReportResponse:
    return ReportResponse(
        id=report.id,
        analysis_id=report.analysis_id,
        format=report.format,
        generated_by=report.generated_by,
        generated_at=report.generated_at,
    )


@router.post("/analyses/{analysis_id}/reports", response_model=ReportResponse, status_code=201)
async def generate_report(
    analysis_id: str,
    body: GenerateReportRequest,
    current_user: dict = Depends(require_auth),
):
    service = ReportService()
    try:
        report = service.generate_report(current_user, analysis_id, body.format)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_response(report)


@router.get("/analyses/{analysis_id}/reports", response_model=List[ReportResponse])
async def list_reports(
    analysis_id: str,
    current_user: dict = Depends(require_auth),
):
    service = ReportService()
    try:
        reports = service.list_reports(current_user, analysis_id)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    return [_to_response(report) for report in reports]


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    current_user: dict = Depends(require_auth),
):
    service = ReportService()
    try:
        path, media_type, filename = service.get_report_file(current_user, report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return FileResponse(path, media_type=media_type, filename=filename)
