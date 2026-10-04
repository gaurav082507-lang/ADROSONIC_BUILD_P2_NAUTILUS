import os
import cv2
import numpy as np
from PIL import Image, ImageOps
from typing import Dict, Any, Optional
from ..base import DetectorOutput, AnalysisContext
from ...schemas.evidence import Evidence
from ...schemas.result import QualityWarning

ALLOWED_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp"
}

def estimate_jpeg_quality(img: Image.Image) -> Optional[int]:
    """Estimates JPEG compression quality from luminance quantization table DC coefficient."""
    try:
        tables = getattr(img, "quantization", None)
        if not tables or 0 not in tables:
            return None
        qtable = tables[0]
        if not qtable:
            return None
        dc = float(qtable[0])
        if dc <= 0:
            return 100
        scale = (dc / 16.0) * 100.0
        if scale > 100.0:
            q = int(round(5000.0 / scale))
        else:
            q = int(round((200.0 - scale) / 2.0))
        return max(1, min(100, q))
    except Exception:
        return None

def is_screenshot_heuristic(w: int, h: int) -> bool:
    """Detects standard smartphone and monitor aspect ratios common to screenshots."""
    if w == 0 or h == 0:
        return False
    aspect = max(w, h) / min(w, h)
    # Common smartphone & monitor aspect ratios: 16:9 (~1.78), 19.5:9 (~2.17), 20:9 (~2.22), 18:9 (2.0)
    screen_aspects = [16/9, 19.5/9, 20/9, 18/9, 19/9, 16/10]
    return any(abs(aspect - sa) < 0.02 for sa in screen_aspects)

class ImagePreprocessor:
    name: str = "preprocess"
    timeout_s: float = 10.0

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        if not ctx.file_paths:
            raise ValueError("No file path provided to image preprocessor.")

        file_path = ctx.file_paths[0]
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # 1. Magic byte verification
        with open(file_path, "rb") as f:
            header = f.read(32)

        matched_mime = None
        for magic, mime in ALLOWED_MAGIC.items():
            if header.startswith(magic):
                matched_mime = mime
                break

        if not matched_mime:
            raise ValueError("Corrupt or unsupported image format (magic-byte check failed).")

        # 2. Decode with Pillow and apply EXIF orientation
        try:
            raw_img = Image.open(file_path)
            img = ImageOps.exif_transpose(raw_img)
            img_rgb = img.convert("RGB")
        except Exception as e:
            raise ValueError(f"Failed to decode image: {e}")

        w, h = img_rgb.size
        mp = round((w * h) / 1_000_000, 2)
        jpeg_q = estimate_jpeg_quality(raw_img) if matched_mime == "image/jpeg" else None

        # 3. Sharpness metric via Laplacian variance
        img_np = np.array(img_rgb)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        is_screenshot = is_screenshot_heuristic(w, h)

        # Populate context quality metrics and decoded image
        quality_metrics = {
            "width": w,
            "height": h,
            "megapixels": mp,
            "jpeg_quality": jpeg_q,
            "sharpness": round(lap_var, 2),
            "is_screenshot": is_screenshot,
            "mime_type": matched_mime,
            "short_side": min(w, h)
        }
        ctx.quality_metrics = quality_metrics
        ctx.decoded_images = [img_rgb]
        ctx.scratch["original_file_path"] = file_path

        # 4. Quality Gating Warning Emission
        evidence = []
        warnings = []

        is_low_res = min(w, h) < 512
        is_low_q = (jpeg_q is not None and jpeg_q < 50)
        is_blurry = lap_var < 80.0

        if is_low_res or is_low_q or is_blurry:
            reasons = []
            if is_low_res:
                reasons.append(f"low resolution ({w}x{h} px)")
                warnings.append(QualityWarning(code="LOW_RES", message=f"Short side < 512 px ({min(w,h)} px)."))
            if is_low_q:
                reasons.append(f"heavy JPEG compression (q={jpeg_q})")
                warnings.append(QualityWarning(code="HEAVY_COMPRESSION", message=f"Estimated JPEG quality {jpeg_q} < 50."))
            if is_blurry:
                reasons.append(f"low sharpness (Laplacian variance {round(lap_var, 1)})")
                warnings.append(QualityWarning(code="BLURRY", message="Image is blurry or lacks edge details."))

            reason_str = ", ".join(reasons)
            evidence.append(
                Evidence(
                    id="IMG-QUAL-01",
                    kind="info",
                    raw_score=0.0,
                    calibrated_score=0.0,
                    weight=0.0,
                    effective_weight=0.0,
                    severity="low",
                    title="Input Quality Warning",
                    reason=f"Degraded input quality detected: {reason_str}. Secondary forensic detector weights gated.",
                    details=quality_metrics
                )
            )

        return DetectorOutput(
            evidence=evidence,
            extras={
                "quality_metrics": quality_metrics,
                "quality_warnings": warnings
            }
        )
