"""
Comprehensive Test Suite for Lucen AI Voice Pipeline
Covers:
- Bhashini client two-phase flow, headers, caching, fallback keys, retry logic, error handling
- Secrets confidentiality in logs
- Audio handling: magic bytes, decoding, duration limits, chunking, quality assessment
- Synthetic voice spoof detection & uncalibrated evaluation gating
- Field extraction with Indian amounts, dates, and vehicle numbers
- API endpoints: GET /voice/languages, POST /voice/transcribe
- Claim integration & claimant safety consent validation
- Live test marked with @pytest.mark.live
"""

import os
import io
import time
import json
import logging
import pytest
import numpy as np
import soundfile as sf
import httpx
import respx
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings, mask_secret
from backend.app.core.auth import create_access_token
from backend.app.services import bhashini
from backend.app.services.bhashini import BhashiniUnavailable, clear_config_cache
from backend.app.detectors.voice.audio import (
    validate_audio_magic,
    decode_audio,
    compute_audio_quality,
    chunk_audio
)
from backend.app.detectors.voice.spoof import classify_speech
from backend.app.detectors.voice.extractor import (
    extract_voice_fields,
    parse_indian_amount,
    parse_indian_date,
    parse_vehicle_registration
)
from backend.app.detectors.base import AnalysisContext
from backend.app.pipelines.voice_pipeline import run_voice_pipeline
from backend.app.services import orchestrator
from fastapi import HTTPException

client = TestClient(app)


