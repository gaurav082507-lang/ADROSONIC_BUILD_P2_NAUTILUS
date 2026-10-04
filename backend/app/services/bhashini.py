"""
Bhashini Client Service
Integrates with Government of India ULCA / Bhashini language services
for ASR (Automatic Speech Recognition) and Machine Translation.

Documentation References:
- ULCA API Spec: https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline
- ULCA Swagger Spec: https://app.swaggerhub.com/apis/ulca/ULCA/0.7.0
- Bhashini Inference API: https://dhruva-api.bhashini.gov.in/services/inference/pipeline
"""

import base64
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
import httpx
from ..core.config import settings, mask_secret

logger = logging.getLogger(__name__)


class BhashiniUnavailable(Exception):
    """Raised when the Bhashini service fails, is unreachable, or returns an error."""
    pass


SUPPORTED_LANGUAGES = [
    {"code": "hi", "name": "Hindi", "native": "हिन्दी"},
    {"code": "bn", "name": "Bengali", "native": "বাংলা"},
    {"code": "te", "name": "Telugu", "native": "తెలుగు"},
    {"code": "mr", "name": "Marathi", "native": "मराठी"},
    {"code": "ta", "name": "Tamil", "native": "தமிழ்"},
    {"code": "ur", "name": "Urdu", "native": "اردو"},
    {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી"},
    {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ"},
    {"code": "ml", "name": "Malayalam", "native": "മലയാളം"},
    {"code": "or", "name": "Odia", "native": "ଓଡ଼ିଆ"},
    {"code": "pa", "name": "Punjabi", "native": "ਪੰਜਾਬੀ"},
    {"code": "as", "name": "Assamese", "native": "অসমীয়া"},
    {"code": "en", "name": "English", "native": "English"},
]

# In-memory config cache: (source_lang, target_lang, task_type) -> {data, expires_at}
_CONFIG_CACHE: Dict[tuple, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600


async def _execute_with_retries(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
    """
    Executes an HTTP request with:
    - 20s timeout
    - 2 retries on 5xx or timeout/network error with exponential backoff (0.5s, 1.0s)
    - 0 retries on 4xx status codes (immediately raises BhashiniUnavailable)
    """
    delays = [0.5, 1.0]
    last_err: Optional[Exception] = None

    for attempt in range(len(delays) + 1):
        try:
            resp = await client.request(method, url, timeout=20.0, **kwargs)
            if resp.status_code >= 500:
                if attempt < len(delays):
                    await asyncio.sleep(delays[attempt])
                    continue
                raise BhashiniUnavailable(f"Bhashini server error {resp.status_code}")
            if resp.status_code >= 400:
                # 4xx -> No retry
                raise BhashiniUnavailable(f"Bhashini client error {resp.status_code}: {resp.text}")
            return resp
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as exc:
            last_err = exc
            if attempt < len(delays):
                await asyncio.sleep(delays[attempt])
                continue
            raise BhashiniUnavailable(f"Bhashini network/timeout error: {exc}") from exc
        except BhashiniUnavailable:
            raise
        except Exception as exc:
            raise BhashiniUnavailable(f"Unexpected Bhashini error: {exc}") from exc

    raise BhashiniUnavailable(f"Bhashini call failed after retries: {last_err}")


def clear_config_cache() -> None:
    """Clears the in-memory pipeline config cache (used in tests)."""
    global _CONFIG_CACHE
    _CONFIG_CACHE.clear()


async def get_pipeline_config(
    source_language: str = "hi",
    target_language: str = "en",
    task_mode: str = "asr_translation"
) -> Dict[str, Any]:
    """
    Phase 1: Calls getModelsPipeline to fetch service IDs and inference endpoint.
    Caches the result per language pair with a 1-hour TTL.
    """
    cache_key = (source_language, target_language, task_mode)
    now = time.time()
    if cache_key in _CONFIG_CACHE:
        entry = _CONFIG_CACHE[cache_key]
        if entry["expires_at"] > now:
            logger.debug(f"Bhashini config cache hit for {cache_key}")
            return entry["data"]

    user_id = settings.BHASHINI_USER_ID.get_secret_value() if settings.BHASHINI_USER_ID else ""
    udyat_key = settings.BHASHINI_UDYAT_KEY.get_secret_value() if settings.BHASHINI_UDYAT_KEY else ""

    if not user_id or not udyat_key or not settings.BHASHINI_CONFIG_URL:
        raise BhashiniUnavailable("Bhashini credentials or config URL not configured")

    headers = {
        "userID": user_id,
        "ulcaApiKey": udyat_key,
        "Content-Type": "application/json",
    }

    if task_mode == "asr_translation":
        pipeline_tasks = [
            {
                "taskType": "asr",
                "config": {
                    "language": {
                        "sourceLanguage": source_language
                    }
                }
            },
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_language,
                        "targetLanguage": target_language
                    }
                }
            }
        ]
    elif task_mode == "translation":
        pipeline_tasks = [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_language,
                        "targetLanguage": target_language
                    }
                }
            }
        ]
    else:
        raise ValueError(f"Unsupported task_mode: {task_mode}")

    body = {
        "pipelineTasks": pipeline_tasks,
        "pipelineRequestConfig": {
            "pipelineId": settings.BHASHINI_PIPELINE_ID
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await _execute_with_retries(client, "POST", settings.BHASHINI_CONFIG_URL, headers=headers, json=body)
        data = resp.json()

    # Parse response
    service_ids: Dict[str, str] = {}
    for task_cfg in data.get("pipelineResponseConfig", []):
        ttype = task_cfg.get("taskType")
        cfg_list = task_cfg.get("config", [])
        if cfg_list and isinstance(cfg_list, list):
            service_ids[ttype] = cfg_list[0].get("serviceId", "")

    endpoint = data.get("pipelineInferenceAPIEndPoint", {})
    callback_url = endpoint.get("callbackUrl", "")
    inference_api_key = endpoint.get("inferenceApiKey", {})

    parsed = {
        "callbackUrl": callback_url,
        "inferenceApiKey": inference_api_key,
        "serviceIds": service_ids,
    }

    _CONFIG_CACHE[cache_key] = {
        "data": parsed,
        "expires_at": now + CACHE_TTL_SECONDS
    }
    return parsed


async def transcribe_and_translate(audio_wav_bytes: bytes, source_language: str = "hi") -> Dict[str, Any]:
    """
    Phase 2 (Compute):
    Transcribes audio in source language and translates to English using Bhashini.
    Returns: {"transcript": str, "translation_en": str, "source_language": str}
    """
    cfg = await get_pipeline_config(source_language=source_language, target_language="en", task_mode="asr_translation")

    callback_url = cfg.get("callbackUrl")
    if not callback_url:
        raise BhashiniUnavailable("Missing callbackUrl from Bhashini config response")

    inf_key_obj = cfg.get("inferenceApiKey") or {}
    key_name = inf_key_obj.get("name") or "Authorization"
    key_val = inf_key_obj.get("value")

    # Fallback to env key if phase 1 returned no key
    if not key_val:
        env_fallback = settings.BHASHINI_INFERENCE_KEY.get_secret_value() if settings.BHASHINI_INFERENCE_KEY else ""
        if not env_fallback:
            raise BhashiniUnavailable("No inference API key in phase-1 response and BHASHINI_INFERENCE_KEY is empty")
        key_val = env_fallback
        logger.info(f"Using Bhashini inference key from env fallback: {mask_secret(settings.BHASHINI_INFERENCE_KEY)}")
    else:
        logger.info(f"Using Bhashini inference key from phase-1 response: {mask_secret(key_val)}")

    headers = {
        key_name: key_val,
        "Content-Type": "application/json"
    }

    b64_audio = base64.b64encode(audio_wav_bytes).decode("ascii")

    asr_service_id = cfg.get("serviceIds", {}).get("asr", "")
    trans_service_id = cfg.get("serviceIds", {}).get("translation", "")

    body = {
        "pipelineTasks": [
            {
                "taskType": "asr",
                "config": {
                    "language": {
                        "sourceLanguage": source_language
                    },
                    "serviceId": asr_service_id,
                    "audioFormat": "wav",
                    "samplingRate": 16000
                }
            },
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_language,
                        "targetLanguage": "en"
                    },
                    "serviceId": trans_service_id
                }
            }
        ],
        "inputData": {
            "audio": [
                {
                    "audioContent": b64_audio
                }
            ]
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await _execute_with_retries(client, "POST", callback_url, headers=headers, json=body)
        data = resp.json()

    pipeline_resp = data.get("pipelineResponse", [])
    transcript = ""
    translation_en = ""

    for item in pipeline_resp:
        ttype = item.get("taskType")
        out_list = item.get("output", [])
        if not out_list:
            continue
        first_out = out_list[0]
        if ttype == "asr":
            transcript = first_out.get("source", "") or first_out.get("target", "")
        elif ttype == "translation":
            translation_en = first_out.get("target", "") or first_out.get("source", "")

    return {
        "transcript": transcript,
        "translation_en": translation_en,
        "source_language": source_language,
    }


async def translate_text(text: str, source_language: str = "hi") -> str:
    """
    Translates text from source_language to English using Bhashini.
    """
    if source_language.lower() in ("en", "english"):
        return text

    cfg = await get_pipeline_config(source_language=source_language, target_language="en", task_mode="translation")

    callback_url = cfg.get("callbackUrl")
    if not callback_url:
        raise BhashiniUnavailable("Missing callbackUrl from Bhashini config response")

    inf_key_obj = cfg.get("inferenceApiKey") or {}
    key_name = inf_key_obj.get("name") or "Authorization"
    key_val = inf_key_obj.get("value")

    if not key_val:
        env_fallback = settings.BHASHINI_INFERENCE_KEY.get_secret_value() if settings.BHASHINI_INFERENCE_KEY else ""
        if not env_fallback:
            raise BhashiniUnavailable("No inference API key available for translation")
        key_val = env_fallback
        logger.info(f"Using Bhashini inference key from env fallback: {mask_secret(settings.BHASHINI_INFERENCE_KEY)}")
    else:
        logger.info(f"Using Bhashini inference key from phase-1 response: {mask_secret(key_val)}")

    headers = {
        key_name: key_val,
        "Content-Type": "application/json"
    }

    trans_service_id = cfg.get("serviceIds", {}).get("translation", "")

    body = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_language,
                        "targetLanguage": "en"
                    },
                    "serviceId": trans_service_id
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

    async with httpx.AsyncClient() as client:
        resp = await _execute_with_retries(client, "POST", callback_url, headers=headers, json=body)
        data = resp.json()

    pipeline_resp = data.get("pipelineResponse", [])
    for item in pipeline_resp:
        out_list = item.get("output", [])
        if out_list:
            return out_list[0].get("target", "") or out_list[0].get("source", "")

    return ""
