from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class DecisionDraftRequest(BaseModel):
    action: str  # reject | request_evidence | approve
    reason_category: str
    investigator_note: Optional[str] = None

class DecisionDraftResponse(BaseModel):
    claimant_message_en: str
    claimant_message_hi: str
    next_steps: List[str] = Field(default_factory=list)
    slots_to_resubmit: List[str] = Field(default_factory=list)
    source: str  # template | llm

class DecisionSubmitRequest(BaseModel):
    action: str  # approve | reject | request_evidence | escalate
    reason_category: str
    claimant_message: Optional[str] = ""
    claimant_message_en: Optional[str] = None
    claimant_message_hi: Optional[str] = None
    internal_note: Optional[str] = None
    slots_to_resubmit: List[str] = Field(default_factory=list)

class ActionItem(BaseModel):
    id: int
    claim_id: Optional[str] = None
    result_id: Optional[str] = None
    actor: str
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    reason_category: Optional[str] = None
    claimant_message: Optional[str] = None
    internal_note: Optional[str] = None
    slots_to_resubmit: List[str] = Field(default_factory=list)
    created_at: str
