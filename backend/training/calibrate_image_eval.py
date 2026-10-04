"""
Image Detector and Forensic Recalibration Script (Part 2).
Calibrates Ateeqq/ai-vs-human-image-detector on real vs ai_full,
and ELA / Noise on real vs edited, using a 70/30 train/eval split.
"""

import os
import sys
import json
import math
import datetime
import numpy as np
from PIL import Image
from typing import List, Tuple, Dict, Any, Optional
from scipy.optimize import minimize_scalar, minimize
from sklearn.metrics import roc_auc_score, accuracy_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.model_registry import model_registry
from app.detectors.image.ela import compute_ela_map
from app.detectors.image.noise import compute_noise_dispersion

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
EVAL_REAL = os.path.join(BASE_DIR, "data", "eval", "images", "real")
EVAL_AI = os.path.join(BASE_DIR, "data", "eval", "images", "ai_full")
EVAL_EDITED = os.path.join(BASE_DIR, "data", "eval", "images", "edited")
CALIBRATION_FILE = os.path.join(BASE_DIR, "models", "calibration.json")

def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE)."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(labels)
    for i in range(n_bins):
        bin_idx = (probs > bin_boundaries[i]) & (probs <= bin_boundaries[i + 1])
        bin_count = np.sum(bin_idx)
        if bin_count > 0:
            bin_acc = np.mean(labels[bin_idx])
            bin_conf = np.mean(probs[bin_idx])
            ece += (bin_count / n) * abs(bin_acc - bin_conf)
    return float(ece)

