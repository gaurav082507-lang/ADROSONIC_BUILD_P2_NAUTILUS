from typing import List, Optional, Any, Set
from ..core.config import settings

CONFIDENCE_LEVELS = ["high", "medium", "low"]

def get_band(risk: float) -> str:
    """
    Classifies risk into bands:
    - LOW: < BAND_LOW_MAX (default 0.35)
    - MEDIUM: 0.35 to < BAND_MED_MAX (default 0.65)
    - HIGH: >= BAND_MED_MAX (default 0.65)
    """
    r = float(risk)
    if r < settings.BAND_LOW_MAX:
        return "LOW"
    elif r < settings.BAND_MED_MAX:
        return "MEDIUM"
    return "HIGH"

def determine_confidence(
    evidence_ids: Optional[List[str]] = None,
    detector_statuses: Optional[List[Any]] = None,
    quality_warnings: Optional[List[Any]] = None,
    sources: Optional[List[str]] = None,
    disagreement: bool = False,
    ood_input: bool = False,
    liveness_missing_on_id: bool = False,
    top_detector_auc: Optional[float] = None,
    initial_conf: str = "high"
) -> str:
    """
    Computes confidence level (high | medium | low) via step-downs (§15.7, §15.10).
    Starts at 'high' and steps down one level for each adverse condition.
    """
    ev_ids = set(evidence_ids or [])
    step_downs = 0

    # 1. Any detector failed
    if detector_statuses:
        for s in detector_statuses:
            status = getattr(s, "status", None) or (s.get("status") if isinstance(s, dict) else None)
            if status == "failed":
                step_downs += 1
                break

    # 2. Quality warning that gated weights by > 30% or checks failed
    if quality_warnings:
        for w in quality_warnings:
            code = getattr(w, "code", "") or (w.get("code") if isinstance(w, dict) else "")
            if code == "CHECKS_FAILED":
                return "low"
            if "DEGRADED" in code or "LOW_RES" in code:
                step_downs += 1
                break

    # 3. Fewer than two independent evidence sources
    if sources and len(set(sources)) < 2:
        step_downs += 1

    # 4. Disagreement between AI detector and forensics
    if disagreement:
        step_downs += 1

    # 5. Out of distribution input
    if ood_input:
        step_downs += 1

    # 6. §15.10: Aadhaar QR unreadable
    if "ID-QR-04" in ev_ids:
        step_downs += 1

    # 7. §15.10: Liveness not performed on a claim with ID document
    if liveness_missing_on_id:
        step_downs += 1

    # 8. Calibration AUC of top-contributing detector is < 0.80
    if top_detector_auc is not None and top_detector_auc < 0.80:
        step_downs += 1

    # Apply step-downs from initial level
    current_idx = CONFIDENCE_LEVELS.index(initial_conf) if initial_conf in CONFIDENCE_LEVELS else 0
    new_idx = min(len(CONFIDENCE_LEVELS) - 1, current_idx + step_downs)
    return CONFIDENCE_LEVELS[new_idx]

def get_severity(effective_weight: float, calibrated_score: float) -> str:
    """
    Computes evidence severity card color:
    val >= 0.50 -> high
    val >= 0.20 -> medium
    else -> low
    """
    val = float(effective_weight) * float(calibrated_score)
    if val >= 0.50:
        return "high"
    elif val >= 0.20:
        return "medium"
    return "low"
