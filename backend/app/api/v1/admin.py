from fastapi import APIRouter, Depends, HTTPException
from ...core.config import settings
from ...db.database import get_connection
from ...db.seed import seed_demo_users_and_policies
from .auth import require_role
from ...detectors.image.duplicates import rebuild_duplicate_index
import logging
import sqlite3

logger = logging.getLogger("lucen_ai")
router = APIRouter()

@router.post("/reset-demo")
def reset_demo(user: dict = Depends(require_role("investigator"))):
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="DEMO_MODE is not enabled")
    
    conn = get_connection()
    try:
        conn.execute("DELETE FROM claim_evidence")
        conn.execute("DELETE FROM actions")
        conn.execute("DELETE FROM jobs")
        conn.execute("DELETE FROM results")
        conn.execute("DELETE FROM claims")
        conn.execute("DELETE FROM rings")

        conn.commit()
    except Exception as e:
        logger.error(f"Failed to clear db: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    # Clear in-memory caches and FAISS
    rebuild_duplicate_index()
    
    # Re-seed users and policies
    seed_demo_users_and_policies()
    
    # Re-seed claims
    from scripts.seed_demo_claims import seed_demo_claims
    # seed_demo_claims()
    
    return {"status": "ok", "message": "Demo reset complete"}
