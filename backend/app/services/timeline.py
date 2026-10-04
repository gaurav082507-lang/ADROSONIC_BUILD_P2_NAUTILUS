"""
Digital Evidence Timeline Service (§14.5).
Generates chronological sequence of events, contradiction connectors, and undated items.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import json

from ..db.database import get_connection
from ..pipelines.claim_pipeline import parse_date_safe

def format_iso_ist(dt: datetime) -> str:
    """Formats datetime to ISO 8601 with assumed IST (+05:30) offset if tzinfo is missing."""
    if dt.tzinfo is None:
        return dt.strftime("%Y-%m-%dT%H:%M:%S+05:30")
    return dt.isoformat()

def build_result_timeline(result_id: str, result_obj: Any) -> Dict[str, Any]:
    """
    Constructs the chronological timeline for an analysis result.
    """
    events = []
    contradictions = []
    undated = []

    conn = get_connection()
    # 1. Fetch associated claim if available
    claim_row = conn.execute(
        "SELECT * FROM claims WHERE result_id = ? OR result_ids_json LIKE ? ORDER BY created_at DESC LIMIT 1",
        (result_id, f'%"{result_id}"%')
    ).fetchone()
    
    claim = dict(claim_row) if claim_row else {}
    claim_id = claim.get("id")

    # 2. Fetch associated policy
    policy = {}
    pol_no = claim.get("policy_number")
    if pol_no:
        p_row = conn.execute("SELECT * FROM policies WHERE policy_number = ?", (pol_no,)).fetchone()
        if p_row:
            policy = dict(p_row)

    # 3. Fetch actions on this claim
    actions = []
    if claim_id:
        a_rows = conn.execute("SELECT * FROM actions WHERE claim_id = ? ORDER BY id ASC", (claim_id,)).fetchall()
        actions = [dict(a) for a in a_rows]

    conn.close()

    # Build Events:
    # A. Policy start & end
    if policy.get("start_date"):
        dt = parse_date_safe(policy["start_date"])
        if dt:
            events.append({
                "timestamp": format_iso_ist(dt),
                "at": policy["start_date"],
                "kind": "policy_start",
                "source": "system",
                "source_badge": "Policy Record",
                "label": "Policy coverage started",
                "confidence": "date-only",
                "artifact_id": None
            })
    if policy.get("end_date"):
        dt = parse_date_safe(policy["end_date"])
        if dt:
            events.append({
                "timestamp": format_iso_ist(dt),
                "at": policy["end_date"],
                "kind": "policy_end",
                "source": "system",
                "source_badge": "Policy Record",
                "label": "Policy coverage expires",
                "confidence": "date-only",
                "artifact_id": None
            })

    # B. Incident (stated)
    if claim.get("incident_date"):
        dt = parse_date_safe(claim["incident_date"])
        if dt:
            inc_time = claim.get("incident_time")
            has_time = bool(inc_time)
            label = f"Incident occurred ({claim.get('peril', 'damage')})" if claim.get("peril") else "Incident occurred"
            events.append({
                "timestamp": format_iso_ist(dt),
                "at": f"{claim['incident_date']}T{inc_time}" if has_time else claim["incident_date"],
                "kind": "incident",
                "source": "claimant",
                "source_badge": "Claimant Stated",
                "label": label,
                "confidence": "exact" if has_time else "date-only",
                "artifact_id": None
            })

    # C. Photos & EXIF timestamps
    evidence_list = getattr(result_obj, "evidence", []) or []
    res_artifacts = getattr(result_obj, "artifacts", {}) or {}

    # Inspect evidence for photo details & EXIF
    photo_evs = [e for e in evidence_list if (getattr(e, "pipeline_input", "") or "").startswith("img_") or (getattr(e, "pipeline_input", "") or "") == "image"]
    slots_seen = set()

    for e in evidence_list:
        details = getattr(e, "details", {}) or {}
        # Date from photo EXIF
        if "datetime_original" in details or "photo_date" in details:
            dt_str = details.get("datetime_original") or details.get("photo_date")
            slot = details.get("image_slot") or getattr(e, "pipeline_input", "image")
            dt = parse_date_safe(dt_str)
            if dt and slot not in slots_seen:
                slots_seen.add(slot)
                events.append({
                    "timestamp": format_iso_ist(dt),
                    "at": dt_str,
                    "kind": "photo_captured",
                    "source": "photo metadata",
                    "source_badge": "Photo EXIF",
                    "label": f"Damage photo taken ({slot})",
                    "confidence": "exact",
                    "artifact_id": slot
                })

    # If there are photos in artifacts or image_results that had no date
    img_results = getattr(result_obj, "image_results", []) or []
    for ir in img_results:
        slot = getattr(ir, "pipeline", "image")
        if slot not in slots_seen:
            undated.append({
                "artifact_id": slot,
                "label": f"Photo {slot} (no EXIF capture date)"
            })

    # D. Document Dates & PDF Metadata
    for e in evidence_list:
        details = getattr(e, "details", {}) or {}
        if "doc_date" in details:
            dt = parse_date_safe(details["doc_date"])
            if dt:
                events.append({
                    "timestamp": format_iso_ist(dt),
                    "at": details["doc_date"],
                    "kind": "document_date",
                    "source": "document text",
                    "source_badge": "Document Text",
                    "label": f"Repair estimate / bill dated",
                    "confidence": "date-only",
                    "artifact_id": "document"
                })
        if "datetime_modified" in details and (getattr(e, "id", "") or "").startswith("DOC"):
            dt = parse_date_safe(details["datetime_modified"])
            if dt:
                events.append({
                    "timestamp": format_iso_ist(dt),
                    "at": details["datetime_modified"],
                    "kind": "pdf_modified",
                    "source": "pdf metadata",
                    "source_badge": "PDF Metadata",
                    "label": "Document last saved / modified",
                    "confidence": "exact",
                    "artifact_id": "document"
                })

    # E. Claim Submitted
    if claim.get("created_at"):
        dt = parse_date_safe(claim["created_at"])
        if dt:
            events.append({
                "timestamp": format_iso_ist(dt),
                "at": claim["created_at"],
                "kind": "submitted",
                "source": "system",
                "source_badge": "System Event",
                "label": "Claim submitted to portal",
                "confidence": "exact",
                "artifact_id": None
            })

    # F. Actions (Investigator decisions, resubmissions)
    for act in actions:
        dt = parse_date_safe(act.get("created_at"))
        if dt:
            action_name = act.get("action", "").capitalize()
            actor = act.get("actor", "Investigator")
            events.append({
                "timestamp": format_iso_ist(dt),
                "at": act["created_at"],
                "kind": "action",
                "source": "investigator" if actor != "system" else "system",
                "source_badge": "Investigator Action" if actor != "system" else "System Action",
                "label": f"{action_name} by {actor}",
                "confidence": "exact",
                "artifact_id": None
            })

    # G. Analysis completed
    res_created = getattr(result_obj, "created_at", None)
    if res_created:
        dt = parse_date_safe(res_created)
        if dt:
            events.append({
                "timestamp": format_iso_ist(dt),
                "at": res_created,
                "kind": "analysis_complete",
                "source": "system",
                "source_badge": "System Event",
                "label": "AI forensic analysis completed",
                "confidence": "exact",
                "artifact_id": None
            })

    # Sort events chronologically (oldest at top)
    events.sort(key=lambda x: x["timestamp"])

    # Assign IDs and indices
    for idx, ev in enumerate(events):
        ev["id"] = f"ev_{idx + 1}"

    # Build Contradiction Connectors
    # Map by kind for easy index lookup
    photo_ev_indices = [i for i, ev in enumerate(events) if ev["kind"] == "photo_captured"]
    inc_indices = [i for i, ev in enumerate(events) if ev["kind"] == "incident"]
    pol_start_indices = [i for i, ev in enumerate(events) if ev["kind"] == "policy_start"]
    doc_indices = [i for i, ev in enumerate(events) if ev["kind"] == "document_date"]
    sub_indices = [i for i, ev in enumerate(events) if ev["kind"] == "submitted"]

    for ev in evidence_list:
        ev_id = getattr(ev, "id", "")
        reason = getattr(ev, "reason", "")
        if ev_id == "CLM-X-01" and photo_ev_indices and inc_indices:
            contradictions.append({
                "from_event": photo_ev_indices[0],
                "to_event": inc_indices[0],
                "rule_id": "CLM-X-01",
                "reason": reason
            })
        elif ev_id == "CLM-X-07" and pol_start_indices and (inc_indices or photo_ev_indices):
            target = inc_indices[0] if inc_indices else photo_ev_indices[0]
            contradictions.append({
                "from_event": pol_start_indices[0],
                "to_event": target,
                "rule_id": "CLM-X-07",
                "reason": reason
            })
        elif ev_id == "CLM-X-08" and doc_indices and inc_indices:
            contradictions.append({
                "from_event": doc_indices[0],
                "to_event": inc_indices[0],
                "rule_id": "CLM-X-08",
                "reason": reason
            })
        elif ev_id == "CLM-X-05" and doc_indices and sub_indices:
            contradictions.append({
                "from_event": doc_indices[0],
                "to_event": sub_indices[0],
                "rule_id": "CLM-X-05",
                "reason": reason
            })

    return {
        "events": events,
        "contradictions": contradictions,
        "undated": undated,
        "timezone_note": "Timestamps without explicit offset are assumed to be in Indian Standard Time (IST, UTC+05:30)."
    }

def build_evidence_timeline(events_raw: Any, contradictions_raw: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Helper to build evidence timeline from raw events list or result object."""
    if isinstance(events_raw, str):
        return build_result_timeline(events_raw, contradictions_raw)

    events = []
    undated = []
    contradictions = []

    for item in events_raw:
        ts = item.get("timestamp")
        if ts:
            dt = parse_date_safe(ts)
            if dt:
                events.append({
                    "timestamp": format_iso_ist(dt),
                    "at": ts,
                    "kind": item.get("kind", "generic"),
                    "source": item.get("source", "system"),
                    "label": item.get("label", "")
                })
            else:
                undated.append(item)
        else:
            undated.append(item)

    events.sort(key=lambda x: x["timestamp"])
    for idx, ev in enumerate(events):
        ev["id"] = f"ev_{idx + 1}"

    for c in (contradictions_raw or []):
        from_rule = c.get("from_rule") or c.get("rule_id")
        if from_rule == "CLM-X-01":
            photo_idx = next((i for i, ev in enumerate(events) if ev["kind"] == "photo_captured"), None)
            inc_idx = next((i for i, ev in enumerate(events) if ev["kind"] == "incident"), None)
            if photo_idx is not None and inc_idx is not None:
                contradictions.append({
                    "from_event": photo_idx,
                    "to_event": inc_idx,
                    "rule_id": from_rule,
                    "reason": c.get("message", "")
                })
        else:
            contradictions.append(c)

    return {
        "events": events,
        "contradictions": contradictions,
        "undated": undated,
        "timezone_note": "Timestamps without explicit offset are assumed to be in Indian Standard Time (IST, UTC+05:30)."
    }
