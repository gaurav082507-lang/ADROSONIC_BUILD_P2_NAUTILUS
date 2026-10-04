from typing import List, Dict, Any, Tuple
from .templates import TEMPLATES, RECOMMENDED_ACTIONS
from .llm import generate_llm_summary

def compose_template_summary(
    band: str,
    risk: float,
    evidence_list: List[Dict[str, Any]],
    confidence: str = "high"
) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    Composes deterministic summary following the strict grammar (§16.1):
    "[Band] fraud likelihood ([score]%). [Top reason 1]. [Top reason 2]... [Caveat if confidence not high]. Recommended action: [action]."
    """
    # 1. Filter and sort risk items by contribution (or effective weight * score)
    risk_evidence = [e for e in evidence_list if e.get("kind") == "risk"]
    sorted_ev = sorted(
        risk_evidence,
        key=lambda x: float(x.get("contribution", 0.0) or (float(x.get("effective_weight", 0.0)) * float(x.get("calibrated_score", 0.0)))),
        reverse=True
    )

    # Part 2 rule: when IMG-ELA-01 contributes more than IMG-AI-01, lead with edit sentence
    ela_item = next((e for e in sorted_ev if e.get("id") == "IMG-ELA-01"), None)
    ai_item = next((e for e in sorted_ev if e.get("id") == "IMG-AI-01"), None)
    if ela_item and ai_item:
        ela_contrib = float(ela_item.get("contribution", 0.0) or (float(ela_item.get("effective_weight", 0.0)) * float(ela_item.get("calibrated_score", 0.0))))
        ai_contrib = float(ai_item.get("contribution", 0.0) or (float(ai_item.get("effective_weight", 0.0)) * float(ai_item.get("calibrated_score", 0.0))))
        if ela_contrib >= ai_contrib:
            if sorted_ev.index(ela_item) > sorted_ev.index(ai_item):
                sorted_ev.remove(ela_item)
                ai_pos = sorted_ev.index(ai_item)
                sorted_ev.insert(ai_pos, ela_item)

    # Ensure DOC-CNN-01 is never lead summary reason when uncorroborated
    cnn_item = next((e for e in sorted_ev if e.get("id") == "DOC-CNN-01"), None)
    if cnn_item and not (cnn_item.get("details") or {}).get("corroborated", True):
        if len(sorted_ev) > 1 and sorted_ev[0] == cnn_item:
            sorted_ev.remove(cnn_item)
            sorted_ev.append(cnn_item)

    # 2. Select top 3 to 5 reasons
    top_items = sorted_ev[:5] if len(sorted_ev) >= 5 else sorted_ev[:3] if len(sorted_ev) >= 3 else sorted_ev
    reasons = []

    for rank, ev in enumerate(top_items):
        ev_id = ev.get("id")
        p_ai = float(ev.get("calibrated_score") or ev.get("raw_score") or 0.0)

        # DOC-CNN-01 uncorroborated should never lead summary or appear alone on LOW band
        if ev_id == "DOC-CNN-01" and not (ev.get("details") or {}).get("corroborated", True):
            if band == "LOW" or rank == 0:
                continue

        # Part 2 rule: IMG-AI-01 only if calibrated p_ai >= 0.5 AND it is a top-2 contributor
        if ev_id == "IMG-AI-01":
            if p_ai < 0.5 or rank >= 2:
                continue

        template = TEMPLATES.get(ev_id)
        details = ev.get("details") or {}

        if template:
            try:
                # Format template with available details
                formatted = template.format(**details)
            except Exception:
                # Fallback to template string if keys missing
                formatted = template
        else:
            formatted = ev.get("reason") or "Suspicious pattern detected."

        # Ensure sentence ends with a period
        formatted = formatted.strip()
        if not formatted.endswith("."):
            formatted += "."
        reasons.append(formatted)

    # 3. Handle LOW band with no significant items
    if band == "LOW" and not reasons:
        reasons_str = "No anomalous patterns or tamper artifacts were detected."
    else:
        reasons_str = " ".join(reasons)

    # 4. Confidence caveat
    caveat = ""
    if confidence == "medium":
        caveat = " Some secondary forensic checks were inconclusive or limited."
    elif confidence == "low":
        caveat = " Analysis confidence is low due to degraded input quality or limited checks."

    # 5. Recommended action (§16.3)
    action = RECOMMENDED_ACTIONS.get(band, RECOMMENDED_ACTIONS["LOW"])

    # 6. Compose paragraph
    score_pct = int(round(risk * 100))
    summary = f"{band} fraud likelihood ({score_pct}%). {reasons_str}{caveat} Recommended action: {action}"

    # "Why this score" breakdown (§16.5)
    why_this_score = {
        "band": band,
        "risk": risk,
        "confidence": confidence,
        "top_reasons_count": len(reasons),
        "strongest_contributor": (top_items[0].get("title") if top_items else "None")
    }

    return summary, reasons, why_this_score

def format_summary(
    band: str,
    risk: float,
    evidence_list: List[Dict[str, Any]],
    confidence: str = "high"
) -> str:
    """
    Standard entrypoint for summary generation.
    """
    summary, _, _ = compose_template_summary(band, risk, evidence_list, confidence)
    return summary
