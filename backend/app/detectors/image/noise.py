import os
import cv2
import json
import numpy as np
import math
import logging
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple
from ..base import DetectorOutput, AnalysisContext
from ...schemas.evidence import Evidence
from ...scoring.weights import EVIDENCE_CATALOG

logger = logging.getLogger("lucen_ai.noise")

CALIBRATION_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../models/calibration.json")
)

def get_noise_platt_params() -> Tuple[float, float]:
    """Loads logistic calibration parameters for Noise from calibration.json."""
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cfg = data.get("platt", {}).get("noise", {})
                a = float(cfg.get("a", 3.0))
                b = float(cfg.get("b", -2.0))
                return a, b
        except Exception:
            pass
    return 3.0, -2.0

def compute_fft_peak_metric(residual: np.ndarray) -> float:
    """Computes periodic artifact energy ratio in 2D FFT high-frequency spectrum."""
    try:
        # Resize to standard 256x256 patch for fast FFT analysis
        h, w = residual.shape
        if h < 64 or w < 64:
            return 0.0
        patch = cv2.resize(residual, (256, 256))
        f = np.fft.fft2(patch)
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)

        # Mask out center DC component (radius 16)
        ch, cw = 128, 128
        y, x = np.ogrid[:256, :256]
        dist_from_center = np.sqrt((x - cw)**2 + (y - ch)**2)
        magnitude[dist_from_center <= 16] = 0.0

        med = float(np.median(magnitude[dist_from_center > 16]))
        peak = float(np.max(magnitude[dist_from_center > 16]))
        ratio = (peak / med) if med > 0 else 1.0
        return round(min(50.0, ratio), 2)
    except Exception:
        return 1.0

def compute_noise_dispersion(img: Image.Image) -> float:
    """Computes block-wise noise variance dispersion across 64x64 non-flat blocks."""
    img_np = np.array(img)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY).astype(np.float32)
    h, w = gray.shape
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    residual = gray - blurred

    block_size = 64
    variances = []
    for r in range(0, h - block_size + 1, block_size):
        for c in range(0, w - block_size + 1, block_size):
            orig_block = gray[r:r+block_size, c:c+block_size]
            res_block = residual[r:r+block_size, c:c+block_size]
            if np.std(orig_block) < 5.0:
                continue
            variances.append(float(np.var(res_block)))

    if not variances:
        return 0.0
    mean_var = np.mean(variances)
    std_var = np.std(variances)
    return float(std_var / mean_var) if mean_var > 0 else 0.0

class NoiseDetector:
    name: str = "noise"
    timeout_s: float = 15.0

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        if not ctx.decoded_images:
            return DetectorOutput()

        img = ctx.decoded_images[0]
        img_np = np.array(img)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY).astype(np.float32)
        h, w = gray.shape

        # 1. High-pass residual: gray minus mild Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        residual = gray - blurred

        # Store noise variance map in scratch for localization
        ctx.scratch["noise_residual"] = np.abs(residual).astype(np.uint8)

        # 2. Block-wise noise variance dispersion (64x64 blocks)
        block_size = 64
        variances = []
        flat_blocks_excluded = 0

        for r in range(0, h - block_size + 1, block_size):
            for c in range(0, w - block_size + 1, block_size):
                orig_block = gray[r:r+block_size, c:c+block_size]
                res_block = residual[r:r+block_size, c:c+block_size]

                # Check if original block is flat (e.g. clear sky, plain wall)
                orig_std = np.std(orig_block)
                if orig_std < 5.0:  # low texture threshold
                    flat_blocks_excluded += 1
                    continue

                res_var = float(np.var(res_block))
                variances.append(res_var)

        if not variances:
            dispersion = 0.0
            raw_score = 0.05
        else:
            mean_var = np.mean(variances)
            std_var = np.std(variances)
            # Coefficient of variation (dispersion of noise across textures)
            dispersion = float(std_var / mean_var) if mean_var > 0 else 0.0

            # Logistic mapping via calibrated Platt scaling
            a, b = get_noise_platt_params()
            logit_val = a * dispersion + b
            logit_val = max(-15.0, min(15.0, logit_val))
            raw_score = float(1.0 / (1.0 + math.exp(-logit_val)))

        raw_score = round(max(0.02, min(0.95, raw_score)), 4)
        fft_peak = compute_fft_peak_metric(residual)

        cat = EVIDENCE_CATALOG.get("IMG-NOISE-01", {"weight": 0.20, "title": "Inconsistent Noise Pattern"})
        severity = "high" if raw_score >= 0.65 else "medium" if raw_score >= 0.35 else "low"

        evidence = [
            Evidence(
                id="IMG-NOISE-01",
                kind="risk",
                raw_score=raw_score,
                calibrated_score=raw_score,
                weight=cat["weight"],
                effective_weight=cat["weight"],
                severity=severity,
                title=cat["title"],
                reason="Noise pattern dispersion across textured image blocks suggests spliced or synthesized regions.",
                details={
                    "noise_dispersion": round(float(dispersion), 4),
                    "blocks_analyzed": int(len(variances)),
                    "flat_blocks_excluded": int(flat_blocks_excluded),
                    "fft_periodicity_ratio": float(fft_peak)
                }
            )
        ]

        return DetectorOutput(
            evidence=evidence,
            extras={
                "noise_score": raw_score,
                "noise_dispersion": dispersion,
                "fft_ratio": fft_peak
            }
        )
