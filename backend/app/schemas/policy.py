from typing import Optional, Dict, Any
from pydantic import BaseModel

class PolicyItem(BaseModel):
    policy_number: str
    claim_type: str
    sum_insured: float
    start_date: str
    end_date: str
    vehicle_or_asset: str
    details: Optional[Dict[str, Any]] = None
