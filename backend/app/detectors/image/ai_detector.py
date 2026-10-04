import os
import io
import json
import math
import logging
import torch
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple
from ..base import DetectorOutput, AnalysisContext
from ...schemas.evidence import Evidence
from ...scoring.weights import EVIDENCE_CATALOG
from ...core.model_registry import model_registry

logger = logging.getLogger("lucen_ai.ai_detector")

CALIBRATION_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../models/calibration.json")
)

def get_temperature() -> Tuple[float, bool]:
    """Loads temperature T for AI detector from calibration.json. Returns (T, is_calibrated)."""
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                t = float(data.get("temperature", {}).get("ai_detector", 1.0))
                if t > 0:
                    return t, True
        except Exception:
            pass
    return 1.0, False

class AiImageDetector:
    name: str = "ai_detector"
    timeout_s: float = 30.0

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        model = model_registry.ai_model
        processor = model_registry.ai_processor
        ai_idx = model_registry.ai_class_idx

        if model is None and processor is None and not model_registry.models.get("ai_detector"):
            model_registry.load_ai_detector()
            model = model_registry.ai_model
            processor = model_registry.ai_processor
            ai_idx = model_registry.ai_class_idx

        if model is None or processor is None:
            raise RuntimeError("AI Detector model not loaded in ModelRegistry.")

        if not ctx.decoded_images:
            raise ValueError("No decoded image available in AnalysisContext.")

        img = ctx.decoded_images[0]
        w, h = img.size

        # 1. Primary evaluation
        def score_single(pil_image: Image.Image) -> Tuple[float, float, List[float]]:
            inputs = processor(images=pil_image, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits[0]
                probs = torch.softmax(logits, dim=-1)
                p = float(probs[ai_idx].item())
                # Relative logit (difference from non-AI class)
                other_idx = 1 if ai_idx == 0 else 0
                rel_logit = float((logits[ai_idx] - logits[other_idx]).item())
                raw_logits = [round(float(l.item()), 4) for l in logits]
                return p, rel_logit, raw_logits

        p_orig, logit_orig, raw_logits_orig = score_single(img)

        # 2. Test-Time Augmentation (TTA) with JPEG q85 (diagnostic view)
        p_q85 = None
        has_tta_disagreement = False
        try:
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=85)
            buf.seek(0)
            img_q85 = Image.open(buf)
            p_q85, _, _ = score_single(img_q85)
            tta_diff = abs(p_orig - p_q85)
            has_tta_disagreement = tta_diff > 0.20
        except Exception as e:
            logger.debug(f"TTA q85 evaluation skipped: {e}")

        # 3. Large image center crop evaluation (diagnostic view)
        crop_scored = False
        p_crop = None
        if min(w, h) >= 768:
            try:
                crop_size = 512
                left = (w - crop_size) // 2
                top = (h - crop_size) // 2
                center_crop = img.crop((left, top, left + crop_size, top + crop_size))
                p_crop, _, _ = score_single(center_crop)
                crop_scored = True
            except Exception as e:
                logger.debug(f"Center crop evaluation skipped: {e}")

        # Runtime matches calibration path: unaugmented whole image prediction
        p_ai = max(0.0001, min(0.9999, p_orig))

        # 4. Temperature calibration
        T, is_calibrated = get_temperature()
        logit = math.log(p_ai / (1.0 - p_ai))
        calibrated_p = 1.0 / (1.0 + math.exp(-logit / T))
        calibrated_p = round(max(0.0001, min(0.9999, calibrated_p)), 4)

        # 5. Build Evidence
        cat = EVIDENCE_CATALOG.get("IMG-AI-01", {"weight": 0.65, "title": "AI Generated Image"})
        severity = "high" if calibrated_p >= 0.65 else "medium" if calibrated_p >= 0.35 else "low"

        details = {
            "p_ai_raw": round(p_orig, 4),
            "raw_logits": raw_logits_orig,
            "p_ai_tta_q85": round(p_q85, 4) if p_q85 is not None else None,
            "p_ai_crop": round(p_crop, 4) if p_crop is not None else None,
            "tta_disagreement": has_tta_disagreement,
            "crop_evaluated": crop_scored,
            "temperature": T,
            "uncalibrated": not is_calibrated,
            "model": "Ateeqq/ai-vs-human-image-detector",
            "p": calibrated_p
        }

        evidence = [
            Evidence(
                id="IMG-AI-01",
                kind="risk",
                raw_score=round(p_orig, 4),
                calibrated_score=calibrated_p,
                weight=cat["weight"],
                effective_weight=cat["weight"],
                severity=severity,
                title=cat["title"],
                reason=f"The image shows patterns typical of AI-generated pictures ({calibrated_p:.0%} likelihood after calibration).",
                details=details
            )
        ]

        # Record into scratch for downstream localization & pipeline summary
        ctx.scratch["p_ai"] = calibrated_p
        ctx.scratch["tta_disagreement"] = has_tta_disagreement

        return DetectorOutput(
            evidence=evidence,
            extras={
                "p_ai": calibrated_p,
                "tta_disagreement": has_tta_disagreement,
                "details": details
            }
        )
