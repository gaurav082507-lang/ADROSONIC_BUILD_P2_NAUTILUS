from typing import Optional, List
from pydantic import BaseModel
from .requests import ClaimMetadata

# Strictly claimant-safe: NO score, band, evidence, or internal_note
class ClaimCreate(BaseModel):
    policy_number: str
    claim_type: str
    peril: str
    claimant_name: str
    metadata: Optional[ClaimMetadata] = None

class ClaimStatus(BaseModel):
    id: str
    status: str
    claimant_name: str
    policy_number: str
    claim_type: str
    peril: str
    claimant_message: Optional[str] = None
    created_at: str
    updated_at: str
