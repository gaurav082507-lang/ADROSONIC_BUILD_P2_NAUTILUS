"""
Voice Pipeline
Coordinates audio validation, quality metrics, synthetic voice spoof detection,
Bhashini ASR + Machine Translation, and claim field extraction.
"""

import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..schemas.evidence import Evidence
from ..schemas.result import DetectorStatus
from ..detectors.base import AnalysisContext
from ..detectors.voice.audio import decode_audio, compute_audio_quality, chunk_audio
from ..detectors.voice.spoof import classify_speech
from ..detectors.voice.extractor import extract_voice_fields, VoiceExtractedFields
from ..services import bhashini

logger = logging.getLogger("lucen_ai.voice_pipeline")


@dataclass
class VoicePipelineOutput:
    evidence: List[Evidence] = field(default_factory=list)
    status: List[DetectorStatus] = field(default_factory=list)
    artifacts: Dict[str, Path] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)


async def run_voice_pipeline(ctx: AnalysisContext) -> VoicePipelineOutput:
    """
    Executes the voice analysis pipeline:
    1. Audio validation, decoding to 16kHz mono PCM, and quality evaluation.
    2. Synthetic speech spoof detection (offline model).
    3. Bhashini ASR & English translation (online service, optional/graceful degradation).
    4. Structured claim field extraction from translated statement.
    """
    out = VoicePipelineOutput()
    start_time = time.time()

    # 1. Retrieve audio data
    raw_bytes: Optional[bytes] = None
    if ctx.scratch.get("voice_audio_bytes"):
        raw_bytes = ctx.scratch["voice_audio_bytes"]
    elif ctx.file_paths:
        audio_path = Path(ctx.file_paths[0])
        if audio_path.exists():
            try:
                raw_bytes = audio_path.read_bytes()
            except Exception as e:
                logger.error(f"Failed to read audio file {audio_path}: {e}")

    if not raw_bytes:
        out.status.append(DetectorStatus(
            detector="voice_audio",
            status="failed",
            duration_ms=0,
            error="No audio data provided to voice pipeline."
        ))
        return out

    # 2. Decode & assess quality
    try:
        samples, wav_bytes, duration_s = decode_audio(raw_bytes)
        qual = compute_audio_quality(samples, duration_s)
        if qual.get("warning_evidence"):
            out.evidence.append(qual["warning_evidence"])
            out.extras["quality_warning"] = qual["warning_evidence"].model_dump()
        is_poor_quality = qual["is_poor_quality"]
        out.extras["audio_quality"] = qual
        out.extras["duration_s"] = duration_s
    except Exception as e:
        logger.warning(f"Audio decode/quality failure: {e}")
        out.status.append(DetectorStatus(
            detector="voice_audio",
            status="failed",
            duration_ms=int((time.time() - start_time) * 1000),
            error=str(e)
        ))
        return out

    out.status.append(DetectorStatus(
        detector="voice_audio",
        status="ok",
        duration_ms=int((time.time() - start_time) * 1000)
    ))

    # 3. Spoof detection (offline)
    chunks = chunk_audio(samples, chunk_len_s=30.0, overlap_s=1.0, threshold_s=60.0)
    spoof_ev, spoof_status = classify_speech(chunks, duration_s, is_poor_quality=is_poor_quality)
    out.status.append(spoof_status)
    if spoof_ev:
        out.evidence.append(spoof_ev)
        out.extras["spoof_evidence"] = spoof_ev.model_dump()

    # 4. Bhashini ASR + Translation (online, optional)
    meta = ctx.scratch.get("claim_metadata", {})
    transcript = meta.get("voice_transcript", "")
    translation_en = meta.get("voice_translation_en", "")
    source_lang = meta.get("voice_language") or meta.get("language") or "hi"

    # If transcript was already supplied (e.g. from sync wizard call or web speech)
    if transcript or translation_en:
        out.status.append(DetectorStatus(
            detector="bhashini_asr",
            status="ok",
            duration_ms=5
        ))
    else:
        asr_start = time.time()
        try:
            res = await bhashini.transcribe_and_translate(wav_bytes, source_language=source_lang)
            transcript = res.get("transcript", "")
            translation_en = res.get("translation_en", "")
            duration_ms = int((time.time() - asr_start) * 1000)
            out.status.append(DetectorStatus(
                detector="bhashini_asr",
                status="ok",
                duration_ms=duration_ms
            ))
        except bhashini.BhashiniUnavailable as e:
            duration_ms = int((time.time() - asr_start) * 1000)
            logger.info(f"Bhashini service unavailable ({e}); voice ASR step marked skipped.")
            out.status.append(DetectorStatus(
                detector="bhashini_asr",
                status="skipped",
                duration_ms=duration_ms,
                error=str(e)
            ))
        except Exception as e:
            duration_ms = int((time.time() - asr_start) * 1000)
            logger.warning(f"Bhashini ASR unexpected error ({e}); step skipped.")
            out.status.append(DetectorStatus(
                detector="bhashini_asr",
                status="skipped",
                duration_ms=duration_ms,
                error=str(e)
            ))

    if transcript or translation_en:
        out.evidence.append(
            Evidence(
                id="VOI-TXT-00",
                kind="info",
                raw_score=0.0,
                calibrated_score=0.0,
                weight=0.0,
                effective_weight=0.0,
                severity="low",
                title="Voice Statement Transcript",
                reason=f"Recorded statement transcribed ({source_lang}) and translated to English.",
                details={
                    "transcript": transcript,
                    "translation_en": translation_en,
                    "language": source_lang,
                }
            )
        )

    # 5. Field extraction
    extracted = extract_voice_fields(translation_en, transcript)
    out.extras["extracted_fields"] = extracted.model_dump()
    out.extras["transcript"] = transcript
    out.extras["translation_en"] = translation_en
    out.extras["language"] = source_lang

    return out
