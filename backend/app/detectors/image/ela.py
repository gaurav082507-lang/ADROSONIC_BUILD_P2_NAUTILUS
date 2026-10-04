import io
import os
import json
import math
import logging
import cv2
import numpy as np
from PIL import Image, ImageChops
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from ..base import DetectorOutput, AnalysisContext
from ...schemas.evidence import Evidence, BBox
from ...scoring.weights import EVIDENCE_CATALOG

logger = logging.getLogger("lucen_ai.ela")

CALIBRATION_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../models/calibration.json")
)

def get_ela_platt_params() -> Tuple[float, float]:
    """Loads logistic calibration parameters for ELA from calibration.json."""
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                ela_cfg = data.get("platt", {}).get("ela", {})
                a = float(ela_cfg.get("a", 15.0))
                b = float(ela_cfg.get("b", -2.5))
                return a, b
        except Exception:
            pass
    return 15.0, -2.5

def compute_ela_map(img: Image.Image, quality: int = 90, scale: float = 15.0) -> np.ndarray:
    """Exact Error Level Analysis implementation from arch §10 Step 4."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=quality)
    buf.seek(0)
    recompressed = Image.open(buf)
    diff = ImageChops.difference(img.convert("RGB"), recompressed)
    return np.clip(np.asarray(diff).astype("float32") * scale, 0, 255).astype("uint8")

class ElaDetector:
    name: str = "ela"
    timeout_s: float = 15.0

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        quality_metrics = ctx.quality_metrics or {}
        mime = quality_metrics.get("mime_type", "")
        is_screenshot = quality_metrics.get("is_screenshot", False)

        # Status skipped (NOT scored) for non-JPEG or screenshots (§10 Step 4, §15.3, F40)
        if mime != "image/jpeg" or is_screenshot:
            reason = "Skipped: format is non-JPEG (PNG/WebP)" if mime != "image/jpeg" else "Skipped: image appears to be a screenshot"
            logger.info(f"ELA detector skipped: {reason}")
            return DetectorOutput(
                evidence=[],
                extras={"skipped": True, "reason": reason}
            )

        if not ctx.decoded_images:
            return DetectorOutput()

        img = ctx.decoded_images[0]
        w, h = img.size

        # 1. Compute raw ELA diff map
        ela_rgb = compute_ela_map(img, quality=90, scale=15.0)
        ela_gray = cv2.cvtColor(ela_rgb, cv2.COLOR_RGB2GRAY)
        ela_blurred = cv2.GaussianBlur(ela_gray, (5, 5), 0)

        # Store ela_gray in scratch for localization
        ctx.scratch["ela_gray"] = ela_gray

        # 2. Robust thresholding: median + k * MAD
        median = float(np.median(ela_blurred))
        mad = float(np.median(np.abs(ela_blurred - median)))
        threshold = median + (3.5 * mad)
        threshold = max(25.0, threshold)  # floor threshold against noise

        binary_mask = (ela_blurred > threshold).astype(np.uint8) * 255
        anomalous_pixels = int(np.count_nonzero(binary_mask))
        total_pixels = w * h
        anomaly_fraction = anomalous_pixels / max(1, total_pixels)

        # 3. Find largest connected anomalous component and bounding box
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
        largest_box = None
        largest_area = 0

        # stats: [x, y, width, height, area] (index 0 is background)
        for i in range(1, num_labels):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area > largest_area and area > 100:  # minimum 100 px region
                largest_area = area
                bx = int(stats[i, cv2.CC_STAT_LEFT])
                by = int(stats[i, cv2.CC_STAT_TOP])
                bw = int(stats[i, cv2.CC_STAT_WIDTH])
                bh = int(stats[i, cv2.CC_STAT_HEIGHT])
                largest_box = BBox(
                    page=1,
                    x=round(float(bx) / w, 3),
                    y=round(float(by) / h, 3),
                    w=round(float(bw) / w, 3),
                    h=round(float(bh) / h, 3)
                )

        # 4. Logistic mapping to calibrated risk score
        a, b = get_ela_platt_params()
        logit_val = a * anomaly_fraction + b
        logit_val = max(-20.0, min(20.0, logit_val))
        score = 1.0 / (1.0 + math.exp(-logit_val))
        score = round(max(0.01, min(0.99, score)), 4)

        # 5. Save ela_heatmap.png artifact
        heatmap_colored = cv2.applyColorMap(ela_blurred, cv2.COLORMAP_JET)
        artifacts_dir = ctx.scratch.get("artifacts_dir")
        artifacts = {}
        if artifacts_dir:
            ela_path = os.path.join(artifacts_dir, "ela_heatmap.png")
            cv2.imwrite(ela_path, heatmap_colored)
            artifacts["ela_heatmap"] = Path(ela_path)

        cat = EVIDENCE_CATALOG.get("IMG-ELA-01", {"weight": 0.25, "title": "ELA Compression Anomaly"})
        severity = "high" if score >= 0.65 else "medium" if score >= 0.35 else "low"

        evidence = [
            Evidence(
                id="IMG-ELA-01",
                kind="info",  # AUC=0.467 < 0.60 → info-only per P0-4b AUC rule
                raw_score=float(score),
                calibrated_score=float(score),
                weight=float(cat["weight"]),
                effective_weight=0.0,  # not scored in fusion
                severity="low",
                title=cat["title"],
                reason="One region of the photo was compressed differently from the rest (supporting context — low discriminative AUC).",
                bbox=largest_box,
                details={
                    "anomaly_fraction": round(float(anomaly_fraction), 4),
                    "anomalous_pixels": int(anomalous_pixels),
                    "threshold": round(float(threshold), 2),
                    "largest_region_area": int(largest_area),
                    "auc": 0.4667,
                    "auc_rule": "AUC < 0.60 → info-only, not scored"
                },
                artifact="ela_heatmap.png" if artifacts else None
            )
        ]

        return DetectorOutput(
            evidence=evidence,
            artifacts=artifacts,
            extras={
                "ela_score": score,
                "anomaly_fraction": anomaly_fraction,
                "largest_box": largest_box
            }
        )