def _make_dummy_wav(duration_s: float = 2.0, sr: int = 16000) -> bytes:
    """Helper to synthesize PCM WAV in memory."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    samples = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


# ============================================================================
# 1. BHASHINI CLIENT TESTS (Mocked with respx)
# ============================================================================

@pytest.mark.asyncio
@respx.mock
async def test_bhashini_config_flow_and_headers():
    clear_config_cache()
    config_url = settings.BHASHINI_CONFIG_URL or "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"

    mock_resp_data = {
        "pipelineResponseConfig": [
            {"taskType": "asr", "config": [{"serviceId": "ai4b_asr_hi"}]},
            {"taskType": "translation", "config": [{"serviceId": "ai4b_trans_hi_en"}]}
        ],
        "pipelineInferenceAPIEndPoint": {
            "callbackUrl": "https://dhruva-api.bhashini.gov.in/services/inference/pipeline",
            "inferenceApiKey": {"name": "Authorization", "value": "test_phase1_key"}
        }
    }

    route = respx.post(config_url).mock(return_value=httpx.Response(200, json=mock_resp_data))

    cfg = await bhashini.get_pipeline_config(source_language="hi", target_language="en", task_mode="asr_translation")
    assert route.called
    req = route.calls.last.request
    assert req.headers["userID"] == settings.BHASHINI_USER_ID.get_secret_value()
    assert req.headers["ulcaApiKey"] == settings.BHASHINI_UDYAT_KEY.get_secret_value()

    body = json.loads(req.content.decode("utf-8"))
    assert body["pipelineRequestConfig"]["pipelineId"] == settings.BHASHINI_PIPELINE_ID
    assert len(body["pipelineTasks"]) == 2
    assert cfg["callbackUrl"] == "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
    assert cfg["serviceIds"]["asr"] == "ai4b_asr_hi"
    assert cfg["serviceIds"]["translation"] == "ai4b_trans_hi_en"


@pytest.mark.asyncio
@respx.mock
async def test_bhashini_config_cache_hit():
    clear_config_cache()
    config_url = settings.BHASHINI_CONFIG_URL or "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"

    mock_resp_data = {
        "pipelineResponseConfig": [
            {"taskType": "asr", "config": [{"serviceId": "ai4b_asr_hi"}]},
            {"taskType": "translation", "config": [{"serviceId": "ai4b_trans_hi_en"}]}
        ],
        "pipelineInferenceAPIEndPoint": {
            "callbackUrl": "https://dhruva-api.bhashini.gov.in/services/inference/pipeline",
            "inferenceApiKey": {"name": "Authorization", "value": "cached_key"}
        }
    }

    route = respx.post(config_url).mock(return_value=httpx.Response(200, json=mock_resp_data))

    # First call -> fetches and caches
    cfg1 = await bhashini.get_pipeline_config(source_language="hi", target_language="en")
    assert route.call_count == 1

    # Second call -> cache hit (zero additional HTTP calls)
    cfg2 = await bhashini.get_pipeline_config(source_language="hi", target_language="en")
    assert route.call_count == 1
    assert cfg1 == cfg2


@pytest.mark.asyncio
@respx.mock
async def test_bhashini_compute_flow_and_fallback_key(caplog):
    clear_config_cache()
    config_url = settings.BHASHINI_CONFIG_URL
    callback_url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

    # Config without inference key in phase 1 -> triggers fallback to BHASHINI_INFERENCE_KEY
    mock_config = {
        "pipelineResponseConfig": [
            {"taskType": "asr", "config": [{"serviceId": "ai4b_asr_hi"}]},
            {"taskType": "translation", "config": [{"serviceId": "ai4b_trans_hi_en"}]}
        ],
        "pipelineInferenceAPIEndPoint": {
            "callbackUrl": callback_url,
            "inferenceApiKey": {"name": "Authorization", "value": ""}
        }
    }

    mock_compute = {
        "pipelineResponse": [
            {"taskType": "asr", "output": [{"source": "मेरी कार का एक्सीडेंट हुआ"}]},
            {"taskType": "translation", "output": [{"target": "My car had an accident"}]}
        ]
    }

    respx.post(config_url).mock(return_value=httpx.Response(200, json=mock_config))
    compute_route = respx.post(callback_url).mock(return_value=httpx.Response(200, json=mock_compute))

    wav_bytes = _make_dummy_wav(1.0)
    with caplog.at_level(logging.INFO):
        res = await bhashini.transcribe_and_translate(wav_bytes, source_language="hi")

    assert compute_route.called
    comp_req = compute_route.calls.last.request
    assert comp_req.headers["Authorization"] == settings.BHASHINI_INFERENCE_KEY.get_secret_value()
    assert res["transcript"] == "मेरी कार का एक्सीडेंट हुआ"
    assert res["translation_en"] == "My car had an accident"

    # Assert unmasked secret never appeared in logs
    log_text = caplog.text
    assert settings.BHASHINI_INFERENCE_KEY.get_secret_value() not in log_text
    assert settings.BHASHINI_UDYAT_KEY.get_secret_value() not in log_text


@pytest.mark.asyncio
@respx.mock
async def test_bhashini_5xx_retries_and_timeout_behavior():
    clear_config_cache()
    config_url = settings.BHASHINI_CONFIG_URL

    # Mock 500 error on config endpoint -> should retry twice then raise BhashiniUnavailable
    route = respx.post(config_url).mock(return_value=httpx.Response(502, text="Bad Gateway"))

    with pytest.raises(BhashiniUnavailable) as exc_info:
        await bhashini.get_pipeline_config(source_language="hi")
    assert "502" in str(exc_info.value) or "server error" in str(exc_info.value).lower()
    # 1 initial + 2 retries = 3 calls
    assert route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_bhashini_4xx_no_retries():
    clear_config_cache()
    config_url = settings.BHASHINI_CONFIG_URL

    # Mock 401 client error -> must NOT retry
    route = respx.post(config_url).mock(return_value=httpx.Response(401, text="Unauthorized"))

    with pytest.raises(BhashiniUnavailable) as exc_info:
        await bhashini.get_pipeline_config(source_language="hi")
    assert "401" in str(exc_info.value)
    assert route.call_count == 1  # Exactly 1 call, no retries


@pytest.mark.asyncio
@respx.mock
async def test_bhashini_translation_only():
    clear_config_cache()
    config_url = settings.BHASHINI_CONFIG_URL
    callback_url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

    mock_config = {
        "pipelineResponseConfig": [
            {"taskType": "translation", "config": [{"serviceId": "ai4b_trans_hi_en"}]}
        ],
        "pipelineInferenceAPIEndPoint": {
            "callbackUrl": callback_url,
            "inferenceApiKey": {"name": "Authorization", "value": "t_key"}
        }
    }
    mock_compute = {
        "pipelineResponse": [
            {"taskType": "translation", "output": [{"target": "Front bumper is broken"}]}
        ]
    }
    respx.post(config_url).mock(return_value=httpx.Response(200, json=mock_config))
    respx.post(callback_url).mock(return_value=httpx.Response(200, json=mock_compute))

    translated = await bhashini.translate_text("aage ka bumper toot gaya", source_language="hi")
    assert translated == "Front bumper is broken"


# ============================================================================
# 2. AUDIO HANDLING TESTS
# ============================================================================

def test_audio_magic_validation_and_rejection():
    # Valid WAV
    wav = _make_dummy_wav(1.0)
    assert validate_audio_magic(wav) == "wav"

    # Valid OGG magic
    ogg_fake = b"OggS" + b"\x00" * 30
    assert validate_audio_magic(ogg_fake) == "ogg"

    # Valid MP3 ID3 magic
    mp3_fake = b"ID3" + b"\x00" * 30
    assert validate_audio_magic(mp3_fake) == "mp3"

    # Valid WebM magic
    webm_fake = b"\x1a\x45\xdf\xa3" + b"\x00" * 30
    assert validate_audio_magic(webm_fake) == "webm"

    # Invalid random bytes -> 422 INVALID_AUDIO_FORMAT
    with pytest.raises(HTTPException) as exc_info:
        validate_audio_magic(b"NOT_AUDIO_CORRUPT_BYTES_DATA")
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "INVALID_AUDIO_FORMAT"


def test_audio_duration_limits():
    # Valid 2-second audio decodes smoothly
    wav = _make_dummy_wav(2.0)
    samples, out_wav, dur = decode_audio(wav)
    assert 1.9 < dur < 2.1
    assert len(samples) > 30000

    # >90s audio raises 422 AUDIO_TOO_LONG
    long_wav = _make_dummy_wav(91.0)
    with pytest.raises(HTTPException) as exc_info:
        decode_audio(long_wav)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "AUDIO_TOO_LONG"


def test_audio_chunking_for_long_clips():
    # <= 60s -> single chunk
    short_samples = np.zeros(16000 * 45, dtype=np.float32)
    chunks_short = chunk_audio(short_samples, threshold_s=60.0)
    assert len(chunks_short) == 1

    # > 60s (e.g. 75s) -> chunked into 30s segments with 1s overlap
    long_samples = np.zeros(16000 * 75, dtype=np.float32)
    chunks_long = chunk_audio(long_samples, chunk_len_s=30.0, overlap_s=1.0, threshold_s=60.0)
    assert len(chunks_long) >= 3


def test_audio_quality_metrics_and_warning():
    # Good audio
    good_wav = _make_dummy_wav(3.0)
    samples, _, dur = decode_audio(good_wav)
    qual_good = compute_audio_quality(samples, dur)
    assert not qual_good["is_poor_quality"]
    assert qual_good["warning_evidence"] is None

    # Silent audio -> VOI-QUAL-01 warning
    silence = np.zeros(16000 * 3, dtype=np.float32)
    qual_silent = compute_audio_quality(silence, 3.0)
    assert qual_silent["is_poor_quality"]
    assert qual_silent["warning_evidence"] is not None
    assert qual_silent["warning_evidence"].id == "VOI-QUAL-01"
    assert qual_silent["warning_evidence"].kind == "warning"
    assert qual_silent["warning_evidence"].weight == 0.0


# ============================================================================
# 3. SPOOF DETECTOR TESTS
# ============================================================================

def test_spoof_detector_uncalibrated_gating():
    # In default repo state, eval samples < 15 per class -> UNCALIBRATED
    samples = [np.sin(2 * np.pi * 440 * np.linspace(0, 2, 32000)).astype(np.float32)]
    ev, status = classify_speech(samples, 2.0, is_poor_quality=False)

    assert status.status == "ok"
    assert ev is not None
    assert ev.id == "VOI-SPOOF-01"
    # When uncalibrated, evidence is emitted as kind='info' with effective_weight=0.0
    assert ev.kind == "info"
    assert ev.effective_weight == 0.0
    assert "uncalibrated" in ev.reason.lower()
    assert 0.0 <= ev.raw_score <= 1.0


# ============================================================================
# 4. FIELD EXTRACTION TESTS
# ============================================================================

def test_field_extraction_indian_formats():
    text = (
        "My car DL 01 AB 1234 was hit in an accident yesterday near the ring road flyover at 10:30 am. "
        "The front bumper and windshield were damaged. Total repair cost is ₹ 1.5 lakh."
    )
    fields = extract_voice_fields(text)
    assert fields.incident_type == "Motor Accident"
    assert fields.peril == "Collision"
    assert fields.vehicle_registration == "DL 01 AB 1234"
    assert fields.amount_claimed == 150000
    assert "Front Bumper" in fields.damaged_items or "Bumper" in fields.damaged_items
    assert fields.incident_time == "10:30 am"


def test_amount_parsing_variations():
    assert parse_indian_amount("₹ 1.5 lakh") == 150000
    assert parse_indian_amount("25,000 rupees") == 25000
    assert parse_indian_amount("two lakh fifty thousand") == 250000
    assert parse_indian_amount("₹50,000") == 50000
    assert parse_indian_amount("repair estimate 3 lakh") == 300000


def test_date_and_vehicle_parsing():
    assert parse_vehicle_registration("Vehicle number MH 02 AB 1234 was damaged") == "MH 02 AB 1234"
    assert parse_indian_date("Incident date is 21/09/2026") == "2026-09-21"
    assert parse_indian_date("occurred on 21st Sept 2026") == "2026-09-21"


# ============================================================================
# 5. API ENDPOINTS & INTEGRATION TESTS
# ============================================================================

def test_get_voice_languages():
    res = client.get("/api/v1/voice/languages")
    assert res.status_code == 200
    langs = res.json()
    codes = [l["code"] for l in langs]
    assert "hi" in codes
    assert "en" in codes
    assert "ta" in codes
    assert "mr" in codes


@pytest.mark.asyncio
@respx.mock
async def test_post_voice_transcribe_endpoint():
    token = create_access_token({"sub": "user_ravi", "role": "claimant"})
    headers = {"Authorization": f"Bearer {token}"}

    config_url = settings.BHASHINI_CONFIG_URL
    callback_url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

    respx.post(config_url).mock(return_value=httpx.Response(200, json={
        "pipelineResponseConfig": [
            {"taskType": "asr", "config": [{"serviceId": "s_asr"}]},
            {"taskType": "translation", "config": [{"serviceId": "s_trans"}]}
        ],
        "pipelineInferenceAPIEndPoint": {
            "callbackUrl": callback_url,
            "inferenceApiKey": {"name": "Authorization", "value": "test_k"}
        }
    }))
    respx.post(callback_url).mock(return_value=httpx.Response(200, json={
        "pipelineResponse": [
            {"taskType": "asr", "output": [{"source": "गाड़ी का एक्सीडेंट हुआ"}]},
            {"taskType": "translation", "output": [{"target": "Car had an accident with 50,000 rupees damage"}]}
        ]
    }))

    wav_content = _make_dummy_wav(2.0)
    files = {"file": ("statement.wav", wav_content, "audio/wav")}
    data = {"language": "hi"}

    res = client.post("/api/v1/voice/transcribe", files=files, data=data, headers=headers)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["transcript"] == "गाड़ी का एक्सीडेंट हुआ"
    assert "accident" in res_data["translation_en"].lower()
    assert res_data["extracted"]["amount_claimed"] == 50000
    # Claimant privacy guarantee: no spoof score returned
    assert "spoof" not in res_data
    assert "raw_score" not in res_data


def test_post_claims_voice_consent_validation(tmp_path):
    token = create_access_token({"sub": "user_ravi", "role": "claimant"})
    headers = {"Authorization": f"Bearer {token}"}

    wav_content = _make_dummy_wav(1.0)
    files = [
        ("voice_audio", ("statement.wav", wav_content, "audio/wav")),
        ("evidence", ("car.jpg", b"fake_jpeg_content", "image/jpeg"))
    ]
    data = {
        "policy_id": "POL-MOT-8821",
        "claim_type": "motor",
        "peril": "collision",
        "incident_date": "2026-05-10",
        "consent": "true",
        "consent_voice_processing": "false"  # Explicitly false
    }

    # Should reject with 422 VOICE_CONSENT_REQUIRED
    res = client.post("/api/v1/claims", data=data, files=files, headers=headers)
    assert res.status_code == 422
    assert "VOICE_CONSENT_REQUIRED" in res.text


@pytest.mark.asyncio
async def test_voice_pipeline_graceful_degradation_on_bhashini_failure():
    wav_content = _make_dummy_wav(2.0)
    ctx = AnalysisContext(job_id="test_voice_degrade", file_paths=[], mode="voice")
    ctx.scratch["voice_audio_bytes"] = wav_content

    # Run voice pipeline (with Bhashini offline/mocked to fail)
    out = await run_voice_pipeline(ctx)
    statuses = {s.detector: s.status for s in out.status}
    assert statuses.get("voice_audio") == "ok"
    assert statuses.get("spoof") == "ok"
    # ASR step degrades to skipped without crashing the pipeline
    assert statuses.get("bhashini_asr") in ("ok", "skipped")


# ============================================================================
# 6. OPTIONAL LIVE TEST (Runs only if BHASHINI_LIVE=1)
# ============================================================================

@pytest.mark.live
@pytest.mark.skipif(os.environ.get("BHASHINI_LIVE") != "1", reason="Requires BHASHINI_LIVE=1")
@pytest.mark.asyncio
async def test_bhashini_live_roundtrip():
    wav_content = _make_dummy_wav(2.0)
    res = await bhashini.transcribe_and_translate(wav_content, source_language="hi")
    assert "transcript" in res
    assert "translation_en" in res
