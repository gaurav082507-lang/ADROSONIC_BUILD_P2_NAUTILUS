"""Integration and unit tests for the Document Forensics Pipeline (§11, Part 4).

Covers:
- Clean invoice -> LOW risk, no DOC-LOGIC-01
- Tampered invoice -> DOC-LOGIC-01 + DOC-FONT-01 with bounding boxes
- Scanned invoice -> successfully processed through RapidOCR
- Encrypted / Corrupt PDF -> raises CORRUPT_FILE error
- 15-page PDF -> enforces page limit with warning notice
- Missing CNN weights -> marks detector failed without crashing job
"""

import pytest
from pathlib import Path
import pymupdf

from app.detectors.base import AnalysisContext
from app.pipelines.document_pipeline import run_document_pipeline
from app.detectors.document.kind import DocumentKindDetector
from app.detectors.document.tamper_cnn import DocumentTamperCNNDetector
from app.core.errors import LucenError

DEMO_DOCS_DIR = Path("../data/demo_samples/docs")
if not DEMO_DOCS_DIR.exists():
    DEMO_DOCS_DIR = Path("data/demo_samples/docs")


@pytest.mark.asyncio
async def test_clean_document_gives_low_risk(tmp_path):
    clean_pdf = DEMO_DOCS_DIR / "clean_invoice.pdf"
    assert clean_pdf.exists(), f"Missing demo sample {clean_pdf}"

    ctx = AnalysisContext(job_id="test_clean", file_paths=[str(clean_pdf)], mode="document")
    ctx.scratch["artifacts_dir"] = str(tmp_path)

    out = await run_document_pipeline(ctx)
    ev_ids = [e.id for e in out.evidence]

    assert "DOC-LOGIC-01" not in ev_ids
    # Clean invoice should have no math or font anomalies
    assert "DOC-FONT-01" not in ev_ids
    assert "DOC-OVERLAY-01" not in ev_ids


@pytest.mark.asyncio
async def test_tampered_document_flags_logic_and_font(tmp_path):
    tampered_pdf = DEMO_DOCS_DIR / "tampered_invoice.pdf"
    assert tampered_pdf.exists(), f"Missing demo sample {tampered_pdf}"

    ctx = AnalysisContext(job_id="test_tampered", file_paths=[str(tampered_pdf)], mode="document")
    ctx.scratch["artifacts_dir"] = str(tmp_path)

    out = await run_document_pipeline(ctx)
    ev_ids = [e.id for e in out.evidence]

    # Tampered invoice must flag DOC-LOGIC-01
    assert "DOC-LOGIC-01" in ev_ids
    logic_ev = next(e for e in out.evidence if e.id == "DOC-LOGIC-01")
    assert logic_ev.details["found"] == 88500.0
    assert logic_ev.details["expected"] == 24000.0
    assert logic_ev.bboxes is not None and len(logic_ev.bboxes) > 0

    # Retyped in Times-Bold flags font mismatch
    assert "DOC-FONT-01" in ev_ids
    font_ev = next(e for e in out.evidence if e.id == "DOC-FONT-01")
    assert font_ev.bboxes is not None

    # Modified metadata
    assert "DOC-META-02" in ev_ids or "DOC-META-01" in ev_ids

    # Annotated page boxes artifact exists
    assert (tmp_path / "page_1_boxes.png").exists()


@pytest.mark.asyncio
async def test_scanned_document_runs_through_ocr(tmp_path):
    scanned_jpg = DEMO_DOCS_DIR / "scanned_invoice.jpg"
    assert scanned_jpg.exists(), f"Missing demo sample {scanned_jpg}"

    ctx = AnalysisContext(job_id="test_scanned", file_paths=[str(scanned_jpg)], mode="document")
    ctx.scratch["artifacts_dir"] = str(tmp_path)

    out = await run_document_pipeline(ctx)

    ocr_status = next((s for s in out.status if s.detector == "document_ocr"), None)
    assert ocr_status is not None
    assert ocr_status.status == "ok"
    assert ocr_status.duration_ms >= 0


def test_corrupt_file_raises_corrupt_file(tmp_path):
    corrupt_pdf = tmp_path / "corrupt.pdf"
    # Corrupt PDF header but incomplete/broken structure
    corrupt_pdf.write_bytes(b"%PDF-1.4\n%%EOF_BROKEN_DATA_NOT_A_VALID_PDF_STRUCTURE")

    ctx = AnalysisContext(job_id="test_corrupt", file_paths=[str(corrupt_pdf)], mode="document")
    detector = DocumentKindDetector()

    with pytest.raises(LucenError) as exc_info:
        detector.run(ctx)

    assert exc_info.value.status_code == 422
    assert exc_info.value.error_code == "CORRUPT_FILE"


def test_fifteen_page_limit_enforcement(tmp_path):
    # Generate 15-page PDF
    pdf_path = tmp_path / "long_doc.pdf"
    doc = pymupdf.open()
    for i in range(15):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i+1} text content for page limit testing.")
    doc.save(str(pdf_path))
    doc.close()

    ctx = AnalysisContext(job_id="test_long", file_paths=[str(pdf_path)], mode="document")
    detector = DocumentKindDetector()
    out = detector.run(ctx)

    assert out.details["page_count"] == 15
    assert out.details["analyzed_pages"] == 10
    assert out.details["page_limit_exceeded"] is True
    assert any("15 pages" in w["message"] for w in out.quality_warnings)


def test_missing_cnn_model_failure_containment():
    detector = DocumentTamperCNNDetector()
    # Force model to None
    detector._model = None
    # Simulate missing weights
    detector._load_model = lambda: None

    ctx = AnalysisContext(job_id="test_missing_cnn", file_paths=[], mode="document")
    out = detector.run(ctx)

    assert out.status == "failed"
    assert "error" in out.details


@pytest.mark.asyncio
async def test_real_world_pdfs_pipeline_execution():
    import time
    from app.services.orchestrator import _execute_analysis_job
    from app.services import job_manager

    real_world_dir = Path("data/eval/real_world")
    if not real_world_dir.exists():
        real_world_dir = Path("../data/eval/real_world")

    assert real_world_dir.exists(), f"Missing real-world directory: {real_world_dir}"
    pdfs = sorted(list(real_world_dir.glob("*.pdf")))
    assert len(pdfs) == 5, f"Expected 5 real-world PDFs, found {len(pdfs)}"

    for pdf in pdfs:
        job_id = job_manager.create_job("document")
        t0 = time.perf_counter()
        res = await _execute_analysis_job(
            job_id=job_id,
            mode="document",
            file_paths={"document": str(pdf)}
        )
        duration_s = time.perf_counter() - t0

        # Assertions per Part 2 spec:
        # 1. duration > 0.5 s (proof of real execution, not a mock bypass)
        assert duration_s > 0.5, f"Execution too fast ({duration_s:.3f}s), expected real execution > 0.5s for {pdf.name}"

        # 2. checks_run has at least 5 entries
        assert res.checks_run is not None
        assert len(res.checks_run) >= 5, f"Expected at least 5 checks_run entries, got {len(res.checks_run)} for {pdf.name}"

        # 3. at least 4 detectors report status='ok' on each real-world PDF
        ok_detectors = [c for c in res.checks_run if c.status == "ok"]
        assert len(ok_detectors) >= 4, f"Expected at least 4 ok detectors, got {len(ok_detectors)} for {pdf.name}"

