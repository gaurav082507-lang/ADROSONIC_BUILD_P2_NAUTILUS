from typing import Optional
from pydantic import BaseModel

class TimelineEvent(BaseModel):
    id: Optional[int] = None
    claim_id: Optional[str] = None
    result_id: Optional[str] = None
    at: str
    at_precision: str  # exact | day | approximate
    kind: str
    source: Optional[str] = None
    artifact_id: Optional[str] = None
    label: Optional[str] = None
    claimant_visible: bool = True

class Contradiction(BaseModel):
    event_a_id: str
    event_b_id: str
    description: str

class ClaimantTimelineItem(BaseModel):
    at: str
    label: str
    kind: str
