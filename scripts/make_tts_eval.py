"""
Generate synthetic voice evaluation samples using Bhashini TTS.
Saves >= 20 audio clips into data/eval/voice/synthetic/.

NOTE: This script must be run manually by the user.
Never run this script automatically or from tests.
"""

import os
import sys
import base64
import json
from pathlib import Path
import httpx

# Ensure repo root and backend are in path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.config import settings, mask_secret

OUTPUT_DIR = ROOT_DIR / "data" / "eval" / "voice" / "synthetic"

PROMPTS = [
    # 10 Hindi prompts
    ("hi", "female", "meri gaadi ka accident kal shaam ko ring road par hua tha."),
    ("hi", "male", "samne se aane wale auto ne meri bike ko zor se takkar maar di."),
    ("hi", "female", "gaadi ka aage ka bumper aur headlights poori tarah toot gaye hain."),
    ("hi", "male", "kripya meri claim application ko jald se jald process karein."),
    ("hi", "female", "hospital me dakhil hone ke baad maine doctor ka parcha sambhal kar rakha hai."),
    ("hi", "male", "repair invoice kul pachas hazaar rupaye ka banaya gaya hai."),
    ("hi", "female", "accident ke samay meri gaadi ki speed tees kilometer prati ghanta thi."),
    ("hi", "male", "police station me maine FIR darj karva di hai aur copy upload ki hai."),
    ("hi", "female", "yeh mera insurance policy number hai jisme vehicle covered hai."),
    ("hi", "male", "kripya inspection ke liye surveyor ko mere ghar bhejne ki kripa karein."),
    # 10 English prompts
    ("en", "female", "My car collided with a divider near the airport signal yesterday afternoon."),
    ("en", "male", "The rear windshield and tail lamps were completely shattered in the accident."),
    ("en", "female", "The total repair estimate provided by the workshop is seventy-five thousand rupees."),
    ("en", "male", "I have uploaded the original invoice and the payment receipt for verification."),
    ("en", "female", "The incident occurred on twenty-first of September around five in the evening."),
    ("en", "male", "Please review my claim statement and dispatch a surveyor for inspection."),
    ("en", "female", "The vehicle registration number is DL 01 AB 1234 as registered on the policy."),
    ("en", "male", "Both doors on the driver side are dented and require full replacement."),
    ("en", "female", "I was driving alone when the vehicle suddenly skidded due to wet road conditions."),
    ("en", "male", "All medical bills and pharmacy receipts have been submitted with the claim."),
]


def fetch_tts_config(source_language: str) -> dict:
    user_id = settings.BHASHINI_USER_ID.get_secret_value() if settings.BHASHINI_USER_ID else ""
    udyat_key = settings.BHASHINI_UDYAT_KEY.get_secret_value() if settings.BHASHINI_UDYAT_KEY else ""

    headers = {
        "userID": user_id,
        "ulcaApiKey": udyat_key,
        "Content-Type": "application/json"
    }

    body = {
        "pipelineTasks": [
            {
                "taskType": "tts",
                "config": {
                    "language": {
                        "sourceLanguage": source_language
                    }
                }
            }
        ],
        "pipelineRequestConfig": {
            "pipelineId": settings.BHASHINI_PIPELINE_ID
        }
    }

    with httpx.Client(timeout=25.0) as client:
        resp = client.post(settings.BHASHINI_CONFIG_URL, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    service_id = ""
    for item in data.get("pipelineResponseConfig", []):
        if item.get("taskType") == "tts":
            cfg_list = item.get("config", [])
            if cfg_list:
                service_id = cfg_list[0].get("serviceId", "")

    endpoint = data.get("pipelineInferenceAPIEndPoint", {})
    return {
        "callbackUrl": endpoint.get("callbackUrl", ""),
        "inferenceApiKey": endpoint.get("inferenceApiKey", {}),
        "serviceId": service_id
    }


def synthesize_clip(lang: str, gender: str, text: str, cfg: dict, out_path: Path):
    callback_url = cfg["callbackUrl"]
    inf_key_obj = cfg["inferenceApiKey"]
    key_name = inf_key_obj.get("name") or "Authorization"
    key_val = inf_key_obj.get("value") or (settings.BHASHINI_INFERENCE_KEY.get_secret_value() if settings.BHASHINI_INFERENCE_KEY else "")

    headers = {
        key_name: key_val,
        "Content-Type": "application/json"
    }

    body = {
        "pipelineTasks": [
            {
                "taskType": "tts",
                "config": {
                    "language": {
                        "sourceLanguage": lang
                    },
                    "serviceId": cfg["serviceId"],
                    "gender": gender,
                    "samplingRate": 16000
                }
            }
        ],
        "inputData": {
            "input": [
                {
                    "source": text
                }
            ]
        }
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(callback_url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    audio_b64 = ""
    for item in data.get("pipelineResponse", []):
        audios = item.get("audio", [])
        if audios:
            audio_b64 = audios[0].get("audioContent", "")
            break

    if not audio_b64:
        raise RuntimeError("No audioContent in Bhashini TTS response")

    raw_audio = base64.b64decode(audio_b64)
    with open(out_path, "wb") as f:
        f.write(raw_audio)


def main():
    print(f"Bhashini User ID: {mask_secret(settings.BHASHINI_USER_ID)}")
    print(f"Bhashini Udyat Key: {mask_secret(settings.BHASHINI_UDYAT_KEY)}")
    print(f"Bhashini Pipeline ID: {settings.BHASHINI_PIPELINE_ID}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    configs = {}
    for lang in ("hi", "en"):
        print(f"Fetching TTS config for language: {lang}...")
        try:
            configs[lang] = fetch_tts_config(lang)
            print(f"[OK] Got serviceId: {configs[lang]['serviceId']}")
        except Exception as e:
            print(f"[ERROR] Failed to fetch config for {lang}: {e}")
            return

    for idx, (lang, gender, text) in enumerate(PROMPTS, start=1):
        out_file = OUTPUT_DIR / f"tts_sample_{idx:02d}_{lang}_{gender}.wav"
        print(f"[{idx}/{len(PROMPTS)}] Synthesizing ({lang}, {gender}) -> {out_file.name}...")
        try:
            synthesize_clip(lang, gender, text, configs[lang], out_file)
            print(f"       -> Saved {out_file.stat().st_size} bytes")
        except Exception as e:
            print(f"       -> [FAIL] {e}")

    print(f"\nDone! Clips saved to {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
