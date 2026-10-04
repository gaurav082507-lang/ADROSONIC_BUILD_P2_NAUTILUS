import os
import sys
import zlib
import io
import re
import logging
import cv2
import numpy as np
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple

sys.set_int_max_str_digits(50000)

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import rapidfuzz

from ...core.config import settings
from ...core.model_registry import model_registry
from ...schemas.evidence import Evidence, BBox
from ...scoring.weights import EVIDENCE_CATALOG

logger = logging.getLogger("lucen_ai.identity.aadhaar_qr")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
TEST_PUBKEY_PATH = os.path.join(REPO_ROOT, "models", "uidai", "test_pubkey.pem")
TEST_PRIVKEY_PATH = os.path.join(REPO_ROOT, "models", "uidai", "test_key.pem")


def decode_qr_from_image(image_bgr: np.ndarray) -> Optional[str]:
    """
    Attempts to read QR code string from image using zxing-cpp, pyzbar, and OpenCV.
    """
    # 1. Try zxingcpp (fastest and handles high-density QRs)
    try:
        import zxingcpp
        res = zxingcpp.read_barcode(image_bgr)
        if res and res.text:
            return res.text
    except Exception as e:
        logger.debug(f"zxingcpp QR decode failed: {e}")

    # 2. Try pyzbar
    try:
        from pyzbar.pyzbar import decode
        decoded = decode(image_bgr)
        if decoded:
            return decoded[0].data.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.debug(f"pyzbar QR decode failed: {e}")

    # 3. Try OpenCV QRCodeDetector
    try:
        detector = cv2.QRCodeDetector()
        val, _, _ = detector.detectAndDecode(image_bgr)
        if val:
            return val
    except Exception as e:
        logger.debug(f"OpenCV QR decode failed: {e}")

    return None


