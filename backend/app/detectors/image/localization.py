import os
import cv2
import numpy as np
import logging
from PIL import Image
from pathlib import Path

logger = logging.getLogger("lucen_ai.localization")
from typing import Dict, Any, List, Optional
from ..base import DetectorOutput, AnalysisContext
from ...core.config import settings
from ...core.model_registry import model_registry

class LocalizationDetector:
    name: str = "localization"
    timeout_s: float = 25.0

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        if not ctx.decoded_images:
            return DetectorOutput()

        img_rgb = ctx.decoded_images[0]
        w, h = img_rgb.size
        img_np = np.array(img_rgb)

        artifacts_dir = ctx.scratch.get("artifacts_dir")
        artifacts = {}

        # 1. Forensic Heatmap (ELA + Noise fusion)
        ela_gray = ctx.scratch.get("ela_gray")
        noise_res = ctx.scratch.get("noise_residual")

        # Fallback maps if missing or skipped
        if ela_gray is None:
            ela_gray = np.zeros((h, w), dtype=np.uint8)
        else:
            ela_gray = cv2.resize(ela_gray, (w, h))

        if noise_res is None:
            noise_res = np.zeros((h, w), dtype=np.uint8)
        else:
            noise_res = cv2.resize(noise_res, (w, h))

        # Normalize components to [0.0, 1.0]
        norm_ela = cv2.normalize(ela_gray.astype(np.float32), None, 0.0, 1.0, cv2.NORM_MINMAX)
        norm_noise = cv2.normalize(noise_res.astype(np.float32), None, 0.0, 1.0, cv2.NORM_MINMAX)

        # Weighting: 60% ELA (localized tamper), 40% noise (splice variance)
        if ctx.quality_metrics.get("mime_type") != "image/jpeg":
            fused_forensic = norm_noise
        else:
            fused_forensic = 0.60 * norm_ela + 0.40 * norm_noise

        fused_forensic = cv2.GaussianBlur(fused_forensic, (9, 9), 0)
        heatmap_uint8 = (cv2.normalize(fused_forensic, None, 0, 255, cv2.NORM_MINMAX)).astype(np.uint8)

        # Apply JET colormap
        heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        heatmap_color_rgb = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)

        # Alpha blend overlay: 65% original photo + 35% heatmap
        overlay_np = cv2.addWeighted(img_np, 0.65, heatmap_color_rgb, 0.35, 0)

        if artifacts_dir:
            overlay_path = os.path.join(artifacts_dir, "overlay.png")
            cv2.imwrite(overlay_path, cv2.cvtColor(overlay_np, cv2.COLOR_RGB2BGR))
            artifacts["overlay"] = Path(overlay_path)

            heatmap_path = os.path.join(artifacts_dir, "image_heatmap.png")
            cv2.imwrite(heatmap_path, heatmap_color)
            artifacts["image_heatmap"] = Path(heatmap_path)

        # 2. Model-based Occlusion Sensitivity (Optional & gated)
        # Runs ONLY when p_ai > medium threshold (0.35) AND OCCLUSION_ENABLED=True
        p_ai = ctx.scratch.get("p_ai", 0.0)
        if settings.OCCLUSION_ENABLED and p_ai > settings.BAND_LOW_MAX:
            model = model_registry.ai_model
            processor = model_registry.ai_processor
            ai_idx = model_registry.ai_class_idx

            if model is not None and processor is not None:
                try:
                    grid_size = 7
                    patch_w = w // grid_size
                    patch_h = h // grid_size
                    sensitivity_map = np.zeros((grid_size, grid_size), dtype=np.float32)

                    base_img_np = img_np.copy()
                    for gy in range(grid_size):
                        for gx in range(grid_size):
                            # Grey-out patch (occlusion)
                            occluded = base_img_np.copy()
                            y1 = gy * patch_h
                            y2 = (gy + 1) * patch_h if gy < grid_size - 1 else h
                            x1 = gx * patch_w
                            x2 = (gx + 1) * patch_w if gx < grid_size - 1 else w
                            occluded[y1:y2, x1:x2] = 128  # Neutral grey

                            pil_occ = Image.fromarray(occluded)
                            inputs = processor(images=pil_occ, return_tensors="pt")
                            import torch
                            with torch.no_grad():
                                outputs = model(**inputs)
                                occ_p = float(torch.softmax(outputs.logits[0], dim=-1)[ai_idx].item())

                            # Sensitivity = drop in AI probability when patch is occluded
                            drop = max(0.0, p_ai - occ_p)
                            sensitivity_map[gy, gx] = drop

                    # Upsample sensitivity map to image resolution
                    occ_resized = cv2.resize(sensitivity_map, (w, h), interpolation=cv2.INTER_CUBIC)
                    occ_norm = (cv2.normalize(occ_resized, None, 0, 255, cv2.NORM_MINMAX)).astype(np.uint8)
                    occ_color = cv2.applyColorMap(occ_norm, cv2.COLORMAP_TURBO)

                    if artifacts_dir:
                        occ_path = os.path.join(artifacts_dir, "occlusion_map.png")
                        cv2.imwrite(occ_path, occ_color)
                        artifacts["occlusion_map"] = Path(occ_path)
                except Exception as e:
                    logger.warning(f"Occlusion sensitivity map generation failed: {e}")

        return DetectorOutput(
            evidence=[],
            artifacts=artifacts,
            extras={
                "heatmap_generated": True,
                "label_forensic": "regions with unusual compression or noise",
                "label_model": "regions the AI detector relied on"
            }
        )
