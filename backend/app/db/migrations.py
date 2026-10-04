"""Create-if-missing + simple ALTERs on startup."""
from .database import get_connection
from .models import init_db
from backend.app.core.config import settings

def run_migrations():
    """Run init_db and any pending schema migrations."""
    init_db()
    conn = get_connection()
    
    # Safe alter table helper
    def add_col_if_missing(table: str, col_def: str, col_name: str):
        try:
            conn.execute(f"SELECT {col_name} FROM {table} LIMIT 1")
        except Exception:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
                conn.commit()
            except Exception:
                pass

    # Results migrations
    add_col_if_missing("results", "is_seed INTEGER DEFAULT 0", "is_seed")

    # Jobs migrations — owner tracking (P2-12)
    add_col_if_missing("jobs", "owner_id TEXT", "owner_id")
    
    # Policies migrations
    add_col_if_missing("policies", "sum_insured REAL DEFAULT 0.0", "sum_insured")
    add_col_if_missing("policies", "details_json TEXT", "details_json")
    add_col_if_missing("policies", "created_at TEXT", "created_at")

    # Claims migrations
    add_col_if_missing("claims", "incident_date TEXT", "incident_date")
    add_col_if_missing("claims", "incident_time TEXT", "incident_time")
    add_col_if_missing("claims", "incident_location_json TEXT", "incident_location_json")
    add_col_if_missing("claims", "claimed_amount REAL DEFAULT 0.0", "claimed_amount")
    add_col_if_missing("claims", "damaged_items_json TEXT", "damaged_items_json")
    add_col_if_missing("claims", "description_text TEXT", "description_text")
    add_col_if_missing("claims", "description_lang TEXT DEFAULT 'en'", "description_lang")
    add_col_if_missing("claims", "consent INTEGER DEFAULT 1", "consent")
    add_col_if_missing("claims", "result_ids_json TEXT", "result_ids_json")
    add_col_if_missing("claims", "fast_track INTEGER DEFAULT 0", "fast_track")

    # Actions migrations
    add_col_if_missing("actions", "claim_id TEXT", "claim_id")
    add_col_if_missing("actions", "from_status TEXT", "from_status")
    add_col_if_missing("actions", "to_status TEXT", "to_status")
    add_col_if_missing("actions", "reason_category TEXT", "reason_category")
    add_col_if_missing("actions", "slots_to_resubmit_json TEXT", "slots_to_resubmit_json")

    # Ensure claim_evidence table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS claim_evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_id TEXT,
        slot TEXT,
        file_label TEXT,
        file_path TEXT,
        capture_source TEXT,
        state TEXT,
        version INTEGER DEFAULT 1,
        created_at TEXT,
        updated_at TEXT
    );
    """)
    conn.commit()
    conn.close()


