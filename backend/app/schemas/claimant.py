from typing import List, Optional
from pydantic import BaseModel, Field

class ClaimantClaimSummary(BaseModel):
    claim_id: str
    policy_label: str
    claim_type: str
    submitted_at: str
    status: str
    last_update: str

class TimelineStep(BaseModel):
    name: str
    status: str
    date: str

class ClaimantDecision(BaseModel):
    outcome: str
    reason_category_label: str
    claimant_message: str
    next_steps: List[str] = Field(default_factory=list)
    can_resubmit: bool = False
    slots_to_resubmit: List[str] = Field(default_factory=list)

class ClaimantStatusResponse(BaseModel):
    claim_id: str
    status: str
    timeline: List[TimelineStep] = Field(default_factory=list)
    decision: Optional[ClaimantDecision] = None

class ClaimantEvidenceTimelineItem(BaseModel):
    slot: str
    file_label: str
    state: str  # received | checked | needs_replacing
    updated_at: str
