from pydantic import BaseModel
from typing import Optional

class ClaimMetadata(BaseModel):
    claim_date: Optional[str] = None
    incident_date: Optional[str] = None
    incident_time: Optional[str] = None
    claimed_amount: Optional[float] = None
    currency: Optional[str] = None
    claimant_name: Optional[str] = None
    claimant_phone: Optional[str] = None
    claimant_email: Optional[str] = None
    bank_account_ref: Optional[str] = None
    claim_type: Optional[str] = None
    peril: Optional[str] = None
    incident_lat: Optional[float] = None
    incident_lng: Optional[float] = None
    incident_location_text: Optional[str] = None
    statement_language: Optional[str] = None
    statement_original: Optional[str] = None
    statement_en: Optional[str] = None
    liveness_session_id: Optional[str] = None
    aadhaar_qr_session_id: Optional[str] = None
