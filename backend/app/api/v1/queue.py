from typing import Optional
from fastapi import APIRouter, Depends, Query

from backend.app.core.auth import require_role
from backend.app.db.repository import list_queue_records
from backend.app.schemas.queue import QueueResponse, QueueItem

router = APIRouter(tags=["Queue"])

@router.get("/queue", response_model=QueueResponse)
async def get_triage_queue(
    band: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH"),
    type: Optional[str] = Query(None, description="motor | health | property"),
    status: Optional[str] = Query(None, description="submitted | under_review | needs_evidence | approved | rejected"),
    q: Optional[str] = Query(None, description="Search query"),
    sort: str = Query("newest", description="Sort by newest or risk"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = None
):
    items, total = list_queue_records(
        band=band,
        claim_type=type,
        status_filter=status,
        search=q,
        limit=limit,
        offset=offset,
        sort=sort
    )
    return QueueResponse(
        items=[QueueItem(**it) for it in items],
        total=total,
        limit=limit,
        offset=offset
    )
