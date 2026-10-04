from typing import List, Dict, Any
from pydantic import BaseModel

class TrendsResponse(BaseModel):
    total_claims: int
    flagged_claims: int
    fraud_rate: float
    recent_trend: List[Dict[str, Any]]
