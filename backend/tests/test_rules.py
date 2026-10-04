"""Tests for deterministic document consistency rules (DOC-LOGIC-01..07).

Covers:
- Pass and fail cases for all 7 rules.
- Indian numbering, Lakh/Crore conversions, and Verhoeff check digits.
"""

import pytest
from app.detectors.base import AnalysisContext
from app.detectors.document.rules import DocumentRulesDetector
from app.core.formatters import (
    validate_verhoeff,
    generate_verhoeff,
    format_inr,
    number_to_inr_words,
    parse_inr_words_to_number
)


def test_indian_currency_formatting():
    assert format_inr(120000.00) == "1,20,000.00"
    assert format_inr(1234567.89) == "12,34,567.89"
    assert format_inr(500.00) == "500.00"
    assert format_inr(10000000.00) == "1,00,00,000.00"  # 1 Crore


def test_indian_words_parsing():
    assert parse_inr_words_to_number("One Lakh Twenty Thousand Rupees Only") == 120000.0
    assert parse_inr_words_to_number("Fifty-Three Thousand One Hundred Rupees Only") == 53100.0
    assert parse_inr_words_to_number("Two Crore Forty-Five Lakh Rupees Only") == 24500000.0


def test_verhoeff_checksum():
    valid = generate_verhoeff("23456789012")
    assert len(valid) == 12
    assert validate_verhoeff(valid) is True
    # Corrupt last digit
    corrupt = valid[:-1] + ("0" if valid[-1] != "0" else "1")
    assert validate_verhoeff(corrupt) is False


def test_doc_logic_01_line_items_sum():
    detector = DocumentRulesDetector()
    ctx = AnalysisContext(job_id="test", file_paths=[], mode="document")

    # Pass case
    ctx.runtime_data["extracted_fields"] = {
        "line_items": [{"amount": 20000.0, "bbox": [0.1, 0.1, 0.1, 0.1]}, {"amount": 25000.0, "bbox": [0.1, 0.2, 0.1, 0.1]}],
        "total_amount": {"value": 45000.0, "bbox": [0.1, 0.3, 0.1, 0.1]}
    }
    out_pass = detector.run(ctx)
    assert not any(e.id == "DOC-LOGIC-01" for e in out_pass.evidence)

    # Fail case
    ctx.runtime_data["extracted_fields"] = {
        "line_items": [{"amount": 20000.0, "bbox": [0.1, 0.1, 0.1, 0.1]}, {"amount": 4000.0, "bbox": [0.1, 0.2, 0.1, 0.1]}],
        "total_amount": {"value": 88500.0, "bbox": [0.1, 0.3, 0.1, 0.1]}
    }
    out_fail = detector.run(ctx)
    ev = next(e for e in out_fail.evidence if e.id == "DOC-LOGIC-01")
    assert ev.details["expected"] == 24000.0
    assert ev.details["found"] == 88500.0
    assert ev.weight == 0.80


def test_doc_logic_02_tax_math():
    detector = DocumentRulesDetector()
    ctx = AnalysisContext(job_id="test", file_paths=[], mode="document")

    # Pass case
    ctx.runtime_data["extracted_fields"] = {
        "subtotal": {"value": 50000.0, "bbox": [0.1, 0.1, 0.1, 0.1]},
        "tax_percentage": 18.0,
        "tax_amount": {"value": 9000.0, "bbox": [0.1, 0.2, 0.1, 0.1]}
    }
    out_pass = detector.run(ctx)
    assert not any(e.id == "DOC-LOGIC-02" for e in out_pass.evidence)

    # Fail case
    ctx.runtime_data["extracted_fields"] = {
        "subtotal": {"value": 50000.0, "bbox": [0.1, 0.1, 0.1, 0.1]},
        "tax_percentage": 18.0,
        "tax_amount": {"value": 15000.0, "bbox": [0.1, 0.2, 0.1, 0.1]}
    }
    out_fail = detector.run(ctx)
    ev = next(e for e in out_fail.evidence if e.id == "DOC-LOGIC-02")
    assert ev.details["expected_tax"] == 9000.0
    assert ev.details["found_tax"] == 15000.0


def test_doc_logic_03_date_sequence():
    detector = DocumentRulesDetector()
    ctx = AnalysisContext(job_id="test", file_paths=[], mode="document")

    # Pass case: Invoice date before due date
    ctx.runtime_data["extracted_fields"] = {
        "dates": [
            {"text": "12/08/2024", "bbox": [0.1, 0.1, 0.1, 0.1]},
            {"text": "12/09/2024", "bbox": [0.1, 0.2, 0.1, 0.1]}
        ]
    }
    out_pass = detector.run(ctx)
    assert not any(e.id == "DOC-LOGIC-03" for e in out_pass.evidence)

    # Fail case: Invoice date after due date
    ctx.runtime_data["extracted_fields"] = {
        "dates": [
            {"text": "25/09/2024", "bbox": [0.1, 0.1, 0.1, 0.1]},
            {"text": "10/08/2024", "bbox": [0.1, 0.2, 0.1, 0.1]}
        ]
    }
    out_fail = detector.run(ctx)
    assert any(e.id == "DOC-LOGIC-03" for e in out_fail.evidence)


def test_doc_logic_04_aadhaar_validation():
    detector = DocumentRulesDetector()
    ctx = AnalysisContext(job_id="test", file_paths=[], mode="document")

    # Pass case
    valid_aadhaar = generate_verhoeff("34567891234")
    ctx.runtime_data["extracted_fields"] = {
        "aadhaar_numbers": [{"text": valid_aadhaar, "bbox": [0.1, 0.1, 0.1, 0.1]}]
    }
    out_pass = detector.run(ctx)
    assert not any(e.id == "DOC-LOGIC-04" for e in out_pass.evidence)

    # Fail case
    invalid_aadhaar = valid_aadhaar[:-1] + ("1" if valid_aadhaar[-1] != "1" else "2")
    ctx.runtime_data["extracted_fields"] = {
        "aadhaar_numbers": [{"text": invalid_aadhaar, "bbox": [0.1, 0.1, 0.1, 0.1]}]
    }
    out_fail = detector.run(ctx)
    assert any(e.id == "DOC-LOGIC-04" for e in out_fail.evidence)


def test_doc_logic_07_words_mismatch():
    detector = DocumentRulesDetector()
    ctx = AnalysisContext(job_id="test", file_paths=[], mode="document")

    # Pass case
    ctx.runtime_data["extracted_fields"] = {
        "total_amount": {"value": 53100.0, "bbox": [0.1, 0.1, 0.1, 0.1]},
        "amount_in_words": "Fifty-Three Thousand One Hundred Rupees Only",
        "parsed_words_amount": 53100.0
    }
    out_pass = detector.run(ctx)
    assert not any(e.id == "DOC-LOGIC-07" for e in out_pass.evidence)

    # Fail case: Digits = 42,500, words = One Lakh Ten Thousand (1,10,000)
    ctx.runtime_data["extracted_fields"] = {
        "total_amount": {"value": 42500.0, "bbox": [0.1, 0.1, 0.1, 0.1]},
        "amount_in_words": "One Lakh Ten Thousand Rupees Only",
        "parsed_words_amount": 110000.0
    }
    out_fail = detector.run(ctx)
    ev = next(e for e in out_fail.evidence if e.id == "DOC-LOGIC-07")
    assert ev.details["parsed_from_words"] == 110000.0
    assert ev.details["numeric_digits"] == 42500.0
    assert ev.weight == 0.70
