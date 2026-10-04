import os
import json
import logging

logger = logging.getLogger("lucen_ai.weights")

CALIBRATION_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../models/calibration.json")
)

# Complete catalog of evidence weights
EVIDENCE_CATALOG = {
    # Image
    "IMG-AI-01": {"weight": 0.65, "source": "ai_detector", "title": "AI Generated"},
    "IMG-ELA-01": {"weight": 0.25, "source": "forensics", "title": "ELA Compression Anomaly"},
    "IMG-EXIF-01": {"weight": 0.10, "source": "metadata", "title": "Missing Camera EXIF"},
    "IMG-EXIF-02a": {"weight": 0.30, "source": "metadata", "title": "AI Software in EXIF"},
    "IMG-NOISE-01": {"weight": 0.25, "source": "forensics", "title": "Inconsistent Noise"},
    "IMG-C2PA-01": {"weight": 0.95, "source": "metadata", "title": "Content Credentials"},

    # Document
    "DOC-META-01": {"weight": 0.15, "source": "metadata", "title": "Consumer/Online Editor Producer"},
    "DOC-META-02": {"weight": 0.20, "source": "metadata", "title": "Modified Long After Creation"},
    "DOC-META-03": {"weight": 0.20, "source": "metadata", "title": "Appended Revisions Detected"},
    "DOC-META-04": {"weight": 0.35, "source": "metadata", "title": "Creation Date Inconsistency"},
    "DOC-FONT-01": {"weight": 0.40, "source": "rules", "title": "Font Mismatch in Field Group"},
    "DOC-FONT-02": {"weight": 0.30, "source": "rules", "title": "Size/Baseline Inconsistency"},
    "DOC-OVERLAY-01": {"weight": 0.70, "source": "forensics", "title": "Text Overlay Mismatch"},
    "DOC-OCR-01": {"weight": 0.15, "source": "ocr", "title": "Low OCR Confidence in Numbers"},
    "DOC-LOGIC-01": {"weight": 0.80, "source": "rules", "title": "Line Items Sum Mismatch"},
    "DOC-LOGIC-02": {"weight": 0.50, "source": "rules", "title": "Tax/Discount Math Inconsistent"},
    "DOC-LOGIC-03": {"weight": 0.50, "source": "rules", "title": "Invalid Date Sequence"},
    "DOC-LOGIC-04": {"weight": 0.50, "source": "rules", "title": "ID/Checksum Format Invalid"},
    "DOC-LOGIC-05": {"weight": 0.60, "source": "rules", "title": "Cross-Page Field Disagreement"},
    "DOC-LOGIC-06": {"weight": 0.25, "source": "rules", "title": "Inconsistent Number Formatting"},
    "DOC-LOGIC-07": {"weight": 0.70, "source": "rules", "title": "Amount in Words Mismatch"},
    "DOC-CNN-01": {"weight": 0.50, "source": "forensics", "title": "Tamper CNN Anomaly"},
    "DOC-ANOM-01": {"weight": 0.30, "source": "anomaly", "title": "Word-Level Style Outlier"},
    "DOC-VIS-01": {"weight": 0.25, "source": "forensics", "title": "Visual Compression Anomaly"},
    "DOC-QUAL-01": {"weight": 0.00, "source": "quality", "title": "Low Scan Quality Warning"},

    # Identity (§12)
    "ID-FACE-01": {"weight": 0.85, "source": "face", "title": "Face Mismatch"},
    "ID-FACE-02": {"weight": 0.45, "source": "face", "title": "Ambiguous Face Match"},
    "ID-DEEP-01": {"weight": 0.70, "source": "selfie_ai", "title": "Selfie AI Generated"},
    "ID-QUAL-01": {"weight": 0.00, "source": "quality", "title": "No Usable Face"},
    "ID-LIVE-01": {"weight": 0.75, "source": "liveness", "title": "Liveness Failed"},
    "ID-LIVE-02": {"weight": 0.50, "source": "liveness", "title": "Code Mismatch"},
    "ID-LIVE-03": {"weight": 0.15, "source": "liveness", "title": "Liveness Not Performed"},
    "ID-LIVE-00": {"weight": 0.00, "source": "liveness", "title": "Liveness Passed"},
    "ID-QR-01": {"weight": 0.85, "source": "aadhaar_qr", "title": "QR Signature Invalid"},
    "ID-QR-02": {"weight": 0.75, "source": "aadhaar_qr", "title": "QR Data Mismatch"},
    "ID-QR-03": {"weight": 0.45, "source": "aadhaar_qr", "title": "QR Photo Mismatch"},
    "ID-QR-04": {"weight": 0.00, "source": "aadhaar_qr", "title": "Unreadable QR"},
    "ID-QR-00": {"weight": 0.00, "source": "aadhaar_qr", "title": "QR Verified"},

    # Duplicates & Cross-Checks (§10, §14)
    "IMG-DUP-01": {"weight": 0.70, "source": "duplicates", "title": "Near-Duplicate Image (Same Claimant)"},
    "IMG-DUP-02": {"weight": 0.85, "source": "duplicates", "title": "Duplicate Image Across Different Claimants"},
    "DOC-DUP-01": {"weight": 0.70, "source": "rules", "title": "Duplicate Invoice/Receipt Across Claims"},

    "VOI-SPOOF-01": {"weight": 0.55, "source": "voice", "title": "Synthetic Voice"},
    "VOI-QUAL-01": {"weight": 0.00, "source": "quality", "title": "Audio Quality Warning"},
    "VOI-TXT-00": {"weight": 0.00, "source": "voice", "title": "Voice Statement Transcript"},
    "CLM-X-01": {"weight": 0.40, "source": "rules", "title": "Photo Outside Incident Window"},
    "CLM-X-02": {"weight": 0.50, "source": "rules", "title": "Claim Amount Mismatch"},
    "CLM-X-03": {"weight": 0.45, "source": "rules", "title": "Name Mismatch on ID vs Claim/Document"},
    "CLM-X-04": {"weight": 0.70, "source": "rules", "title": "Reused Evidence Across Claims"},
    "CLM-X-05": {"weight": 0.40, "source": "rules", "title": "Document Created After Claim Filing"},
    "CLM-X-06": {"weight": 0.35, "source": "rules", "title": "Photo GPS Far from Incident Location"},
    "CLM-X-07": {"weight": 0.45, "source": "rules", "title": "Evidence Dated Before Policy Start"},
    "CLM-X-08": {"weight": 0.45, "source": "rules", "title": "Invoice/Bill Dated Before Incident"},
    "CLM-VEH-01": {"weight": 0.60, "source": "rules", "title": "Vehicle Number Mismatch"},
    "CLM-ID-01": {"weight": 0.50, "source": "rules", "title": "ID Name vs Policyholder Mismatch"},
    "CLM-CHRONO-01": {"weight": 0.50, "source": "rules", "title": "Invalid Medical Chronology"},

    "CLM-NET-01": {"weight": 0.40, "source": "network", "title": "Shared Strong Identifier Across Claimants"},
    "CLM-NET-02": {"weight": 0.55, "source": "network", "title": "Fraud Ring Member"},
    "CLM-STORY-00": {"weight": 0.00, "source": "story", "title": "Story-vs-Evidence Review"}
}

def apply_calibrated_weights():
    """Dynamically applies empirical weights stored in models/calibration.json.
    Keys starting with '_' are treated as comments and skipped."""
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                custom_weights = data.get("weights", {})
                for ev_id, w in custom_weights.items():
                    if ev_id.startswith("_"):
                        continue  # comment/note key
                    if ev_id in EVIDENCE_CATALOG:
                        EVIDENCE_CATALOG[ev_id]["weight"] = float(w)
        except Exception as e:
            logger.warning(f"Could not load calibrated weights from {CALIBRATION_FILE}: {e}")

# Apply on module import
apply_calibrated_weights()
