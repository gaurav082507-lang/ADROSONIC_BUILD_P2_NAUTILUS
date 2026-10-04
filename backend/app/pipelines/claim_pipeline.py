"""
Claim Mode Cross-Checks and Pseudo-Pipeline R_claim (§14, §15.5).
Cross-validates:
- Photo capture date vs incident date (CLM-X-01)
- Photo GPS vs stated incident location (CLM-X-06)
- Document total vs claimed amount (CLM-X-02)
- Bill date vs incident date / chronology (CLM-X-08, CLM-CHRONO-01)
- Name on bill vs policyholder / insured members (CLM-X-03)
- Incident date vs policy validity (CLM-X-07)
- Vehicle number on estimate vs policy (CLM-VEH-01)
- Verified ID name vs policyholder (CLM-ID-01)
- Duplicate invoice across claims (DOC-DUP-01 / CLM-X-04)
- Duplicate images across claims (IMG-DUP-01 / IMG-DUP-02)
"""
import os
import re
import math
import json
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

import rapidfuzz.fuzz as fuzz

from ..schemas.evidence import Evidence
from ..schemas.result import DetectorStatus
from ..scoring.weights import EVIDENCE_CATALOG
from ..scoring.fusion import compute_fusion_with_contributions
from ..db.database import get_connection
from ..db.repository import mask_claimant_name

logger = logging.getLogger("lucen_ai.claim_pipeline")

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes the great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

haversine_distance_km = haversine_km

def parse_date_safe(d_input: Any) -> Optional[datetime]:
    """Parses various date/time representations into a datetime object."""
    if not d_input:
        return None
    if isinstance(d_input, datetime):
        return d_input
    d_str = str(d_input).strip()
    if not d_str:
        return None

    # Replace colons in EXIF date like "2026:09:12"
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y:%m:%d %H:%M:%S",
        "%Y:%m:%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
    ]
    # Strip timezone or fractional seconds if needed
    cleaned = d_str[:19].replace("T", " ")
    for fmt in formats:
        try:
            return datetime.strptime(d_str, fmt)
        except Exception:
            pass
        try:
            return datetime.strptime(cleaned, fmt)
        except Exception:
            pass
    return None

def clean_vehicle_no(s: Optional[str]) -> str:
    """Normalizes vehicle registration numbers for matching."""
    if not s:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()

class ClaimPipelineResult(tuple):
    def __new__(cls, evidence, statuses, r_claim, extras):
        return super().__new__(cls, (evidence, statuses, r_claim, extras))

    def __init__(self, evidence, statuses, r_claim, extras):
        self.evidence = evidence
        self.statuses = statuses
        self.r_claim = r_claim
        self.risk = r_claim
        self.extras = extras
        self.score = type("Score", (), {
            "risk": r_claim,
            "band": "HIGH" if r_claim >= 0.70 else ("MEDIUM" if r_claim >= 0.40 else "LOW")
        })()
        self.checks_run = [
            type("Check", (), {
                "detector": s.detector,
                "status": s.status,
                "duration_ms": s.duration_ms,
                "reason": getattr(s, "reason", None) or getattr(s, "error", None) or "OK"
            })()
            for s in statuses
        ]

    def __await__(self):
        async def _identity():
            return self
        return _identity().__await__()

