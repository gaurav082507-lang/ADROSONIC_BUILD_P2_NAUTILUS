import json
from datetime import datetime
from backend.app.core.auth import hash_password
from backend.app.db.database import get_db

DEMO_USERS = [
    {
        "id": "user_ravi",
        "name": "Ravi Kumar",
        "email": "ravi@demo.in",
        "role": "claimant",
        "preferred_language": "en",
        "password": "demo"
    },
    {
        "id": "user_sunita",
        "name": "Sunita Sharma",
        "email": "sunita@demo.in",
        "role": "claimant",
        "preferred_language": "hi",
        "password": "demo"
    },
    {
        "id": "user_investigator",
        "name": "Pooja Mehta",
        "email": "investigator@demo.in",
        "role": "investigator",
        "preferred_language": "en",
        "password": "demo"
    },
    {
        "id": "user_investigator_lucen",
        "name": "Lucen Investigator",
        "email": "investigator@lucen.ai",
        "role": "investigator",
        "preferred_language": "en",
        "password": "Password123!"
    },
    {
        "id": "user_claimant_lucen",
        "name": "Lucen Claimant",
        "email": "claimant@example.com",
        "role": "claimant",
        "preferred_language": "en",
        "password": "Password123!"
    }
]

DEMO_POLICIES = [
    {
        "policy_number": "POL-MOT-8821",
        "holder_user_id": "user_ravi",
        "claim_type": "motor",
        "sum_insured": 500000.0,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "vehicle_or_asset": "KA-01-MJ-5521 (Hyundai Creta)",
        "details_json": json.dumps({"vehicle_number": "KA-01-MJ-5521", "model": "Hyundai Creta", "year": 2023})
    },
    {
        "policy_number": "POL-HLT-4402",
        "holder_user_id": "user_ravi",
        "claim_type": "health",
        "sum_insured": 1000000.0,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "vehicle_or_asset": "Family Floater",
        "details_json": json.dumps({"members": ["Ravi Kumar", "Priya Kumar"], "hospital_tier": "Tier-1 Cashless"})
    },
    {
        "policy_number": "POL-PRP-1093",
        "holder_user_id": "user_ravi",
        "claim_type": "property",
        "sum_insured": 2500000.0,
        "start_date": "2025-06-01",
        "end_date": "2027-05-31",
        "vehicle_or_asset": "42 Indiranagar 100ft Rd, Bengaluru",
        "details_json": json.dumps({"address": "42 Indiranagar 100ft Rd, Bengaluru 560038", "structure_type": "Apartment"})
    },
    {
        "policy_number": "POL-MOT-3319",
        "holder_user_id": "user_sunita",
        "claim_type": "motor",
        "sum_insured": 650000.0,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "vehicle_or_asset": "DL-04-AB-1290 (Maruti Brezza)",
        "details_json": json.dumps({"vehicle_number": "DL-04-AB-1290", "model": "Maruti Brezza", "year": 2022})
    },
    {
        "policy_number": "POL-HLT-9182",
        "holder_user_id": "user_sunita",
        "claim_type": "health",
        "sum_insured": 750000.0,
        "start_date": "2026-03-01",
        "end_date": "2027-02-28",
        "vehicle_or_asset": "Individual Health",
        "details_json": json.dumps({"members": ["Sunita Sharma", "Aarav Sharma"]})
    },
    {
        "policy_number": "POL-MOT-1001",
        "holder_user_id": "user_claimant_lucen",
        "claim_type": "motor",
        "sum_insured": 800000.0,
        "start_date": "2025-01-01",
        "end_date": "2027-12-31",
        "vehicle_or_asset": "MH-02-CD-4321 (Honda City)",
        "details_json": json.dumps({"vehicle_number": "MH-02-CD-4321", "model": "Honda City", "year": 2024})
    }
]

def seed_demo_users_and_policies():
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        for u in DEMO_USERS:
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (u["email"],)).fetchone()
            pw_hash = hash_password(u["password"])
            if not existing:
                conn.execute(
                    "INSERT INTO users (id, name, email, role, password_hash, preferred_language, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (u["id"], u["name"], u["email"], u["role"], pw_hash, u["preferred_language"], now)
                )
            else:
                conn.execute(
                    "UPDATE users SET name=?, role=?, password_hash=?, preferred_language=? WHERE email=?",
                    (u["name"], u["role"], pw_hash, u["preferred_language"], u["email"])
                )

        for p in DEMO_POLICIES:
            existing = conn.execute("SELECT policy_number FROM policies WHERE policy_number = ?", (p["policy_number"],)).fetchone()
            if not existing:
                conn.execute(
                    """INSERT INTO policies (policy_number, holder_user_id, claim_type, sum_insured, start_date, end_date, vehicle_or_asset, details_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (p["policy_number"], p["holder_user_id"], p["claim_type"], p["sum_insured"], p["start_date"], p["end_date"], p["vehicle_or_asset"], p["details_json"], now)
                )
            else:
                conn.execute(
                    """UPDATE policies SET holder_user_id=?, claim_type=?, sum_insured=?, start_date=?, end_date=?, vehicle_or_asset=?, details_json=?
                       WHERE policy_number=?""",
                    (p["holder_user_id"], p["claim_type"], p["sum_insured"], p["start_date"], p["end_date"], p["vehicle_or_asset"], p["details_json"], p["policy_number"])
                )
        conn.commit()
