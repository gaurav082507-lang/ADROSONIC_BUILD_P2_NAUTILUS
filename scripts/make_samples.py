"""
scripts/make_samples.py

Automated collection and generation of demo and evaluation assets:
- Subcommand `ai-images`: Generates 6 realistic damage images using SD-Turbo (1-4 steps, CPU)
- Subcommand `genuine-images`: Downloads 6 genuine CC0/public domain damage photos from Wikimedia Commons
- Subcommand `real-voice`: Streams real voice clips from google/fleurs (hi_in, en_us)
- Subcommand `synthetic-voice`: Generates synthetic clips using Bhashini TTS via make_tts_eval.py
- Subcommand `calibrate`: Evaluates & updates image and voice calibration metrics
- Subcommand `copy-frontend-samples`: Copies demo files to web/public/samples/
- Subcommand `all`: Executes all pipeline steps sequentially
"""

import os
import sys
import time
import argparse
import json
import shutil
import urllib.parse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import httpx
import soundfile as sf
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

EVAL_AI_DIR = ROOT_DIR / "data" / "eval" / "images" / "ai_full"
EVAL_REAL_DIR = ROOT_DIR / "data" / "eval" / "images" / "real"
EVAL_VOICE_REAL_DIR = ROOT_DIR / "data" / "eval" / "voice" / "real"
EVAL_VOICE_SYNTH_DIR = ROOT_DIR / "data" / "eval" / "voice" / "synthetic"
DEMO_SAMPLES_DIR = ROOT_DIR / "data" / "demo_samples"
DEMO_VOICE_DIR = DEMO_SAMPLES_DIR / "voice"
SAMPLES_MD = ROOT_DIR / "data" / "SAMPLES.md"
WEB_SAMPLES_DIR = ROOT_DIR / "web" / "public" / "samples"

