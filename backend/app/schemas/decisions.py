from typing import Optional
from pydantic import BaseModel

class DecisionRequest(BaseModel):
    status: str  # approved | rejected | info_requested
    reason_code: str
    claimant_message: str
    internal_note: str

class DecisionDraft(BaseModel):
    reason_code: str
    claimant_message: str
    internal_note: str
    message_source: str  # llm_draft | template | manual
