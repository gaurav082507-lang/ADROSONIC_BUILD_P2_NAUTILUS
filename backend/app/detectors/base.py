from typing import Protocol, List, Dict, Any, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import asyncio
import time
import inspect
from ..schemas.evidence import Evidence
from ..schemas.result import DetectorStatus
from ..schemas.requests import ClaimMetadata
from ..core.config import settings


@dataclass
class AnalysisContext:
    job_id: str
    file_paths: List[str] = field(default_factory=list)
    mode: str = "image"
    claim_metadata: Optional[ClaimMetadata] = None
    decoded_images: List[Any] = field(default_factory=list)
    parsed_pdf: Optional[Any] = None
    ocr_result: Optional[Any] = None
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    scratch: Dict[str, Any] = field(default_factory=dict)
    runtime_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def file_path(self) -> Optional[Path]:
        if self.file_paths:
            return Path(self.file_paths[0])
        return None

    @property
    def artifacts_dir(self) -> Optional[Path]:
        art = self.scratch.get("artifacts_dir")
        return Path(art) if art else None


@dataclass
class DetectorOutput:
    status: str = "ok"
    evidence: List[Evidence] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Path] = field(default_factory=dict)
    quality_warnings: List[Any] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)


class Detector(Protocol):
    name: str
    timeout_s: float
    def run(self, ctx: AnalysisContext) -> DetectorOutput: ...


async def run_safely(
    detector_or_func: Union[Detector, Callable],
    ctx: AnalysisContext,
    detector_name: Optional[str] = None
) -> Tuple[DetectorStatus, DetectorOutput]:
    """
    Executes a detector with time-boxing and full exception containment.
    A failure or timeout records a 'failed' status and returns empty output;
    it NEVER fails the calling job.
    """
    name = detector_name or getattr(detector_or_func, "name", "unknown_detector")
    timeout_s = getattr(detector_or_func, "timeout_s", settings.DETECTOR_TIMEOUT_S)

    start = time.time()
    try:
        # Check if it has a run method
        if hasattr(detector_or_func, "run"):
            fn = detector_or_func.run
        else:
            fn = detector_or_func

        if inspect.iscoroutinefunction(fn):
            output = await asyncio.wait_for(fn(ctx), timeout=timeout_s)
        else:
            # Run sync detector in default executor thread
            loop = asyncio.get_event_loop()
            output = await asyncio.wait_for(loop.run_in_executor(None, fn, ctx), timeout=timeout_s)

        duration_ms = int((time.time() - start) * 1000)

        # Standardize return type
        if isinstance(output, list):
            output = DetectorOutput(evidence=output)
        elif not isinstance(output, DetectorOutput):
            output = DetectorOutput()

        return DetectorStatus(detector=name, status="ok", duration_ms=duration_ms), output

    except asyncio.TimeoutError:
        duration_ms = int((time.time() - start) * 1000)
        return DetectorStatus(
            detector=name,
            status="failed",
            duration_ms=duration_ms,
            error="timeout"
        ), DetectorOutput(status="failed")

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        return DetectorStatus(
            detector=name,
            status="failed",
            duration_ms=duration_ms,
            error=str(e)
        ), DetectorOutput(status="failed")
