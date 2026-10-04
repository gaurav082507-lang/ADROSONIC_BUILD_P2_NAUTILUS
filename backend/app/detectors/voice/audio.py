"""
Audio Validation, Decoding, and Quality Assessment Service
Supports webm/opus, ogg, mp3, m4a, wav.
Decodes to mono 16 kHz PCM float32 and 16-bit PCM WAV.
Computes quality metrics and emits VOI-QUAL-01 warning if quality is poor.
"""

import io
import math
import logging
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import av
import soundfile as sf
from fastapi import HTTPException

from ...schemas.evidence import Evidence
from ...core.config import settings

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_AUDIO_DURATION_S = 90.0         # 90 seconds
TARGET_SAMPLE_RATE = 16000


def validate_audio_magic(raw_bytes: bytes) -> str:
    """
    Validates audio format by header / magic bytes inspection (never trusting Content-Type alone).
    Returns format name or raises 422 INVALID_AUDIO_FORMAT.
    """
    if len(raw_bytes) < 12:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_AUDIO_FORMAT", "message": "Audio file is too small or empty."}
        )

    # WAV / RIFF: starts with RIFF and has WAVE at offset 8
    if raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WAVE":
        return "wav"

    # OGG: starts with OggS
    if raw_bytes[:4] == b"OggS":
        return "ogg"

    # WebM / MKV: starts with EBML ID \x1a\x45\xdf\xa3
    if raw_bytes[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"

    # MP3: ID3 header or sync frame (\xff\xfb, \xff\xf3, \xff\xf2)
    if raw_bytes[:3] == b"ID3" or raw_bytes[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"

    # M4A / MP4 / AAC: ftyp box at offset 4..8 or ADTS sync \xff\xf1 / \xff\xf9
    if raw_bytes[4:8] == b"ftyp" or raw_bytes[:2] in (b"\xff\xf1", b"\xff\xf9"):
        return "m4a"

    # FLAC magic: fLaC
    if raw_bytes[:4] == b"fLaC":
        return "flac"

    raise HTTPException(
        status_code=422,
        detail={
            "code": "INVALID_AUDIO_FORMAT",
            "message": "Unsupported audio format. Expected webm, ogg, mp3, m4a, or wav."
        }
    )


def validate_audio_size(raw_bytes: bytes, max_bytes: int = MAX_AUDIO_BYTES) -> None:
    """Rejects audio exceeding size limit with 422 AUDIO_TOO_LARGE."""
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "AUDIO_TOO_LARGE",
                "message": f"Audio file exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB."
            }
        )


def decode_audio(raw_bytes: bytes) -> Tuple[np.ndarray, bytes, float]:
    """
    Decodes audio from supported formats into mono 16kHz PCM float32 array
    and returns (samples_float32, wav_16k_pcm16_bytes, duration_s).
    Rejects duration > 90s with 422 AUDIO_TOO_LONG.
    """
    validate_audio_magic(raw_bytes)
    validate_audio_size(raw_bytes)

    # First attempt decode via PyAV
    samples: Optional[np.ndarray] = None
    try:
        container = av.open(io.BytesIO(raw_bytes))
        if not container.streams.audio:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_AUDIO_FORMAT", "message": "No audio stream found in container."}
            )
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="flt", layout="mono", rate=TARGET_SAMPLE_RATE)
        frames = []
        for frame in container.decode(stream):
            resampled = resampler.resample(frame)
            if resampled:
                for r in resampled:
                    frames.append(r.to_ndarray())
        if frames:
            samples = np.concatenate(frames, axis=-1).squeeze()
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"PyAV decode error, attempting fallback: {e}")

    # Fallback to soundfile if PyAV couldn't decode
    if samples is None or len(samples) == 0:
        try:
            data, sr = sf.read(io.BytesIO(raw_bytes), dtype="float32")
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            if sr != TARGET_SAMPLE_RATE:
                # Basic linear resample fallback
                num_target_samples = int(len(data) * TARGET_SAMPLE_RATE / sr)
                samples = np.interp(
                    np.linspace(0.0, 1.0, num_target_samples, endpoint=False),
                    np.linspace(0.0, 1.0, len(data), endpoint=False),
                    data
                ).astype(np.float32)
            else:
                samples = data
        except Exception as e2:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_AUDIO_FORMAT", "message": f"Could not decode audio: {e2}"}
            )

    if samples is None or len(samples) == 0:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_AUDIO_FORMAT", "message": "Decoded audio is empty."}
        )

    duration_s = float(len(samples)) / float(TARGET_SAMPLE_RATE)
    if duration_s > MAX_AUDIO_DURATION_S:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "AUDIO_TOO_LONG",
                "message": f"Audio duration ({duration_s:.1f}s) exceeds maximum allowed limit of {int(MAX_AUDIO_DURATION_S)}s."
            }
        )

    # Encode as standard mono 16kHz 16-bit PCM WAV in memory
    wav_buf = io.BytesIO()
    sf.write(wav_buf, samples, TARGET_SAMPLE_RATE, format="WAV", subtype="PCM_16")
    wav_bytes = wav_buf.getvalue()

    return samples, wav_bytes, duration_s


