# Lucen AI — Evaluation Record

> All numbers here come from calibration runs, not from manual tuning on demo samples.
> Every threshold change must reference a section in this document.

---

## 1. AI Image Detector (IMG-AI-01)

| Setting | Value | Source |
|---|---|---|
| Model | `Ateeqq/ai-vs-human-image-detector` (SigLIP-based) | HuggingFace Hub |
| Eval set | 60 real + 60 AI-generated + 60 edited images (30/30/30 held-out split) | `docs/metrics/` |
| AUC (held-out) | 0.9846 | `models/calibration.json` → `auc.IMG-AI-01` |
| Accuracy (held-out) | 86.1% | `models/calibration.json` → `metadata.eval_30_split.ai_accuracy` |
| ECE (T=1, no calibration) | **0.139** | `models/calibration.json` → `metadata.eval_30_split.ai_ece_before` |
| ECE (T=5.0366, fitted) | 0.176 | `models/calibration.json` → `metadata.eval_30_split.ai_ece_after` |

### Temperature Decision (P0-4a)

**Rule**: Pick T by the lower held-out ECE.

- T=1 ECE = 0.139 < T=5.0366 ECE = 0.176 → **T=1 wins**.

`models/calibration.json` `temperature.ai_detector` set to **1.0**.

The fitted T=5.0366 over-sharpened probabilities on the held-out set (ECE went up), so
calibration is actually *harmful* here. T=1 (identity mapping) is the principled choice.

---

## 2. ELA Detector (IMG-ELA-01)

| Setting | Value | Source |
|---|---|---|
| AUC (test set) | 0.4667 | `models/calibration.json` → `auc.IMG-ELA-01` |
| Kind | **info** (not scored) | Applied per AUC rule below |

### AUC-to-Weight Rule (P0-4b)

| AUC range | Decision |
|---|---|
| < 0.60 | `kind="info"` — supporting context only, `effective_weight=0.0` |
| 0.60 – 0.75 | `weight=0.15` |
| 0.75 – 0.90 | `weight=0.45` |
| ≥ 0.90 | catalog weight (unchanged) |

**IMG-ELA-01**: AUC=0.467 < 0.60 → **info-only**. Changed in `ela.py` and `calibration.json`.

---

## 3. Noise Detector (IMG-NOISE-01)

| Setting | Value | Source |
|---|---|---|
| AUC (test set) | 0.6614 | `models/calibration.json` → `auc.IMG-NOISE-01` |
| Weight | **0.15** | AUC in [0.60, 0.75] range per AUC rule |

---

## 4. Tamper CNN (DOC-CNN-01)

| Setting | Value | Source |
|---|---|---|
| AUC val | 0.9019 | `models/calibration.json` → `DOC-CNN-01.auc_val` |
| AUC test | 0.8006 | `models/calibration.json` → `DOC-CNN-01.auc_test` |
| Clean false-alarm rate | 30% | `models/calibration.json` → `DOC-CNN-01.clean_false_alarm_rate` |
| Clean recall (test confusion) | 0.0 | `docs/metrics/tamper_metrics.json` → confusion [[0,33],[0,27]] |
| Weight (catalog) | 0.45 | AUC=0.80 in [0.75, 0.90] range |

### Corroboration Cap (P0-5)

Due to the 30% clean false-alarm rate and 0.0 clean recall, DOC-CNN-01 fires on clean documents.

**Rule**: `forensics` source cap = **0.30** in `scoring/fusion.py CAPS`.

**Lift**: The cap is removed (set to 1.0) when DOC-CNN-01's bounding box overlaps a
rule-based flag (DOC-LOGIC-*, DOC-FONT-*, DOC-OVERLAY-01) on the same page.
This mirrors the O2 override logic and prevents the CNN from dominating on clean docs.

---

## 5. Document Anomaly Detector (DOC-ANOM-01)

| Setting | Value | Source |
|---|---|---|
| AUC val | 0.50 | `models/calibration.json` → `DOC-ANOM-01.auc_val` |
| AUC test | 0.50 | `docs/metrics/anomaly_metrics.json` → 0 samples evaluated |
| Kind | **info** (not scored) | AUC < 0.60 per rule |

test_samples_evaluated = 0 in `docs/metrics/anomaly_metrics.json` — model was not evaluated
on a real test set. AUC=0.50 is uninformative (random). Detector remains **experimental**.

---

## 6. SFace Thresholds (ID-FACE-*)

| Threshold | Value | Source |
|---|---|---|
| t_high (MATCH) | 0.363 | OpenCV Zoo SFace published operating point (LFW FAR 0.1%) |
| t_low (AMBIGUOUS floor) | 0.30 | Conservative lower bound from SFace paper |

**P1-8** decision: Change `t_high` from 0.40 → **0.363** to align with published operating
point. `calibration.json` `face_match.sface.t_high` updated.

---

## 7. Items NOT Yet Measured

| ID | Metric | Status |
|---|---|---|
| IMG-NOISE-01 | TAR@FAR, full ROC | NOT MEASURED — only AUC available |
| DOC-CNN-01 | Clean recall on val set | 0.0 (all clean misclassified as tampered) |
| DOC-ANOM-01 | Any real test set | NOT MEASURED — 0 test samples |
| Face match | TAR@FAR on LFW | NOT MEASURED locally — using published values |
| Voice | AUC, EER | NOT MEASURED — model not loaded |

---

*Last updated: 2026-10-03 by correction run P0–P1.*
