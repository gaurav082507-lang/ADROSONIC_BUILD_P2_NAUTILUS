import os
import pytest
import numpy as np
from PIL import Image
from pathlib import Path

from app.detectors.base import AnalysisContext
from app.pipelines.image_pipeline import run_image_pipeline
from app.detectors.image.preprocess import ImagePreprocessor
from app.detectors.image.ela import ElaDetector
from app.detectors.image.ai_detector import AiImageDetector
from app.core.model_registry import model_registry
from app.scoring.bands import determine_confidence

DEMO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/demo_samples"))

@pytest.fixture
def sample_jpeg(tmp_path):
    p = tmp_path / "test.jpg"
    img = Image.new("RGB", (600, 600), color=(120, 140, 160))
    img.save(p, "JPEG", quality=90)
    return str(p)

@pytest.fixture
def sample_png(tmp_path):
    p = tmp_path / "test.png"
    img = Image.new("RGB", (600, 600), color=(120, 140, 160))
    img.save(p, "PNG")
    return str(p)

@pytest.mark.asyncio
async def test_image_pipeline_steps_and_evidence(sample_jpeg, tmp_path):
    model_registry.load_ai_detector()
    art_dir = tmp_path / "artifacts"
    art_dir.mkdir()

    ctx = AnalysisContext(
        job_id="test-job-img-01",
        file_paths=[sample_jpeg],
        mode="image"
    )
    ctx.scratch["artifacts_dir"] = str(art_dir)

    out = await run_image_pipeline(ctx)
    assert len(out.status) == 6
    step_names = [s.detector for s in out.status]
    assert "preprocess" in step_names
    assert "metadata" in step_names
    assert "ai_detector" in step_names
    assert "ela" in step_names
    assert "noise" in step_names
    assert "localization" in step_names

    ev_ids = [e.id for e in out.evidence]
    # Missing camera EXIF should be flagged
    assert "IMG-EXIF-01" in ev_ids
    # AI detector evidence should participate
    assert "IMG-AI-01" in ev_ids

@pytest.mark.asyncio
async def test_ela_skipped_on_png(sample_png):
    ctx = AnalysisContext(
        job_id="test-job-png",
        file_paths=[sample_png],
        mode="image"
    )
    # Run preprocessor first
    pre = ImagePreprocessor()
    pre.run(ctx)

    ela = ElaDetector()
    out = ela.run(ctx)
    # ELA must be skipped for PNG
    assert out.extras.get("skipped") is True
    assert len(out.evidence) == 0

@pytest.mark.asyncio
async def test_quality_gating_warning_on_small_image(tmp_path):
    p = tmp_path / "small.jpg"
    # 320x240 (short side < 512 px) and heavy compression (q=35 < 50)
    img = Image.new("RGB", (320, 240), color=(100, 100, 100))
    img.save(p, "JPEG", quality=35)

    ctx = AnalysisContext(
        job_id="test-job-qual",
        file_paths=[str(p)],
        mode="image"
    )
    pre = ImagePreprocessor()
    out = pre.run(ctx)

    ev_ids = [e.id for e in out.evidence]
    assert "IMG-QUAL-01" in ev_ids
    warnings = out.extras.get("quality_warnings", [])
    warning_codes = [w.code for w in warnings]
    assert "LOW_RES" in warning_codes
    assert "HEAVY_COMPRESSION" in warning_codes

@pytest.mark.asyncio
async def test_corrupt_file_handling(tmp_path):
    corrupt_file = tmp_path / "corrupt.jpg"
    with open(corrupt_file, "wb") as f:
        f.write(b"NOT_A_VALID_IMAGE_BYTES_XYZ123")

    ctx = AnalysisContext(
        job_id="test-corrupt",
        file_paths=[str(corrupt_file)],
        mode="image"
    )
    pre = ImagePreprocessor()
    with pytest.raises(ValueError) as excinfo:
        pre.run(ctx)
    assert "Corrupt or unsupported" in str(excinfo.value)

@pytest.mark.asyncio
async def test_model_load_failure_containment(sample_jpeg, tmp_path):
    # Temporarily remove model to simulate load failure
    saved_model = model_registry.ai_model
    model_registry.ai_model = None

    try:
        ctx = AnalysisContext(
            job_id="test-job-modelfail",
            file_paths=[sample_jpeg],
            mode="image"
        )
        ctx.scratch["artifacts_dir"] = str(tmp_path)

        out = await run_image_pipeline(ctx)
        # ai_detector should have status failed
        ai_stat = next(s for s in out.status if s.detector == "ai_detector")
        assert ai_stat.status == "failed"
        assert "not loaded" in ai_stat.error.lower()

        # Job continues, other detectors still succeed
        ela_stat = next(s for s in out.status if s.detector == "ela")
        assert ela_stat.status == "ok"

        # Confidence steps down
        conf = determine_confidence(
            evidence_ids=[e.id for e in out.evidence],
            detector_statuses=out.status,
            initial_conf="high"
        )
        assert conf in ("medium", "low")

    finally:
        model_registry.ai_model = saved_model

@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_model_inference_on_demo_sample(tmp_path):
    ai_sample = os.path.join(DEMO_DIR, "01_ai_generated_car_damage.jpg")
    if not os.path.exists(ai_sample):
        pytest.skip("Demo sample not found.")

    model_registry.load_ai_detector()
    if model_registry.ai_model is None:
        pytest.skip("PyTorch model not loaded.")

    ctx = AnalysisContext(
        job_id="test-real-sample",
        file_paths=[ai_sample],
        mode="image"
    )
    ctx.scratch["artifacts_dir"] = str(tmp_path)

    out = await run_image_pipeline(ctx)
    ai_ev = next(e for e in out.evidence if e.id == "IMG-AI-01")
    assert 0.0 <= ai_ev.raw_score <= 1.0
    assert 0.0 <= ai_ev.calibrated_score <= 1.0

    # Heatmap overlay artifact generated
    assert "overlay" in out.artifacts
    assert os.path.exists(out.artifacts["overlay"])