def compute_audio_quality(samples: np.ndarray, duration_s: float) -> Dict[str, Any]:
    """
    Computes quality metrics on mono 16kHz samples:
    - duration_s
    - rms (root-mean-square amplitude)
    - peak (maximum absolute sample value)
    - clipping_ratio (share of samples at or near [-1.0, 1.0])
    - silent (rms < 0.005)
    - snr_estimate (signal-to-noise ratio in dB: top 20% vs bottom 20% frame energies)

    If silent, duration < 2s, or clipping > 0.05:
    Emits VOI-QUAL-01 warning evidence.
    Per §15.4 / §18: quality warning lowers confidence, never raises risk score.
    """
    if len(samples) == 0:
        rms = 0.0
        peak = 0.0
        clipping_ratio = 0.0
        silent = True
        snr_db = 0.0
    else:
        rms = float(np.sqrt(np.mean(samples ** 2)))
        peak = float(np.max(np.abs(samples)))
        clipping_ratio = float(np.sum(np.abs(samples) >= 0.99) / len(samples))
        silent = bool(rms < 0.005)

        # 20ms frames = 320 samples at 16kHz
        frame_size = 320
        num_frames = len(samples) // frame_size
        if num_frames > 5:
            frames = samples[: num_frames * frame_size].reshape((num_frames, frame_size))
            frame_rms = np.sqrt(np.mean(frames ** 2, axis=1))
            sorted_rms = np.sort(frame_rms)
            k = max(1, int(math.ceil(num_frames * 0.2)))
            top_k_rms = float(np.mean(sorted_rms[-k:]))
            bot_k_rms = float(np.mean(sorted_rms[:k]))
            snr_db = float(20.0 * np.log10(max(top_k_rms, 1e-6) / max(bot_k_rms, 1e-6)))
        else:
            snr_db = 15.0 if not silent else 0.0

    is_poor_quality = bool(silent or (duration_s < 2.0) or (clipping_ratio > 0.05))

    quality_warning: Optional[Evidence] = None
    if is_poor_quality:
        reasons = []
        if silent:
            reasons.append("audio is near silent (RMS < 0.005)")
        if duration_s < 2.0:
            reasons.append(f"audio is too short ({duration_s:.1f}s < 2s)")
        if clipping_ratio > 0.05:
            reasons.append(f"high audio clipping ({clipping_ratio:.1%})")

        reason_str = f"Audio quality degraded: {', '.join(reasons)}."
        quality_warning = Evidence(
            id="VOI-QUAL-01",
            kind="warning",
            raw_score=0.0,
            calibrated_score=0.0,
            weight=0.0,
            effective_weight=0.0,
            severity="low",
            title="Audio Quality Warning",
            reason=reason_str,
            details={
                "duration_s": round(duration_s, 2),
                "rms": round(rms, 4),
                "peak": round(peak, 4),
                "clipping_ratio": round(clipping_ratio, 4),
                "silent": silent,
                "snr_db": round(snr_db, 1),
            }
        )

    return {
        "duration_s": round(duration_s, 2),
        "rms": round(rms, 4),
        "peak": round(peak, 4),
        "clipping_ratio": round(clipping_ratio, 4),
        "silent": silent,
        "snr_db": round(snr_db, 1),
        "is_poor_quality": is_poor_quality,
        "warning_evidence": quality_warning,
    }


def chunk_audio(
    samples: np.ndarray,
    chunk_len_s: float = 30.0,
    overlap_s: float = 1.0,
    threshold_s: float = 60.0
) -> List[np.ndarray]:
    """
    If duration > 60s, chunks audio into 30s segments with 1s overlap
    to prevent memory exhaustion in transformer models.
    Otherwise returns [samples].
    """
    duration_s = float(len(samples)) / float(TARGET_SAMPLE_RATE)
    if duration_s <= threshold_s:
        return [samples]

    chunk_size = int(chunk_len_s * TARGET_SAMPLE_RATE)
    step = int((chunk_len_s - overlap_s) * TARGET_SAMPLE_RATE)

    chunks: List[np.ndarray] = []
    start = 0
    while start < len(samples):
        end = min(start + chunk_size, len(samples))
        chunk = samples[start:end]
        if len(chunk) >= TARGET_SAMPLE_RATE:  # At least 1 second
            chunks.append(chunk)
        if end >= len(samples):
            break
        start += step

    return chunks if chunks else [samples]
