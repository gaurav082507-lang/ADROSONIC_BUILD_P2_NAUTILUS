"""Indian formatting, currency, words parser and Verhoeff checks."""
import sys
from pathlib import Path

# Add project root to sys.path if not present
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from training.indian_numbers import (
    validate_verhoeff,
    generate_verhoeff,
    format_inr,
    number_to_inr_words,
    parse_inr_words_to_number,
)

__all__ = [
    "validate_verhoeff",
    "generate_verhoeff",
    "format_inr",
    "number_to_inr_words",
    "parse_inr_words_to_number",
]
