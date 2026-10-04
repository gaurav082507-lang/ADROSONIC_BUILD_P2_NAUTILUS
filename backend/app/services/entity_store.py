"""
Light Entity Store Service (§14.3, Prompt 8 Part 5).
Normalizes and stores entities:
- phone, email, bank account (salted hash + masked display)
- vehicle registration number
- invoice number + issuer
- garage / hospital facility name
Table: entities(claim_id, result_id, kind, value_hash, display, created_at)
"""
import re
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from ..db.database import get_connection

ENTITY_SALT = "lucen_ai_entity_salt_2026"

def _hash_val(val: str) -> str:
    salted = f"{val.strip().lower()}:{ENTITY_SALT}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()

def mask_phone(phone: str) -> Tuple[str, str]:
    digits = re.sub(r"\D", "", phone)
    last4 = digits[-4:] if len(digits) >= 4 else digits
    display = f"••••{last4}"
    return _hash_val(digits), display

def mask_email(email: str) -> Tuple[str, str]:
    clean = email.strip().lower()
    parts = clean.split("@")
    if len(parts) == 2 and len(parts[0]) > 2:
        uname, domain = parts
        display = f"{uname[0]}•••{uname[-1]}@{domain}"
    else:
        display = "••••@demo.in"
    return _hash_val(clean), display

def mask_bank_account(acc: str) -> Tuple[str, str]:
    digits = re.sub(r"\D", "", str(acc))
    last4 = digits[-4:] if len(digits) >= 4 else digits
    display = f"••••{last4}"
    return _hash_val(digits), display

def format_vehicle(veh: str) -> Tuple[str, str]:
    clean = re.sub(r"[^A-Za-z0-9]", "", veh).upper()
    return _hash_val(clean), clean

def format_invoice(inv: str, issuer: Optional[str] = None) -> Tuple[str, str]:
    clean_inv = inv.strip().upper()
    clean_iss = (issuer or "").strip().title()
    combined = f"{clean_inv}:{clean_iss.lower()}"
    display = f"{clean_inv} ({clean_iss})" if clean_iss else clean_inv
    return _hash_val(combined), display

def format_facility(name: str) -> Tuple[str, str]:
    clean = re.sub(r"\s+", " ", name).strip()
    return _hash_val(clean), clean

def extract_and_store_entities(
    claim_id: str,
    result_id: Optional[str],
    claim_data: Dict[str, Any],
    doc_fields: Optional[Dict[str, Any]] = None,
    user_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Extracts normalized entities from claim, documents, and claimant profile.
    Inserts them into the SQLite entities table.
    """
    doc_fields = doc_fields or {}
    user_data = user_data or {}
    now = datetime.utcnow().isoformat()
    extracted = []

    # 1. Phone
    phone = claim_data.get("phone") or user_data.get("phone")
    if phone:
        v_hash, disp = mask_phone(str(phone))
        extracted.append(("phone", v_hash, disp))

    # 2. Email
    email = claim_data.get("email") or user_data.get("email")
    if email:
        v_hash, disp = mask_email(str(email))
        extracted.append(("email", v_hash, disp))

    # 3. Bank Account
    bank = claim_data.get("bank_account") or claim_data.get("account_number")
    if bank:
        v_hash, disp = mask_bank_account(str(bank))
        extracted.append(("bank_account", v_hash, disp))

    # 4. Vehicle Number
    veh = claim_data.get("vehicle_number") or doc_fields.get("vehicle_number") or claim_data.get("policy_vehicle")
    if veh:
        v_hash, disp = format_vehicle(str(veh))
        extracted.append(("vehicle_number", v_hash, disp))

    # 5. Invoice & Issuer
    inv_list = doc_fields.get("invoice_numbers", [])
    issuer = doc_fields.get("issuer")
    for inv_item in inv_list:
        inv_str = inv_item.get("text") if isinstance(inv_item, dict) else str(inv_item)
        if inv_str:
            v_hash, disp = format_invoice(inv_str, issuer)
            extracted.append(("invoice", v_hash, disp))

    # 6. Garage / Hospital
    if issuer:
        v_hash, disp = format_facility(str(issuer))
        kind = "hospital" if "hospital" in str(issuer).lower() else "garage"
        extracted.append((kind, v_hash, disp))

    # 7. Image Cluster / Reused Photo
    img_cluster = claim_data.get("image_cluster")
    if img_cluster:
        v_hash = hashlib.sha256(str(img_cluster).encode('utf-8')).hexdigest()
        extracted.append(("image_cluster", v_hash, "Reused Car Damage Photo"))

    # Store in database
    conn = get_connection()
    c = conn.cursor()
    # Avoid duplicate entities for the same claim
    for kind, val_hash, display in extracted:
        existing = c.execute(
            "SELECT id FROM entities WHERE claim_id = ? AND kind = ? AND value_hash = ?",
            (claim_id, kind, val_hash)
        ).fetchone()
        if not existing:
            c.execute(
                """INSERT INTO entities (claim_id, result_id, kind, value_hash, display, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (claim_id, result_id, kind, val_hash, display, now)
            )
    conn.commit()
    conn.close()

    return [{"type": k, "display_masked": d, "value_hash": h} for k, h, d in extracted]

def get_claim_entities(claim_id: str) -> List[Dict[str, Any]]:
    """Retrieves all entities linked to a claim."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, claim_id, result_id, kind, value_hash, display, created_at FROM entities WHERE claim_id = ? ORDER BY id ASC",
        (claim_id,)
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "claim_id": r["claim_id"],
            "result_id": r["result_id"],
            "type": r["kind"],
            "kind": r["kind"],
            "value_hash": r["value_hash"],
            "display_masked": r["display"],
            "created_at": r["created_at"]
        }
        for r in rows
    ]
