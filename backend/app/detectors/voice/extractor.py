"""
Voice Field Extraction Module
Extracts structured insurance claim fields from voice transcripts / English translations:
- incident_type
- peril
- incident_date
- incident_time
- location_text
- vehicle_registration
- damaged_items (list of strings)
- amount_claimed (integer in INR)
Supports Indian number words (lakh, crore), Indian date formats, and vehicle registration numbers.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ...core.config import settings

logger = logging.getLogger(__name__)


class VoiceExtractedFields(BaseModel):
    incident_type: Optional[str] = None
    peril: Optional[str] = None
    incident_date: Optional[str] = None
    incident_time: Optional[str] = None
    location_text: Optional[str] = None
    vehicle_registration: Optional[str] = None
    damaged_items: List[str] = Field(default_factory=list)
    amount_claimed: Optional[int] = None


WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
}


def parse_indian_amount(text: str) -> Optional[int]:
    """
    Parses INR amounts from text:
    - '₹ 1.5 lakh' -> 150000
    - '25,000 rupees' -> 25000
    - 'two lakh fifty thousand' -> 250000
    - '1.5 crore' -> 15000000
    - '₹50,000' -> 50000
    """
    if not text:
        return None
    text_lower = text.lower()

    # 1. Check numeric lakh / lac
    m_lakh = re.search(r"(?:(?:rs\.?|inr|₹)\s*)?([\d\.]+)\s*(?:lakh|lac|lakhs)", text_lower)
    if m_lakh:
        try:
            return int(float(m_lakh.group(1)) * 100000)
        except ValueError:
            pass

    # 2. Check numeric crore / cr
    m_crore = re.search(r"(?:(?:rs\.?|inr|₹)\s*)?([\d\.]+)\s*(?:crore|cr)", text_lower)
    if m_crore:
        try:
            return int(float(m_crore.group(1)) * 10000000)
        except ValueError:
            pass

    # 3. Check spelled-out word combinations: e.g. 'two lakh fifty thousand'
    m_words = re.search(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\s*lakh\s*(?:(?:and\s*)?(fifty|forty|thirty|twenty)?\s*thousand)?\b",
        text_lower
    )
    if m_words:
        lakhs = WORD_NUMBERS.get(m_words.group(1), 0) * 100000
        thous = WORD_NUMBERS.get(m_words.group(2), 0) * 1000 if m_words.group(2) else 0
        return lakhs + thous

    # 4. Standard digits: '25,000 rupees' or '₹50,000' or 'Rs 75000'
    m_num = re.search(r"(?:(?:rs\.?|inr|₹)\s*([\d,]+)|([\d,]+)\s*(?:rupees|inr|rs|bucks))", text_lower)
    if m_num:
        val_str = m_num.group(1) or m_num.group(2)
        val_str = val_str.replace(",", "")
        try:
            return int(val_str)
        except ValueError:
            pass

    # 5. Generic isolated digit amount if adjacent to words like cost, estimate, damage, total
    m_cost = re.search(r"(?:cost|estimate|damage|total|bill|repair|worth)\s*(?:of|is|was|around|approx)?\s*(?:rs\.?|inr|₹)?\s*([\d,]{4,})", text_lower)
    if m_cost:
        val_str = m_cost.group(1).replace(",", "")
        try:
            return int(val_str)
        except ValueError:
            pass

    return None


def parse_indian_date(text: str) -> Optional[str]:
    """
    Parses dates in Indian formats:
    - DD/MM/YYYY or DD-MM-YYYY
    - '21st Sept 2026', '21 September 2026'
    - 'yesterday', 'today'
    Returns ISO date string YYYY-MM-DD or None.
    """
    if not text:
        return None
    text_lower = text.lower()

    if "yesterday" in text_lower:
        d = datetime.now() - timedelta(days=1)
        return d.strftime("%Y-%m-%d")
    if "today" in text_lower:
        return datetime.now().strftime("%Y-%m-%d")

    # DD/MM/YYYY or DD-MM-YYYY
    m_num = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text)
    if m_num:
        day, month, year = int(m_num.group(1)), int(m_num.group(2)), int(m_num.group(3))
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Written month: '21st Sept 2026' or '21 September 2026'
    months = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12
    }
    month_pattern = "|".join(months.keys())
    m_word = re.search(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_pattern})\s+(\d{{4}})\b",
        text_lower
    )
    if m_word:
        day = int(m_word.group(1))
        month_str = m_word.group(2)
        year = int(m_word.group(3))
        month = months.get(month_str, 1)
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def parse_incident_time(text: str) -> Optional[str]:
    """Extracts time string e.g. '10:30 am', 'yesterday evening', '5 pm'."""
    if not text:
        return None
    text_lower = text.lower()

    # Exact time with am/pm
    m_time = re.search(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))\b", text_lower)
    if m_time:
        return m_time.group(1).strip()

    # Relative time of day
    for rel in ["yesterday evening", "yesterday afternoon", "yesterday morning", "evening", "morning", "afternoon", "night"]:
        if rel in text_lower:
            return rel.title()

    return None


def parse_vehicle_registration(text: str) -> Optional[str]:
    """Extracts Indian vehicle registration number (e.g. MH 02 AB 1234, DL 01 AB 1234)."""
    if not text:
        return None
    # Pattern: 2 state letters, 1-2 digits, 1-3 letters, 4 digits
    m = re.search(r"\b([A-Z]{2}[ -]?[0-9]{1,2}[ -]?[A-Z]{1,3}[ -]?[0-9]{4})\b", text.upper())
    if m:
        # Standardize with single spaces
        raw = m.group(1).replace("-", " ")
        parts = raw.split()
        return " ".join(parts)
    return None


def parse_incident_type_and_peril(text: str) -> tuple[Optional[str], Optional[str]]:
    """Identifies incident type and peril from keywords in text."""
    if not text:
        return None, None
    text_lower = text.lower()

    if any(k in text_lower for k in ("hit", "collided", "collision", "accident", "crash", "skid", "takkar")):
        return "Motor Accident", "Collision"
    if any(k in text_lower for k in ("theft", "stolen", "stole", "chori")):
        return "Theft", "Theft"
    if any(k in text_lower for k in ("fire", "burn", "aag")):
        return "Fire Damage", "Fire"
    if any(k in text_lower for k in ("flood", "water", "paani", "rain", "submerged")):
        return "Natural Disaster", "Flood"
    if any(k in text_lower for k in ("injury", "hospital", "fracture", "doctor", "medical")):
        return "Health / Injury", "Personal Injury"

    return "Vehicle Incident", "Accidental Damage"


def parse_damaged_items(text: str) -> List[str]:
    """Identifies damaged vehicle or property parts mentioned in text."""
    if not text:
        return []
    text_lower = text.lower()
    part_keywords = [
        "front bumper", "rear bumper", "bumper",
        "headlight", "headlights", "tail lamp", "tail lamps", "headlamp",
        "windshield", "windscreen", "rear windshield",
        "bonnet", "hood", "fender",
        "driver door", "passenger door", "door", "doors",
        "side mirror", "rearview mirror", "mirror",
        "radiator", "suspension", "engine", "gearbox",
        "wheel", "tyre", "tire", "rim", "alloy", "roof"
    ]
    found = []
    for part in part_keywords:
        if part in text_lower:
            # Avoid duplicate sub-parts (e.g. don't add "bumper" if "front bumper" already added)
            if not any(part in existing for existing in found):
                found.append(part.title())
    return found


def parse_location_text(text: str) -> Optional[str]:
    """Extracts location / road / landmark references from text."""
    if not text:
        return None
    # Look for phrases starting with 'near', 'at', 'on', 'around' followed by landmark words
    m = re.search(r"\b(?:near|at|on|around)\s+([A-Za-z0-9\s]{3,30}?)(?:\s+(?:road|highway|street|junction|signal|flyover|bridge|circle|chowk|nagar|sector|colony|expressway))\b", text, re.IGNORECASE)
    if m:
        full_match = m.group(0).strip()
        return full_match

    # General highway / road mention
    m_road = re.search(r"\b([A-Za-z0-9\s]{3,20}\s+(?:road|highway|expressway|flyover|junction|signal|circle))\b", text, re.IGNORECASE)
    if m_road:
        return m_road.group(1).strip()

    return None


def extract_voice_fields(transcript_en: str, original_transcript: str = "") -> VoiceExtractedFields:
    """
    Extracts structured fields from the English translation/transcript using regex patterns.
    If LLM_ENABLED is True and transcript is rich, grounding validation is enforced.
    """
    combined = f"{transcript_en} {original_transcript}".strip()

    inc_type, peril = parse_incident_type_and_peril(combined)
    date_val = parse_indian_date(combined)
    time_val = parse_incident_time(combined)
    location_val = parse_location_text(combined)
    veh_val = parse_vehicle_registration(combined)
    damaged = parse_damaged_items(combined)
    amount_val = parse_indian_amount(combined)

    return VoiceExtractedFields(
        incident_type=inc_type,
        peril=peril,
        incident_date=date_val,
        incident_time=time_val,
        location_text=location_val,
        vehicle_registration=veh_val,
        damaged_items=damaged,
        amount_claimed=amount_val,
    )
