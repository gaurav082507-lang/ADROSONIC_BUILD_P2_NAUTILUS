"""
Synthetic Voice Detector (Spoof Detector)
Uses HuggingFace pre-trained Wav2Vec2 audio deepfake classification model.
Evaluates calibration status against evaluation dataset in data/eval/voice/{real,synthetic}/.
Emits VOI-SPOOF-01 evidence.
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
import numpy as np

from ...core.config import settings
from ...schemas.evidence import Evidence
from ...schemas.result import DetectorStatus
from ...scoring.weights import EVIDENCE_CATALOG

logger = logging.getLogger(__name__)

DEFAULT_VOICE_MODEL = "mo-thecreator/Deepfake-audio-detection"
CALIBRATION_FILE = Path("models/calibration.json")
EVAL_REAL_DIR = Path("data/eval/voice/real")
EVAL_SYNTH_DIR = Path("data/eval/voice/synthetic")

_feature_extractor = None
_model = None
_model_failed = False
_id2label = {}


def _get_eval_counts() -> Tuple[int, int]:
    """Returns (real_count, synth_count) from data/eval/voice/."""
    real_count = len(list(EVAL_REAL_DIR.glob("*.wav"))) if EVAL_REAL_DIR.exists() else 0
    synth_count = len(list(EVAL_SYNTH_DIR.glob("*.wav"))) if EVAL_SYNTH_DIR.exists() else 0
    return real_count, synth_count


def _load_model():
    """Lazy loads the HuggingFace audio deepfake classification model."""
    global _feature_extractor, _model, _model_failed, _id2label
    if _model_failed:
        return None, None
    if _model is not None and _feature_extractor is not None:
        return _feature_extractor, _model

    model_id = settings.VOICE_MODEL_ID or DEFAULT_VOICE_MODEL
    try:
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        logger.info(f"Loading synthetic voice detector: {model_id}")
        _feature_extractor = AutoFeatureExtractor.from_pretrained(model_id)
        _model = AutoModelForAudioClassification.from_pretrained(model_id)
        _model.eval()
        _id2label = getattr(_model.config, "id2label", {0: "fake", 1: "real"})
        return _feature_extractor, _model
    except Exception as e:
        logger.error(f"Failed to load synthetic voice model {model_id}: {e}")
        _model_failed = True
        return None, None


def classify_speech(
    samples_list: List[np.ndarray],
    duration_s: float,
    is_poor_quality: bool = False
) -> Tuple[Optional[Evidence], DetectorStatus]:
    """
    Runs synthetic voice detection on audio samples.
    Handles chunked audio by evaluating each chunk and taking maximum spoof probability.
    Respects calibration rules (§15.2, §17.11) and AUC-to-weight mapping.
    """
    start_time = time.time()
    model_id = settings.VOICE_MODEL_ID or DEFAULT_VOICE_MODEL

    extractor, model = _load_model()
    if model is None or extractor is None:
        duration_ms = int((time.time() - start_time) * 1000)
        return None, DetectorStatus(
            detector="spoof",
            status="failed",
            duration_ms=duration_ms,
            error=f"Model {model_id} failed to load."
        )

    try:
        # Determine fake index in id2label
        fake_idx = 0
        for idx, lbl in _id2label.items():
            if str(lbl).lower() in ("fake", "spoof", "synthetic"):
                fake_idx = int(idx)
                break

        chunk_probs = []
        chunk_raw_logits = []

        for chunk in samples_list:
            if len(chunk) < 1600:  # < 0.1s
                continue
            inputs = extractor(chunk, sampling_rate=16000, return_tensors="pt")
            import torch
            with torch.no_grad():
                logits = model(**inputs).logits.squeeze()
                probs = torch.softmax(logits, dim=-1)
                p_fake = float(probs[fake_idx].item())
                chunk_probs.append(p_fake)
                chunk_raw_logits.append(float(logits[fake_idx].item()))

        if not chunk_probs:
            raw_p = 0.0
            raw_logit = 0.0
        else:
            # Maximum spoof probability across chunks
            raw_p = float(np.max(chunk_probs))
            raw_logit = float(np.max(chunk_raw_logits))

        # Check calibration status: requires >= 15 samples per class AND calibrated entry in calibration.json
        real_count, synth_count = _get_eval_counts()
        voice_calibrated_in_file = False
        if CALIBRATION_FILE.exists():
            try:
                with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                    cal_data = json.load(f)
                    voice_calibrated_in_file = ("VOI-SPOOF-01" in cal_data.get("auc", {})) or bool(cal_data.get("voice_calibrated"))
            except Exception:
                pass
        is_calibrated = (real_count >= 15 and synth_count >= 15 and voice_calibrated_in_file)

        catalog_weight = EVIDENCE_CATALOG.get("VOI-SPOOF-01", {}).get("weight", 0.55)

        if not is_calibrated:
            # UNCALIBRATED: emit as info-only (effective_weight = 0.0)
            calibrated_p = raw_p
            effective_weight = 0.0
            kind = "info"
            reason = (
                f"The recorded statement shows patterns of a synthetic or cloned voice "
                f"({raw_p:.0%} raw likelihood); voice classifier uncalibrated – not scored."
            )
        else:
            # CALIBRATED: temperature scaling
            t_voice = 1.0
            if CALIBRATION_FILE.exists():
                try:
                    with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                        cal_data = json.load(f)
                        t_voice = float(cal_data.get("temperature", {}).get("voice", 1.0))
                except Exception:
                    pass

            calibrated_p = float(1.0 / (1.0 + np.exp(-raw_logit / max(t_voice, 0.01))))
            effective_weight = catalog_weight

            # If audio quality warning fired, gate weight by half (50%) per §14.1 / §15.4
            if is_poor_quality:
                effective_weight *= 0.5

            kind = "risk" if calibrated_p >= 0.20 else "info"
            reason = (
                f"The recorded statement shows patterns of a synthetic or cloned voice "
                f"({calibrated_p:.0%} likelihood after calibration)."
            )

        evidence = Evidence(
            id="VOI-SPOOF-01",
            kind=kind,
            raw_score=round(raw_p, 4),
            calibrated_score=round(calibrated_p, 4),
            weight=round(catalog_weight, 4),
            effective_weight=round(effective_weight, 4),
            severity="high" if calibrated_p >= 0.65 else ("medium" if calibrated_p >= 0.35 else "low"),
            title="Synthetic Voice",
            reason=reason,
            details={
                "calibrated": is_calibrated,
                "raw_p": round(raw_p, 4),
                "calibrated_p": round(calibrated_p, 4),
                "duration_s": round(duration_s, 2),
                "quality_ok": not is_poor_quality,
                "model": model_id,
                "real_eval_count": real_count,
                "synth_eval_count": synth_count,
            }
        )

        duration_ms = int((time.time() - start_time) * 1000)
        return evidence, DetectorStatus(
            detector="spoof",
            status="ok",
            duration_ms=duration_ms
        )

    except Exception as exc:
        logger.error(f"Error during synthetic voice inference: {exc}", exc_info=True)
        duration_ms = int((time.time() - start_time) * 1000)
        return None, DetectorStatus(
            detector="spoof",
            status="failed",
            duration_ms=duration_ms,
            error=str(exc)
        )
