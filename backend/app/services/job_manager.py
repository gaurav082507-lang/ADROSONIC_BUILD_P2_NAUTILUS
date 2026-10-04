import asyncio
import uuid
import datetime
import json
from typing import Dict, Any, Optional
from ..schemas.job import JobStatus, StepStatus
from ..core.config import settings
from ..db import repository

import threading

# In-memory fast cache + SQLite backing
JOBS_DB: Dict[str, JobStatus] = {}

# Threading semaphore initialized with MAX_CONCURRENT_JOBS for CPU tasks
_semaphore: Optional[threading.Semaphore] = None

def get_semaphore() -> threading.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = threading.Semaphore(settings.MAX_CONCURRENT_JOBS)
    return _semaphore



def get_job(job_id: str) -> Optional[JobStatus]:
    if job_id in JOBS_DB:
        return JOBS_DB[job_id]
    
    # Try fetching from DB
    try:
        row = repository.get_job(job_id)
        if row:
            steps_data = json.loads(row.get("steps_json", "[]"))
            steps = [StepStatus(**s) for s in steps_data]
            job = JobStatus(
                job_id=row["id"],
                status=row["status"],
                mode=row["mode"],
                steps=steps,
                result_id=row.get("result_id"),
                error=row.get("error")
            )
            JOBS_DB[job_id] = job
            return job
    except Exception:
        pass
        
    return None

def update_job_status(job_id: str, status: str, error: Optional[str] = None, result_id: Optional[str] = None):
    job = get_job(job_id)
    if job:
        job.status = status
        if error:
            job.error = error
        if result_id:
            job.result_id = result_id
            
    try:
        now = datetime.datetime.utcnow().isoformat()
        update_data = {"status": status, "updated_at": now}
        if error:
            update_data["error"] = error
        if result_id:
            update_data["result_id"] = result_id
        repository.update_job(job_id, **update_data)
    except Exception:
        pass

def start_step(job_id: str, step_name: str):
    job = get_job(job_id)
    if job:
        job.steps.append(StepStatus(name=step_name, status="running"))
        _sync_steps(job_id, job)

def finish_step(job_id: str, step_name: str, status: str, duration_ms: int = 0):
    job = get_job(job_id)
    if job:
        for s in job.steps:
            if s.name == step_name:
                s.status = status
                s.duration_ms = duration_ms
        _sync_steps(job_id, job)

def _sync_steps(job_id: str, job: JobStatus):
    try:
        steps_json = json.dumps([s.model_dump() for s in job.steps])
        repository.update_job(job_id, steps_json=steps_json)
    except Exception:
        pass


def get_job_owner(job_id: str) -> Optional[str]:
    """Return owner_id for a job from SQLite (P2-12)."""
    try:
        from ..db.database import get_connection
        conn = get_connection()
        row = conn.execute("SELECT owner_id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def create_job(mode: str, owner_id: Optional[str] = None) -> str:
    """Create a job, optionally storing the submitting user's ID for ownership checks."""
    job_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()
    job = JobStatus(job_id=job_id, status="queued", mode=mode, steps=[])
    JOBS_DB[job_id] = job

    try:
        from ..db.database import get_connection
        conn = get_connection()
        conn.execute(
            "INSERT INTO jobs (id, mode, status, steps_json, created_at, updated_at, owner_id) "
            "VALUES (?, ?, ?, '[]', ?, ?, ?)",
            (job_id, mode, "queued", now, now, owner_id)
        )
        conn.commit()
        conn.close()
    except Exception:
        # Fallback: old schema without owner_id
        try:
            repository.insert_job(job_id=job_id, mode=mode, status="queued", created_at=now)
        except Exception:
            pass

    return job_id

