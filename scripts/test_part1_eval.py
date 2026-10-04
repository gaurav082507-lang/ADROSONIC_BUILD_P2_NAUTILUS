import os
import sys
import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score, accuracy_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.model_registry import model_registry
from backend.app.detectors.base import AnalysisContext
from backend.app.detectors.image.ai_detector import AiImageDetector
from backend.app.scoring.quality import apply_quality_gate

def evaluate_runtime_vs_calibration():
    print("=" * 70)
    print("PART 1: EVALUATING RUNTIME AI DETECTOR vs CALIBRATION")
    print("=" * 70)

    model_registry.load_ai_detector()
    detector = AiImageDetector()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    real_dir = os.path.join(base_dir, "data", "eval", "images", "real")
    ai_dir = os.path.join(base_dir, "data", "eval", "images", "ai_full")

    real_files = sorted([os.path.join(real_dir, f) for f in os.listdir(real_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    ai_files = sorted([os.path.join(ai_dir, f) for f in os.listdir(ai_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))])

    y_true = [0] * len(real_files) + [1] * len(ai_files)
    all_files = real_files + ai_files

    runtime_p_list = []
    raw_p_list = []
    tta_p_list = []
    crop_p_list = []

    for fpath in all_files:
        with Image.open(fpath) as img:
            img_rgb = img.convert("RGB")
            ctx = AnalysisContext(
                job_id="eval_test",
                file_paths=[fpath],
                decoded_images=[img_rgb]
            )
            out = detector.run(ctx)
            p_calib = out.extras["p_ai"]
            details = out.extras["details"]
            runtime_p_list.append(p_calib)
            raw_p_list.append(details.get("p_ai_raw", p_calib))
            tta_p_list.append(details.get("p_ai_tta_q85", p_calib))

    # Metrics
    y_true = np.array(y_true)
    runtime_p = np.array(runtime_p_list)
    raw_p = np.array(raw_p_list)

    runtime_auc = roc_auc_score(y_true, runtime_p)
    runtime_acc = accuracy_score(y_true, (runtime_p >= 0.5).astype(int))

    raw_auc = roc_auc_score(y_true, raw_p)
    raw_acc = accuracy_score(y_true, (raw_p >= 0.5).astype(int))

    n_real = len(real_files)
    mean_p_real = np.mean(runtime_p[:n_real])
    mean_p_ai = np.mean(runtime_p[n_real:])

    raw_mean_p_real = np.mean(raw_p[:n_real])
    raw_mean_p_ai = np.mean(raw_p[n_real:])

    # Held-out 30/30 split (last 30 of real, last 30 of AI as per evaluation split)
    held_out_mask = np.zeros(len(y_true), dtype=bool)
    held_out_mask[30:60] = True
    held_out_mask[90:120] = True
    held_out_auc = roc_auc_score(y_true[held_out_mask], runtime_p[held_out_mask])
    held_out_acc = accuracy_score(y_true[held_out_mask], (runtime_p[held_out_mask] >= 0.5).astype(int))

    # Test different combinations
    print(f"Dataset: {len(real_files)} Real, {len(ai_files)} AI (Total: {len(all_files)})")
    print(f"\n--- Runtime Path (Exact detector.run: whole-image, T=1.0) ---")
    print(f"Runtime AUC (All 120):       {runtime_auc:.4f}")
    print(f"Runtime Accuracy (All 120):  {runtime_acc:.4f} (at threshold 0.5)")
    print(f"Held-out 30/30 AUC:          {held_out_auc:.4f} (Calibration baseline: 0.9846)")
    print(f"Held-out 30/30 Accuracy:     {held_out_acc:.4f} (Calibration baseline: 0.8611)")
    print(f"Mean p_ai (Real):            {mean_p_real:.4f}")
    print(f"Mean p_ai (AI):              {mean_p_ai:.4f}")

    print(f"\n--- Raw Single-Pass (Pre-TTA/Crop) ---")
    print(f"Raw AUC (All 120):           {raw_auc:.4f}")
    print(f"Raw Accuracy (All 120):      {raw_acc:.4f}")
    print(f"Mean raw p (Real):           {raw_mean_p_real:.4f}")
    print(f"Mean raw p (AI):             {raw_mean_p_ai:.4f}")

    print("\n" + "=" * 70)
    print("EVALUATING 4 DEMO SAMPLES")
    print("=" * 70)
    demo_dir = os.path.join(base_dir, "data", "demo_samples")
    demo_samples = [
        ("01_ai_generated_car_damage.jpg", "AI Generated Car Damage"),
        ("02_genuine_phone_photo.jpg", "Real / Genuine Phone Photo"),
        ("03_edited_spliced_photo.jpg", "Edited / Spliced Photo"),
        ("04_low_res_compressed.jpg", "Low-Res Compressed")
    ]

    for fname, label in demo_samples:
        fpath = os.path.join(demo_dir, fname)
        if not os.path.exists(fpath):
            print(f"MISSING demo sample: {fpath}")
            continue

        with Image.open(fpath) as img:
            img_rgb = img.convert("RGB")
            ctx = AnalysisContext(
                job_id="demo_eval",
                file_paths=[fpath],
                decoded_images=[img_rgb]
            )
            out = detector.run(ctx)
            ev = out.evidence[0]
            det = out.extras["details"]

            # Quality gate evaluation
            w, h = img.size
            q_flags = {
                "short_side_lt_512": min(w, h) < 512,
                "jpeg_quality_lt_50": False,
            }
            eff_weight, conf_mult = apply_quality_gate(
                evidence_id="IMG-AI-01",
                raw_weight=ev.weight,
                quality_flags=q_flags
            )

            print(f"\nSample: {fname} [{label}]")
            print(f"  Dimensions: {img.size[0]}x{img.size[1]}, Mode: {img.mode}")
            print(f"  Raw p_ai:             {det.get('p_ai_raw', 'N/A')}")
            print(f"  TTA q85 p_ai:         {det.get('p_ai_tta_q85', 'N/A')}")
            print(f"  Crop evaluated:       {det.get('crop_evaluated', False)}")
            print(f"  Calibrated p_ai:      {ev.calibrated_score}")
            print(f"  Severity:             {ev.severity}")
            print(f"  Quality multiplier:   {conf_mult} (Effective weight: {eff_weight:.4f} from base {ev.weight})")
            print(f"  Quality flags:        {q_flags}")

            # Check for demo suspect
            if "ai_generated" in fname.lower() and ev.calibrated_score < 0.5:
                print("  >>> DEMO SAMPLE SUSPECT: Expected AI, but calibrated p_ai < 0.5")
            elif "genuine" in fname.lower() and ev.calibrated_score >= 0.5:
                print("  >>> DEMO SAMPLE SUSPECT: Expected Genuine, but calibrated p_ai >= 0.5")

if __name__ == "__main__":
    evaluate_runtime_vs_calibration()


