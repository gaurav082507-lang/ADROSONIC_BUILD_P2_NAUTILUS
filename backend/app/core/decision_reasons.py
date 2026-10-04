import re
from typing import Dict, Any, List, Set, Tuple

REASON_CATEGORIES = {
    "photo_unclear": {
        "label_en": "Photo clarity check",
        "label_hi": "फ़ोटो स्पष्टता जांच"
    },
    "document_needs_verification": {
        "label_en": "Document verification needed",
        "label_hi": "दस्तावेज़ सत्यापन आवश्यक"
    },
    "details_mismatch": {
        "label_en": "Claim details clarification",
        "label_hi": "दावा विवरण स्पष्टीकरण"
    },
    "identity_verification_needed": {
        "label_en": "Identity confirmation needed",
        "label_hi": "पहचान पुष्टि आवश्यक"
    },
    "duplicate_submission": {
        "label_en": "Previous submission check",
        "label_hi": "पिछला सबमिशन जांच"
    },
    "other": {
        "label_en": "Additional information needed",
        "label_hi": "अतिरिक्त जानकारी आवश्यक"
    }
}

TEMPLATE_DRAFTS = {
    "request_evidence": {
        "photo_unclear": {
            "en": "We could not clearly verify the vehicle damage from the photos provided. Please upload clear, well-lit photos taken with your mobile camera showing the entire damaged area.",
            "hi": "प्रदान किए गए फ़ोटो से वाहन के नुकसान की स्पष्ट पुष्टि नहीं हो सकी। कृपया अपने मोबाइल कैमरे से ली गई स्पष्ट और अच्छी रोशनी वाली फ़ोटो अपलोड करें जिसमें पूरा क्षतिग्रस्त क्षेत्र दिखे।",
            "next_steps": ["Take new photos in daylight", "Use the in-app camera if prompted", "Upload replacement damage photos"],
            "slots": ["damage_closeup"]
        },
        "document_needs_verification": {
            "en": "Some details on the submitted bill or estimate are unreadable or could not be verified with the issuer. Please upload an original clear PDF or a clean photograph of the complete bill.",
            "hi": "जमा किए गए बिल या अनुमान पर कुछ विवरण अपठनीय हैं। कृपया मूल स्पष्ट पीडीएफ या पूरे बिल की स्पष्ट तस्वीर अपलोड करें।",
            "next_steps": ["Obtain the original invoice from the service provider", "Ensure all line items and totals are visible", "Upload the complete document"],
            "slots": ["repair_estimate"]
        },
        "details_mismatch": {
            "en": "The claimed amount or incident details differ from the figures in the supporting documents. Please review your claim details and upload an updated invoice or explanation.",
            "hi": "दावा की गई राशि या घटना का विवरण सहायक दस्तावेजों के आंकड़ों से भिन्न है। कृपया अपने दावे के विवरण की समीक्षा करें और अद्यतन चालान अपलोड करें।",
            "next_steps": ["Check the invoice total against the claimed amount", "Upload the corrected bill", "Contact support if you need assistance"],
            "slots": ["repair_estimate"]
        },
        "identity_verification_needed": {
            "en": "We could not verify your identity from the provided ID card and photo. Please provide a clear photo of your government-issued ID card and a well-lit selfie.",
            "hi": "प्रदान किए गए पहचान पत्र और तस्वीर से आपकी पहचान सत्यापित नहीं हो सकी। कृपया अपने पहचान पत्र की स्पष्ट फ़ोटो और अच्छी रोशनी वाली सेल्फ़ी प्रदान करें।",
            "next_steps": ["Keep your ID flat on a plain background", "Take a clear selfie facing the camera", "Ensure text on your ID is fully legible"],
            "slots": ["id_photo", "selfie"]
        },
        "duplicate_submission": {
            "en": "The photos submitted appear similar to a previous claim on our records. Please provide original, new photographs of the current damage showing the vehicle license plate.",
            "hi": "सबमिट की गई फ़ोटो हमारे रिकॉर्ड में किसी पिछले दावे के समान प्रतीत होती हैं। कृपया नंबर प्लेट दिखाते हुए मौजूदा नुकसान की नई फ़ोटो प्रदान करें।",
            "next_steps": ["Take fresh photos showing the number plate and damage together", "Submit the current repair estimate"],
            "slots": ["full_vehicle", "damage_closeup"]
        },
        "other": {
            "en": "Additional documentation is required to complete the review of your claim. Please review the requested items and upload the necessary files.",
            "hi": "आपके दावे की समीक्षा पूरी करने के लिए अतिरिक्त दस्तावेज़ों की आवश्यकता है। कृपया आवश्यक फ़ाइलें अपलोड करें।",
            "next_steps": ["Review requested documents", "Upload the required files"],
            "slots": []
        }
    },
    "reject": {
        "photo_unclear": {
            "en": "The damage photos submitted could not be verified as original photos of the incident. You may contact customer support or file an appeal with new evidence.",
            "hi": "सबमिट की गई क्षति फ़ोटो घटना की मूल फ़ोटो के रूप में सत्यापित नहीं की जा सकीं। आप ग्राहक सहायता से संपर्क कर सकते हैं या नई जानकारी के साथ अपील कर सकते हैं।",
            "next_steps": ["Contact customer support", "File an appeal if you have new evidence"],
            "slots": []
        },
        "document_needs_verification": {
            "en": "The submitted repair invoice or estimate could not be verified with the issuing workshop. You may contact customer support to appeal this decision.",
            "hi": "प्रस्तुत मरम्मत चालान जारीकर्ता द्वारा सत्यापित नहीं किया जा सका। आप इस निर्णय के विरुद्ध सहायता टीम से संपर्क कर सकते हैं।",
            "next_steps": ["Contact customer support", "Provide official receipt from the workshop if available"],
            "slots": []
        },
        "details_mismatch": {
            "en": "The claim details contain inconsistencies with the provided documentation that could not be resolved. You may appeal this decision with additional documentation.",
            "hi": "दावे के विवरण में प्रदान किए गए दस्तावेज़ों के साथ ऐसी विसंगतियां हैं जिनका समाधान नहीं किया जा सका। आप अतिरिक्त दस्तावेज़ों के साथ अपील कर सकते हैं।",
            "next_steps": ["Contact support for appeal instructions"],
            "slots": []
        },
        "identity_verification_needed": {
            "en": "We were unable to confirm the claimant identity based on the submitted identification documents. Please contact support to verify your account.",
            "hi": "हम प्रस्तुत पहचान दस्तावेजों के आधार पर दावेदार की पहचान की पुष्टि करने में असमर्थ रहे। कृपया अपने खाते को सत्यापित करने के लिए सहायता से संपर्क करें।",
            "next_steps": ["Contact support with valid government photo identification"],
            "slots": []
        },
        "duplicate_submission": {
            "en": "The evidence submitted matches an existing claim already settled or processed in our system. If you believe this is an error, please contact customer support.",
            "hi": "प्रस्तुत साक्ष्य हमारे सिस्टम में पहले से संसाधित दावे से मेल खाता है। यदि आपको लगता है कि यह कोई त्रुटि है, तो सहायता से संपर्क करें।",
            "next_steps": ["Contact customer support for investigation review"],
            "slots": []
        },
        "other": {
            "en": "We are unable to approve this claim based on the policy criteria and submitted materials. Please contact support for further clarification.",
            "hi": "हम पॉलिसी मानदंडों और प्रस्तुत सामग्रियों के आधार पर इस दावे को स्वीकृत करने में असमर्थ हैं। अधिक जानकारी के लिए कृपया सहायता से संपर्क करें।",
            "next_steps": ["Contact customer support"],
            "slots": []
        }
    },
    "approve": {
        "other": {
            "en": "Your claim has been reviewed and approved. Our disbursement team will process the payment according to your policy terms.",
            "hi": "आपके दावे की समीक्षा कर ली गई है और इसे स्वीकृत कर दिया गया है। हमारी टीम आपके पॉलिसी नियमों के अनुसार भुगतान संसाधित करेगी।",
            "next_steps": ["Wait for bank transfer confirmation", "Contact support if funds are not received within 3 business days"],
            "slots": []
        }
    }
}

