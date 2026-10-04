"""
Voice API Endpoints
- GET /voice/languages: List supported Bhashini Indian languages.
- POST /voice/transcribe: Synchronous voice transcription + translation + field auto-fill for claimant wizard.
"""

import base64
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel

from ...core.auth import get_current_user, require_role
from ...services import bhashini
from ...detectors.voice.audio import decode_audio
from ...detectors.voice.extractor import extract_voice_fields, VoiceExtractedFields

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice"])

_VOICE_ROLES = Depends(require_role("claimant", "investigator"))


class LanguageItem(BaseModel):
    code: str
    name: str
    native: str


class TranscribeRequest(BaseModel):
    audio_base64: Optional[str] = None
    language: str = "hi"
    text: Optional[str] = None  # For Web Speech fallback translation


class TranscribeResponse(BaseModel):
    language: str
    duration_s: float
    transcript: str
    translation_en: str
    extracted: VoiceExtractedFields
    source: str  # "bhashini" | "web_speech" | "mock"


@router.get("/languages", response_model=List[LanguageItem])
def get_supported_languages():
    """Returns list of supported Indian languages with codes, English names, and native names."""
    return [LanguageItem(**item) for item in bhashini.SUPPORTED_LANGUAGES]


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_voice(
    request: Request,
    file: Optional[UploadFile] = File(default=None),
    language: str = Form("hi"),
    text: Optional[str] = Form(None),
    _user: Dict[str, Any] = _VOICE_ROLES
):
    """
    Synchronously transcribes audio, translates to English via Bhashini,
    and extracts structured claim fields.
    Does NOT return spoof score or risk metrics (claimant privacy safety).
    Supports text-only translation for browser Web Speech API fallbacks.
    """
    upload = file
    if not upload or not getattr(upload, 'filename', None):
        try:
            form_data = await request.form()
            for k in ("file", "audio", "voice"):
                val = form_data.get(k)
                if hasattr(val, 'filename') and bool(val.filename):
                    upload = val
                    break
        except Exception:
            pass
            
    # 1. Text-only translation (Web Speech fallback)
    if text and not upload:
        try:
            trans_en = await bhashini.translate_text(text, source_language=language)
        except Exception as e:
            logger.warning(f"Translation failed for text fallback: {e}")
            trans_en = text
        extracted = extract_voice_fields(trans_en, text)
        return TranscribeResponse(
            language=language,
            duration_s=0.0,
            transcript=text,
            translation_en=trans_en,
            extracted=extracted,
            source="web_speech"
        )

    # 2. Audio file transcription
    if file is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_AUDIO_FORMAT", "message": "No audio file or text provided."}
        )

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_AUDIO_FORMAT", "message": "Audio file is empty."}
        )

    # Decode and validate audio (enforces <= 10MB, <= 90s, and magic bytes)
    samples, wav_bytes, duration_s = decode_audio(raw_bytes)

    transcript = ""
    translation_en = ""
    source = "bhashini"

    try:
        res = await bhashini.transcribe_and_translate(wav_bytes, source_language=language)
        transcript = res.get("transcript", "")
        translation_en = res.get("translation_en", "")
    except bhashini.BhashiniUnavailable as e:
        logger.warning(f"Bhashini unavailable during transcribe endpoint: {e}")
        # Return empty transcript with graceful notice rather than 500 crash
        transcript = ""
        translation_en = ""
        source = "mock"

    extracted = extract_voice_fields(translation_en, transcript)

    return TranscribeResponse(
        language=language,
        duration_s=round(duration_s, 2),
        transcript=transcript,
        translation_en=translation_en,
        extracted=extracted,
        source=source
    )
