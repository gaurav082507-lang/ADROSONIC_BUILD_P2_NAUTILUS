"""Indian numbering, currency formatting, words conversion, and Verhoeff checksum.

Rules:
- Indian numbering format: 1,20,000.00 (last 3 digits, then pairs of 2 digits).
- Words parser with lakh (1,00,000) and crore (1,00,00,000).
- Verhoeff check digit algorithm for 12-digit Aadhaar validation.
"""

# Verhoeff algorithm matrices
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def validate_verhoeff(number_str: str) -> bool:
    """Validates a number string using the Verhoeff checksum algorithm."""
    clean = "".join(c for c in str(number_str) if c.isdigit())
    if not clean:
        return False
    c = 0
    for i, digit in enumerate(reversed(clean)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(digit)]]
    return c == 0


def generate_verhoeff(number_str: str) -> str:
    """Appends the Verhoeff check digit to a number string."""
    clean = "".join(c for c in str(number_str) if c.isdigit())
    c = 0
    for i, digit in enumerate(reversed(clean)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[(i + 1) % 8][int(digit)]]
    check_digit = _VERHOEFF_INV[c]
    return clean + str(check_digit)


def format_inr(amount: float, symbol: bool = False, decimals: int = 2) -> str:
    """Formats a number into Indian currency style (e.g. 1,20,000.00).

    Last 3 digits are grouped, then preceding digits are grouped in pairs of 2.
    """
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    parts = f"{amount:.{decimals}f}".split(".")
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ""

    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted = ",".join(groups) + "," + last3

    res = f"{sign}{formatted}"
    if decimals > 0:
        res += f".{decimal_part}"
    if symbol:
        res = f"₹ {res}"
    return res


_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
         "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two_digits_to_words(n: int) -> str:
    if n == 0:
        return ""
    if n < 20:
        return _ONES[n]
    tens = _TENS[n // 10]
    ones = _ONES[n % 10]
    return f"{tens} {ones}".strip()


def _three_digits_to_words(n: int) -> str:
    res = []
    hundreds = n // 100
    remainder = n % 100
    if hundreds > 0:
        res.append(f"{_ONES[hundreds]} Hundred")
    if remainder > 0:
        res.append(_two_digits_to_words(remainder))
    return " ".join(res).strip()


def number_to_inr_words(amount: float) -> str:
    """Converts a monetary amount into Indian English words with Lakhs and Crores."""
    amount_int = int(round(amount))
    if amount_int == 0:
        return "Zero Rupees Only"

    crores = amount_int // 10000000
    remainder = amount_int % 10000000

    lakhs = remainder // 100000
    remainder = remainder % 100000

    thousands = remainder // 1000
    remainder = remainder % 1000

    hundreds = remainder

    parts = []
    if crores > 0:
        parts.append(f"{_three_digits_to_words(crores)} Crore")
    if lakhs > 0:
        parts.append(f"{_two_digits_to_words(lakhs)} Lakh")
    if thousands > 0:
        parts.append(f"{_two_digits_to_words(thousands)} Thousand")
    if hundreds > 0:
        parts.append(_three_digits_to_words(hundreds))

    words = " ".join(parts).strip()
    return f"{words} Rupees Only"


def parse_inr_words_to_number(text: str) -> float:
    """Parses Indian English words containing Crore, Lakh, Thousand, Hundred into float."""
    import re
    word_map = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
        "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    }

    clean = text.lower().replace("-", " ")
    clean = re.sub(r"\b(rupees|rupee|only|and)\b", " ", clean)
    tokens = clean.split()
    total = 0
    current_segment = 0

    for token in tokens:
        if token in word_map:
            current_segment += word_map[token]
        elif token == "hundred":
            current_segment = max(1, current_segment) * 100
        elif token == "thousand":
            total += max(1, current_segment) * 1000
            current_segment = 0
        elif token in ("lakh", "lakhs", "lac", "lacs"):
            total += max(1, current_segment) * 100000
            current_segment = 0
        elif token in ("crore", "crores"):
            total += max(1, current_segment) * 10000000
            current_segment = 0

    total += current_segment
    return float(total)