BANNED_WORDS = [
    "fraud", "fake", "ai-generated", "deepfake", "tampered", "forged",
    "suspicious", "detector", "score", "risk", "band", "confidence",
    "img-", "doc-", "id-", "voice-", "clm-", "heatmap", "high", "medium", "low",
    "%", "percent", "probability", "noisy-or", "siglip", "efficientnet",
    # Hindi fraud/AI terms (transliterated)
    "dhokha", "jaali", "nakli", "naqli",
]

# Pre-compile whole-word patterns for each banned term (faster + correct)
# Non-alphanumeric terms (%, img-) use literal substring match as fallback
_BANNED_PATTERNS = []
for _w in BANNED_WORDS:
    if re.match(r"^[A-Za-z]+$", _w):
        _BANNED_PATTERNS.append(re.compile(r"\b" + re.escape(_w) + r"\b", re.IGNORECASE))
    else:
        _BANNED_PATTERNS.append(_w)  # literal substring for punctuation/mixed terms

def extract_numbers_from_text(text: str) -> Set[str]:
    # Extract numbers like 1200, 24000, 2026, 01, etc.
    return set(re.findall(r"\b\d+\b", text))

def validate_draft_guardrails(text: str, allowed_numbers: Set[str] = None) -> bool:
    if not text:
        return False
    lower = text.lower()
    for pat in _BANNED_PATTERNS:
        if isinstance(pat, str):
            # Literal substring (for non-word tokens like %, img-)
            if pat in lower:
                return False
        else:
            # Whole-word regex match
            if pat.search(text):
                return False

    if allowed_numbers is not None:
        found_numbers = extract_numbers_from_text(text)
        # Any number found in text that is not in allowed numbers is a violation
        diff = found_numbers - allowed_numbers
        if diff:
            return False

    return True

def get_template_draft(action: str, reason_category: str) -> Dict[str, Any]:
    action_dict = TEMPLATE_DRAFTS.get(action, TEMPLATE_DRAFTS["request_evidence"])
    cat_dict = action_dict.get(reason_category) or action_dict.get("other") or TEMPLATE_DRAFTS["request_evidence"]["other"]
    return {
        "claimant_message_en": cat_dict["en"],
        "claimant_message_hi": cat_dict["hi"],
        "next_steps": cat_dict.get("next_steps", []),
        "slots_to_resubmit": cat_dict.get("slots", []),
        "source": "template"
    }
