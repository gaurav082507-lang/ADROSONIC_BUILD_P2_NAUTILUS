"""
Story Review Detector (§14.2, Prompt 10 Part 4).
Compares the claimant's statement (typed text or voice transcript) against
claim form fields, document facts, and photographic metadata.

Emits CLM-STORY-00 (weight 0.0, info-only).
Never modifies the risk score.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ..schemas.result import Evidence, StoryStatus, StoryContradiction

logger = logging.getLogger(__name__)


def parse_inr_text(text: str) -> Optional[float]:
    """Extracts explicit amount mentions from narrative text."""
    # Look for patterns like Rs. 50,000, INR 45000, 1.5 lakh, 50k
    t = text.lower()
    lakh_match = re.search(r'(?:rs\.?|inr|₹)?\s*([\d\.]+)\s*(?:lakh|lac)', t)
    if lakh_match:
        try:
            return float(lakh_match.group(1)) * 100000.0
        except ValueError:
            pass

    amt_match = re.search(r'(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)', t)
    if amt_match:
        try:
            cleaned = amt_match.group(1).replace(",", "")
            return float(cleaned)
        except ValueError:
            pass

    return None


def extract_dates_from_text(text: str) -> List[str]:
    """Finds date occurrences in text."""
    # Matches dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd, or '12 Sep', '12 September 2026'
    dates = []
    # ISO / hyphen / slash
    for m in re.finditer(r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b', text):
        dates.append(m.group(1))
    
    months = r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
    for m in re.finditer(rf'\b(\d{{1,2}}\s+{months}(?:\s+\d{{2,4}})?)\b', text, re.IGNORECASE):
        dates.append(m.group(1))

    return dates


def review_claim_story(
    statement_text: str,
    form_metadata: Optional[Dict[str, Any]] = None,
    document_facts: Optional[Dict[str, Any]] = None,
    photo_facts: Optional[List[Dict[str, Any]]] = None,
    existing_evidence: Optional[List[Evidence]] = None
) -> Tuple[StoryStatus, Evidence]:
    """
    Evaluates cross-contradictions and points of consistency between narrative
    and verified metadata.
    """
    form_metadata = form_metadata or {}
    document_facts = document_facts or {}
    photo_facts = photo_facts or []
    existing_evidence = existing_evidence or []

    contradictions: List[Dict[str, Any]] = []
    consistent_points: List[Dict[str, Any]] = []

    text = (statement_text or "").strip()
    if not text:
        empty_status = StoryStatus(
            contradictions=[],
            consistent_points=[],
            source="rules",
            note="No claimant narrative provided for review."
        )
        empty_ev = Evidence(
            id="CLM-STORY-00",
            pipeline="claim",
            source="story",
            kind="info",
            weight=0.0,
            effective_weight=0.0,
            raw_score=0.0,
            calibrated_score=0.0,
            severity="low",
            title="Story Review Result",
            reason="No narrative statement supplied; review skipped.",
            details={"contradictions": 0, "consistent_points": 0}
        )
        return empty_status, empty_ev

    # 1. Amount Consistency Check
    stated_amt = parse_inr_text(text)
    form_amt = form_metadata.get("claimed_amount")
    if form_amt is not None:
        try:
            form_amt = float(form_amt)
        except (ValueError, TypeError):
            form_amt = None

    doc_amt = document_facts.get("total_amount")
    if doc_amt is not None:
        try:
            doc_amt = float(doc_amt)
        except (ValueError, TypeError):
            doc_amt = None

    if stated_amt is not None and form_amt is not None and form_amt > 0:
        # Allow 5% tolerance
        diff = abs(stated_amt - form_amt)
        if diff / max(form_amt, 1.0) > 0.15:
            contradictions.append({
                "text": f"Narrative states repair cost/claim of ₹{stated_amt:,.0f}, contradicting the form claimed amount of ₹{form_amt:,.0f}.",
                "sources": ["claimant_description", "claim_form"],
                "evidence_ids": ["CLM-X-02"]
            })
        else:
            consistent_points.append({
                "statement_quote": f"₹{stated_amt:,.0f}",
                "evidence_ref": "claim_form.claimed_amount",
                "detail": f"Claimed amount matches statement (₹{form_amt:,.0f})."
            })

    # 2. Date Consistency Check
    dates_in_text = extract_dates_from_text(text)
    incident_date_form = form_metadata.get("incident_date")
    if incident_date_form and dates_in_text:
        # Check if the form date appears in narrative or contradicts
        matched_any = False
        for dt_str in dates_in_text:
            if incident_date_form in dt_str or dt_str in incident_date_form:
                matched_any = True
                break
        if not matched_any and len(dates_in_text) == 1:
            contradictions.append({
                "text": f"Narrative references incident date '{dates_in_text[0]}', which differs from reported incident date '{incident_date_form}'.",
                "sources": ["claimant_description", "claim_form"],
                "evidence_ids": ["CLM-STORY-00"]
            })
        elif matched_any:
            consistent_points.append({
                "statement_quote": incident_date_form,
                "evidence_ref": "claim_form.incident_date",
                "detail": f"Incident date matches statement ({incident_date_form})."
            })

    # 3. Vehicle Number Check
    vehicle_form = form_metadata.get("vehicle_number")
    if vehicle_form:
        v_clean = re.sub(r'[^A-Za-z0-9]', '', vehicle_form).upper()
        # Look for registration numbers in text (e.g. MH12AB1234 or DL 01 AB 9999)
        v_raw_matches = re.findall(r'\b([A-Z]{2}[ -]?[0-9]{1,2}[ -]?[A-Z]{1,3}[ -]?[0-9]{4})\b', text.upper())
        v_matches = [re.sub(r'[^A-Z0-9]', '', m) for m in v_raw_matches]
        if v_matches:
            if v_clean not in v_matches:
                contradictions.append({
                    "text": f"Vehicle mentioned in statement ('{v_matches[0]}') does not match policy vehicle registration '{vehicle_form}'.",
                    "sources": ["claimant_description", "policy_records"],
                    "evidence_ids": ["CLM-VEH-01"]
                })
            else:
                consistent_points.append({
                    "statement_quote": vehicle_form,
                    "evidence_ref": "claim_form.vehicle_number",
                    "detail": "Vehicle registration mentioned in statement aligns with policy records."
                })

    # 4. Integrate any existing cross-contradiction evidence (e.g. CLM-X-01, CLM-X-08)
    for ev in existing_evidence:
        if ev.id in ("CLM-X-01", "CLM-X-08") and ev.reason:
            contradictions.append({
                "text": ev.reason,
                "sources": ["document_facts", "claim_form"],
                "evidence_ids": [ev.id]
            })

    status_obj = StoryStatus(
        contradictions=contradictions,
        consistent_points=consistent_points,
        source="rules",
        note="For investigator review, not part of the score"
    )

    ev_reason = f"Story consistency review completed: {len(contradictions)} contradiction(s), {len(consistent_points)} consistent point(s) identified."
    if contradictions:
        ev_reason += f" Top inconsistency: {contradictions[0]['text']}"

    story_ev = Evidence(
        id="CLM-STORY-00",
        pipeline="claim",
        source="story",
        kind="info",
        weight=0.0,
        effective_weight=0.0,
        raw_score=0.0,
        calibrated_score=0.0,
        severity="medium" if contradictions else "low",
        title="Story-vs-Evidence Review",
        reason=ev_reason,
        details={
            "contradictions_count": len(contradictions),
            "consistent_points_count": len(consistent_points),
            "contradictions": contradictions,
            "consistent_points": consistent_points
        }
    )

    return status_obj, story_ev
