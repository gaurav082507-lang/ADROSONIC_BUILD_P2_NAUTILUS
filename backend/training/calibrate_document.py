"""Page-level calibration for DOC-CNN-01 and DOC-ANOM-01.

Fits a logistic (Platt) map on the VAL split of data/training (clean vs tampered
pages) and reports AUC / clean-false-alarm rate on the TEST split. Writes the
results into models/calibration.json (merged, nothing else touched).
Scoring maths is untouched; only the detector input scores are calibrated.
"""
import os, sys, json, glob
import cv2
import numpy as np
import joblib
from scipy.optimize import minimize
from sklearn.metrics import roc_auc_score

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.chdir(ROOT)

from app.detectors.document.tamper_cnn import DocumentTamperCNNDetector
from app.detectors.document.word_features import extract_word_features
import pymupdf

CAL = os.path.join(ROOT, "models", "calibration.json")
SLOPE_SHRINK = 0.25  # small val set (48 pages) -> shrink Platt slope to avoid saturated scores


def load_split(split):
    items = []
    for label, d in ((0, "clean"), (1, "tampered")):
        for jf in sorted(glob.glob(f"data/training/{d}/*.json")):
            m = json.load(open(jf))
            if m.get("split") != split:
                continue
            png = jf[:-5] + ".png"
            if os.path.exists(png):
                items.append((label, png, m))
    return items


def words_for(png_path, meta, label):
    """Word boxes from the clean PDF text layer (same layout as the page image)."""
    clean_id = meta.get("clean_id") if label else meta.get("sample_id")
    pdf = f"data/training/clean/{clean_id}.pdf"
    img = cv2.imread(png_path)
    if not os.path.exists(pdf) or img is None:
        return img, []
    doc = pymupdf.open(pdf)
    page = doc[0]
    sx = img.shape[1] / max(page.rect.width, 1.0)
    sy = img.shape[0] / max(page.rect.height, 1.0)
    words = []
    for w in page.get_text("words"):
        bh = max(int((w[3] - w[1]) * sy), 1)
        words.append({"bbox": [int(w[0] * sx), int(w[1] * sy), max(int((w[2] - w[0]) * sx), 1), bh],
                      "text": w[4], "conf": 1.0, "font_size": float(bh * 0.8), "font_name": "default"})
    doc.close()
    return img, words


def fit_platt(x, y):
    def obj(p):
        z = np.clip(p[0] * x + p[1], -30, 30)
        pr = np.clip(1 / (1 + np.exp(-z)), 1e-6, 1 - 1e-6)
        return -np.sum(y * np.log(pr) + (1 - y) * np.log(1 - pr))
    r = minimize(obj, [4.0, -2.0], method="L-BFGS-B")
    return float(r.x[0]), float(r.x[1])


def weight_from_auc(auc):
    return 0.65 if auc >= 0.90 else 0.45 if auc >= 0.75 else 0.25


def main():
    det = DocumentTamperCNNDetector()
    model = joblib.load("models/anomaly.joblib")
    model = model.get("model") if isinstance(model, dict) else model

    def features(split):
        rows = []
        for label, png, meta in load_split(split):
            img, words = words_for(png, meta, label)
            probs = det.page_probs(img)
            top5 = float(np.mean(sorted(probs, reverse=True)[:5])) if len(probs) else 0.0
            frac = float(np.mean(probs > 0.8)) if len(probs) else 0.0
            anom = 0.0
            if len(words) >= 5:
                f, _ = extract_word_features(img, words)
                anom = float(np.max(-model.decision_function(f)))
            rows.append((label, top5, frac, anom))
        return np.array(rows)

    val, test = features("val"), features("test")
    print(f"val pages={len(val)} test pages={len(test)}")
    out = {}
    for name, col in (("DOC-CNN-01", 2), ("DOC-ANOM-01", 3)):
        # CNN page score = fraction of patches > 0.8 (top-5 mean saturates on clean pages)
        a, _ = fit_platt(val[:, col], val[:, 0])
        a = abs(a) if a > 0 else 1.0
        a = max(1.0, a * SLOPE_SHRINK) if name == "DOC-CNN-01" else a
        # Operating point: 90th percentile of CLEAN val pages -> maps to calibrated 0.5.
        thr = float(np.percentile(val[val[:, 0] == 0, col], 90))
        b = -a * thr
        auc_val = roc_auc_score(val[:, 0], val[:, col])
        auc_test = roc_auc_score(test[:, 0], test[:, col])
        p_test = 1 / (1 + np.exp(-(a * test[:, col] + b)))
        far = float(np.mean(p_test[test[:, 0] == 0] >= 0.5))
        rec = float(np.mean(p_test[test[:, 0] == 1] >= 0.5))
        print(f"{name}: a={a:.3f} b={b:.3f} thr={thr:.4f} AUC val={auc_val:.3f} test={auc_test:.3f} clean-FAR@0.5={far:.2f} recall@0.5={rec:.2f}")
        print(f"   mean feature clean={test[test[:,0]==0, col].mean():.4f} tampered={test[test[:,0]==1, col].mean():.4f}")
        out[name] = {"platt": {"a": round(a, 3), "b": round(b, 3)}, "threshold": round(thr, 5),
                     "feature": "frac_patches_gt_0.8" if col == 2 else "max_word_anomaly",
                     "auc_val": round(auc_val, 4), "auc_test": round(auc_test, 4),
                     "clean_false_alarm_rate": round(far, 3), "recall_at_0.5": round(rec, 3)}

    cal = json.load(open(CAL, encoding="utf-8"))
    for k, v in out.items():
        cal.setdefault(k, {}).update(v)
        cal.setdefault("weights", {})[k] = weight_from_auc(v["auc_test"]) if k != "DOC-CNN-01" else min(0.50, weight_from_auc(v["auc_test"]))
        cal.setdefault("auc", {})[k] = v["auc_test"]
    cal["DOC-ANOM-01"]["weight_note"] = "capped at 0.30 by catalog"
    cal["weights"]["DOC-ANOM-01"] = min(0.30, cal["weights"]["DOC-ANOM-01"])
    json.dump(cal, open(CAL, "w", encoding="utf-8"), indent=2)
    print("Wrote", CAL)


if __name__ == "__main__":
    main()