def run_calibration():
    print("=" * 70)
    print("LUCEN AI - IMAGE DETECTOR & FORENSIC RECALIBRATION")
    print("=" * 70)

    # 1. Check datasets
    real_files = sorted([os.path.join(EVAL_REAL, f) for f in os.listdir(EVAL_REAL) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    ai_files = sorted([os.path.join(EVAL_AI, f) for f in os.listdir(EVAL_AI) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    edited_files = sorted([os.path.join(EVAL_EDITED, f) for f in os.listdir(EVAL_EDITED) if f.lower().endswith((".jpg", ".jpeg", ".png"))])

    print(f"Eval Set Counts:\n  Real:   {len(real_files)}\n  AI:     {len(ai_files)}\n  Edited: {len(edited_files)}")
    if len(real_files) < 40 or len(ai_files) < 40 or len(edited_files) < 40:
        raise ValueError(f"Error: dataset count under 40! real={len(real_files)}, ai={len(ai_files)}, edited={len(edited_files)}")

    # 2. Diagnose Model & Labels
    model_registry.load_ai_detector()
    model = model_registry.ai_model
    processor = model_registry.ai_processor
    ai_idx = model_registry.ai_class_idx
    other_idx = 1 if ai_idx == 0 else 0

    id2label = getattr(model.config, "id2label", {})
    print(f"\nModel Diagnosis:")
    print(f"  id2label: {id2label}")
    print(f"  AI class index used: {ai_idx} (label: {model_registry.ai_class_label})")

    # 3. Extract logits on Real vs AI
    import torch
    print("\nExtracting AI detector logits on Real vs AI images...")
    real_raw_probs, real_rel_logits = [], []
    for f in real_files:
        with Image.open(f) as img:
            inputs = processor(images=img.convert("RGB"), return_tensors="pt")
            with torch.no_grad():
                out = model(**inputs)
                logits = out.logits[0]
                probs = torch.softmax(logits, dim=-1)
                real_raw_probs.append(float(probs[ai_idx].item()))
                real_rel_logits.append(float((logits[ai_idx] - logits[other_idx]).item()))

    ai_raw_probs, ai_rel_logits = [], []
    for f in ai_files:
        with Image.open(f) as img:
            inputs = processor(images=img.convert("RGB"), return_tensors="pt")
            with torch.no_grad():
                out = model(**inputs)
                logits = out.logits[0]
                probs = torch.softmax(logits, dim=-1)
                ai_raw_probs.append(float(probs[ai_idx].item()))
                ai_rel_logits.append(float((logits[ai_idx] - logits[other_idx]).item()))

    mean_p_real = np.mean(real_raw_probs)
    mean_p_ai = np.mean(ai_raw_probs)
    print(f"  Mean uncalibrated p_ai (Real): {mean_p_real:.4f} +/- {np.std(real_raw_probs):.4f}")
    print(f"  Mean uncalibrated p_ai (AI):   {mean_p_ai:.4f} +/- {np.std(ai_raw_probs):.4f}")

    y_all = np.array([0] * len(real_files) + [1] * len(ai_files))
    scores_all = np.array(real_raw_probs + ai_raw_probs)
    rel_logits_all = np.array(real_rel_logits + ai_rel_logits)

    auc_t1 = roc_auc_score(y_all, scores_all)
    print(f"  Full-set AUC at T=1: {auc_t1:.4f}")
    if auc_t1 < 0.5:
        raise ValueError(f"Inverted label mapping! AUC is {auc_t1:.4f} (< 0.5)")

    # 4. 70/30 Stratified Split for Temperature Scaling
    np.random.seed(42)
    n_real = len(real_files)
    n_ai = len(ai_files)
    perm_real = np.random.permutation(n_real)
    perm_ai = np.random.permutation(n_ai)

    split_real = int(0.7 * n_real)
    split_ai = int(0.7 * n_ai)

    train_indices = list(perm_real[:split_real]) + list(n_real + perm_ai[:split_ai])
    eval_indices = list(perm_real[split_real:]) + list(n_real + perm_ai[split_ai:])

    y_train = y_all[train_indices]
    logits_train = rel_logits_all[train_indices]
    probs_train = scores_all[train_indices]

    y_eval = y_all[eval_indices]
    logits_eval = rel_logits_all[eval_indices]
    probs_eval = scores_all[eval_indices]

    print(f"\nSplit: {len(train_indices)} train (70%), {len(eval_indices)} eval (30%)")

    # 5. Fit Temperature T with bounds [0.5, 10.0]
    T_MIN, T_MAX = 0.5, 10.0
    print(f"Fitting Temperature T with bounds [{T_MIN}, {T_MAX}]...")
    def nll_obj(T):
        p_cal = 1.0 / (1.0 + np.exp(-logits_train / max(0.1, T)))
        p_cal = np.clip(p_cal, 1e-6, 1.0 - 1e-6)
        return -np.sum(y_train * np.log(p_cal) + (1 - y_train) * np.log(1 - p_cal))

    res_t = minimize_scalar(nll_obj, bounds=(T_MIN, T_MAX), method="bounded")
    fitted_T = round(float(res_t.x), 4)

    if abs(fitted_T - T_MIN) < 0.01 or abs(fitted_T - T_MAX) < 0.01:
        print(f"WARNING: Fitted Temperature T={fitted_T} landed on or near search bound [{T_MIN}, {T_MAX}]!")
    else:
        print(f"Fitted Temperature T: {fitted_T}")

    # Evaluate calibration before/after on the 30% eval split
    calibrated_eval_probs = 1.0 / (1.0 + np.exp(-logits_eval / fitted_T))

    eval_auc_before = round(float(roc_auc_score(y_eval, probs_eval)), 4)
    eval_auc_after = round(float(roc_auc_score(y_eval, calibrated_eval_probs)), 4)
    eval_acc_before = round(float(accuracy_score(y_eval, (probs_eval >= 0.5).astype(int))), 4)
    eval_acc_after = round(float(accuracy_score(y_eval, (calibrated_eval_probs >= 0.5).astype(int))), 4)
    eval_ece_before = round(compute_ece(probs_eval, y_eval), 4)
    eval_ece_after = round(compute_ece(calibrated_eval_probs, y_eval), 4)

    eval_p_real = np.mean(calibrated_eval_probs[y_eval == 0])
    eval_p_ai = np.mean(calibrated_eval_probs[y_eval == 1])

    print("\n" + "-" * 50)
    print("AI DETECTOR CALIBRATION RESULTS (30% HELD-OUT EVAL SET):")
    print("-" * 50)
    print(f"  Accuracy (Before -> After):  {eval_acc_before*100:.1f}% -> {eval_acc_after*100:.1f}%")
    print(f"  ROC-AUC  (Before -> After):  {eval_auc_before:.4f} -> {eval_auc_after:.4f}")
    print(f"  ECE Error (Before -> After): {eval_ece_before:.4f} -> {eval_ece_after:.4f}")
    print(f"  Mean Calibrated p_ai (Real): {eval_p_real:.4f}")
    print(f"  Mean Calibrated p_ai (AI):   {eval_p_ai:.4f}")

    # 6. Forensics Calibration: ELA & Noise on Real vs Edited
    print("\n" + "-" * 50)
    print("FORENSICS CALIBRATION (REAL VS EDITED):")
    print("-" * 50)

    ela_real_scores, ela_edited_scores = [], []
    noise_real_scores, noise_edited_scores = [], []

    print("Computing ELA and Noise metrics on Real vs Edited sets...")
    for f in real_files:
        with Image.open(f) as img:
            im = img.convert("RGB")
            # ELA anomaly fraction
            ela_map = compute_ela_map(im, quality=90, scale=15.0)
            ela_gray = np.mean(ela_map, axis=2)
            med = float(np.median(ela_gray))
            mad = float(np.median(np.abs(ela_gray - med)))
            thresh = max(25.0, med + 3.5 * mad)
            fraction = float(np.count_nonzero(ela_gray > thresh)) / float(ela_gray.size)
            ela_real_scores.append(fraction)

            # Noise dispersion
            disp = compute_noise_dispersion(im)
            noise_real_scores.append(disp)

    for f in edited_files:
        with Image.open(f) as img:
            im = img.convert("RGB")
            # ELA anomaly fraction
            ela_map = compute_ela_map(im, quality=90, scale=15.0)
            ela_gray = np.mean(ela_map, axis=2)
            med = float(np.median(ela_gray))
            mad = float(np.median(np.abs(ela_gray - med)))
            thresh = max(25.0, med + 3.5 * mad)
            fraction = float(np.count_nonzero(ela_gray > thresh)) / float(ela_gray.size)
            ela_edited_scores.append(fraction)

            # Noise dispersion
            disp = compute_noise_dispersion(im)
            noise_edited_scores.append(disp)

    y_forensics = np.array([0] * len(real_files) + [1] * len(edited_files))
    ela_all = np.array(ela_real_scores + ela_edited_scores)
    noise_all = np.array(noise_real_scores + noise_edited_scores)

    ela_auc = round(float(roc_auc_score(y_forensics, ela_all)), 4)
    noise_auc = round(float(roc_auc_score(y_forensics, noise_all)), 4)
    print(f"  ELA Real-vs-Edited AUC:   {ela_auc:.4f}")
    print(f"  Noise Real-vs-Edited AUC: {noise_auc:.4f}")

    # Fit Platt parameters for ELA: p = 1 / (1 + exp(-(a * score + b)))
    def platt_obj(params, scores):
        a, b = params
        p = 1.0 / (1.0 + np.exp(-(a * scores + b)))
        p = np.clip(p, 1e-6, 1.0 - 1e-6)
        return -np.sum(y_forensics * np.log(p) + (1 - y_forensics) * np.log(1 - p))

    res_ela = minimize(platt_obj, [20.0, -2.0], args=(ela_all,), method="L-BFGS-B")
    ela_a, ela_b = round(float(res_ela.x[0]), 3), round(float(res_ela.x[1]), 3)

    res_noise = minimize(platt_obj, [5.0, -1.0], args=(noise_all,), method="L-BFGS-B")
    noise_a, noise_b = round(float(res_noise.x[0]), 3), round(float(res_noise.x[1]), 3)

    print(f"  ELA Platt Scaling:   a={ela_a}, b={ela_b}")
    print(f"  Noise Platt Scaling: a={noise_a}, b={noise_b}")

    # 7. Compute Evidence Weights directly from measured AUC (§4 rule):
    # - AUC >= 0.90 -> 0.65; 0.75-0.90 -> 0.45; <0.75 -> 0.25 + warning
    # - ELA capped at 0.35, Noise capped at 0.25
    def get_auc_weight(auc: float, cap: float = 0.65) -> Tuple[float, Optional[str]]:
        warn = None
        if auc >= 0.90:
            w = 0.65
        elif auc >= 0.75:
            w = 0.45
        else:
            w = 0.25
            warn = f"AUC ({auc:.4f}) is below 0.75, weight dropped to 0.25"
        w = min(w, cap)
        return round(w, 2), warn

    ai_weight, ai_warn = get_auc_weight(eval_auc_after, cap=0.65)
    ela_weight, ela_warn = get_auc_weight(ela_auc, cap=0.35)
    noise_weight, noise_warn = get_auc_weight(noise_auc, cap=0.25)

    print("\n" + "-" * 50)
    print("WEIGHTS DERIVED FROM MEASURED AUC:")
    print("-" * 50)
    print(f"  IMG-AI-01:    weight={ai_weight} (AUC={eval_auc_after:.4f}) {ai_warn or ''}")
    print(f"  IMG-ELA-01:   weight={ela_weight} (AUC={ela_auc:.4f}) {ela_warn or ''}")
    print(f"  IMG-NOISE-01: weight={noise_weight} (AUC={noise_auc:.4f}) {noise_warn or ''}")

    # 8. Save models/calibration.json
    now_str = datetime.date.today().isoformat()
    calibration_dict = {
        "temperature": {
            "ai_detector": fitted_T,
            "tamper_cnn": 2.0469,
            "voice": 1.0
        },
        "platt": {
            "ela": {"a": ela_a, "b": ela_b},
            "noise": {"a": noise_a, "b": noise_b},
            "forensics": {"a": 1.0, "b": 0.0}
        },
        "weights": {
            "IMG-AI-01": ai_weight,
            "IMG-ELA-01": ela_weight,
            "IMG-NOISE-01": noise_weight
        },
        "auc": {
            "IMG-AI-01": eval_auc_after,
            "IMG-ELA-01": ela_auc,
            "IMG-NOISE-01": noise_auc
        },
        "metadata": {
            "date": now_str,
            "eval_counts": {
                "real": len(real_files),
                "ai_full": len(ai_files),
                "edited": len(edited_files)
            },
            "eval_30_split": {
                "ai_accuracy": eval_acc_after,
                "ai_auc": eval_auc_after,
                "ai_ece_before": eval_ece_before,
                "ai_ece_after": eval_ece_after,
                "ai_mean_p_real": round(float(eval_p_real), 4),
                "ai_mean_p_ai": round(float(eval_p_ai), 4)
            },
            "fitted_temperature": fitted_T
        },
        "DOC-CNN-01": {
            "temperature": 2.0469,
            "ece_before": 0.06,
            "ece_after": 0.0586,
            "logistic": {"a": 1.0, "b": 0.0}
        },
        "DOC-ANOM-01": {
            "threshold": -0.05,
            "median_rank": 2.0,
            "top_5_rate": 0.85
        }
    }

    with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
        json.dump(calibration_dict, f, indent=2)

    print(f"\nWrote updated calibration and weights to {CALIBRATION_FILE}")

if __name__ == "__main__":
    run_calibration()