def run_claim_pipeline(
    ctx: Any = None,
    claim_metadata: Optional[Dict[str, Any]] = None,
    images_metadata: Optional[List[Dict[str, Any]]] = None,
    doc_extracted_fields: Optional[Dict[str, Any]] = None,
    identity_info: Optional[Dict[str, Any]] = None
) -> ClaimPipelineResult:
    """
    Executes all claim cross-checks (§14).
    Returns ClaimPipelineResult (unpackable as (evidence_list, statuses, r_claim, extras) and awaitable).
    """
    scratch = getattr(ctx, "scratch", {}) if ctx else {}
    meta = claim_metadata or scratch.get("claim_metadata") or scratch.get("metadata") or {}
    if not isinstance(meta, dict):
        try:
            meta = meta.model_dump()
        except Exception:
            meta = {}

    current_claim_id = meta.get("claim_id") or scratch.get("claim_id")
    current_claimant_id = meta.get("claimant_user_id") or scratch.get("claimant_id")
    current_claimant_name = meta.get("claimant_name", "")

    # Fetch policy if policy_number present
    pol_no = meta.get("policy_number") or meta.get("policy_id")
    policy = scratch.get("policy")
    if not policy and pol_no:
        from ..db.repository import get_policy
        policy = get_policy(pol_no)
    policy = policy or {}

    images_data = images_metadata if images_metadata is not None else scratch.get("images_data", [])
    doc_fields = doc_extracted_fields if doc_extracted_fields is not None else (scratch.get("document_fields", {}) or {})
    identity_info = identity_info if identity_info is not None else (scratch.get("identity_info", {}) or {})
    voice_fields = scratch.get("voice_fields", {}) or {}

    evidence: List[Evidence] = []
    statuses: List[DetectorStatus] = []
    extras: Dict[str, Any] = {"cross_checks": []}

    # ──────────────────────────────────────────────────────────────────────────
    # Check 1: CLM-X-01 - Photo capture date BEFORE incident date
    # ──────────────────────────────────────────────────────────────────────────
    t0 = datetime.utcnow()
    inc_date = parse_date_safe(meta.get("incident_date"))
    has_photo_dates = False
    flagged_photo_date = False

    if inc_date:
        for idx, img in enumerate(images_data):
            exif = img.get("exif_summary") or {}
            dt_orig_str = exif.get("datetime_original") or img.get("exif_datetime") or img.get("datetime_original")
            if dt_orig_str:
                has_photo_dates = True
                p_date = parse_date_safe(dt_orig_str)
                if p_date and p_date.date() < inc_date.date():
                    delta_days = (inc_date.date() - p_date.date()).days
                    flagged_photo_date = True
                    cat = EVIDENCE_CATALOG.get("CLM-X-01", {"weight": 0.40, "title": "Photo Outside Incident Window"})
                    p_str = p_date.strftime("%d %b %Y")
                    inc_str = inc_date.strftime("%d %b %Y")
                    reason = f"Photo taken {p_str}, {delta_days} days before the stated incident on {inc_str}."
                    
                    ev = Evidence(
                        id="CLM-X-01",
                        pipeline="claim",
                        source="rules",
                        kind="risk",
                        raw_score=0.85,
                        calibrated_score=0.85,
                        weight=cat["weight"],
                        effective_weight=cat["weight"],
                        severity="high",
                        title=cat["title"],
                        reason=reason,
                        details={
                            "days": delta_days,
                            "delta_days": delta_days,
                            "photo_date": p_date.strftime("%Y-%m-%d"),
                            "incident_date": inc_date.strftime("%Y-%m-%d"),
                            "image_slot": img.get("slot", f"img_{idx+1}")
                        }
                    )
                    evidence.append(ev)
                    break

    dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
    if not inc_date:
        statuses.append(DetectorStatus(detector="claim:check_photo_incident_date", status="skipped", duration_ms=dur_ms, reason="Stated incident date missing from claim metadata"))
    elif not has_photo_dates:
        statuses.append(DetectorStatus(detector="claim:check_photo_incident_date", status="skipped", duration_ms=dur_ms, reason="Photos lack EXIF capture timestamps"))
    else:
        status_word = "ok" if not flagged_photo_date else "ok"
        statuses.append(DetectorStatus(detector="claim:check_photo_incident_date", status=status_word, duration_ms=dur_ms, reason="Photo capture timestamp evaluated"))

    # ──────────────────────────────────────────────────────────────────────────
    # Check 2: CLM-X-06 - Photo GPS far from stated incident location
    # ──────────────────────────────────────────────────────────────────────────
    t0 = datetime.utcnow()
    claimed_loc = meta.get("incident_location")
    if isinstance(claimed_loc, str):
        try:
            claimed_loc = json.loads(claimed_loc)
        except Exception:
            if "," in claimed_loc:
                parts = claimed_loc.split(",")
                try:
                    claimed_loc = {"lat": float(parts[0].strip()), "lng": float(parts[1].strip())}
                except Exception:
                    claimed_loc = None
            else:
                claimed_loc = None
    elif not isinstance(claimed_loc, dict):
        claimed_loc = None

    claimed_lat = claimed_loc.get("lat") if claimed_loc else None
    claimed_lng = claimed_loc.get("lng") if claimed_loc else None
    has_gps = False
    flagged_gps = False
    gps_photos_info = []
    max_dist = 0.0

    if claimed_lat is not None and claimed_lng is not None:
        try:
            c_lat = float(claimed_lat)
            c_lng = float(claimed_lng)
            for idx, img in enumerate(images_data):
                exif = img.get("exif_summary") or {}
                coords = exif.get("gps")
                if not coords and img.get("gps_lat") is not None and img.get("gps_lng") is not None:
                    coords = {"lat": img.get("gps_lat"), "lng": img.get("gps_lng")}
                slot_name = img.get("slot", f"photo_{idx+1}")
                if coords and coords.get("lat") is not None and coords.get("lng") is not None:
                    has_gps = True
                    p_lat = float(coords["lat"])
                    p_lng = float(coords["lng"])
                    dist_km = haversine_km(c_lat, c_lng, p_lat, p_lng)
                    if dist_km > max_dist:
                        max_dist = dist_km
                    gps_photos_info.append({
                        "image": slot_name,
                        "lat": p_lat,
                        "lng": p_lng,
                        "distance_km": dist_km
                    })
                    if dist_km > 50.0 and not flagged_gps:
                        flagged_gps = True
                        cat = EVIDENCE_CATALOG.get("CLM-X-06", {"weight": 0.35, "title": "Photo GPS Far from Stated Location"})
                        reason = f"The photo was taken {dist_km:.0f} km from the location given for the incident."
                        ev = Evidence(
                            id="CLM-X-06",
                            pipeline="claim",
                            source="rules",
                            kind="risk",
                            raw_score=0.80,
                            calibrated_score=0.80,
                            weight=cat["weight"],
                            effective_weight=cat["weight"],
                            severity="medium",
                            title=cat["title"],
                            reason=reason,
                            details={
                                "distance_km": round(dist_km, 1),
                                "claimed_lat": c_lat,
                                "claimed_lng": c_lng,
                                "photo_lat": p_lat,
                                "photo_lng": p_lng,
                                "slot": slot_name
                            }
                        )
                        evidence.append(ev)
        except Exception as e:
            logger.warning(f"Error computing GPS distances: {e}")

    dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
    if claimed_lat is None or claimed_lng is None:
        statuses.append(DetectorStatus(detector="claim:check_photo_gps_location", status="skipped", duration_ms=dur_ms, reason="No incident location coordinates provided"))
    elif not has_gps:
        statuses.append(DetectorStatus(detector="claim:check_photo_gps_location", status="skipped", duration_ms=dur_ms, reason="Photos lack GPS coordinates (common after messaging apps)"))
    else:
        statuses.append(DetectorStatus(detector="claim:check_photo_gps_location", status="ok", duration_ms=dur_ms, reason=f"Photo GPS evaluated (max distance {max_dist:.1f} km)"))

    extras["location"] = {
        "claimed": {
            "lat": float(claimed_lat) if claimed_lat is not None else None,
            "lng": float(claimed_lng) if claimed_lng is not None else None,
            "text": claimed_loc.get("text", "") if claimed_loc else ""
        },
        "photos": gps_photos_info,
        "max_distance_km": round(max_dist, 1)
    }

    # ──────────────────────────────────────────────────────────────────────────
    # Check 3: CLM-X-02 - Document total differs from claimed amount
    # ──────────────────────────────────────────────────────────────────────────
    t0 = datetime.utcnow()
    claimed_amt = meta.get("claimed_amount")
    doc_amt_obj = doc_fields.get("total_amount")
    doc_amt = doc_amt_obj.get("value") if isinstance(doc_amt_obj, dict) else (doc_amt_obj if isinstance(doc_amt_obj, (int, float)) else None)
    
    if doc_amt is None and doc_fields.get("subtotal"):
        sub_obj = doc_fields.get("subtotal")
        doc_amt = sub_obj.get("value") if isinstance(sub_obj, dict) else sub_obj

    if doc_amt is not None and claimed_amt is not None:
        try:
            d_val = float(doc_amt)
            c_val = float(claimed_amt)
            diff = abs(d_val - c_val)
            if diff > 1.0:
                cat = EVIDENCE_CATALOG.get("CLM-X-02", {"weight": 0.50, "title": "Claim Amount Mismatch"})
                reason = f"The document total (INR {d_val:,.2f}) differs from the amount claimed (INR {c_val:,.2f})."
                ev = Evidence(
                    id="CLM-X-02",
                    pipeline="claim",
                    source="rules",
                    kind="risk",
                    raw_score=0.85,
                    calibrated_score=0.85,
                    weight=cat["weight"],
                    effective_weight=cat["weight"],
                    severity="high",
                    title=cat["title"],
                    reason=reason,
                    details={"doc": d_val, "claimed": c_val, "diff": round(diff, 2), "delta": round(diff, 2)}
                )
                evidence.append(ev)
            dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
            statuses.append(DetectorStatus(detector="claim:check_amount_match", status="ok", duration_ms=dur_ms, reason="Amount comparison complete"))
        except Exception:
            statuses.append(DetectorStatus(detector="claim:check_amount_match", status="failed", duration_ms=0, reason="Amount parsing error"))
    else:
        dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
        statuses.append(DetectorStatus(detector="claim:check_amount_match", status="skipped", duration_ms=dur_ms, reason="Document total or claimed amount missing"))

    # ──────────────────────────────────────────────────────────────────────────
    # Check 4: CLM-X-08 & CLM-CHRONO-01 - Bill date / chronology checks
    # ──────────────────────────────────────────────────────────────────────────
    t0 = datetime.utcnow()
    doc_dates = doc_fields.get("dates", [])
    if not isinstance(doc_dates, list):
        doc_dates = [doc_dates] if doc_dates else []
    else:
        doc_dates = list(doc_dates)
    if doc_fields.get("invoice_date"):
        doc_dates.append(doc_fields.get("invoice_date"))
    flagged_bill_date = False
    
    if inc_date and doc_dates:
        parsed_doc_dates = []
        for d_item in doc_dates:
            dt_txt = d_item.get("text") if isinstance(d_item, dict) else str(d_item)
            dt_p = parse_date_safe(dt_txt)
            if dt_p:
                parsed_doc_dates.append(dt_p)

        if parsed_doc_dates:
            earliest_doc_date = min(parsed_doc_dates)
            if earliest_doc_date.date() < inc_date.date():
                flagged_bill_date = True
                delta = (inc_date.date() - earliest_doc_date.date()).days
                cat = EVIDENCE_CATALOG.get("CLM-X-08", {"weight": 0.45, "title": "Bill Dated Before Incident"})
                reason = f"The repair invoice / bill is dated {earliest_doc_date.strftime('%d %b %Y')}, before the incident on {inc_date.strftime('%d %b %Y')}."
                ev = Evidence(
                    id="CLM-X-08",
                    pipeline="claim",
                    source="rules",
                    kind="risk",
                    raw_score=0.85,
                    calibrated_score=0.85,
                    weight=cat["weight"],
                    effective_weight=cat["weight"],
                    severity="high",
                    title=cat["title"],
                    reason=reason,
                    details={
                        "doc_kind": "invoice/bill",
                        "doc_date": earliest_doc_date.strftime("%Y-%m-%d"),
                        "incident_date": inc_date.strftime("%Y-%m-%d"),
                        "days_before": delta
                    }
                )
                evidence.append(ev)

    # Check medical chronology (discharge before admission)
    adm_date = parse_date_safe(doc_fields.get("admission_date"))
    dis_date = parse_date_safe(doc_fields.get("discharge_date"))
    if adm_date and dis_date:
        if dis_date.date() < adm_date.date():
            cat = EVIDENCE_CATALOG.get("CLM-CHRONO-01", {"weight": 0.50, "title": "Invalid Medical Chronology"})
            reason = f"Discharge date ({dis_date.strftime('%d %b %Y')}) occurs before admission date ({adm_date.strftime('%d %b %Y')})."
            ev = Evidence(
                id="CLM-CHRONO-01",
                pipeline="claim",
                source="rules",
                kind="risk",
                raw_score=0.85,
                calibrated_score=0.85,
                weight=cat["weight"],
                effective_weight=cat["weight"],
                severity="high",
                title=cat["title"],
                reason=reason,
                details={"reason": reason}
            )
            evidence.append(ev)

    dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
    if not doc_dates and not (adm_date and dis_date):
        statuses.append(DetectorStatus(detector="claim:check_chronology", status="skipped", duration_ms=dur_ms, reason="No document dates available for chronology check"))
    else:
        statuses.append(DetectorStatus(detector="claim:check_chronology", status="ok", duration_ms=dur_ms, reason="Chronology evaluation complete"))

    # ──────────────────────────────────────────────────────────────────────────
    # Check 5: CLM-X-03 - Name on bill vs policyholder / insured members
    # ──────────────────────────────────────────────────────────────────────────
    t0 = datetime.utcnow()
    doc_name = doc_fields.get("customer_name") or doc_fields.get("patient_name")
    pol_holder = policy.get("holder_user_id") or current_claimant_name
    # Check insured members in policy details
    insured_members = []
    pol_details = policy.get("details") or {}
    if isinstance(pol_details, dict):
        insured_members = pol_details.get("insured_members", [])

    candidate_names = [pol_holder] + insured_members
    candidate_names = [c for c in candidate_names if c]

    if doc_name and candidate_names:
        best_ratio = max(fuzz.token_sort_ratio(str(doc_name).lower(), str(cand).lower()) for cand in candidate_names)
        if best_ratio < 70:
            cat = EVIDENCE_CATALOG.get("CLM-X-03", {"weight": 0.45, "title": "Name Mismatch on Bill vs Policy"})
            reason = f"The name on the bill ('{doc_name}') differs from the policyholder ('{pol_holder}')."
            ev = Evidence(
                id="CLM-X-03",
                pipeline="claim",
                source="rules",
                kind="risk",
                raw_score=0.85,
                calibrated_score=0.85,
                weight=cat["weight"],
                effective_weight=cat["weight"],
                severity="high",
                title=cat["title"],
                reason=reason,
                details={
                    "doc_name": str(doc_name),
                    "id_name": str(pol_holder),
                    "ratio": round(best_ratio / 100.0, 2)
                }
            )
            evidence.append(ev)
        dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
        statuses.append(DetectorStatus(detector="claim:check_bill_name", status="ok", duration_ms=dur_ms, reason="Name matching evaluated"))
    else:
        dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
        statuses.append(DetectorStatus(detector="claim:check_bill_name", status="skipped", duration_ms=dur_ms, reason="Customer/patient name not extracted from document"))

    # ──────────────────────────────────────────────────────────────────────────
    # Check 6: CLM-X-07 - Incident date outside policy validity
    # ──────────────────────────────────────────────────────────────────────────
    t0 = datetime.utcnow()
    pol_start = parse_date_safe(policy.get("start_date") or meta.get("policy_start"))
    pol_end = parse_date_safe(policy.get("end_date") or meta.get("policy_end"))

    if inc_date and (pol_start or pol_end):
        is_outside = False
        if pol_start and inc_date.date() < pol_start.date():
            is_outside = True
        if pol_end and inc_date.date() > pol_end.date():
            is_outside = True

        if is_outside:
            cat = EVIDENCE_CATALOG.get("CLM-X-07", {"weight": 0.45, "title": "Evidence Dated Before Policy Start"})
            start_str = pol_start.strftime("%d %b %Y") if pol_start else "N/A"
            end_str = pol_end.strftime("%d %b %Y") if pol_end else "N/A"
            reason = f"The incident is dated {inc_date.strftime('%d %b %Y')}, outside the policy validity period ({start_str} to {end_str})."
            ev = Evidence(
                id="CLM-X-07",
                pipeline="claim",
                source="rules",
                kind="risk",
                raw_score=0.90,
                calibrated_score=0.90,
                weight=cat["weight"],
                effective_weight=cat["weight"],
                severity="high",
                title=cat["title"],
                reason=reason,
                details={
                    "item": "incident",
                    "item_date": inc_date.strftime("%Y-%m-%d"),
                    "policy_start": start_str,
                    "policy_end": end_str
                }
            )
            evidence.append(ev)
        dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
        statuses.append(DetectorStatus(detector="claim:check_policy_validity", status="ok", duration_ms=dur_ms, reason="Policy validity window evaluated"))
    else:
        dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
        statuses.append(DetectorStatus(detector="claim:check_policy_validity", status="skipped", duration_ms=dur_ms, reason="Policy start/end dates or incident date missing"))

    # ──────────────────────────────────────────────────────────────────────────
    # Check 7: CLM-VEH-01 - Vehicle number on estimate vs policy
    # ──────────────────────────────────────────────────────────────────────────
    t0 = datetime.utcnow()
    pol_veh = policy.get("vehicle_or_asset") or meta.get("vehicle_registration")
    doc_veh = doc_fields.get("vehicle_number") or doc_fields.get("vehicle_registration")
    claim_type = meta.get("claim_type") or policy.get("claim_type")

    if (claim_type == "motor" or pol_veh) and pol_veh and doc_veh:
        norm_pol = clean_vehicle_no(pol_veh)
        norm_doc = clean_vehicle_no(doc_veh)
        if norm_pol and norm_doc and norm_pol != norm_doc:
            cat = EVIDENCE_CATALOG.get("CLM-VEH-01", {"weight": 0.60, "title": "Vehicle Number Mismatch"})
            reason = f"The vehicle registration number '{doc_veh}' does not match the insured vehicle '{pol_veh}'."
            ev = Evidence(
                id="CLM-VEH-01",
                pipeline="claim",
                source="rules",
                kind="risk",
                raw_score=0.90,
                calibrated_score=0.90,
                weight=cat["weight"],
                effective_weight=cat["weight"],
                severity="high",
                title=cat["title"],
                reason=reason,
                details={"found": doc_veh, "expected": pol_veh}
            )
            evidence.append(ev)
        dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
        statuses.append(DetectorStatus(detector="claim:check_vehicle_number", status="ok", duration_ms=dur_ms, reason="Vehicle number comparison complete"))
    else:
        dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
        statuses.append(DetectorStatus(detector="claim:check_vehicle_number", status="skipped", duration_ms=dur_ms, reason="Not a motor claim or vehicle number missing from document"))

    # ──────────────────────────────────────────────────────────────────────────
    # Check 8: CLM-ID-01 - Verified ID name vs policyholder
    # ──────────────────────────────────────────────────────────────────────────
    t0 = datetime.utcnow()
    verified_id_name = identity_info.get("verified_name") or identity_info.get("name")
    expected_name = pol_holder or current_claimant_name or meta.get("claimant_name")
    if verified_id_name and expected_name:
        ratio = fuzz.token_sort_ratio(str(verified_id_name).lower(), str(expected_name).lower())
        if ratio < 70:
            cat = EVIDENCE_CATALOG.get("CLM-ID-01", {"weight": 0.50, "title": "ID Name vs Policyholder Mismatch"})
            reason = f"The verified identity name '{verified_id_name}' differs from the policyholder '{expected_name}'."
            ev = Evidence(
                id="CLM-ID-01",
                pipeline="claim",
                source="rules",
                kind="risk",
                raw_score=0.85,
                calibrated_score=0.85,
                weight=cat["weight"],
                effective_weight=cat["weight"],
                severity="high",
                title=cat["title"],
                reason=reason,
                details={"id_name": verified_id_name, "policy_holder": expected_name, "ratio": round(ratio / 100.0, 2)}
            )
            evidence.append(ev)
        dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
        statuses.append(DetectorStatus(detector="claim:check_id_name", status="ok", duration_ms=dur_ms, reason="ID name vs policyholder evaluated"))
    else:
        dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
        statuses.append(DetectorStatus(detector="claim:check_id_name", status="skipped", duration_ms=dur_ms, reason="Identity verification not performed or name unavailable"))

    # ──────────────────────────────────────────────────────────────────────────
    # Check 9: DOC-DUP-01 / CLM-X-04 - Duplicate invoice across other claims
    # ──────────────────────────────────────────────────────────────────────────
    t0 = datetime.utcnow()
    inv_numbers = doc_fields.get("invoice_numbers", [])
    issuer = doc_fields.get("issuer", "")
    flagged_inv_dup = False

    if inv_numbers:
        conn = get_connection()
        for inv_item in inv_numbers:
            inv_txt = inv_item.get("text") if isinstance(inv_item, dict) else str(inv_item)
            if not inv_txt:
                continue
            # Search entities table for existing invoice entity in OTHER claims
            query = """
                SELECT claim_id, display FROM entities
                WHERE kind = 'invoice' AND display LIKE ? AND (claim_id != ? OR claim_id IS NULL)
            """
            row = conn.execute(query, (f"%{inv_txt}%", current_claim_id or "")).fetchone()
            if row:
                flagged_inv_dup = True
                other_cid = row["claim_id"] or "earlier claim"
                cat = EVIDENCE_CATALOG.get("DOC-DUP-01", {"weight": 0.70, "title": "Duplicate Invoice Across Claims"})
                reason = f"The invoice number {inv_txt} from {issuer or 'vendor'} was previously submitted in claim {other_cid}."
                ev = Evidence(
                    id="DOC-DUP-01",
                    pipeline="claim",
                    source="rules",
                    kind="risk",
                    raw_score=0.90,
                    calibrated_score=0.90,
                    weight=cat["weight"],
                    effective_weight=cat["weight"],
                    severity="high",
                    title=cat["title"],
                    reason=reason,
                    details={"invoice_number": inv_txt, "issuer": issuer, "other_id": other_cid}
                )
                evidence.append(ev)
                break
        conn.close()

    dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
    if not inv_numbers:
        statuses.append(DetectorStatus(detector="claim:check_duplicate_document", status="skipped", duration_ms=dur_ms, reason="No invoice number extracted from document"))
    else:
        statuses.append(DetectorStatus(detector="claim:check_duplicate_document", status="ok", duration_ms=dur_ms, reason="Document uniqueness cross-check evaluated"))

    # ──────────────────────────────────────────────────────────────────────────
    # Check 10: Duplicate Image Search across other claims (IMG-DUP-01 / IMG-DUP-02)
    # ──────────────────────────────────────────────────────────────────────────
    t0 = datetime.utcnow()
    flagged_img_dup = False
    from ..detectors.image.duplicates import search_duplicates
    for idx, img in enumerate(images_data):
        img_p = img.get("path")
        slot_name = img.get("slot", f"img_{idx+1}")
        if img_p and os.path.exists(img_p):
            dup_matches = search_duplicates(
                image_path=img_p,
                current_claim_id=current_claim_id,
                current_claimant_id=current_claimant_id,
                current_slot=slot_name
            )
            if dup_matches:
                flagged_img_dup = True
                best = dup_matches[0]
                diff_claimant = best.get("different_claimant", True)
                ev_id = "IMG-DUP-02" if diff_claimant else "IMG-DUP-01"
                cat = EVIDENCE_CATALOG.get(ev_id, EVIDENCE_CATALOG["IMG-DUP-01"])
                sim_pct = int(best["similarity"] * 100)
                other_cid = best.get("other_claim_id") or "another claim"
                masked_name = best.get("other_claimant", "Another Claimant")
                m_type = best.get("match_type", "exact")
                
                if diff_claimant:
                    reason = f"This photo was previously submitted by a different claimant ({masked_name}) in claim {other_cid} ({sim_pct}% similar, {m_type})."
                else:
                    reason = f"This photo closely matches one submitted earlier in claim {other_cid} ({sim_pct}% similar, {m_type})."

                ev = Evidence(
                    id=ev_id,
                    pipeline="claim",
                    source="duplicates",
                    kind="risk",
                    raw_score=round(best["similarity"], 3),
                    calibrated_score=round(best["similarity"], 3),
                    weight=cat["weight"],
                    effective_weight=cat["weight"],
                    severity="high",
                    title=cat["title"],
                    reason=reason,
                    details={
                        "other_id": other_cid,
                        "other_claim_id": other_cid,
                        "other_claimant": masked_name,
                        "similarity": best["similarity"],
                        "sim": best["similarity"],
                        "match_type": m_type,
                        "different_claimant": diff_claimant,
                        "thumbnail_earlier": best.get("thumbnail_earlier")
                    }
                )
                evidence.append(ev)

    dur_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
    if not images_data:
        statuses.append(DetectorStatus(detector="claim:check_duplicate_images", status="skipped", duration_ms=dur_ms, reason="No claim photos available for duplicate search"))
    else:
        statuses.append(DetectorStatus(detector="claim:check_duplicate_images", status="ok", duration_ms=dur_ms, reason="Duplicate image search complete"))

    # ──────────────────────────────────────────────────────────────────────────
    # Check 11: Network Intelligence (CLM-NET-01, CLM-NET-02) (§14.3)
    # ──────────────────────────────────────────────────────────────────────────
    t0_net = datetime.utcnow()
    try:
        from ..services.network import get_claim_network_info
        if current_claim_id:
            net_info = get_claim_network_info(current_claim_id)
            for nev in net_info.get("evidence", []):
                ev = Evidence(
                    id=nev["id"],
                    pipeline="claim",
                    source="network",
                    kind="risk",
                    weight=nev["weight"],
                    effective_weight=nev["weight"],
                    raw_score=nev["raw_score"],
                    calibrated_score=nev["calibrated_score"],
                    severity="high" if nev["raw_score"] >= 0.65 else "medium",
                    title=nev["title"],
                    reason=nev["reason"],
                    details={"rings": net_info.get("rings", []), "shared": net_info.get("shared_identifiers", [])}
                )
                evidence.append(ev)
            extras["network"] = net_info
        dur_net = int((datetime.utcnow() - t0_net).total_seconds() * 1000)
        statuses.append(DetectorStatus(detector="claim:network_cross_check", status="ok", duration_ms=dur_net, reason="Fraud network correlation completed"))
    except Exception as e:
        logger.warning(f"Error checking network intelligence: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Check 12: Story Review (CLM-STORY-00) (§14.2)
    # ──────────────────────────────────────────────────────────────────────────
    t0_story = datetime.utcnow()
    try:
        from ..detectors.story_reviewer import review_claim_story
        stmt_text = (
            meta.get("description_text") or
            meta.get("description") or
            (voice_fields.get("translation_en") if isinstance(voice_fields, dict) else "") or
            (voice_fields.get("transcript") if isinstance(voice_fields, dict) else "") or
            ""
        )
        if stmt_text:
            story_status, story_ev = review_claim_story(
                statement_text=stmt_text,
                form_metadata=meta,
                document_facts=doc_fields,
                photo_facts=images_data,
                existing_evidence=evidence
            )
            if story_ev:
                evidence.append(story_ev)
            extras["story"] = story_status
            dur_story = int((datetime.utcnow() - t0_story).total_seconds() * 1000)
            statuses.append(DetectorStatus(detector="claim:story_review", status="ok", duration_ms=dur_story, reason="Story consistency evaluated"))
        else:
            dur_story = int((datetime.utcnow() - t0_story).total_seconds() * 1000)
            statuses.append(DetectorStatus(detector="claim:story_review", status="skipped", duration_ms=dur_story, reason="No statement narrative provided"))
    except Exception as e:
        logger.warning(f"Error checking story review: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Calculate R_claim Pseudo-Pipeline Risk
    # ──────────────────────────────────────────────────────────────────────────
    risk_ev = [e for e in evidence if e.kind == "risk"]
    if risk_ev:
        ev_dicts = [e.model_dump() for e in risk_ev]
        r_claim, contribs = compute_fusion_with_contributions(ev_dicts)
        for e in evidence:
            c = contribs.get(e.id, 0.0)
            e.contribution = c
            e.contribution_pct = round((c / r_claim * 100.0), 1) if r_claim > 0 else 0.0
            e.details = e.details or {}
            e.details["contribution"] = c
    else:
        r_claim = 0.05

    extras["r_claim"] = round(r_claim, 4)
    return ClaimPipelineResult(evidence, statuses, r_claim, extras)
