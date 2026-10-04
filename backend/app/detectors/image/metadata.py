import os
import io
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from ..base import DetectorOutput, AnalysisContext
from ...schemas.evidence import Evidence
from ...scoring.weights import EVIDENCE_CATALOG

logger = logging.getLogger("lucen_ai.metadata")

# Known generator & editor signatures
AI_GENERATOR_KEYWORDS = [
    "midjourney", "dall-e", "dalle", "stable diffusion", "stablediffusion",
    "firefly", "novelai", "comfyui", "automatic1111", "bing image creator",
    "adobe firefly", "craiyon", "runway", "flux"
]

IMAGE_EDITOR_KEYWORDS = [
    "photoshop", "gimp", "lightroom", "snapseed", "canva", "pixlr",
    "vsco", "facetune", "picsart", "affinity photo", "paint.net"
]

def dms_to_decimal(dms, ref) -> float:
    """Converts EXIF degrees, minutes, seconds tuple/list to signed decimal degrees."""
    def _val(x):
        if isinstance(x, (tuple, list)):
            if len(x) == 2 and x[1] != 0:
                return float(x[0]) / float(x[1])
            return float(x[0])
        return float(x)
    try:
        deg = _val(dms[0])
        minute = _val(dms[1])
        sec = _val(dms[2])
        dec = deg + (minute / 60.0) + (sec / 3600.0)
        if isinstance(ref, bytes):
            ref = ref.decode("utf-8", errors="ignore")
        ref = str(ref).upper().strip()
        if ref in ("S", "W"):
            dec = -dec
        return round(dec, 6)
    except Exception:
        return 0.0

def parse_exif_gps(file_path: str) -> Optional[Dict[str, float]]:
    """Extracts latitude and longitude as decimal numbers from image EXIF."""
    try:
        import piexif
        exif_dict = piexif.load(file_path)
        gps = exif_dict.get("GPS", {})
        if gps and piexif.GPSIFD.GPSLatitude in gps and piexif.GPSIFD.GPSLongitude in gps:
            lat_dms = gps[piexif.GPSIFD.GPSLatitude]
            lat_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef, b'N')
            lng_dms = gps[piexif.GPSIFD.GPSLongitude]
            lng_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef, b'E')
            lat = dms_to_decimal(lat_dms, lat_ref)
            lng = dms_to_decimal(lng_dms, lng_ref)
            return {"lat": lat, "lng": lng}
    except Exception:
        pass

    try:
        with Image.open(file_path) as img:
            info = img.getexif()
            if info:
                gps_ifd = info.get_ifd(0x8825)
                if gps_ifd and 2 in gps_ifd and 4 in gps_ifd:
                    lat_dms = gps_ifd[2]
                    lat_ref = gps_ifd.get(1, 'N')
                    lng_dms = gps_ifd[4]
                    lng_ref = gps_ifd.get(3, 'E')
                    lat = dms_to_decimal(lat_dms, lat_ref)
                    lng = dms_to_decimal(lng_dms, lng_ref)
                    return {"lat": lat, "lng": lng}
    except Exception:
        pass

    return None

