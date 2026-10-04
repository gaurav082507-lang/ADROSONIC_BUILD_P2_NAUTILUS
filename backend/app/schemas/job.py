from pydantic import BaseModel
from typing import List, Optional

class StepStatus(BaseModel):
    name: str
    status: str
    duration_ms: Optional[int] = None

class JobStatus(BaseModel):
    job_id: str
    status: str
    mode: str
    steps: List[StepStatus]
    result_id: Optional[str] = None
    error: Optional[str] = None
