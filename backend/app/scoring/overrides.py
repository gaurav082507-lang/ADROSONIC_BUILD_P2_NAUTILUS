from typing import List, Tuple, Dict, Any, Optional

OVERRIDE_RULES = {
    "O1": {
        "condition": lambda ids, ptype: "IMG-C2PA-01" in ids and ptype in ("image", "overall"),
        "floor": 0.95,
        "entry": "Rule O1 applied: content credentials state the image is AI-generated."
    },
    "O2": {
        "condition": lambda ids, ptype: "DOC-LOGIC-01" in ids and "DOC-CNN-01" in ids and ptype in ("document", "overall"),
        "floor": 0.85,
        "entry": "Rule O2 applied: mathematical mismatch confirmed by tamper detection."
    },
    "O3": {
        "condition": lambda ids, ptype: "ID-FACE-01" in ids and ptype in ("identity", "overall"),
        "floor": 0.80,
        "entry": "Rule O3 applied: face on ID does not match selfie."
    },
    "O4": {
        "condition": lambda ids, ptype: ("IMG-DUP-01" in ids or "IMG-DUP-02" in ids) and ptype == "overall",
        "floor": 0.90,
        "entry": "Rule O4 applied: duplicate image matched against known fraudulent claim."
    },
    "O5": {
        "condition": lambda ids, ptype: "DOC-OVERLAY-01" in ids and ptype in ("document", "overall"),
        "floor": 0.80,
        "entry": "Rule O5 applied: text overlay detected on document."
    },
    "O6": {
        "condition": lambda ids, ptype: "ID-LIVE-01" in ids and "ID-FACE-01" in ids and ptype == "overall",
        "floor": 0.85,
        "entry": "Rule O6 applied: liveness failure combined with facial mismatch."
    },
    "O7": {
        "condition": lambda ids, ptype: "ID-QR-01" in ids and ptype in ("identity", "overall"),
        "floor": 0.85,
        "entry": "Rule O7 applied: Aadhaar QR digital signature is invalid."
    },
}

def apply_overrides(evidence_ids: List[str], current_risk: float, pipeline_type: str = "overall") -> float:
    """
    Applies decisive override rules O1-O7 (§15.6).
    Returns the new risk score (floored at rule threshold).
    """
    risk, _ = apply_overrides_with_entries(evidence_ids, current_risk, pipeline_type)
    return risk

def apply_overrides_with_entries(
    evidence_ids: List[str],
    current_risk: float,
    pipeline_type: str = "overall"
) -> Tuple[float, List[Dict[str, str]]]:
    """
    Applies rules O1-O7 and returns (new_risk, applied_override_entries).
    Each triggered rule is made visible so nothing is hidden.
    """
    risk = float(current_risk)
    applied = []

    for rule_id, rule in OVERRIDE_RULES.items():
        if rule["condition"](evidence_ids, pipeline_type):
            if risk < rule["floor"]:
                risk = rule["floor"]
            applied.append({
                "rule": rule_id,
                "text": rule["entry"],
                "floor": rule["floor"]
            })

    return round(risk, 4), applied
