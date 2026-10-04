from typing import List, Optional
from pydantic import BaseModel, Field

class QueueItem(BaseModel):
    claim_id: str
    result_id: Optional[str] = None
    claimant_name: str
    type: str
    submitted_at: str
    band: str
    overall_risk: float
    top_reason: str
    status: str
    can_fast_track: bool = False

class QueueResponse(BaseModel):
    items: List[QueueItem]
    total: int
    limit: int
    offset: int
