"""
Network & Fraud Ring API Endpoints (§14.3, Prompt 10).
All endpoints investigator-only under /api/v1/network.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from ...core.auth import require_role
from ...services import network
from ...services.report_generator import generate_ring_report_pdf, generate_ring_report_json

router = APIRouter(prefix="/network", tags=["Network"])
_INVESTIGATOR = Depends(require_role("investigator"))


class StatusUpdateRequest(BaseModel):
    status: str
    note: Optional[str] = None


@router.get("/graph")
def get_graph(
    focus_type: Optional[str] = Query(None, pattern="^(claim|claimant|ring)$"),
    focus_id: Optional[str] = Query(None),
    hops: int = Query(2, ge=1, le=4),
    min_strength: float = Query(0.3, ge=0.0, le=1.0),
    limit: int = Query(300, ge=10, le=1000),
    user: Dict[str, Any] = _INVESTIGATOR
):
    """
    Returns graph nodes and edges for visualization.
    If no focus is provided, returns top rings overview.
    """
    return network.get_network_subgraph(
        focus_type=focus_type,
        focus_id=focus_id,
        hops=hops,
        min_strength=min_strength,
        limit=limit
    )


@router.get("/rings")
def list_rings(
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: Dict[str, Any] = _INVESTIGATOR
):
    """Lists detected fraud rings with pagination and filtering."""
    return network.get_rings_list(
        min_score=min_score,
        status=status,
        limit=limit,
        offset=offset
    )


@router.get("/rings/{ring_id}")
def get_ring(
    ring_id: str,
    user: Dict[str, Any] = _INVESTIGATOR
):
    """Returns detailed case overview of a fraud ring with timeline and focused graph."""
    try:
        return network.get_ring_detail(ring_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ring {ring_id} not found")


@router.post("/rings/{ring_id}/status")
def update_ring_status_endpoint(
    ring_id: str,
    body: StatusUpdateRequest,
    user: Dict[str, Any] = _INVESTIGATOR
):
    """
    Updates the operational governance status of a fraud ring.
    Requires a non-empty note when setting status to 'confirmed' or 'dismissed'.
    """
    actor = user.get("sub", "investigator")
    try:
        return network.update_ring_status(
            ring_id=ring_id,
            new_status=body.status,
            note=body.note,
            actor=actor
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ring {ring_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/rings/{ring_id}/report.json")
def get_ring_json_report(
    ring_id: str,
    user: Dict[str, Any] = _INVESTIGATOR
):
    """Downloads structured JSON case file for an identified fraud ring."""
    try:
        data = network.get_ring_detail(ring_id)
        return generate_ring_report_json(data)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ring {ring_id} not found")


@router.get("/rings/{ring_id}/report.pdf")
def get_ring_pdf_report(
    ring_id: str,
    user: Dict[str, Any] = _INVESTIGATOR
):
    """Downloads formal A4 PDF case file for an identified fraud ring."""
    try:
        data = network.get_ring_detail(ring_id)
        pdf_bytes = generate_ring_report_pdf(data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="lucen_ring_{ring_id}.pdf"'}
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ring {ring_id} not found")
