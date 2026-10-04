import os
import json
import math
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

CALIBRATION_FILE = os.path.join(
    os.path.dirname(__file__), "../../../models/calibration.json"
)

# Safe defaults if calibration.json is absent
DEFAULT_CALIBRATION = {
    "temperature": {"ai_detector": 1.0, "tamper_cnn": 1.0, "voice": 1.0},
    "platt": {
        "forensics": {"a": 1.0, "b": 0.0},
        "ela": {"a": 1.0, "b": 0.0},
        "noise": {"a": 1.0, "b": 0.0},
    }
}

_params: Dict[str, Any] = {}

def load_calibration():
    global _params
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                _params = json.load(f)
            logger.info("Loaded models/calibration.json successfully.")
            return
        except Exception as e:
            logger.warning(f"Error loading {CALIBRATION_FILE}: {e}")
    _params = DEFAULT_CALIBRATION

load_calibration()

def calibrate(raw_score: float, source: str) -> float:
    """
    Transforms raw detector statistics into calibrated probabilities in [0, 1].
    - Logit-based (AI detector, tamper CNN, voice): temperature scaling on log-odds.
    - Forensics (ELA, noise): Platt scaling sigmoid(A * raw + B).
    - Rules: identity.
    """
    # Clamp raw score to [0, 1]
    raw = max(0.0, min(1.0, float(raw_score)))

    # Rules are deterministic
    if source == "rules" or source == "aadhaar_qr":
        return raw

    # Temperature scaling
    temps = _params.get("temperature", {})
    if source in temps:
        T = float(temps[source])
        if T <= 0:
            T = 1.0
        # Prevent math domain errors at extremes
        p = max(1e-6, min(1.0 - 1e-6, raw))
        logit = math.log(p / (1.0 - p))
        calibrated = 1.0 / (1.0 + math.exp(-logit / T))
        return round(calibrated, 4)

    # Platt scaling for forensics
    platts = _params.get("platt", {})
    if source in platts:
        cfg = platts[source]
        a = float(cfg.get("a", 1.0))
        b = float(cfg.get("b", 0.0))
        val = -(a * raw + b)
        val = max(-20.0, min(20.0, val))  # overflow protection
        calibrated = 1.0 / (1.0 + math.exp(val))
        return round(calibrated, 4)

    return raw
