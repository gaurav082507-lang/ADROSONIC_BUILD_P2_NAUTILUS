from typing import Dict, Any, Tuple, Optional

QUALITY_GATES = [
    {
        "flag": "short_side_lt_512",
        "affected": {"IMG-AI-01", "IMG-ELA-01", "IMG-NOISE-01"},
        "gate": 0.7,
        "message": "Image resolution low (short side < 512 px); weights discounted by 30%."
    },
    {
        "flag": "jpeg_quality_lt_50",
        "affected": {"IMG-ELA-01", "IMG-NOISE-01"},
        "gate": 0.5,
        "message": "Low JPEG quality (< 50); compression artifacts discounted by 50%."
    },
    {
        "flag": "non_jpeg_or_screenshot",
        "affected": {"IMG-ELA-01"},
        "gate": 0.0,
        "message": "Screenshot or non-JPEG format; ELA detector skipped."
    },
    {
        "flag": "scan_res_lt_100_dpi",
        "affected": {"DOC-CNN-01", "DOC-ANOM-01", "DOC-VIS-01"},
        "gate": 0.6,
        "message": "Scan resolution below 100 dpi equivalent; document tamper detectors discounted by 40%."
    },
    {
        "flag": "high_ocr_failure_rate",
        "affected": {"DOC-LOGIC-01", "DOC-FONT-01", "CLM-X-02"},
        "gate": 0.5,
        "message": "High OCR failure rate; field-based rules discounted by 50%."
    },
]

def apply_quality_gate(
    evidence_id: str,
    raw_weight: float,
    quality_flags: Optional[Dict[str, Any]] = None
) -> Tuple[float, float]:
    """
    Applies quality gating to raw evidence weight (§15.3).
    Poor input reduces the influence of unreliable detectors rather than adding risk.
    effective_weight = weight * gate
    Returns: (effective_weight, gate_factor)
    """
    if not quality_flags:
        return raw_weight, 1.0

    combined_gate = 1.0
    for rule in QUALITY_GATES:
        flag = rule["flag"]
        if quality_flags.get(flag) and evidence_id in rule["affected"]:
            combined_gate = min(combined_gate, rule["gate"])

    effective_weight = round(raw_weight * combined_gate, 4)
    return effective_weight, combined_gate
