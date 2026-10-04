import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..schemas.evidence import Evidence
from ..schemas.result import DetectorStatus
from ..detectors.base import AnalysisContext, run_safely
from ..detectors.image.preprocess import ImagePreprocessor
from ..detectors.image.metadata import MetadataDetector
from ..detectors.image.ai_detector import AiImageDetector
from ..detectors.image.ela import ElaDetector
from ..detectors.image.noise import NoiseDetector
from ..detectors.image.localization import LocalizationDetector
from ..services import job_manager

logger = logging.getLogger("lucen_ai.image_pipeline")

@dataclass
class PipelineOutput:
    evidence: List[Evidence] = field(default_factory=list)
    status: List[DetectorStatus] = field(default_factory=list)
    artifacts: Dict[str, Path] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)

async def run_image_pipeline(ctx: AnalysisContext, prefix: str = "") -> PipelineOutput:
    """
    Executes the full image forensic pipeline in sequence:
    1. Preprocess & quality metrics
    2. EXIF & C2PA Metadata
    3. AI-generated image classification (SigLIP)
    4. Error Level Analysis (recompression diff)
    5. Noise residual consistency
    6. Forensic heatmap localization
    7. Duplicate lookup (TODO: Prompt 10)
    """
    job_id = ctx.job_id
    all_evidence: List[Evidence] = []
    all_statuses: List[DetectorStatus] = []
    all_artifacts: Dict[str, Path] = {}
    pipeline_extras: Dict[str, Any] = {}

    detectors = [
        ("preprocess", ImagePreprocessor()),
        ("metadata", MetadataDetector()),
        ("ai_detector", AiImageDetector()),
        ("ela", ElaDetector()),
        ("noise", NoiseDetector()),
        ("localization", LocalizationDetector()),
    ]

    for step_name, detector in detectors:
        full_step = f"{prefix}{step_name}" if prefix else step_name
        if job_id:
            job_manager.start_step(job_id, full_step)

        status, output = await run_safely(detector, ctx, step_name)
        status.detector = full_step
        all_statuses.append(status)

        if job_id:
            job_manager.finish_step(job_id, full_step, status.status, status.duration_ms)

        all_evidence.extend(output.evidence)
        all_artifacts.update(output.artifacts)
        pipeline_extras.update(output.extras)

    # TODO: Step 7: Duplicate lookup (Prompt 10) - SHA256 -> pHash -> CLIP + FAISS

    # Consolidate extras for claim pipeline and downstream scoring
    pipeline_extras["p_ai"] = ctx.scratch.get("p_ai")
    pipeline_extras["quality_metrics"] = ctx.quality_metrics
    pipeline_extras["exif_summary"] = ctx.scratch.get("exif_summary")
    pipeline_extras["tta_disagreement"] = ctx.scratch.get("tta_disagreement", False)

    return PipelineOutput(
        evidence=all_evidence,
        status=all_statuses,
        artifacts=all_artifacts,
        extras=pipeline_extras
    )
