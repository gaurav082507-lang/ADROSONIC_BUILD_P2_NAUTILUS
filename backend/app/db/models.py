# Renamed from database.py to models.py per structure doc.
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../../data/runtime/lucen.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0, isolation_level=None)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')
    c = conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS jobs (
      id TEXT PRIMARY KEY, mode TEXT, status TEXT,
      steps_json TEXT, result_id TEXT, error TEXT,
      created_at TEXT, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS results (
      id TEXT PRIMARY KEY, job_id TEXT, mode TEXT,
      overall_risk REAL, overall_band TEXT,
      image_risk REAL, document_risk REAL, identity_risk REAL,
      summary TEXT, json TEXT,
      created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS evidence (
      id INTEGER PRIMARY KEY AUTOINCREMENT, result_id TEXT,
      evidence_id TEXT, pipeline TEXT, source TEXT, kind TEXT,
      raw_score REAL, calibrated_score REAL, weight REAL, effective_weight REAL,
      severity TEXT, title TEXT, reason TEXT, field TEXT,
      bbox_json TEXT, details_json TEXT, artifact TEXT
    );
    CREATE TABLE IF NOT EXISTS image_hashes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      claim_id TEXT,
      claimant_id TEXT,
      result_id TEXT,
      slot TEXT,
      phash TEXT,
      embedding_row INTEGER,
      file_path TEXT,
      thumbnail_path TEXT,
      created_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_evidence_result ON evidence(result_id);

    CREATE TABLE IF NOT EXISTS claims (
      id TEXT PRIMARY KEY, result_id TEXT, claimant_name TEXT,
      claimant_user_id TEXT, policy_number TEXT,
      claim_type TEXT, peril TEXT, status TEXT,
      metadata_json TEXT, created_at TEXT, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS entities (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      claim_id TEXT,
      result_id TEXT,
      kind TEXT,
      value_hash TEXT,
      display TEXT,
      created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS actions (
      id INTEGER PRIMARY KEY AUTOINCREMENT, result_id TEXT,
      actor TEXT, action TEXT, reason_code TEXT,
      claimant_message TEXT, internal_note TEXT,
      message_source TEXT, draft_edited INTEGER, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS liveness_sessions (
      id TEXT PRIMARY KEY, nonce TEXT, challenges_json TEXT, spoken_code TEXT,
      used INTEGER DEFAULT 0, expires_at TEXT
    );
    CREATE TABLE IF NOT EXISTS id_checks (
      id TEXT PRIMARY KEY, mode TEXT, signature_valid INTEGER,
      comparisons_json TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS timeline_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      claim_id TEXT,
      result_id TEXT,
      at TEXT,
      at_precision TEXT,
      kind TEXT,
      source TEXT,
      label TEXT,
      evidence_id TEXT,
      details_json TEXT,
      created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE,
      role TEXT, password_hash TEXT, preferred_language TEXT DEFAULT 'en', created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS policies (
      policy_number TEXT PRIMARY KEY, holder_user_id TEXT, claim_type TEXT,
      start_date TEXT, end_date TEXT, vehicle_or_asset TEXT
    );

    CREATE TABLE IF NOT EXISTS rings (
      id TEXT PRIMARY KEY,
      ring_score REAL,
      band TEXT,
      claims_count INTEGER,
      claimants_count INTEGER,
      shared_json TEXT,
      total_claimed_amount REAL,
      first_seen TEXT,
      last_seen TEXT,
      status TEXT DEFAULT 'open',
      reasons_json TEXT,
      data_source TEXT DEFAULT 'real',
      created_at TEXT,
      updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS ring_members (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ring_id TEXT,
      claim_id TEXT,
      claimant_id TEXT,
      added_at TEXT
    );

    CREATE TABLE IF NOT EXISTS ring_audits (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ring_id TEXT,
      from_status TEXT,
      to_status TEXT,
      note TEXT,
      actor TEXT,
      created_at TEXT
    );
    ''')

    # Safe migrations for existing SQLite databases
    migrations = [
        ("image_hashes", "claim_id", "TEXT"),
        ("image_hashes", "claimant_id", "TEXT"),
        ("image_hashes", "slot", "TEXT"),
        ("image_hashes", "embedding_row", "INTEGER"),
        ("image_hashes", "file_path", "TEXT"),
        ("image_hashes", "thumbnail_path", "TEXT"),
        ("entities", "claim_id", "TEXT"),
        ("timeline_events", "source", "TEXT"),
        ("timeline_events", "label", "TEXT"),
        ("timeline_events", "evidence_id", "TEXT"),
        ("timeline_events", "details_json", "TEXT"),
        ("timeline_events", "created_at", "TEXT"),
        ("claims", "data_source", "TEXT DEFAULT 'real'"),
        ("results", "data_source", "TEXT DEFAULT 'real'"),
        ("rings", "data_source", "TEXT DEFAULT 'real'"),
    ]
    for table, col, col_type in migrations:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except Exception:
            pass  # Column already exists

    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_image_hashes_claim ON image_hashes(claim_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_image_hashes_result ON image_hashes(result_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_entities_claim ON entities(claim_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_entities_kind_hash ON entities(kind, value_hash)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_timeline_result ON timeline_events(result_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ring_members_ring ON ring_members(ring_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ring_members_claim ON ring_members(claim_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ring_audits_ring ON ring_audits(ring_id)")
    except Exception:
        pass

    conn.commit()
    conn.close()

