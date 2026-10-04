"""Evidence id -> sentence template (§16.2).

Each template is a Python format string. The `details` dict on the Evidence
object is unpacked into it. If a key is missing the explainer catches the
KeyError and uses the raw template text or reason string.
"""

from ..core.formatters import format_inr

TEMPLATES = {
    # Image pipeline (§10.2)
    "IMG-AI-01":    "The image shows patterns typical of AI-generated pictures ({p:.0%} likelihood after calibration).",
    "IMG-ELA-01":   "One region of the photo was compressed differently from the rest, which often means it was edited after capture.",
    "IMG-EXIF-01":  "The file lacks expected camera metadata.",
    "IMG-EXIF-02a": "The file's metadata names an AI image generator ({software}).",
    "IMG-EXIF-02b": "The file's metadata names an image editing software ({software}).",
    "IMG-EXIF-03":  "The file was modified after capture ({delta} difference).",
    "IMG-NOISE-01": "Noise patterns in the image are inconsistent, suggesting parts were generated or spliced.",
    "IMG-C2PA-01":  "Content credentials embedded in the file indicate it was produced by an AI model.",
    "IMG-C2PA-02":  "Content credentials confirm the image was captured by an authentic device.",
    "IMG-DUP-01":   "This photo closely matches one submitted earlier in claim {other_id} ({sim:.0%} similar).",
    "IMG-DUP-02":   "This photo was previously submitted by a different claimant in claim {other_id} ({sim:.0%} similar).",
    "DOC-DUP-01":   "The invoice number {invoice_number} from {issuer} was previously submitted in claim {other_id}.",

    # Document pipeline (§11.2, §16.2)
    "DOC-META-01":   "The PDF metadata indicates it was created or edited using a consumer tool ({matched_tool}).",
    "DOC-META-02":   "The PDF was modified {delta} after it was created, using {producer}.",
    "DOC-META-03":   "The PDF file contains {eof_count} appended revision segments, indicating post-save modifications.",
    "DOC-META-04":   "The PDF creation date is inconsistent with the date stated in the document or claim.",
    "DOC-FONT-01":   "The value '{text}' uses a different font ({font_a}) from the other amounts in the same column ({font_b}).",
    "DOC-FONT-02":   "Character size or baseline of '{word}' deviates {z_score}σ from the surrounding line median.",
    "DOC-OVERLAY-01": "Visible rendered text '{visible_text}' contradicts the underlying digital text layer ('{hidden_text}'), indicating an overlay edit.",
    "DOC-OCR-01":    "Low OCR recognition confidence ({conf:.0%}) detected on numeric text '{token}'.",
    "DOC-LOGIC-01":  "The line items add up to INR {expected:,.2f} but the stated total is INR {found:,.2f}.",
    "DOC-LOGIC-02":  "Stated {tax_percentage:.1f}% tax should be INR {expected_tax:,.2f} on INR {subtotal:,.2f}, but found INR {found_tax:,.2f}.",
    "DOC-LOGIC-03":  "Chronological contradiction: stated date {date_1} occurs after subsequent date {date_2}.",
    "DOC-LOGIC-04":  "12-digit identity number '{aadhaar_masked}' failed Verhoeff checksum validation.",
    "DOC-LOGIC-05":  "Document field disagrees across pages (values inconsistent across pages).",
    "DOC-LOGIC-06":  "The document mixes Indian numbering formatting (1,20,000) with international formatting (120,000).",
    "DOC-LOGIC-07":  "Stated amount in words parses to INR {parsed_from_words:,.2f}, which differs from the numeric digits INR {numeric_digits:,.2f}.",
    "DOC-CNN-01":    "The tamper detector found an area whose compression pattern differs from the rest of the page ({score:.0%} anomaly likelihood).",
    "DOC-ANOM-01":   "Word '{text}' on page {page} shows typographic style anomalies ({most_deviating_feature}).",
    "DOC-VIS-01":    "Visual compression anomalies overlapping text regions detected on page {page}.",
    "DOC-QUAL-01":   "Low document scan resolution or contrast, reducing forensic certainty.",

    # Identity (§12.2, §12.4, §12.5)
    "ID-FACE-01":  "The face on the ID does not match the selfie (similarity {sim:.2f}, below the match threshold).",
    "ID-FACE-02":  "Face match is ambiguous between the ID and selfie (similarity {sim:.2f}); possible morph or low quality photo.",
    "ID-DEEP-01":  "The selfie image appears to be AI-generated ({p:.0%} likelihood after calibration).",
    "ID-QUAL-01":  "No usable face detected or multiple faces found on image.",
    "ID-LIVE-01":  "The person did not complete the live check ({failed_challenge} not detected).",
    "ID-LIVE-02":  "The spoken code did not match the code shown on screen.",
    "ID-LIVE-03":  "Live camera check was not performed; static selfie uploaded instead.",
    "ID-LIVE-00":  "Live face challenges completed successfully.",
    "ID-QR-01":    "The QR code on the ID card failed its digital signature check, so its contents cannot be trusted.",
    "ID-QR-02":    "The printed {field} on the ID card ('{printed}') does not match the value stored in its signed QR code ('{qr}').",
    "ID-QR-03":    "The photo inside the ID card's QR code does not match the printed photo (similarity {sim:.2f}).",
    "ID-QR-04":    "The QR code on the ID card could not be read.",
    "ID-QR-00":    "Aadhaar QR digital signature verified and printed details match.",

    # Voice (§14.1)
    "VOI-SPOOF-01": "The recorded statement shows patterns of a synthetic or cloned voice ({p:.0%} likelihood after calibration).",

    # Claim cross-checks (§14, §14.2, §14.3)
    "CLM-X-01":    "The photo was taken {days} days before the stated incident date ({photo_date} vs {incident_date}).",
    "CLM-X-02":    "The document total ({doc:,.2f}) differs from the amount claimed ({claimed:,.2f}).",
    "CLM-X-03":    "The name on the ID card ('{id_name}') differs from the policyholder or document name ('{doc_name}').",
    "CLM-X-04":    "Reused evidence: document or photo was already submitted in earlier claim {other_id}.",
    "CLM-X-05":    "The document creation date ({doc_date}) is later than the claim filing date ({claim_date}).",
    "CLM-X-06":    "The photo was taken {distance_km:.0f} km from the location given for the incident.",
    "CLM-X-07":    "The {item} is dated {item_date}, before the policy started on {policy_start}.",
    "CLM-X-08":    "The {doc_kind} is dated {doc_date}, before the incident on {incident_date}.",
    "CLM-VEH-01":  "The vehicle registration number '{found}' does not match the insured vehicle '{expected}'.",
    "CLM-ID-01":   "The verified identity name '{id_name}' differs from the policyholder '{policy_holder}'.",
    "CLM-CHRONO-01": "Medical timeline contradiction: {reason}.",

    # Network / entity links
    "CLM-NET-01":  "This claimant shares a {entity_kind} with claim {other_id}.",
    "CLM-NET-02":  "This claim is linked to {n} other claims through shared details.",

    # Story (informational, never scores)
    "CLM-STORY-00": "The claimant's narrative was reviewed for internal consistency.",

    # Override annotations
    "OVERRIDE-O1": "Rule O1 applied: content credentials state the image is AI-generated.",
    "OVERRIDE-O2": "Rule O2 applied: mathematical mismatch confirmed by tamper detection.",
    "OVERRIDE-O3": "Rule O3 applied: face on the ID does not match the selfie.",
    "OVERRIDE-O4": "Rule O4 applied: duplicate image from a claim closed as fraudulent.",
    "OVERRIDE-O5": "Rule O5 applied: text overlay detected on the document.",
    "OVERRIDE-O6": "Rule O6 applied: liveness failure combined with face mismatch.",
    "OVERRIDE-O7": "Rule O7 applied: Aadhaar QR digital signature is invalid.",
}

RECOMMENDED_ACTIONS = {
    "LOW": "Proceed with standard claim processing.",
    "MEDIUM": "Route to specialist for manual forensic review.",
    "HIGH": "Escalate immediately to Special Investigation Unit (SIU) for detailed fraud investigation.",
}

