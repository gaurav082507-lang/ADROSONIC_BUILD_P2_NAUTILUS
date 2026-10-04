"""CRUD helpers per table."""
from .database import get_connection
import json
from typing import Optional, Dict, Any


def insert_job(job_id: str, mode: str, status: str, created_at: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO jobs (id, mode, status, steps_json, created_at, updated_at) VALUES (?, ?, ?, '[]', ?, ?)",
        (job_id, mode, status, created_at, created_at)
    )
    conn.commit()
    conn.close()


def update_job(job_id: str, **kwargs):
    conn = get_connection()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [job_id]
    conn.execute(f"UPDATE jobs SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def insert_result(result_id: str, job_id: str, mode: str, overall_risk: float,
                  overall_band: str, summary: str, result_json: str, created_at: str,
                  image_risk: Optional[float] = None, document_risk: Optional[float] = None,
                  identity_risk: Optional[float] = None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO results (id, job_id, mode, overall_risk, overall_band, summary, json, created_at, "
        "image_risk, document_risk, identity_risk) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (result_id, job_id, mode, overall_risk, overall_band, summary, result_json, created_at,
         image_risk, document_risk, identity_risk)
    )
    conn.commit()
    conn.close()


def get_result(result_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM results WHERE id = ?", (result_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    from backend.app.core.config import settings
    if settings.MOCK_ANALYSIS and result_id and result_id.startswith("mock"):
        from backend.app.api.v1.mock_data import get_canned_result
        variant = "HIGH"
        if "LOW" in result_id.upper():
            variant = "LOW"
        elif "MED" in result_id.upper():
            variant = "MEDIUM"
        canned = get_canned_result(variant=variant, result_id=result_id)
        return {
            "id": result_id,
            "overall_band": canned.overall.band,
            "overall": {"band": canned.overall.band, "confidence": canned.overall.confidence, "risk": canned.overall.risk},
            "json": canned.model_dump_json()
        }
    return None

get_result_by_id = get_result
get_job_by_id = get_job

def create_job_record(job_id: str, mode: str):
    from datetime import datetime
    insert_job(job_id, mode, "queued", datetime.utcnow().isoformat())


def insert_evidence_row(result_id: str, evidence_id: str, pipeline: str, source: str,
                        kind: str, raw_score: float, calibrated_score: float,
                        weight: float, effective_weight: float, severity: str,
                        title: str, reason: str, field: str = None,
                        bbox_json: str = None, details_json: str = None, artifact: str = None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO evidence (result_id, evidence_id, pipeline, source, kind, "
        "raw_score, calibrated_score, weight, effective_weight, severity, title, reason, "
        "field, bbox_json, details_json, artifact) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (result_id, evidence_id, pipeline, source, kind, raw_score, calibrated_score,
         weight, effective_weight, severity, title, reason, field, bbox_json, details_json, artifact)
    )
    conn.commit()
    conn.close()


def list_history(page: int = 1, page_size: int = 20, mode: Optional[str] = None, band: Optional[str] = None):
    conn = get_connection()
    where_clauses = []
    params = []
    if mode:
        where_clauses.append("mode = ?")
        params.append(mode)
    if band:
        where_clauses.append("overall_band = ?")
        params.append(band.upper())

    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_cur = conn.execute(f"SELECT COUNT(*) FROM results {where_str}", params)
    total = count_cur.fetchone()[0]

    offset = max(0, (page - 1) * page_size)
    query = f"SELECT id, created_at, mode, overall_risk, overall_band, summary, json FROM results {where_str} ORDER BY created_at DESC LIMIT ? OFFSET ?"
    rows = conn.execute(query, params + [page_size, offset]).fetchall()

    items = []
    for r in rows:
        r_dict = dict(r)
        ev_count = 0
        thumb_url = None
        top_reason = None
        if r_dict.get("json"):
            try:
                res_obj = json.loads(r_dict["json"])
                evidence = res_obj.get("evidence", [])
                ev_count = len(evidence)
                top_reasons = res_obj.get("top_reasons", [])
                if top_reasons:
                    top_reason = top_reasons[0]
                elif evidence:
                    top_reason = evidence[0].get("reason") or evidence[0].get("title")
                artifacts = res_obj.get("artifacts", {})
                thumb_url = artifacts.get("thumbnail") or artifacts.get("preview_img_1") or artifacts.get("heatmap") or artifacts.get("page_1_boxes")
            except Exception:
                pass
        items.append({
            "id": r_dict["id"],
            "created_at": r_dict["created_at"],
            "mode": r_dict["mode"],
            "overall_risk": float(r_dict.get("overall_risk") or 0.0),
            "overall_band": r_dict.get("overall_band") or "LOW",
            "thumbnail_url": thumb_url,
            "evidence_count": ev_count,
            "top_reason": top_reason,
        })
    conn.close()
    return items, total


def delete_result(result_id: str) -> bool:
    import shutil
    import os
    conn = get_connection()
    row = conn.execute("SELECT job_id FROM results WHERE id = ?", (result_id,)).fetchone()
    if not row:
        conn.close()
        return False
    job_id = row["job_id"]
    conn.execute("DELETE FROM results WHERE id = ?", (result_id,))
    conn.execute("DELETE FROM evidence WHERE result_id = ?", (result_id,))
    conn.execute("DELETE FROM image_hashes WHERE result_id = ?", (result_id,))
    conn.execute("DELETE FROM actions WHERE result_id = ?", (result_id,))
    conn.execute("DELETE FROM entities WHERE result_id = ?", (result_id,))
    if job_id:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

    # Clean disk artifacts and uploads
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/runtime"))
    art_dir = os.path.join(base_dir, "artifacts", result_id)
    if os.path.isdir(art_dir):
        shutil.rmtree(art_dir, ignore_errors=True)
    if job_id:
        upload_dir = os.path.join(base_dir, "uploads", job_id)
        if os.path.isdir(upload_dir):
            shutil.rmtree(upload_dir, ignore_errors=True)

    try:
        from backend.app.detectors.image.duplicates import remove_result_from_index
        remove_result_from_index(result_id)
    except Exception:
        pass

    return True


def get_result_evidence(result_id: str, pipeline: Optional[str] = None, severity: Optional[str] = None, kind: Optional[str] = None):
    conn = get_connection()
    clauses = ["result_id = ?"]
    params = [result_id]
    if pipeline:
        clauses.append("pipeline = ?")
        params.append(pipeline)
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    if kind:
        clauses.append("kind = ?")
        params.append(kind)

    where_str = " AND ".join(clauses)
    rows = conn.execute(f"SELECT * FROM evidence WHERE {where_str}", params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def recover_interrupted_jobs() -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE jobs SET status = 'failed', error = 'Job interrupted by server restart' WHERE status IN ('queued', 'running')"
    )
    count = c.rowcount
    
    # Also update any claims stuck in 'submitted' or 'analysing' 
    c.execute(
        "UPDATE claims SET status = 'analysis_failed' WHERE status IN ('submitted', 'analysing') AND data_source IS NULL"
    )
    
    conn.commit()
    conn.close()
    return count

def mask_claimant_name(name: str) -> str:
    if not name:
        return "Unknown"
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."

def list_policies_for_user(user_id: str):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM policies WHERE holder_user_id = ?", (user_id,)).fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        if d.get("details_json"):
            try:
                d["details"] = json.loads(d["details_json"])
            except Exception:
                d["details"] = {}
        res.append(d)
    return res

def get_policy(policy_number: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM policies WHERE policy_number = ?", (policy_number,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if d.get("details_json"):
        try:
            d["details"] = json.loads(d["details_json"])
        except Exception:
            d["details"] = {}
    return d

def create_claim_record(claim_data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO claims (
            id, claimant_user_id, policy_number, claimant_name, claim_type, peril,
            incident_date, incident_time, incident_location_json, claimed_amount,
            damaged_items_json, description_text, description_lang, consent, status,
            result_id, result_ids_json, fast_track, metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            claimant_user_id=excluded.claimant_user_id,
            policy_number=excluded.policy_number,
            claimant_name=excluded.claimant_name,
            claim_type=excluded.claim_type,
            peril=excluded.peril,
            incident_date=excluded.incident_date,
            incident_time=excluded.incident_time,
            incident_location_json=excluded.incident_location_json,
            claimed_amount=excluded.claimed_amount,
            damaged_items_json=excluded.damaged_items_json,
            description_text=excluded.description_text,
            description_lang=excluded.description_lang,
            consent=excluded.consent,
            status=excluded.status,
            result_id=excluded.result_id,
            result_ids_json=excluded.result_ids_json,
            fast_track=excluded.fast_track,
            metadata_json=excluded.metadata_json,
            updated_at=excluded.updated_at""",
        (
            claim_data["id"],
            claim_data["claimant_user_id"],
            claim_data.get("policy_number") or claim_data.get("policy_id"),
            claim_data.get("claimant_name", ""),
            claim_data.get("claim_type", "motor"),
            claim_data.get("peril", ""),
            claim_data.get("incident_date", ""),
            claim_data.get("incident_time", ""),
            claim_data.get("incident_location_json", "{}"),
            float(claim_data.get("claimed_amount", 0.0)),
            claim_data.get("damaged_items_json", "[]"),
            claim_data.get("description_text", ""),
            claim_data.get("description_lang", "en"),
            1 if claim_data.get("consent") else 0,
            claim_data.get("status", "submitted"),
            claim_data.get("result_id"),
            claim_data.get("result_ids_json", "[]"),
            claim_data.get("fast_track", 0),
            claim_data.get("metadata_json", "{}"),
            claim_data.get("created_at"),
            claim_data.get("updated_at")
        )
    )
    conn.commit()
    conn.close()

def get_claim_record(claim_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def list_claims_for_user(user_id: str):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM claims WHERE claimant_user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_claim_record(claim_id: str, updates: dict):
    conn = get_connection()
    c = conn.cursor()
    clauses = []
    params = []
    for k, v in updates.items():
        clauses.append(f"{k} = ?")
        params.append(v)
    params.append(claim_id)
    query = f"UPDATE claims SET {', '.join(clauses)} WHERE id = ?"
    c.execute(query, params)
    conn.commit()
    conn.close()

def add_claim_evidence_item(evidence_data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO claim_evidence (
            claim_id, slot, file_label, file_path, capture_source, state, version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            evidence_data["claim_id"],
            evidence_data["slot"],
            evidence_data["file_label"],
            evidence_data["file_path"],
            evidence_data.get("capture_source", "upload"),
            evidence_data.get("state", "received"),
            evidence_data.get("version", 1),
            evidence_data.get("created_at"),
            evidence_data.get("updated_at")
        )
    )
    conn.commit()
    conn.close()

def get_claim_evidence_items(claim_id: str):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM claim_evidence WHERE claim_id = ? ORDER BY id ASC", (claim_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_action_record(action_data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO actions (
            claim_id, result_id, actor, action, from_status, to_status,
            reason_category, reason_code, claimant_message, internal_note,
            message_source, draft_edited, slots_to_resubmit_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            action_data.get("claim_id"),
            action_data.get("result_id"),
            action_data.get("actor", "system"),
            action_data.get("action", ""),
            action_data.get("from_status"),
            action_data.get("to_status"),
            action_data.get("reason_category"),
            action_data.get("reason_code"),
            action_data.get("claimant_message"),
            action_data.get("internal_note"),
            action_data.get("message_source"),
            action_data.get("draft_edited", 0),
            action_data.get("slots_to_resubmit_json", "[]"),
            action_data.get("created_at")
        )
    )
    conn.commit()
    conn.close()

def get_actions_for_claim_record(claim_id: str):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM actions WHERE claim_id = ? ORDER BY id ASC", (claim_id,)).fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        if d.get("slots_to_resubmit_json"):
            try:
                d["slots_to_resubmit"] = json.loads(d["slots_to_resubmit_json"])
            except Exception:
                d["slots_to_resubmit"] = []
        else:
            d["slots_to_resubmit"] = []
        res.append(d)
    return res

def list_queue_records(band: Optional[str] = None, claim_type: Optional[str] = None, status_filter: Optional[str] = None, search: Optional[str] = None, limit: int = 20, offset: int = 0, sort: str = "newest"):
    conn = get_connection()
    clauses = ["(c.data_source IS NULL OR c.data_source != 'synthetic_history')"]
    params = []
    
    if band:
        clauses.append("r.overall_band = ?")
        params.append(band.upper())
    if claim_type:
        clauses.append("c.claim_type = ?")
        params.append(claim_type.lower())
    if status_filter:
        clauses.append("c.status = ?")
        params.append(status_filter)
    if search:
        clauses.append("(c.id LIKE ? OR c.claimant_name LIKE ? OR c.policy_number LIKE ?)")
        sp = f"%{search}%"
        params.extend([sp, sp, sp])
        
    where_str = f"WHERE {' AND '.join(clauses)}"
    
    # Total count query
    count_sql = f"""
    SELECT COUNT(*) FROM claims c
    LEFT JOIN results r ON c.result_id = r.id
    {where_str}
    """
    total = conn.execute(count_sql, params).fetchone()[0]
    
    if sort == "newest":
        order_by = "ORDER BY c.created_at DESC"
    else:
        order_by = "ORDER BY CASE WHEN c.status IN ('approved', 'rejected') THEN 1 ELSE 0 END, COALESCE(r.overall_score, 0.0) DESC, c.created_at ASC"
    
    query = f"""
    SELECT 
        c.id as claim_id,
        c.claimant_name,
        c.claim_type,
        c.created_at as submitted_at,
        c.status,
        c.result_id,
        r.overall_band,
        r.overall_risk,
        r.summary,
        r.json as result_json
    FROM claims c
    LEFT JOIN results r ON c.result_id = r.id
    {where_str}
    {order_by}
    LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    items = []
    for r in rows:
        d = dict(r)
        masked_name = mask_claimant_name(d.get("claimant_name") or "")
        band_val = d.get("overall_band") or "UNKNOWN"
        risk_val = float(d.get("overall_risk") or 0.0)
        
        # Determine top reason and confidence
        top_reason = "Under forensic review"
        conf = "high"
        if d.get("result_json"):
            try:
                res_obj = json.loads(d["result_json"])
                conf = res_obj.get("overall", {}).get("confidence", "high")
                reasons = res_obj.get("top_reasons", [])
                if reasons:
                    top_reason = reasons[0]
                elif res_obj.get("summary"):
                    top_reason = res_obj.get("summary")[:120]
            except Exception:
                pass
                
        can_ft = (band_val == "LOW" and conf != "low" and d.get("status") in ("submitted", "under_review"))
        
        items.append({
            "claim_id": d["claim_id"],
            "result_id": d.get("result_id"),
            "claimant_name": masked_name,
            "type": d.get("claim_type") or "motor",
            "submitted_at": d.get("submitted_at") or "",
            "band": band_val,
            "overall_risk": round(risk_val, 4),
            "top_reason": top_reason,
            "status": d.get("status") or "submitted",
            "can_fast_track": can_ft
        })
    return items, total


def create_liveness_session(session_id: str, nonce: str, challenges: list, spoken_code: str, expires_at: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO liveness_sessions (id, nonce, challenges_json, spoken_code, used, expires_at) "
        "VALUES (?, ?, ?, ?, 0, ?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "nonce=excluded.nonce, "
        "challenges_json=excluded.challenges_json, "
        "spoken_code=excluded.spoken_code, "
        "used=excluded.used, "
        "expires_at=excluded.expires_at",
        (session_id, nonce, json.dumps(challenges), spoken_code, expires_at)
    )
    conn.commit()
    conn.close()


def get_liveness_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM liveness_sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        if d.get("challenges_json"):
            try:
                d["challenges"] = json.loads(d["challenges_json"])
            except Exception:
                d["challenges"] = []
        return d
    return None


def mark_liveness_session_used(session_id: str):
    conn = get_connection()
    conn.execute("UPDATE liveness_sessions SET used = 1 WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

