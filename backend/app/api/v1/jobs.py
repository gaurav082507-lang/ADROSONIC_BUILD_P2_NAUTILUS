from fastapi import APIRouter, Depends
from typing import Dict, Any
from ...schemas.job import JobStatus, StepStatus
from ...services import job_manager
from ...core.config import settings
from ...core.errors import AppException
from ...core.auth import get_current_user, require_role

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)  # P2-12: require auth
):
    """Get job status. Investigators see any job; claimants see only their own jobs."""
    if settings.MOCK_ANALYSIS and job_id.startswith("mock"):
        return JobStatus(
            job_id=job_id,
            status="done",
            mode="claim",
            steps=[
                StepStatus(name="validate", status="done", duration_ms=80),
                StepStatus(name="ai_detector", status="done", duration_ms=210),
                StepStatus(name="ela", status="done", duration_ms=90),
                StepStatus(name="rules", status="done", duration_ms=45),
            ],
            result_id="mock-result-HIGH"
        )

    job = job_manager.get_job(job_id)
    if not job:
        raise AppException(
            code="JOB_NOT_FOUND",
            message=f"Job '{job_id}' not found.",
            status_code=404,
            details={"job_id": job_id}
        )

    # P2-12: ownership check — claimants can only see their own jobs
    if current_user["role"] == "claimant":
        owner_id = getattr(job, "owner_id", None) or job_manager.get_job_owner(job_id)
        if owner_id and owner_id != current_user["id"]:
            raise AppException(
                code="FORBIDDEN",
                message="You do not have permission to view this job.",
                status_code=403
            )

    return job
