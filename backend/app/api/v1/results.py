import os
import shutil
import json
from typing import Optional, List
from fastapi import APIRouter, Query, Response, status, Depends
from fastapi.responses import JSONResponse
from ...schemas.result import AnalysisResult, HistoryResponse, HistoryItem
from ...schemas.evidence import Evidence
from ...services import orchestrator
from ...services.report_generator import generate_json_report, generate_pdf_report
from ...core.config import settings
from ...core.errors import AppException
from ...db import repository
from .mock_data import get_canned_result
from ...core.auth import require_role

router = APIRouter(dependencies=[Depends(require_role("investigator"))])

@router.get("/results/{result_id}", response_model=AnalysisResult)
async def get_analysis_result(result_id: str):
    if settings.MOCK_ANALYSIS and result_id.startswith("mock"):
        variant = "HIGH"
        if "LOW" in result_id.upper():
            variant = "LOW"
        elif "MED" in result_id.upper():
            variant = "MEDIUM"
        return get_canned_result(variant=variant, result_id=result_id)

    res = orchestrator.get_result(result_id)
    if not res:
        if settings.MOCK_ANALYSIS and result_id.startswith("mock"):
            return get_canned_result(variant="HIGH", result_id=result_id)
        raise AppException(
            code="RESULT_NOT_FOUND",
            message=f"Analysis result '{result_id}' not found.",
            status_code=404,
            details={"result_id": result_id}
        )
    return res


@router.get("/results/{result_id}/evidence", response_model=List[Evidence])
async def get_result_evidence(
    result_id: str,
    pipeline: Optional[str] = Query(None, description="Filter by pipeline (e.g. image, document, img_1, doc)"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high)"),
    kind: Optional[str] = Query(None, description="Filter by kind (risk, authenticity, info)")
):
    res = orchestrator.get_result(result_id)
    if not res:
        if settings.MOCK_ANALYSIS and result_id.startswith("mock"):
            res = get_canned_result(result_id=result_id)
        elif settings.MOCK_ANALYSIS:
            res = get_canned_result(result_id=result_id)
        else:
            raise AppException(
                code="RESULT_NOT_FOUND",
                message=f"Analysis result '{result_id}' not found.",
                status_code=404,
                details={"result_id": result_id}
            )

    filtered = res.evidence
    if pipeline:
        filtered = [
            e for e in filtered
            if (e.pipeline_input and e.pipeline_input.lower() == pipeline.lower())
            or (e.id.lower().startswith(pipeline.lower()))
            or (pipeline.lower() == "image" and e.id.startswith("IMG"))
            or (pipeline.lower() == "document" and e.id.startswith("DOC"))
        ]
    if severity:
        filtered = [e for e in filtered if e.severity.lower() == severity.lower()]
    if kind:
        filtered = [e for e in filtered if e.kind.lower() == kind.lower()]

    return filtered


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mode: Optional[str] = Query(None),
    band: Optional[str] = Query(None)
):
    items_data, total = repository.list_history(page=page, page_size=page_size, mode=mode, band=band)
    items = [HistoryItem(**item) for item in items_data]
    return HistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.delete("/results/{result_id}", status_code=204)
async def delete_analysis_result(result_id: str):
    # Remove from fast cache; track if it was there
    was_in_memory = result_id in orchestrator.RESULTS_DB
    if was_in_memory:
        del orchestrator.RESULTS_DB[result_id]

    deleted = repository.delete_result(result_id)
    art_dir = os.path.join(orchestrator.BASE_ARTIFACTS_DIR, result_id)
    if os.path.exists(art_dir):
        shutil.rmtree(art_dir, ignore_errors=True)

    if not deleted and not was_in_memory:
        # Check if in mock mode
        if settings.MOCK_ANALYSIS and result_id.startswith("mock"):
            return Response(status_code=204)
        raise AppException(
            code="RESULT_NOT_FOUND",
            message=f"Result '{result_id}' not found to delete.",
            status_code=404,
            details={"result_id": result_id}
        )
    return Response(status_code=204)


@router.get("/results/{result_id}/report.json")
async def get_json_report(result_id: str):
    res = orchestrator.get_result(result_id)
    if not res:
        if settings.MOCK_ANALYSIS and result_id.startswith("mock"):
            res = get_canned_result(result_id=result_id)
        else:
            raise AppException(
                code="RESULT_NOT_FOUND",
                message=f"Analysis result '{result_id}' not found.",
                status_code=404,
                details={"result_id": result_id}
            )

    report_dict = generate_json_report(res)
    return report_dict


@router.get("/results/{result_id}/report.pdf")
async def get_pdf_report(result_id: str):
    res = orchestrator.get_result(result_id)
    if not res:
        if settings.MOCK_ANALYSIS and result_id.startswith("mock"):
            res = get_canned_result(result_id=result_id)
        else:
            raise AppException(
                code="RESULT_NOT_FOUND",
                message=f"Analysis result '{result_id}' not found.",
                status_code=404,
                details={"result_id": result_id}
            )

    pdf_bytes = generate_pdf_report(res)
    headers = {
        "Content-Disposition": f'attachment; filename="lucen_report_{result_id}.pdf"',
        "Content-Type": "application/pdf"
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.get("/results/{result_id}/timeline")
async def get_result_timeline(result_id: str):
    """
    Returns the chronological evidence timeline (§14.5) with contradictions and undated items.
    """
    res = orchestrator.get_result(result_id)
    if not res:
        if settings.MOCK_ANALYSIS and result_id.startswith("mock"):
            res = get_canned_result(result_id=result_id)
        else:
            raise AppException(
                code="RESULT_NOT_FOUND",
                message=f"Analysis result '{result_id}' not found.",
                status_code=404,
                details={"result_id": result_id}
            )

    from ...services.timeline import build_result_timeline
    return build_result_timeline(result_id, res)
