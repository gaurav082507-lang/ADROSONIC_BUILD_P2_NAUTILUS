from fastapi import APIRouter
from ...core.model_registry import model_registry
from ...db.database import get_connection, DB_PATH
import os
import sqlite3

router = APIRouter()

@router.get("/health")
def health_check():
    db_path = os.path.abspath(DB_PATH)
    try:
        conn = get_connection()
        c = conn.execute("SELECT count(*) FROM claims")
        claims_count = c.fetchone()[0]
        c = conn.execute("SELECT count(*) FROM results")
        results_count = c.fetchone()[0]
        conn.close()
    except Exception as e:
        claims_count = -1
        results_count = -1

    return {
        "status": "ok",
        "models": model_registry.models,
        "face_engine": model_registry.face_engine_name,
        "db_path": db_path,
        "db_claims_count": claims_count,
        "db_results_count": results_count,
        "mock_analysis": os.environ.get("MOCK_ANALYSIS", "0"),
        "demo_mode": os.environ.get("DEMO_MODE", "0"),
        "seeding_on_startup": os.environ.get("DEMO_MODE", "0") == "1"
    }