def parse_secure_qr_payload(qr_text: str) -> Optional[Dict[str, Any]]:
    """
    Decodes UIDAI Secure QR payload from a big decimal integer string or compressed bytes.
    Splits text fields delimited by 0xFF, isolates embedded photo bytes and 256-byte RSA signature.
    """
    try:
        # Check if digits string
        if qr_text.strip().isdigit():
            qr_int = int(qr_text.strip())
            qr_bytes = qr_int.to_bytes((qr_int.bit_length() + 7) // 8, byteorder="big")
        else:
            qr_bytes = qr_text.encode("latin-1")

        # Decompress zlib payload
        try:
            decompressed = zlib.decompress(qr_bytes)
        except Exception:
            # Try with wbits for gzip or raw deflate
            decompressed = zlib.decompress(qr_bytes, 16 + zlib.MAX_WBITS)

        if len(decompressed) < 257:
            return None

        # Last 256 bytes are the RSA-2048 SHA-256 signature
        data_to_sign = decompressed[:-256]
        signature = decompressed[-256:]

        # Fields separated by 0xFF
        parts = data_to_sign.split(b"\xff")
        if len(parts) < 5:
            return None

        def safe_decode(b_val: bytes) -> str:
            return b_val.decode("utf-8", errors="ignore").strip()

        fields = {
            "email_mobile_present": safe_decode(parts[0]),
            "reference_id": safe_decode(parts[1]) if len(parts) > 1 else "",
            "name": safe_decode(parts[2]) if len(parts) > 2 else "",
            "dob": safe_decode(parts[3]) if len(parts) > 3 else "",
            "gender": safe_decode(parts[4]) if len(parts) > 4 else "",
            "care_of": safe_decode(parts[5]) if len(parts) > 5 else "",
            "district": safe_decode(parts[6]) if len(parts) > 6 else "",
            "landmark": safe_decode(parts[7]) if len(parts) > 7 else "",
            "house": safe_decode(parts[8]) if len(parts) > 8 else "",
            "location": safe_decode(parts[9]) if len(parts) > 9 else "",
            "pincode": safe_decode(parts[10]) if len(parts) > 10 else "",
            "post_office": safe_decode(parts[11]) if len(parts) > 11 else "",
            "state": safe_decode(parts[12]) if len(parts) > 12 else "",
            "street": safe_decode(parts[13]) if len(parts) > 13 else "",
            "sub_district": safe_decode(parts[14]) if len(parts) > 14 else "",
            "vtc": safe_decode(parts[15]) if len(parts) > 15 else "",
        }

        # The last segment after text fields contains embedded photo bytes
        photo_bytes = parts[-1] if len(parts) > 16 else b""

        return {
            "fields": fields,
            "data_to_sign": data_to_sign,
            "signature": signature,
            "photo_bytes": photo_bytes
        }
    except Exception as e:
        logger.debug(f"Secure QR parsing failed: {e}")
        return None


def verify_rsa_signature(data_to_sign: bytes, signature: bytes) -> Tuple[bool, str, str]:
    """
    Verifies RSA-2048 SHA-256 signature against UIDAI public cert or demo test key.
    Returns (valid: bool, status_code: str, key_label: str).
    status_code: 'verified' | 'invalid' | 'skipped'
    """
    pub_key = None
    key_label = "none"

    # 1. Try UIDAI official cert if path provided
    if settings.UIDAI_CERT_PATH and os.path.exists(settings.UIDAI_CERT_PATH):
        try:
            from cryptography import x509
            with open(settings.UIDAI_CERT_PATH, "rb") as f:
                cert_data = f.read()
                try:
                    cert = x509.load_pem_x509_certificate(cert_data)
                except Exception:
                    cert = x509.load_der_x509_certificate(cert_data)
                pub_key = cert.public_key()
                key_label = "UIDAI official production certificate"
        except Exception as e:
            logger.warning(f"Could not load UIDAI cert: {e}")

    # 2. Try demo test key if in DEMO_MODE
    if pub_key is None and settings.DEMO_MODE:
        if os.path.exists(TEST_PUBKEY_PATH):
            try:
                with open(TEST_PUBKEY_PATH, "rb") as f:
                    pub_key = serialization.load_pem_public_key(f.read())
                    key_label = "verified with TEST key – demo only"
            except Exception as e:
                logger.warning(f"Could not load test pubkey: {e}")
        elif os.path.exists(TEST_PRIVKEY_PATH):
            try:
                with open(TEST_PRIVKEY_PATH, "rb") as f:
                    priv = serialization.load_pem_private_key(f.read(), password=None)
                    pub_key = priv.public_key()
                    key_label = "verified with TEST key – demo only"
            except Exception as e:
                logger.warning(f"Could not load test privkey: {e}")

    if pub_key is None:
        return False, "skipped", "certificate not provided"

    try:
        pub_key.verify(signature, data_to_sign, padding.PKCS1v15(), hashes.SHA256())
        return True, "verified", key_label
    except InvalidSignature:
        return False, "invalid", key_label
    except Exception as e:
        logger.error(f"RSA verification error: {e}")
        return False, "invalid", key_label


def extract_printed_fields_from_card(image_bgr: np.ndarray) -> Dict[str, str]:
    """
    Extracts printed Name, DOB, Gender, and Aadhaar number from card image using RapidOCR.
    """
    out = {"name": "", "dob": "", "gender": "", "last4": ""}
    model_registry.load_ocr()
    ocr = model_registry.ocr_engine

    if ocr is None:
        return out

    try:
        res, _ = ocr(image_bgr)
        if not res:
            return out

        lines = [item[1].strip() for item in res if item and len(item) > 1]
        full_text = " \n ".join(lines)

        # 1. Search for DOB (DD/MM/YYYY or DD-MM-YYYY)
        dob_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", full_text)
        if dob_match:
            out["dob"] = dob_match.group(1).replace("/", "-")

        # 2. Search for Gender (MALE, FEMALE, TRANSGENDER, M, F)
        if re.search(r"\b(female|महिला)\b", full_text, re.IGNORECASE):
            out["gender"] = "F"
        elif re.search(r"\b(male|पुरुष)\b", full_text, re.IGNORECASE):
            out["gender"] = "M"

        # 3. Search for Aadhaar last 4 digits (XXXX XXXX 1234 or 1234)
        num_match = re.findall(r"\b\d{4}\b", full_text)
        if num_match:
            out["last4"] = num_match[-1]

        # 4. Search for Name (line after 'Name' or 'नाम')
        for i, line in enumerate(lines):
            if re.search(r"\b(name|नाम)\b", line, re.IGNORECASE):
                # Check next line or inline
                parts = re.split(r"name|नाम", line, flags=re.IGNORECASE)
                candidate = parts[-1].strip(" :/|-")
                if len(candidate) > 2:
                    out["name"] = candidate
                    break
                elif i + 1 < len(lines):
                    cand_next = lines[i + 1].strip()
                    if not re.search(r"\b(dob|birth|gender|father|government)\b", cand_next, re.IGNORECASE):
                        out["name"] = cand_next
                        break

        # Fallback for name: find capitalized line near top
        if not out["name"]:
            for line in lines[1:5]:
                clean = re.sub(r"[^a-zA-Z\s]", "", line).strip()
                if 2 <= len(clean.split()) <= 4 and not any(w in clean.lower() for w in ["government", "india", "uidai", "aadhaar", "male", "female"]):
                    out["name"] = clean
                    break

    except Exception as e:
        logger.error(f"Card OCR extraction failed: {e}")

    return out


def compare_printed_with_qr(printed: Dict[str, str], qr_fields: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Compares printed details against signed QR fields.
    Returns list of discrepancies: [{"field": name/dob/gender/last4, "printed": str, "qr": str}].
    """
    mismatches = []

    # 1. Compare Name using rapidfuzz token_sort_ratio
    pr_name = printed.get("name", "").strip()
    qr_name = qr_fields.get("name", "").strip()
    if pr_name and qr_name:
        ratio = rapidfuzz.fuzz.token_sort_ratio(pr_name.lower(), qr_name.lower())
        if ratio < 75:
            mismatches.append({"field": "Name", "printed": pr_name, "qr": qr_name, "similarity": round(ratio / 100.0, 2)})

    # 2. Compare DOB
    pr_dob = printed.get("dob", "").replace("/", "-").strip()
    qr_dob = qr_fields.get("dob", "").replace("/", "-").strip()
    if pr_dob and qr_dob and pr_dob != qr_dob:
        mismatches.append({"field": "Date of Birth", "printed": pr_dob, "qr": qr_dob})

    # 3. Compare Gender
    pr_gender = printed.get("gender", "").upper().strip()
    qr_gender = qr_fields.get("gender", "").upper().strip()
    if pr_gender and qr_gender:
        norm_pr = "M" if "M" in pr_gender else ("F" if "F" in pr_gender else pr_gender)
        norm_qr = "M" if "M" in qr_gender else ("F" if "F" in qr_gender else qr_gender)
        if norm_pr != norm_qr:
            mismatches.append({"field": "Gender", "printed": printed.get("gender"), "qr": qr_fields.get("gender")})

    # 4. Compare last 4 digits
    pr_last4 = printed.get("last4", "").strip()
    ref_id = qr_fields.get("reference_id", "").strip()
    if pr_last4 and ref_id and len(ref_id) >= 4:
        qr_last4 = ref_id[:4]
        if pr_last4 != qr_last4:
            mismatches.append({"field": "Aadhaar Last 4 Digits", "printed": pr_last4, "qr": qr_last4})

    return mismatches


def analyze_aadhaar_qr(
    id_card_bgr: Optional[np.ndarray],
    selfie_bgr: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Performs complete Aadhaar QR forensic verification:
    - QR extraction from ID image
    - Secure QR decoding & decompression
    - RSA-2048 SHA-256 digital signature validation
    - Comparison of printed details (OCR) with signed QR data
    - Face comparison of QR embedded photo with selfie
    - Privacy protection: Never persists raw QR payload or full numbers
    """
    evidence: List[Evidence] = []
    result = {
        "has_qr": False,
        "is_secure_qr": False,
        "signature_valid": None,
        "signature_status": "not_attempted",
        "key_label": "none",
        "mismatches": [],
        "masked_reference": None,
        "comparisons": {},
        "evidence": evidence
    }

    if id_card_bgr is None:
        return result

    # 1. Decode QR from card image
    qr_text = decode_qr_from_image(id_card_bgr)
    if not qr_text:
        # QR is missing or unreadable -> ID-QR-04 (info only, 0 weight, NEVER raises risk)
        evidence.append(Evidence(
            id="ID-QR-04",
            kind="info",
            weight=0.0,
            effective_weight=0.0,
            calibrated_score=0.10,
            severity="low",
            title=EVIDENCE_CATALOG["ID-QR-04"]["title"],
            reason="The QR code on the ID card could not be read or is missing; acceptable for older cards, no risk added.",
            details={"status": "missing_or_unreadable"}
        ))
        result["signature_status"] = "missing_or_unreadable"
        return result

    result["has_qr"] = True

    # 2. Parse Secure QR
    qr_payload = parse_secure_qr_payload(qr_text)
    if not qr_payload:
        evidence.append(Evidence(
            id="ID-QR-04",
            kind="info",
            weight=0.0,
            effective_weight=0.0,
            calibrated_score=0.10,
            severity="low",
            title=EVIDENCE_CATALOG["ID-QR-04"]["title"],
            reason="The QR code uses an older unsigned format; skipped signature verification without penalty.",
            details={"status": "legacy_unsigned_qr"}
        ))
        result["signature_status"] = "legacy_unsigned"
        return result

    result["is_secure_qr"] = True
    qr_fields = qr_payload["fields"]
    ref_id = qr_fields.get("reference_id", "")
    masked_ref = f"XXXX-{ref_id[:4]}" if len(ref_id) >= 4 else "XXXX"
    result["masked_reference"] = masked_ref

    # 3. Signature Verification
    valid_sig, sig_status, key_label = verify_rsa_signature(
        qr_payload["data_to_sign"],
        qr_payload["signature"]
    )
    result["signature_valid"] = valid_sig
    result["signature_status"] = sig_status
    result["key_label"] = key_label

    if sig_status == "skipped":
        evidence.append(Evidence(
            id="ID-QR-04",
            kind="info",
            weight=0.0,
            effective_weight=0.0,
            calibrated_score=0.10,
            severity="low",
            title=EVIDENCE_CATALOG["ID-QR-04"]["title"],
            reason=f"Aadhaar QR signature check skipped ({key_label}).",
            details={"key_label": key_label}
        ))
    elif not valid_sig:
        # Strong fraud indicator -> ID-QR-01, triggers override O7
        evidence.append(Evidence(
            id="ID-QR-01",
            kind="risk",
            weight=EVIDENCE_CATALOG["ID-QR-01"]["weight"],
            effective_weight=EVIDENCE_CATALOG["ID-QR-01"]["weight"],
            calibrated_score=0.95,
            severity="high",
            title=EVIDENCE_CATALOG["ID-QR-01"]["title"],
            reason=f"The QR code on the ID card failed its digital signature check ({key_label}), so its contents cannot be trusted.",
            field="qr_signature",
            details={"key_label": key_label, "signature_status": "invalid"}
        ))

    # 4. Printed details vs signed QR comparison
    printed = extract_printed_fields_from_card(id_card_bgr)
    mismatches = compare_printed_with_qr(printed, qr_fields)
    result["mismatches"] = mismatches
    result["comparisons"] = {
        "printed_name": printed.get("name"),
        "qr_name": qr_fields.get("name"),
        "printed_dob": printed.get("dob"),
        "qr_dob": qr_fields.get("dob"),
        "printed_gender": printed.get("gender"),
        "qr_gender": qr_fields.get("gender")
    }

    if mismatches:
        mismatch_descriptions = [f"{m['field']} (printed: '{m['printed']}', QR: '{m['qr']}')" for m in mismatches]
        ev_reason = f"Printed details on ID card do not match signed QR data: {'; '.join(mismatch_descriptions)}."
        evidence.append(Evidence(
            id="ID-QR-02",
            kind="risk",
            weight=EVIDENCE_CATALOG["ID-QR-02"]["weight"],
            effective_weight=EVIDENCE_CATALOG["ID-QR-02"]["weight"],
            calibrated_score=0.85,
            severity="high",
            title=EVIDENCE_CATALOG["ID-QR-02"]["title"],
            reason=ev_reason,
            field="printed_vs_qr",
            details={"mismatches": mismatches, "count": len(mismatches)}
        ))

    # 5. Check QR photo vs selfie if signature is verified
    if valid_sig and selfie_bgr is not None:
        photo_bytes = qr_payload.get("photo_bytes")
        if photo_bytes:
            try:
                from .face import detect_faces, extract_aligned_face_and_embedding
                p_img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
                qr_bgr = cv2.cvtColor(np.array(p_img), cv2.COLOR_RGB2BGR)

                qr_faces = detect_faces(qr_bgr)
                selfie_faces = detect_faces(selfie_bgr)

                if qr_faces and selfie_faces:
                    _, qr_emb = extract_aligned_face_and_embedding(qr_bgr, qr_faces[0])
                    _, sf_emb = extract_aligned_face_and_embedding(selfie_bgr, selfie_faces[0])
                    if qr_emb is not None and sf_emb is not None:
                        sim = float(np.dot(qr_emb.flatten(), sf_emb.flatten()))
                        t_low = 0.30
                        try:
                            with open(os.path.join(REPO_ROOT, "models", "calibration.json"), "r") as cf:
                                cdata = json.load(cf)
                                t_low = cdata.get("face_match", {}).get(settings.FACE_ENGINE, {}).get("t_low", 0.30)
                        except Exception:
                            pass
                        if sim < t_low:
                            evidence.append(Evidence(
                                id="ID-QR-03",
                                kind="risk",
                                weight=EVIDENCE_CATALOG["ID-QR-03"]["weight"],
                                effective_weight=EVIDENCE_CATALOG["ID-QR-03"]["weight"],
                                calibrated_score=0.60,
                                severity="medium",
                                title=EVIDENCE_CATALOG["ID-QR-03"]["title"],
                                reason=f"The photo inside the ID card's QR code does not match the live selfie (similarity {sim:.2f} < threshold {t_low}).",
                                field="qr_photo_match",
                                details={"sim": round(sim, 4), "threshold": t_low}
                            ))
            except Exception as e:
                logger.debug(f"QR photo face comparison failed: {e}")
        else:
            # v2 QR format without embedded photo
            evidence.append(Evidence(
                id="ID-QR-04",
                kind="info",
                weight=0.0,
                effective_weight=0.0,
                calibrated_score=0.05,
                severity="low",
                title=EVIDENCE_CATALOG["ID-QR-04"]["title"],
                reason="The Aadhaar QR uses v2 format without an embedded photo; skipped photo match without penalty.",
                details={"qr_version": "v2_no_photo"}
            ))

    # 6. If verified and zero mismatches -> emit ID-QR-00 info
    if valid_sig and not mismatches and sig_status == "verified":
        evidence.append(Evidence(
            id="ID-QR-00",
            kind="info",
            weight=0.0,
            effective_weight=0.0,
            calibrated_score=0.05,
            severity="low",
            title=EVIDENCE_CATALOG["ID-QR-00"]["title"],
            reason=f"Aadhaar QR digital signature verified ({key_label}) and all printed details match signed card data.",
            details={"key_label": key_label, "masked_reference": masked_ref}
        ))

    # PRIVACY ENFORCEMENT (§20): Clear raw QR payload from memory
    del qr_payload

    return result