for d in [EVAL_AI_DIR, EVAL_REAL_DIR, EVAL_VOICE_REAL_DIR, EVAL_VOICE_SYNTH_DIR, DEMO_VOICE_DIR, WEB_SAMPLES_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def log_sample(category, filename, source, license_str, author, notes=""):
    """Append a record to data/SAMPLES.md."""
    if not SAMPLES_MD.exists():
        SAMPLES_MD.write_text("# Lucen AI — Asset Inventory & Provenance\n\n| Category | File | Source | License | Author | Notes |\n|---|---|---|---|---|---|\n", encoding="utf-8")
    
    with open(SAMPLES_MD, "a", encoding="utf-8") as f:
        f.write(f"| {category} | `{filename}` | {source} | {license_str} | {author} | {notes} |\n")


# ─────────────────────────────────────────────────────────────────────────────
# PART 0-A: AI Generated Images
# ─────────────────────────────────────────────────────────────────────────────
def run_ai_images():
    print("\n--- [Part 0-A] Generating AI Damage Photos (stabilityai/sd-turbo) ---")
    prompts = [
        ("gen_dented_car_door.jpg", "A realistic close-up photo of a modern silver sedan with a heavily dented passenger door after a side-impact car crash, sharp focus, natural daylight"),
        ("gen_cracked_bumper.jpg", "Photo of a black SUV with a severely cracked front plastic bumper and detached fog lamp in an urban parking lot"),
        ("gen_scratched_bonnet.jpg", "High resolution photo of deep key scratches and paint peel across the hood of a red hatchback"),
        ("gen_flooded_room_floor.jpg", "Realistic photo of water damage on a residential wooden parquet floor with puddles, damp walls, and soaked baseboards"),
        ("gen_broken_windscreen.jpg", "Detailed photo of a spiderweb cracked car windshield with shattered tempered glass impact on driver side"),
        ("gen_fire_damaged_kitchen.jpg", "Realistic photo of smoke, soot, and burnt electrical appliances on a modern kitchen counter after a small stove fire"),
    ]

    try:
        import torch
        from diffusers import AutoPipelineForText2Image
        print("Loading stabilityai/sd-turbo pipeline on CPU...")
        pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sd-turbo", torch_dtype=torch.float32, variant="fp16")
        pipe.to("cpu")
    except Exception as e:
        print(f"Skipping AI image generation (diffusers error or model unavailable: {e})")
        return

    for fname, prompt in prompts:
        out_path = EVAL_AI_DIR / fname
        if out_path.exists():
            print(f"Skipping existing {fname}")
            continue

        print(f"Generating {fname}...")
        t0 = time.time()
        try:
            image = pipe(prompt=prompt, num_inference_steps=2, guidance_scale=0.0).images[0]
            dur = time.time() - t0
            if dur > 180:
                print(f"Inference took {dur:.1f}s (> 180s limit). Skipping remaining.")
                break
            image.save(out_path, quality=95)
            print(f"  Saved {fname} in {dur:.1f}s")
            log_sample("AI Image", str(out_path.relative_to(ROOT_DIR)), "stabilityai/sd-turbo", "CreativeML OpenRAIL-M", "Lucen AI Generator", f"Prompt: {prompt[:40]}...")
            
            # If 01_ai_generated_car_damage.jpg does not exist, save there too
            target_demo = DEMO_SAMPLES_DIR / "01_ai_generated_car_damage.jpg"
            if not target_demo.exists() and "car" in fname:
                shutil.copy(out_path, target_demo)
                print(f"  Copied to demo sample: {target_demo.name}")
        except Exception as e:
            print(f"Error generating {fname}: {e}")
            break


# ─────────────────────────────────────────────────────────────────────────────
# PART 0-B: Genuine Photos (Wikimedia Commons API)
# ─────────────────────────────────────────────────────────────────────────────
def run_genuine_images():
    print("\n--- [Part 0-B] Downloading Genuine Photos from Wikimedia Commons ---")
    headers = {"User-Agent": "LucenAI-EvaluationBot/1.0 (contact@lucen.ai)"}
    
    with httpx.Client(headers=headers, timeout=30.0) as client:
        r = client.get("https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=car%20crash%20damage%20vehicle&srnamespace=6&format=json&srlimit=15")
        items = r.json().get("query", {}).get("search", [])
        
        saved_count = 0
        for item in items:
            if saved_count >= 6:
                break
            title = item.get("title", "")
            r2 = client.get(f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=imageinfo&iiprop=url|extmetadata&format=json")
            pages = r2.json().get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                info = pdata.get("imageinfo", [{}])[0]
                img_url = info.get("url")
                if not img_url:
                    continue
                clean_url = img_url.split("?")[0]
                if not clean_url.lower().endswith((".jpg", ".jpeg")):
                    continue
                meta = info.get("extmetadata", {})
                lic = meta.get("LicenseShortName", {}).get("value", "CC-BY-SA / Public Domain")
                artist = meta.get("Artist", {}).get("value", "Wikimedia Contributor")
                import re
                artist_clean = re.sub(r'<[^>]+>', '', artist).strip() or "Wikimedia Contributor"

                fname = f"wm_genuine_damage_{saved_count+1}.jpg"
                target_path = EVAL_REAL_DIR / fname
                
                try:
                    img_resp = client.get(img_url, follow_redirects=True)
                    if img_resp.status_code == 200 and len(img_resp.content) > 10000:
                        target_path.write_bytes(img_resp.content)
                        print(f"  Downloaded {fname} ({title})")
                        log_sample("Genuine Image", str(target_path.relative_to(ROOT_DIR)), clean_url, lic, artist_clean, f"Wikimedia Title: {title}")
                        
                        # Copy first genuine car photo as genuine_car.jpg
                        if saved_count == 0:
                            demo_target = DEMO_SAMPLES_DIR / "02_genuine_phone_photo.jpg"
                            # Backup suspect sample
                            suspect_bak = DEMO_SAMPLES_DIR / "02_genuine_phone_photo_suspect.jpg"
                            if demo_target.exists() and not suspect_bak.exists():
                                shutil.copy(demo_target, suspect_bak)
                            shutil.copy(target_path, demo_target)
                            print(f"  Replaced suspect demo photo with real camera photo: {demo_target.name}")
                        
                        saved_count += 1
                        break
                except Exception as e:
                    print(f"  Error downloading {title}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# PART 0-C: Real Human Voice Clips (google/fleurs)
# ─────────────────────────────────────────────────────────────────────────────
def run_real_voice():
    print("\n--- [Part 0-C] Collecting Real Voice Clips from Wikimedia Spoken / FLEURS ---")
    headers = {"User-Agent": "LucenAI-EvaluationBot/1.0 (contact@lucen.ai)"}
    
    searches = [
        ("LL-Q1568 (hin)", "hi", 10),
        ("LL-Q1860 (eng)", "en", 10),
    ]
    
    import av
    total_saved = 0
    with httpx.Client(headers=headers, timeout=30.0) as client:
        for query, lang, target_count in searches:
            print(f"Searching Wikimedia for {lang} audio ({query})...")
            url = f"https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&srnamespace=6&format=json&srlimit=25"
            resp = client.get(url)
            if resp.status_code != 200:
                continue
            items = resp.json().get("query", {}).get("search", [])
            
            saved = 0
            for item in items:
                if saved >= target_count:
                    break
                title = item.get("title", "")
                r2 = client.get(f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=imageinfo&iiprop=url|extmetadata&format=json")
                pages = r2.json().get("query", {}).get("pages", {})
                for pid, pdata in pages.items():
                    info = pdata.get("imageinfo", [{}])[0]
                    audio_url = info.get("url")
                    if not audio_url:
                        continue
                    
                    try:
                        a_resp = client.get(audio_url, follow_redirects=True)
                        if a_resp.status_code != 200 or len(a_resp.content) < 1000:
                            continue
                        
                        import io
                        in_buf = io.BytesIO(a_resp.content)
                        container = av.open(in_buf)
                        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
                        
                        raw_samples = []
                        for frame in container.decode(audio=0):
                            for r_frame in resampler.resample(frame):
                                raw_samples.append(r_frame.to_ndarray())
                        
                        if not raw_samples:
                            continue
                        
                        audio_arr = np.concatenate(raw_samples, axis=1).squeeze()
                        fname = f"real_{lang}_{saved+1:02d}.wav"
                        out_path = EVAL_VOICE_REAL_DIR / fname
                        sf.write(str(out_path), audio_arr, 16000)
                        print(f"  Saved {fname} ({title})")
                        
                        meta = info.get("extmetadata", {})
                        lic = meta.get("LicenseShortName", {}).get("value", "CC-BY-SA 4.0")
                        artist = meta.get("Artist", {}).get("value", "Lingua Libre Contributor")
                        import re
                        artist_clean = re.sub(r'<[^>]+>', '', artist).strip() or "Lingua Libre Contributor"
                        log_sample("Real Audio", str(out_path.relative_to(ROOT_DIR)), audio_url.split("?")[0], lic, artist_clean, f"Spoken {lang.upper()}")
                        
                        if lang == "hi" and saved == 0:
                            demo_hi = DEMO_VOICE_DIR / "real_hindi_statement.wav"
                            shutil.copy(out_path, demo_hi)
                            print(f"  Copied to demo sample: {demo_hi.name}")
                        
                        saved += 1
                        total_saved += 1
                        break
                    except Exception as e:
                        print(f"  Error processing {title}: {e}")
            print(f"  Saved {saved} {lang} clips.")
    print(f"Total real voice clips collected: {total_saved}")


# ─────────────────────────────────────────────────────────────────────────────
# PART 0-D: Synthetic Voice Clips (Bhashini TTS via make_tts_eval.py)
# ─────────────────────────────────────────────────────────────────────────────
def run_synthetic_voice():
    print("\n--- [Part 0-D] Generating Synthetic Voice Clips (Bhashini TTS) ---")
    tts_script = ROOT_DIR / "scripts" / "make_tts_eval.py"
    if tts_script.exists():
        import subprocess
        python_exe = sys.executable
        res = subprocess.run([python_exe, str(tts_script)], cwd=str(ROOT_DIR), capture_output=True, text=True)
        print(res.stdout)
        if res.returncode != 0:
            print(f"make_tts_eval.py finished with return code {res.returncode}. Stderr: {res.stderr[:200]}")
        
        # Check generated clips
        synth_clips = list(EVAL_VOICE_SYNTH_DIR.glob("*.wav"))
        print(f"Total synthetic voice clips present: {len(synth_clips)}")
        if synth_clips:
            demo_tts = DEMO_VOICE_DIR / "tts_hindi_statement.wav"
            shutil.copy(synth_clips[0], demo_tts)
            print(f"Copied {synth_clips[0].name} to demo sample {demo_tts.name}")
            log_sample("Synthetic Audio", "data/eval/voice/synthetic/*.wav", "Bhashini TTS API (ULCA)", "Government of India / Bhashini", "Bhashini TTS", f"{len(synth_clips)} generated clips")
    else:
        print("scripts/make_tts_eval.py not found.")


# ─────────────────────────────────────────────────────────────────────────────
# PART 0-E: Calibration Re-run
# ─────────────────────────────────────────────────────────────────────────────
def run_calibration():
    print("\n--- [Part 0-E] Re-running Evaluation & Calibration Verification ---")
    eval_script = ROOT_DIR / "scripts" / "test_part1_eval.py"
    if eval_script.exists():
        import subprocess
        res = subprocess.run([sys.executable, str(eval_script)], cwd=str(ROOT_DIR), capture_output=True, text=True)
        print(res.stdout)


# ─────────────────────────────────────────────────────────────────────────────
# PART 0-F: Copy Frontend Samples
# ─────────────────────────────────────────────────────────────────────────────
def run_copy_frontend():
    print("\n--- [Part 0-F] Copying Demo Samples to web/public/samples/ ---")
    mappings = [
        (DEMO_SAMPLES_DIR / "01_ai_generated_car_damage.jpg", WEB_SAMPLES_DIR / "ai_car.jpg"),
        (DEMO_SAMPLES_DIR / "02_genuine_phone_photo.jpg", WEB_SAMPLES_DIR / "genuine_car.jpg"),
        (DEMO_SAMPLES_DIR / "docs" / "tampered_invoice.pdf", WEB_SAMPLES_DIR / "tampered_invoice.pdf"),
        (DEMO_SAMPLES_DIR / "docs" / "clean_invoice.pdf", WEB_SAMPLES_DIR / "clean_invoice.pdf"),
        (DEMO_SAMPLES_DIR / "identity" / "01_valid_aadhaar_card.png", WEB_SAMPLES_DIR / "id_card.png"),
        (DEMO_SAMPLES_DIR / "identity" / "matching_selfie.jpg", WEB_SAMPLES_DIR / "selfie.jpg"),
    ]
    
    for src, dst in mappings:
        if src.exists():
            shutil.copy(src, dst)
            print(f"  Copied {src.name} -> {dst.name}")
        else:
            print(f"  Warning: source {src} not found!")


def main():
    parser = argparse.ArgumentParser(description="Lucen AI Sample Collection & Generation")
    parser.add_argument("command", choices=["ai-images", "genuine-images", "real-voice", "synthetic-voice", "calibrate", "copy-frontend-samples", "all"])
    args = parser.parse_args()

    if args.command in ("ai-images", "all"):
        run_ai_images()
    if args.command in ("genuine-images", "all"):
        run_genuine_images()
    if args.command in ("real-voice", "all"):
        run_real_voice()
    if args.command in ("synthetic-voice", "all"):
        run_synthetic_voice()
    if args.command in ("calibrate", "all"):
        run_calibration()
    if args.command in ("copy-frontend-samples", "all"):
        run_copy_frontend()

if __name__ == "__main__":
    main()
