"""Document Tamper CNN detector using PyTorch EfficientNet-B0 (§11.1 Step 8, §17.6).

Extracts 128x128 ELA patches (stride 64), runs batched inference, applies
calibrated temperature scaling, accumulates a full-page probability heatmap,
extracts anomaly bounding boxes, and scores the page as the mean of top-5 patches.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import cv2
import numpy as np

from ...core.model_registry import model_registry
from ...schemas.evidence import Evidence
from ...scoring.weights import EVIDENCE_CATALOG
from ..base import Detector, DetectorOutput, AnalysisContext

PATCH_SIZE = 128
STRIDE = 64
ELA_QUALITY = 90
ELA_SCALE = 15.0

_CAL_FILE = Path(__file__).resolve().parents[4] / "models" / "calibration.json"


def _cnn_page_calibration() -> Dict[str, float]:
    """Page-level Platt params + clean-page operating threshold from calibration.json."""
    default = {"a": 96.0, "b": -3.6, "threshold": 0.0375}
    try:
        import json
        cfg = json.loads(_CAL_FILE.read_text(encoding="utf-8")).get("DOC-CNN-01", {})
        p = cfg.get("platt", {})
        return {"a": float(p.get("a", default["a"])), "b": float(p.get("b", default["b"])),
                "threshold": float(cfg.get("threshold", default["threshold"]))}
    except Exception:
        return default


def compute_page_ela(img: np.ndarray, quality: int = ELA_QUALITY, scale: float = ELA_SCALE) -> np.ndarray:
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, enc = cv2.imencode(".jpg", img, encode_param)
    recompressed = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    diff = cv2.absdiff(img, recompressed).astype(np.float32)
    ela = np.clip(diff * scale, 0, 255).astype(np.uint8)
    return ela


class DocumentTamperCNNDetector(Detector):
    name: str = "tamper_cnn"

    def __init__(self):
        super().__init__()
        self._model = None
        self._temperature = 1.0
        
        import os
        if os.environ.get("LITE_MODE") == "1":
            return
            
        import torch
        self._device = torch.device("cpu")
        self._load_model()

    def _load_model(self):
        # Check model registry first or disk
        if hasattr(model_registry, "tamper_cnn") and model_registry.tamper_cnn is not None:
            self._model = model_registry.tamper_cnn
            self._temperature = getattr(model_registry, "tamper_cnn_temp", 2.0)
            return

        model_path = Path("models/tamper_cnn.pt")
        if not model_path.exists():
            return

        try:
            import torch
            import timm
            ckpt = torch.load(str(model_path), map_location=self._device)
            m = timm.create_model("efficientnet_b0", pretrained=False, num_classes=1)
            m.load_state_dict(ckpt["state_dict"])
            m.eval()
            self._model = m
            self._temperature = float(ckpt.get("temperature", 2.0))
        except Exception as e:
            self._model = None

    def page_probs(self, img: np.ndarray) -> np.ndarray:
        """Per-patch temperature-scaled probabilities for one page (used by calibration)."""
        if self._model is None:
            self._load_model()
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        h, w = img.shape[:2]
        ela = compute_page_ela(img)
        patches = []
        for y in range(0, h - PATCH_SIZE + 1, STRIDE):
            for x in range(0, w - PATCH_SIZE + 1, STRIDE):
                p = ela[y:y+PATCH_SIZE, x:x+PATCH_SIZE]
                if np.std(p) < 1.5:
                    continue
                rgb = cv2.cvtColor(p, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                patches.append(((rgb - mean) / std).transpose(2, 0, 1))
        if not patches:
            return np.zeros(0, dtype=np.float32)
        with torch.no_grad():
            logits = self._model(torch.tensor(np.array(patches), dtype=torch.float32)).squeeze(-1).numpy()
        return 1.0 / (1.0 + np.exp(-logits / max(self._temperature, 0.1)))

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        if self._model is None:
            # Re-attempt lazy load
            self._load_model()

        if self._model is None:
            return DetectorOutput(
                status="failed",
                evidence=[],
                details={"error": "Tamper CNN model weights (models/tamper_cnn.pt) not loaded."}
            )

        rendered_pages = ctx.runtime_data.get("rendered_pages", [])
        if not rendered_pages:
            file_p = str(ctx.file_path)
            if file_p.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                img = cv2.imread(file_p)
                if img is not None:
                    rendered_pages = [img]

        if not rendered_pages:
            return DetectorOutput(
                status="skipped",
                evidence=[],
                details={"message": "No rendered document pages available."}
            )

        evidence: List[Evidence] = []
        details: Dict[str, Any] = {"pages": []}

        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

        for p_idx, img in enumerate(rendered_pages):
            page_no = p_idx + 1
            h, w = img.shape[:2]
            ela = compute_page_ela(img)

            patches = []
            coords = []

            for y in range(0, h - PATCH_SIZE + 1, STRIDE):
                for x in range(0, w - PATCH_SIZE + 1, STRIDE):
                    patch_ela = ela[y:y+PATCH_SIZE, x:x+PATCH_SIZE]
                    if np.std(patch_ela) < 1.5:
                        continue
                    # Normalize
                    rgb = cv2.cvtColor(patch_ela, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                    norm = (rgb - mean) / std
                    patches.append(norm.transpose(2, 0, 1))
                    coords.append((y, x))

            if not patches:
                details["pages"].append({
                    "page": page_no,
                    "score": 0.05,
                    "patches_evaluated": 0
                })
                continue

            # Batched inference
            tensor_patches = torch.tensor(np.array(patches), dtype=torch.float32)
            with torch.no_grad():
                logits = self._model(tensor_patches).squeeze(-1).numpy()

            # Calibrated probability via temperature
            cal_logits = logits / max(self._temperature, 0.1)
            probs = 1.0 / (1.0 + np.exp(-cal_logits))

            # Page score: calibrated fraction of confidently-tampered patches (calibration.json)
            top5_probs = sorted(probs, reverse=True)[:5]
            top5_mean = float(np.mean(top5_probs))
            frac_hi = float(np.mean(probs > 0.8))
            cal = _cnn_page_calibration()
            page_score = float(1.0 / (1.0 + np.exp(-(cal["a"] * frac_hi + cal["b"]))))
            page_exceeds = frac_hi > cal["threshold"]

            # Reconstruct 2D probability map
            prob_map = np.zeros((h, w), dtype=np.float32)
            count_map = np.zeros((h, w), dtype=np.float32)

            for (py, px), p_val in zip(coords, probs):
                prob_map[py:py+PATCH_SIZE, px:px+PATCH_SIZE] += p_val
                count_map[py:py+PATCH_SIZE, px:px+PATCH_SIZE] += 1.0

            valid_mask = count_map > 0
            prob_map[valid_mask] /= count_map[valid_mask]

            # Smooth heatmap
            smooth_map = cv2.GaussianBlur(prob_map, (15, 15), 0)

            # Threshold and extract connected components as anomaly boxes
            bin_map = (smooth_map >= 0.45).astype(np.uint8) * 255
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(bin_map)

            flagged_boxes = []
            for lbl in range(1, num_labels):
                area = int(stats[lbl, cv2.CC_STAT_AREA])
                if area >= 400:  # Minimum patch size
                    bx = int(stats[lbl, cv2.CC_STAT_LEFT])
                    by = int(stats[lbl, cv2.CC_STAT_TOP])
                    bw = int(stats[lbl, cv2.CC_STAT_WIDTH])
                    bh = int(stats[lbl, cv2.CC_STAT_HEIGHT])
                    flagged_boxes.append([
                        round(bx / w, 4),
                        round(by / h, 4),
                        round(bw / w, 4),
                        round(bh / h, 4)
                    ])

            # Save heatmap artifact if artifacts_dir is available
            artifact_name = f"page_{page_no}_tamper.png"
            if ctx.artifacts_dir:
                heat_u8 = np.clip(smooth_map * 255.0, 0, 255).astype(np.uint8)
                color_heat = cv2.applyColorMap(heat_u8, cv2.COLORMAP_JET)
                # Alpha blend 65/35
                overlay = cv2.addWeighted(img, 0.65, color_heat, 0.35, 0)
                art_path = ctx.artifacts_dir / artifact_name
                cv2.imwrite(str(art_path), overlay)

            page_info = {
                "page": page_no,
                "score": round(page_score, 3),
                "patches_evaluated": len(patches),
                "boxes_found": len(flagged_boxes),
                "artifact": artifact_name
            }
            details["pages"].append(page_info)

            # Emit DOC-CNN-01 evidence if risk is substantial
            if page_exceeds:
                evidence.append(Evidence(
                    id="DOC-CNN-01",
                    pipeline="document",
                    source="forensics",
                    kind="risk",
                    score=round(page_score, 3),
                    weight=EVIDENCE_CATALOG["DOC-CNN-01"]["weight"],
                    title="Tamper CNN Anomaly",
                    reason=f"The tamper CNN detected compression and textural anomalies on page {page_no} (score: {page_score:.0%}).",
                    bboxes=flagged_boxes[:3],
                    details={
                        "page": page_no,
                        "score": round(page_score, 3),
                        "temperature": self._temperature,
                        "artifact": artifact_name
                    }
                ))

        return DetectorOutput(
            status="ok",
            evidence=evidence,
            details=details
        )
