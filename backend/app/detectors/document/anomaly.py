"""Word-level Isolation Forest anomaly detector (§11.1 Step 9, §17.7).

Identifies statistical style outliers across word dimensions (stroke width,
character spacing, baseline offset, ink intensity).
Emits:
- DOC-ANOM-01: Word-level style anomalies with most deviating feature description.
"""

from typing import Dict, Any, List
from pathlib import Path
import numpy as np
import joblib

from ...schemas.evidence import Evidence
from ...scoring.weights import EVIDENCE_CATALOG
from ..base import Detector, DetectorOutput, AnalysisContext
from .word_features import extract_word_features, FEATURE_NAMES

_CAL_FILE = Path(__file__).resolve().parents[4] / "models" / "calibration.json"


def _anomaly_calibration() -> Dict[str, float]:
    """Operating threshold (clean-val p90 of page max anomaly) and slope from calibration.json."""
    default = {"a": 10.0, "threshold": 0.25}
    try:
        import json
        cfg = json.loads(_CAL_FILE.read_text(encoding="utf-8")).get("DOC-ANOM-01", {})
        return {"a": float(cfg.get("platt", {}).get("a", default["a"])) if float(cfg.get("platt", {}).get("a", 0)) > 1.0 else default["a"],
                "threshold": float(cfg.get("threshold", default["threshold"]))}
    except Exception:
        return default


class DocumentAnomalyDetector(Detector):
    name: str = "document_anomaly"

    def __init__(self):
        super().__init__()
        self._model = None
        self._feature_names = FEATURE_NAMES
        self._load_model()

    def _load_model(self):
        path = Path("models/anomaly.joblib")
        if path.exists():
            try:
                data = joblib.load(str(path))
                if isinstance(data, dict):
                    self._model = data.get("model")
                    self._feature_names = data.get("feature_names", FEATURE_NAMES)
                else:
                    self._model = data
            except Exception:
                self._model = None

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        if self._model is None:
            self._load_model()

        if self._model is None:
            return DetectorOutput(
                status="failed",
                evidence=[],
                details={"error": "Anomaly model weights (models/anomaly.joblib) not found."}
            )

        ocr_pages = ctx.runtime_data.get("ocr_pages", [])
        rendered_pages = ctx.runtime_data.get("rendered_pages", [])

        if not ocr_pages or not rendered_pages:
            return DetectorOutput(
                status="skipped",
                evidence=[],
                details={"message": "No OCR words or rendered images available for anomaly scoring."}
            )

        evidence: List[Evidence] = []
        details: Dict[str, Any] = {"pages": []}

        for p_idx in range(min(len(ocr_pages), len(rendered_pages))):
            page_no = p_idx + 1
            words = ocr_pages[p_idx].get("words", [])
            img = rendered_pages[p_idx]

            if len(words) < 5:
                continue

            feats, _ = extract_word_features(img, words)
            # Negative decision function: higher value = more anomalous
            anomaly_scores = -self._model.decision_function(feats)

            # Sort words by anomaly score
            ranked_idx = np.argsort(-anomaly_scores)
            top_outliers = []

            for rank, idx in enumerate(ranked_idx[:3], 1):
                score_val = float(anomaly_scores[idx])
                if score_val > 0.02:  # Anomaly threshold
                    word_rec = words[idx]
                    word_feats = feats[idx]

                    # Find feature with maximum absolute z-score
                    max_feat_idx = int(np.argmax(np.abs(word_feats)))
                    max_feat_name = self._feature_names[max_feat_idx].replace("_", " ")
                    max_feat_sigma = float(abs(word_feats[max_feat_idx]))

                    top_outliers.append({
                        "rank": rank,
                        "text": word_rec["text"],
                        "score": round(score_val, 3),
                        "bbox": word_rec["normalized_bbox"],
                        "most_deviating_feature": f"{max_feat_name} {max_feat_sigma:.1f}σ from document median"
                    })

            details["pages"].append({
                "page": page_no,
                "outliers_count": len(top_outliers),
                "top_outliers": top_outliers
            })

            page_max = float(np.max(anomaly_scores))
            cal = _anomaly_calibration()
            if top_outliers and page_max > cal["threshold"]:
                first_outlier = top_outliers[0]
                cal_score = float(1.0 / (1.0 + np.exp(-cal["a"] * (page_max - cal["threshold"]))))
                evidence.append(Evidence(
                    id="DOC-ANOM-01",
                    pipeline="document",
                    source="anomaly",
                    kind="info",  # AUC=0.50 < 0.60 → info-only per P0-4b AUC rule
                    score=round(cal_score, 3),
                    weight=0.0,  # not scored in fusion
                    title="Word-Level Style Outlier (Experimental)",
                    reason=f"Word '{first_outlier['text']}' on page {page_no} is a style anomaly ({first_outlier['most_deviating_feature']}) — supporting context only.",
                    bboxes=[o["bbox"] for o in top_outliers],
                    details={
                        "page": page_no,
                        "outliers": top_outliers,
                        "page_max_anomaly": round(page_max, 4),
                        "threshold": cal["threshold"],
                        "auc": 0.50,
                        "auc_rule": "AUC < 0.60 → info-only, not scored"
                    }
                ))

        return DetectorOutput(
            status="ok",
            evidence=evidence,
            details=details
        )