def parse_exif(file_path: str) -> Dict[str, Any]:
    """Extracts human-readable EXIF tags using PIL and piexif/exifread."""
    extracted = {}
    try:
        with Image.open(file_path) as img:
            info = img.getexif()
            if info:
                for tag_id, value in info.items():
                    tag = TAGS.get(tag_id, tag_id)
                    # Convert bytes to string if needed
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8", errors="ignore").strip("\x00")
                        except Exception:
                            value = str(value)
                    extracted[str(tag)] = value
                
                # Check Exif sub-IFD (0x8769) for DateTimeOriginal
                exif_sub = info.get_ifd(0x8769)
                if exif_sub:
                    for s_id, s_val in exif_sub.items():
                        s_tag = TAGS.get(s_id, s_id)
                        if isinstance(s_val, bytes):
                            try:
                                s_val = s_val.decode("utf-8", errors="ignore").strip("\x00")
                            except Exception:
                                s_val = str(s_val)
                        if str(s_tag) not in extracted:
                            extracted[str(s_tag)] = s_val
    except Exception as e:
        logger.debug(f"PIL EXIF extraction failed: {e}")

    # Fallback to piexif for DateTimeOriginal if missing
    if "DateTimeOriginal" not in extracted:
        try:
            import piexif
            ex_dict = piexif.load(file_path)
            ex_sub = ex_dict.get("Exif", {})
            if piexif.ExifIFD.DateTimeOriginal in ex_sub:
                dto = ex_sub[piexif.ExifIFD.DateTimeOriginal]
                if isinstance(dto, bytes):
                    dto = dto.decode("utf-8", errors="ignore").strip("\x00")
                extracted["DateTimeOriginal"] = str(dto)
        except Exception:
            pass

    # Fallback to exifread if Make/Model missing
    if "Make" not in extracted:
        try:
            import exifread
            with open(file_path, "rb") as f:
                tags = exifread.process_file(f, stop_tag="UNDEF", details=False)
                for k, v in tags.items():
                    clean_k = k.split()[-1]
                    if clean_k not in extracted:
                        extracted[clean_k] = str(v)
        except Exception:
            pass

    return extracted

def check_c2pa(file_path: str, mime_type: str = "image/jpeg") -> Tuple[Optional[Evidence], bool]:
    """Reads C2PA manifest if c2pa-python is installed and manifest is present."""
    try:
        import c2pa
        fmt = "image/png" if file_path.lower().endswith(".png") else "image/jpeg"
        with open(file_path, "rb") as f:
            with c2pa.Reader(fmt, f) as reader:
                manifest_json = reader.json()
                if not manifest_json:
                    return None, False

                data = json.loads(manifest_json) if isinstance(manifest_json, str) else manifest_json
                manifest_str = json.dumps(data).lower()

                # Check for generative AI declarations
                ai_terms = ["generative", "ai generated", "dall-e", "midjourney", "stable diffusion", "synthetic"]
                if any(t in manifest_str for t in ai_terms):
                    cat = EVIDENCE_CATALOG.get("IMG-C2PA-01", {"weight": 0.95, "title": "Content Credentials"})
                    ev = Evidence(
                        id="IMG-C2PA-01",
                        kind="risk",
                        raw_score=1.0,
                        calibrated_score=1.0,
                        weight=cat["weight"],
                        effective_weight=cat["weight"],
                        severity="high",
                        title=cat["title"],
                        reason="C2PA Content Credentials declare that this image was generated by an AI model.",
                        details={"manifest": data}
                    )
                    return ev, True

                # Signed valid camera manifest (provenance verified)
                cat2 = EVIDENCE_CATALOG.get("IMG-C2PA-02", {"weight": 0.0, "title": "Valid Camera Provenance"})
                ev2 = Evidence(
                    id="IMG-C2PA-02",
                    kind="info",
                    raw_score=0.0,
                    calibrated_score=0.0,
                    weight=0.0,
                    effective_weight=0.0,
                    severity="low",
                    title=cat2.get("title", "Valid Camera Provenance"),
                    reason="Valid digital C2PA signature verified from capture device.",
                    details={"manifest_title": data.get("title")}
                )
                return ev2, True

    except Exception as e:
        logger.debug(f"C2PA check skipped/failed: {e}")
        return None, False

class MetadataDetector:
    name: str = "metadata"
    timeout_s: float = 10.0

    def run(self, ctx: AnalysisContext) -> DetectorOutput:
        file_path = ctx.scratch.get("original_file_path") or (ctx.file_paths[0] if ctx.file_paths else "")
        if not file_path or not os.path.exists(file_path):
            return DetectorOutput()

        evidence: List[Evidence] = []
        exif = parse_exif(file_path)

        make = exif.get("Make", "").strip()
        model = exif.get("Model", "").strip()
        software = exif.get("Software", "").strip()
        dt_orig = exif.get("DateTimeOriginal", "").strip()
        dt_mod = exif.get("DateTime", "").strip()

        # 1. IMG-EXIF-01: No camera EXIF present
        if not make and not model:
            cat = EVIDENCE_CATALOG.get("IMG-EXIF-01", {"weight": 0.10, "title": "Missing Camera EXIF"})
            evidence.append(
                Evidence(
                    id="IMG-EXIF-01",
                    kind="risk",
                    raw_score=0.50,
                    calibrated_score=0.50,
                    weight=cat["weight"],
                    effective_weight=cat["weight"],
                    severity="low",
                    title=cat["title"],
                    reason="The file lacks expected camera device metadata (Make/Model). Commonly stripped by messaging apps.",
                    details={"present_tags": list(exif.keys())[:10]}
                )
            )

        # 2. Software tag analysis: Generator vs Editor
        if software:
            sw_lower = software.lower()
            matched_generator = next((g for g in AI_GENERATOR_KEYWORDS if g in sw_lower), None)
            matched_editor = next((ed for ed in IMAGE_EDITOR_KEYWORDS if ed in sw_lower), None)

            if matched_generator:
                cat = EVIDENCE_CATALOG.get("IMG-EXIF-02a", {"weight": 0.80, "title": "AI Generator in Metadata"})
                evidence.append(
                    Evidence(
                        id="IMG-EXIF-02a",
                        kind="risk",
                        raw_score=0.95,
                        calibrated_score=0.95,
                        weight=cat["weight"],
                        effective_weight=cat["weight"],
                        severity="high",
                        title=cat["title"],
                        reason=f"File metadata explicitly names an AI image generator ({software}).",
                        details={"software": software, "generator": matched_generator}
                    )
                )
            elif matched_editor:
                cat = EVIDENCE_CATALOG.get("IMG-EXIF-02b", {"weight": 0.35, "title": "Image Editor in Metadata"})
                evidence.append(
                    Evidence(
                        id="IMG-EXIF-02b",
                        kind="risk",
                        raw_score=0.80,
                        calibrated_score=0.80,
                        weight=cat["weight"],
                        effective_weight=cat["weight"],
                        severity="medium",
                        title=cat["title"],
                        reason=f"File metadata indicates post-capture editing software ({software}).",
                        details={"software": software, "editor": matched_editor}
                    )
                )

        # 3. IMG-EXIF-03: Timestamp logic check
        if dt_orig and dt_mod:
            try:
                # Standard EXIF format: "YYYY:MM:DD HH:MM:SS"
                fmt = "%Y:%m:%d %H:%M:%S"
                t_orig = datetime.strptime(dt_orig[:19], fmt)
                t_mod = datetime.strptime(dt_mod[:19], fmt)
                if t_orig > t_mod:
                    cat = EVIDENCE_CATALOG.get("IMG-EXIF-03", {"weight": 0.30, "title": "Inconsistent Timestamps"})
                    evidence.append(
                        Evidence(
                            id="IMG-EXIF-03",
                            kind="risk",
                            raw_score=0.70,
                            calibrated_score=0.70,
                            weight=cat["weight"],
                            effective_weight=cat["weight"],
                            severity="medium",
                            title=cat["title"],
                            reason=f"Original capture time ({dt_orig}) is recorded as later than modification time ({dt_mod}).",
                            details={"datetime_original": dt_orig, "datetime_modified": dt_mod}
                        )
                    )
            except Exception:
                pass

        # 4. C2PA Content Credentials check
        c2pa_ev, c2pa_found = check_c2pa(file_path)
        if c2pa_ev:
            evidence.append(c2pa_ev)

        gps_coords = parse_exif_gps(file_path)
        exif_summary = {
            "make": make or None,
            "model": model or None,
            "software": software or None,
            "datetime_original": dt_orig or None,
            "has_gps": bool(gps_coords) or ("GPSInfo" in exif),
            "gps": gps_coords,
            "c2pa_present": c2pa_found
        }
        ctx.scratch["exif_summary"] = exif_summary

        return DetectorOutput(
            evidence=evidence,
            extras={"exif_summary": exif_summary}
        )
