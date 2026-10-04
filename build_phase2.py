import os
import textwrap

BASE_DIR = r"c:\Users\gaura\Desktop\LUCENAI\backend"

def write_file(path, content):
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).strip() + "\n")

write_file("requirements.txt", """
fastapi==0.110.0
uvicorn[standard]==0.27.1
pydantic==2.6.3
pydantic-settings==2.2.1
python-multipart==0.0.9
httpx==0.27.0
pytest==8.1.1
pytest-asyncio==0.23.5
""")

write_file("../dev.ps1", """
$ErrorActionPreference = "Stop"
Write-Host "Starting Lucen AI Backend and Frontend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend ; .\\.venv\\Scripts\\Activate.ps1 ; uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend ; npm run dev"
""")

# schemas
write_file("app/schemas/evidence.py", """
from pydantic import BaseModel
from typing import Optional, Dict, Any

class BBox(BaseModel):
    page: int
    x: float
    y: float
    w: float
    h: float

class Evidence(BaseModel):
    id: str
    kind: str
    raw_score: float
    calibrated_score: float
    weight: float
    effective_weight: float
    severity: str
    title: str
    reason: str
    field: Optional[str] = None
    bbox: Optional[BBox] = None
    details: Optional[Dict[str, Any]] = None
    artifact: Optional[str] = None
""")

write_file("app/schemas/result.py", """
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from .evidence import Evidence

class PipelineScore(BaseModel):
    pipeline: str
    risk: float
    authenticity: float
    band: str
    confidence: str
    evidence_ids: List[str]

class OverallScore(BaseModel):
    risk: float
    band: str
    confidence: str
    summary: str

class QualityWarning(BaseModel):
    code: str
    message: str

class DetectorStatus(BaseModel):
    detector: str
    status: str
    duration_ms: int
    error: Optional[str] = None

class ChallengeStatus(BaseModel):
    name: str
    ok: bool
    ms: int

class LivenessStatus(BaseModel):
    performed: bool
    passed: bool
    code_match: bool
    challenges: List[ChallengeStatus]

class QrComparison(BaseModel):
    field: str
    printed: str
    qr: str
    match: bool

class AadhaarQrStatus(BaseModel):
    found: bool
    signature_valid: bool
    mode: str
    comparisons: List[QrComparison]
    photo_similarity: float

class StoryStatus(BaseModel):
    contradictions: List[str]
    consistent_points: List[str]
    source: str

class Link(BaseModel):
    result_id: str
    reason: str

class Decision(BaseModel):
    status: str
    by: str
    at: str
    reason_code: str
    claimant_message: str
    internal_note: str

class AnalysisResult(BaseModel):
    id: str
    mode: str
    created_at: str
    image: Optional[PipelineScore] = None
    document: Optional[PipelineScore] = None
    identity: Optional[Any] = None
    overall: OverallScore
    evidence: List[Evidence]
    detector_status: List[DetectorStatus]
    quality_warnings: List[QualityWarning]
    artifacts: Dict[str, Any]
    versions: Dict[str, str]
    # v2 blocks
    voice: Optional[PipelineScore] = None
    liveness: Optional[LivenessStatus] = None
    aadhaar_qr: Optional[AadhaarQrStatus] = None
    story: Optional[StoryStatus] = None
    links: Optional[List[Link]] = None
    decision: Optional[Decision] = None
""")

write_file("app/schemas/job.py", """
from pydantic import BaseModel
from typing import List, Optional

class StepStatus(BaseModel):
    name: str
    status: str
    duration_ms: Optional[int] = None

class JobStatus(BaseModel):
    job_id: str
    status: str
    mode: str
    steps: List[StepStatus]
    result_id: Optional[str] = None
    error: Optional[str] = None
""")

write_file("app/schemas/requests.py", """
from pydantic import BaseModel
from typing import Optional

class ClaimMetadata(BaseModel):
    claim_date: Optional[str] = None
    incident_date: Optional[str] = None
    incident_time: Optional[str] = None
    claimed_amount: Optional[float] = None
    currency: Optional[str] = None
    claimant_name: Optional[str] = None
    claimant_phone: Optional[str] = None
    claimant_email: Optional[str] = None
    bank_account_ref: Optional[str] = None
    claim_type: Optional[str] = None
    peril: Optional[str] = None
    incident_lat: Optional[float] = None
    incident_lng: Optional[float] = None
    incident_location_text: Optional[str] = None
    statement_language: Optional[str] = None
    statement_original: Optional[str] = None
    statement_en: Optional[str] = None
    liveness_session_id: Optional[str] = None
    aadhaar_qr_session_id: Optional[str] = None
""")

write_file("app/schemas/auth.py", """
from pydantic import BaseModel
class LoginRequest(BaseModel):
    email: str
    password: str
class TokenResponse(BaseModel):
    token: str
    role: str
class User(BaseModel):
    id: str
    name: str
    email: str
    role: str
""")

write_file("app/schemas/__init__.py", """
from .evidence import Evidence, BBox
from .result import (PipelineScore, OverallScore, QualityWarning, DetectorStatus,
                     ChallengeStatus, LivenessStatus, QrComparison, AadhaarQrStatus,
                     StoryStatus, Link, Decision, AnalysisResult)
from .job import StepStatus, JobStatus
from .requests import ClaimMetadata
from .auth import LoginRequest, TokenResponse, User
""")

# Fix db path
write_file("app/db/models.py", """
# Renamed from database.py to models.py per structure doc.
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../../data/runtime/lucen.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # WAL mode
    conn.execute('PRAGMA journal_mode=WAL')
    c = conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS jobs (
      id TEXT PRIMARY KEY, mode TEXT, status TEXT,
      steps_json TEXT, result_id TEXT, error TEXT,
      created_at TEXT, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS results (
      id TEXT PRIMARY KEY, job_id TEXT, mode TEXT,
      overall_risk REAL, overall_band TEXT,
      image_risk REAL, document_risk REAL, identity_risk REAL,
      summary TEXT, json TEXT,
      created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS evidence (
      id INTEGER PRIMARY KEY AUTOINCREMENT, result_id TEXT,
      evidence_id TEXT, pipeline TEXT, source TEXT, kind TEXT,
      raw_score REAL, calibrated_score REAL, weight REAL, effective_weight REAL,
      severity TEXT, title TEXT, reason TEXT, field TEXT,
      bbox_json TEXT, details_json TEXT, artifact TEXT
    );
    CREATE TABLE IF NOT EXISTS image_hashes (
      id INTEGER PRIMARY KEY AUTOINCREMENT, result_id TEXT,
      phash TEXT, faiss_index INTEGER, created_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_evidence_result ON evidence(result_id);

    CREATE TABLE IF NOT EXISTS claims (
      id TEXT PRIMARY KEY, result_id TEXT, claimant_name TEXT,
      claimant_user_id TEXT, policy_number TEXT,
      claim_type TEXT, peril TEXT, status TEXT,
      metadata_json TEXT, created_at TEXT, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS entities (
      id INTEGER PRIMARY KEY AUTOINCREMENT, result_id TEXT,
      kind TEXT, value_hash TEXT, display TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS actions (
      id INTEGER PRIMARY KEY AUTOINCREMENT, result_id TEXT,
      actor TEXT, action TEXT, reason_code TEXT,
      claimant_message TEXT, internal_note TEXT,
      message_source TEXT, draft_edited INTEGER, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS liveness_sessions (
      id TEXT PRIMARY KEY, nonce TEXT, challenges_json TEXT, spoken_code TEXT,
      used INTEGER DEFAULT 0, expires_at TEXT
    );
    CREATE TABLE IF NOT EXISTS id_checks (
      id TEXT PRIMARY KEY, mode TEXT, signature_valid INTEGER,
      comparisons_json TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS timeline_events (
      id INTEGER PRIMARY KEY, claim_id TEXT, result_id TEXT,
      at TEXT, at_precision TEXT, kind TEXT
    );
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE,
      role TEXT, password_hash TEXT, preferred_language TEXT DEFAULT 'en', created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS policies (
      policy_number TEXT PRIMARY KEY, holder_user_id TEXT, claim_type TEXT,
      start_date TEXT, end_date TEXT, vehicle_or_asset TEXT
    );
    ''')
    conn.commit()
    conn.close()
""")

# Scoring Engine
write_file("app/scoring/weights.py", """
# Complete catalog of evidence weights
EVIDENCE_CATALOG = {
    # Image
    "IMG-AI-01": {"weight": 0.70, "source": "ai_detector", "title": "AI Generated"},
    "IMG-ELA-01": {"weight": 0.25, "source": "forensics", "title": "ELA Compression Anomaly"},
    "IMG-EXIF-01": {"weight": 0.10, "source": "metadata", "title": "Missing Camera EXIF"},
    "IMG-EXIF-02a": {"weight": 0.30, "source": "metadata", "title": "AI Software in EXIF"},
    "IMG-NOISE-01": {"weight": 0.20, "source": "forensics", "title": "Inconsistent Noise"},
    "IMG-C2PA-01": {"weight": 0.95, "source": "metadata", "title": "Content Credentials"},
    "IMG-DUP-01": {"weight": 0.85, "source": "duplicates", "title": "Duplicate Image"},
    
    # Document
    "DOC-LOGIC-01": {"weight": 0.80, "source": "rules", "title": "Mathematical Mismatch"},
    "DOC-CNN-01": {"weight": 0.50, "source": "forensics", "title": "Tamper CNN Anomaly"},
    "DOC-FONT-01": {"weight": 0.30, "source": "rules", "title": "Font Mismatch"},
    "DOC-META-02": {"weight": 0.15, "source": "metadata", "title": "PDF Modified"},
    "DOC-OVERLAY-01": {"weight": 0.80, "source": "forensics", "title": "Text Overlay Detected"},
    "DOC-ANOM-01": {"weight": 0.40, "source": "anomaly", "title": "Layout Anomaly"},
    "DOC-VIS-01": {"weight": 0.20, "source": "forensics", "title": "Visual Artifacts"},
    
    # Identity & Others
    "ID-FACE-01": {"weight": 0.80, "source": "face", "title": "Face Mismatch"},
    "ID-LIVE-01": {"weight": 0.85, "source": "liveness", "title": "Liveness Failed"},
    "ID-LIVE-02": {"weight": 0.70, "source": "liveness", "title": "Code Mismatch"},
    "ID-QR-01": {"weight": 0.90, "source": "aadhaar_qr", "title": "QR Signature Invalid"},
    "ID-QR-02": {"weight": 0.75, "source": "aadhaar_qr", "title": "QR Data Mismatch"},
    "ID-QR-03": {"weight": 0.60, "source": "aadhaar_qr", "title": "QR Photo Mismatch"},
    "ID-QR-04": {"weight": 0.00, "source": "aadhaar_qr", "title": "Unreadable QR"},
    
    "VOI-SPOOF-01": {"weight": 0.55, "source": "voice", "title": "Synthetic Voice"},
    "CLM-X-02": {"weight": 0.40, "source": "rules", "title": "Claim Amount Mismatch"},
    "CLM-X-06": {"weight": 0.35, "source": "rules", "title": "Distance Anomaly"},
    "CLM-X-07": {"weight": 0.50, "source": "rules", "title": "Pre-policy Date"},
    "CLM-X-08": {"weight": 0.50, "source": "rules", "title": "Future Incident Date"},
    
    "CLM-NET-01": {"weight": 0.40, "source": "network", "title": "Linked Entity"},
    "CLM-NET-02": {"weight": 0.30, "source": "network", "title": "Linked to Multiple"},
    "CLM-STORY-00": {"weight": 0.00, "source": "llm_story", "title": "Story Consistency"}
}
""")

write_file("app/scoring/calibration.py", """
def calibrate(raw_score: float, source: str) -> float:
    return raw_score
""")

write_file("app/scoring/quality.py", """
def apply_quality_gates(raw_weight: float, source: str, quality_warnings: list) -> float:
    return raw_weight
""")

write_file("app/scoring/fusion.py", """
from typing import List, Dict, Any

CAPS = {
    "metadata": 0.4,
    "aadhaar_qr": 0.85,
    "liveness": 0.75,
    "voice": 0.55,
    "llm_story": 0.25
}

def compute_fusion(evidence_list: List[Dict[str, Any]]) -> float:
    sources = {}
    
    for ev in evidence_list:
        if ev.get("kind") != "risk":
            continue
        w = ev.get("effective_weight", 0.0)
        p = ev.get("calibrated_score", 0.0)
        source = ev.get("source", "unknown")
        
        # Participation threshold
        if p >= 0.2 and (w * p) >= 0.02:
            t = w * p
            if source not in sources:
                sources[source] = []
            sources[source].append(t)
            
    risk_total = 1.0
    for source, terms in sources.items():
        source_risk = 1.0
        for t in terms:
            source_risk *= (1.0 - t)
        source_risk = 1.0 - source_risk
        
        cap = CAPS.get(source, 1.0)
        source_risk = min(source_risk, cap)
        
        risk_total *= (1.0 - source_risk)
        
    return 1.0 - risk_total
""")

write_file("app/scoring/overall.py", """
from typing import List

def compute_overall_score(pipeline_risks: List[float]) -> float:
    if not pipeline_risks:
        return 0.0
    if len(pipeline_risks) == 1:
        return pipeline_risks[0]
    return 0.7 * max(pipeline_risks) + 0.3 * (sum(pipeline_risks) / len(pipeline_risks))
""")

write_file("app/scoring/overrides.py", """
from typing import List

def apply_overrides(evidence_ids: List[str], current_risk: float, pipeline_type: str) -> float:
    risk = current_risk
    if "IMG-C2PA-01" in evidence_ids:
        risk = max(risk, 0.95)
    if "DOC-LOGIC-01" in evidence_ids and "DOC-CNN-01" in evidence_ids and pipeline_type == "document":
        risk = max(risk, 0.85)
    if "ID-FACE-01" in evidence_ids and pipeline_type == "overall":
        risk = max(risk, 0.80)
    if "IMG-DUP-01" in evidence_ids and pipeline_type == "overall":
        risk = max(risk, 0.90)
    if "DOC-OVERLAY-01" in evidence_ids and pipeline_type == "document":
        risk = max(risk, 0.80)
    if "ID-LIVE-01" in evidence_ids and "ID-FACE-01" in evidence_ids and pipeline_type == "overall":
        risk = max(risk, 0.85)
    if "ID-QR-01" in evidence_ids and pipeline_type in ["identity", "overall"]:
        risk = max(risk, 0.85)
    return risk
""")

write_file("app/scoring/bands.py", """
from ..core.config import settings
from typing import List

def get_band(risk: float) -> str:
    if risk < settings.BAND_LOW_MAX:
        return "LOW"
    elif risk < settings.BAND_MED_MAX:
        return "MEDIUM"
    return "HIGH"

def determine_confidence(evidence_ids: List[str], initial_conf: str = "high") -> str:
    if "ID-QR-04" in evidence_ids:
        if initial_conf == "high": return "medium"
        return "low"
    return initial_conf

def get_severity(effective_weight: float, calibrated_score: float) -> str:
    val = effective_weight * calibrated_score
    if val >= 0.5:
        return "high"
    elif val >= 0.2:
        return "medium"
    return "low"
""")

# Explainer
write_file("app/explain/templates.py", """
TEMPLATES = {
    "IMG-AI-01": "The image shows strong signs of being AI-generated.",
    "IMG-ELA-01": "One region of the photo was compressed differently from the rest, which often means it was edited after capture.",
    "IMG-EXIF-01": "The file lacks expected camera metadata.",
    "IMG-EXIF-02a": "The file's metadata names an AI image generator ({software}).",
    "DOC-LOGIC-01": "The line items add up to {expected} but the stated total is {found}.",
    "DOC-CNN-01": "The tamper detector found an area around '{field}' whose compression pattern differs from the rest of the page.",
    "DOC-FONT-01": "The value '{text}' uses a different font from the other amounts.",
    "DOC-META-02": "The PDF was modified after it was created.",
    "ID-FACE-01": "The face on the ID does not match the selfie.",
    "CLM-X-02": "The document total differs from the amount claimed."
}
""")

write_file("app/explain/explainer.py", """
from typing import List, Dict, Any
from .templates import TEMPLATES

def format_summary(band: str, risk: float, evidence_list: List[Dict[str, Any]], confidence: str) -> str:
    sorted_ev = sorted([e for e in evidence_list if e.get("kind") == "risk"], 
                       key=lambda x: x.get("effective_weight", 0.0) * x.get("calibrated_score", 0.0), reverse=True)
    
    reasons = []
    for ev in sorted_ev[:2]:
        ev_id = ev.get("id")
        template = TEMPLATES.get(ev_id, ev.get("reason", "Suspicious activity detected."))
        details = ev.get("details", {})
        try:
            reason = template.format(**details)
        except Exception:
            reason = template
        reasons.append(reason)
        
    reason_str = " ".join(reasons)
    
    cav_str = " "
    if confidence != "high":
        cav_str = " Some checks were limited or skipped. "
        
    action_texts = {
        "LOW": "No significant indicators. Proceed with the normal process.",
        "MEDIUM": "Route to manual review. Check the highlighted items.",
        "HIGH": "Escalate to the fraud investigation team before any payout."
    }
    action = action_texts.get(band, "")
    
    return f"{band} fraud likelihood ({risk*100:.0f}%). {reason_str}{cav_str}Recommended action: {action}"
""")

write_file("app/explain/llm.py", """
def rewrite_summary(prompt: str) -> str:
    return ""
""")

# Job Manager & Orchestrator
write_file("app/services/job_manager.py", """
import asyncio
import uuid
import datetime
from typing import Dict, Any
from ..schemas.job import JobStatus, StepStatus

JOBS_DB: Dict[str, JobStatus] = {}
SEMAPHORE = asyncio.Semaphore(1) 

def create_job(mode: str) -> str:
    job_id = str(uuid.uuid4())
    JOBS_DB[job_id] = JobStatus(job_id=job_id, status="queued", mode=mode, steps=[])
    return job_id

def get_job(job_id: str) -> JobStatus:
    return JOBS_DB.get(job_id)

def update_job_status(job_id: str, status: str):
    if job_id in JOBS_DB:
        JOBS_DB[job_id].status = status

def start_step(job_id: str, step_name: str):
    if job_id in JOBS_DB:
        JOBS_DB[job_id].steps.append(StepStatus(name=step_name, status="running"))

def finish_step(job_id: str, step_name: str, status: str, duration_ms: int = 0):
    if job_id in JOBS_DB:
        for s in JOBS_DB[job_id].steps:
            if s.name == step_name:
                s.status = status
                s.duration_ms = duration_ms
""")

write_file("app/detectors/base.py", """
import asyncio
import time
from typing import Any
from ..schemas.result import DetectorStatus
from ..core.config import settings

class AnalysisContext:
    pass

class DetectorOutput:
    pass

async def run_safely(detector_func, ctx: AnalysisContext, detector_name: str) -> DetectorStatus:
    start = time.time()
    try:
        await asyncio.wait_for(detector_func(ctx), timeout=settings.DETECTOR_TIMEOUT_S)
        return DetectorStatus(detector=detector_name, status="ok", duration_ms=int((time.time()-start)*1000))
    except asyncio.TimeoutError:
        return DetectorStatus(detector=detector_name, status="failed", duration_ms=int((time.time()-start)*1000), error="timeout")
    except Exception as e:
        return DetectorStatus(detector=detector_name, status="failed", duration_ms=int((time.time()-start)*1000), error=str(e))
""")

write_file("app/pipelines/image_pipeline.py", """
from typing import List
from ..schemas.evidence import Evidence
from ..scoring.weights import EVIDENCE_CATALOG

async def run_image_pipeline(ctx) -> List[Evidence]:
    ev = []
    cat = EVIDENCE_CATALOG["IMG-AI-01"]
    ev.append(Evidence(
        id="IMG-AI-01", kind="risk", raw_score=0.97, calibrated_score=0.97,
        weight=cat["weight"], effective_weight=cat["weight"], severity="high",
        title=cat["title"], reason=cat["title"]
    ))
    return ev
""")

write_file("app/pipelines/document_pipeline.py", """
from typing import List
from ..schemas.evidence import Evidence
from ..scoring.weights import EVIDENCE_CATALOG

async def run_document_pipeline(ctx) -> List[Evidence]:
    ev = []
    cat = EVIDENCE_CATALOG["DOC-LOGIC-01"]
    ev.append(Evidence(
        id="DOC-LOGIC-01", kind="risk", raw_score=1.0, calibrated_score=1.0,
        weight=cat["weight"], effective_weight=cat["weight"], severity="high",
        title=cat["title"], reason=cat["title"], details={"expected": "100.00", "found": "200.00"}
    ))
    return ev
""")

write_file("app/pipelines/claim_pipeline.py", """
from typing import List
from ..schemas.evidence import Evidence

async def run_claim_pipeline(ctx) -> List[Evidence]:
    return []
""")

write_file("app/services/orchestrator.py", """
import asyncio
import uuid
import datetime
import os
from . import job_manager
from ..scoring.fusion import compute_fusion
from ..scoring.bands import get_band, determine_confidence
from ..scoring.overall import compute_overall_score
from ..scoring.overrides import apply_overrides
from ..explain.explainer import format_summary
from ..schemas.result import AnalysisResult, OverallScore, PipelineScore, DetectorStatus
from ..pipelines import image_pipeline, document_pipeline, claim_pipeline
from ..core.config import settings

RESULTS_DB = {}

async def run_analysis_job(job_id: str, mode: str):
    async with job_manager.SEMAPHORE:
        job_manager.update_job_status(job_id, "running")
        try:
            job_manager.start_step(job_id, "validate")
            await asyncio.sleep(0.1)
            job_manager.finish_step(job_id, "validate", "done", 100)
            
            all_evidence = []
            pipeline_risks = []
            img_score = None
            doc_score = None
            
            if mode in ["image", "claim"]:
                job_manager.start_step(job_id, "image_pipeline")
                ev = await image_pipeline.run_image_pipeline(None)
                risk = compute_fusion([e.model_dump() for e in ev])
                risk = apply_overrides([e.id for e in ev], risk, "image")
                img_score = PipelineScore(
                    pipeline="image", risk=risk, authenticity=1.0-risk, 
                    band=get_band(risk), confidence="high", evidence_ids=[e.id for e in ev]
                )
                pipeline_risks.append(risk)
                all_evidence.extend(ev)
                job_manager.finish_step(job_id, "image_pipeline", "done", 500)
                
            if mode in ["document", "claim"]:
                job_manager.start_step(job_id, "document_pipeline")
                ev = await document_pipeline.run_document_pipeline(None)
                risk = compute_fusion([e.model_dump() for e in ev])
                risk = apply_overrides([e.id for e in ev], risk, "document")
                doc_score = PipelineScore(
                    pipeline="document", risk=risk, authenticity=1.0-risk, 
                    band=get_band(risk), confidence="high", evidence_ids=[e.id for e in ev]
                )
                pipeline_risks.append(risk)
                all_evidence.extend(ev)
                job_manager.finish_step(job_id, "document_pipeline", "done", 500)
                
            overall_risk = compute_overall_score(pipeline_risks)
            overall_risk = apply_overrides([e.id for e in all_evidence], overall_risk, "overall")
            band = get_band(overall_risk)
            conf = determine_confidence([e.id for e in all_evidence])
            
            summary = format_summary(band, overall_risk, [e.model_dump() for e in all_evidence], conf)
            
            res_id = str(uuid.uuid4())
            res = AnalysisResult(
                id=res_id, mode=mode, created_at=datetime.datetime.now().isoformat(),
                overall=OverallScore(risk=overall_risk, band=band, confidence=conf, summary=summary),
                evidence=all_evidence,
                image=img_score, document=doc_score,
                detector_status=[], quality_warnings=[], artifacts={}, versions={"detector": "v1"}
            )
            RESULTS_DB[res_id] = res
            
            # Create artifact directory
            os.makedirs(os.path.join(os.path.dirname(__file__), f"../../../data/runtime/artifacts/{res_id}"), exist_ok=True)
            
            job = job_manager.get_job(job_id)
            job.result_id = res_id
            job.status = "done"
            
        except Exception as e:
            job = job_manager.get_job(job_id)
            job.status = "failed"
            job.error = str(e)
""")

write_file("app/api/v1/analyze.py", """
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form, HTTPException
from ...schemas.job import JobStatus
from ...services import job_manager, orchestrator
import os
import uuid
import shutil

router = APIRouter()

def validate_upload(file: UploadFile, job_id: str):
    if file.size and file.size > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    
    upload_dir = os.path.join(os.path.dirname(__file__), f"../../../../data/runtime/uploads/{job_id}")
    os.makedirs(upload_dir, exist_ok=True)
    with open(os.path.join(upload_dir, "uploaded_file"), "wb") as f:
        shutil.copyfileobj(file.file, f)

@router.post("/analyze/image", status_code=202)
async def analyze_image(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = job_manager.create_job("image")
    validate_upload(file, job_id)
    background_tasks.add_task(orchestrator.run_analysis_job, job_id, "image")
    return {"job_id": job_id}

@router.post("/analyze/document", status_code=202)
async def analyze_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = job_manager.create_job("document")
    validate_upload(file, job_id)
    background_tasks.add_task(orchestrator.run_analysis_job, job_id, "document")
    return {"job_id": job_id}

@router.post("/analyze/claim", status_code=202)
async def analyze_claim(background_tasks: BackgroundTasks, metadata: str = Form(None)):
    job_id = job_manager.create_job("claim")
    background_tasks.add_task(orchestrator.run_analysis_job, job_id, "claim")
    return {"job_id": job_id}
""")

write_file("app/api/v1/jobs.py", """
from fastapi import APIRouter, HTTPException
from ...schemas.job import JobStatus
from ...services import job_manager
from ...core.config import settings

router = APIRouter()

@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    if settings.MOCK_ANALYSIS and job_id.startswith("mock"):
        return JobStatus(job_id=job_id, status="done", mode="claim", steps=[], result_id="mock-result-HIGH")
        
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
""")

write_file("app/api/v1/results.py", """
from fastapi import APIRouter, HTTPException
from ...schemas.result import AnalysisResult, OverallScore, PipelineScore, Evidence
from ...services.orchestrator import RESULTS_DB
from ...core.config import settings

router = APIRouter()

@router.get("/results/{result_id}", response_model=AnalysisResult)
def get_result(result_id: str):
    if settings.MOCK_ANALYSIS and result_id.startswith("mock"):
        return AnalysisResult(
            id=result_id, mode="claim", created_at="2026-10-03T00:00:00Z",
            overall=OverallScore(risk=0.88, band="HIGH", confidence="high", summary="Mocked high fraud."),
            evidence=[], detector_status=[], quality_warnings=[], artifacts={}, versions={"detector": "mock"}
        )
        
    res = RESULTS_DB.get(result_id)
    if not res:
        raise HTTPException(status_code=404, detail="Result not found")
    return res
""")

write_file("app/main.py", """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .core.config import settings
from .db.models import init_db
from .core.errors import global_exception_handler
from .api.v1 import health, analyze, jobs, results
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class ModelRegistry:
    def __init__(self):
        self.models = {}

model_registry = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_registry
    model_registry = ModelRegistry()
    init_db()
    # TODO: Start cleanup task stub
    yield
    # Shutdown
    pass

app = FastAPI(title="Lucen AI", lifespan=lifespan)

app.add_exception_handler(Exception, global_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(analyze.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(results.router, prefix="/api/v1")
""")

write_file("tests/test_scoring.py", """
from app.scoring.fusion import compute_fusion
from app.scoring.overall import compute_overall_score
from app.scoring.overrides import apply_overrides
from app.scoring.bands import determine_confidence

def test_worked_example_fusion():
    ev_img = [
        {"id": "IMG-AI-01", "kind": "risk", "effective_weight": 0.70, "calibrated_score": 0.97, "source": "ai_detector"},
        {"id": "IMG-ELA-01", "kind": "risk", "effective_weight": 0.25, "calibrated_score": 0.70, "source": "forensics"},
        {"id": "IMG-EXIF-01", "kind": "risk", "effective_weight": 0.10, "calibrated_score": 0.50, "source": "metadata"}
    ]
    r_img = compute_fusion(ev_img)
    assert abs(r_img - 0.748) < 0.01

    ev_doc = [
        {"id": "DOC-LOGIC-01", "kind": "risk", "effective_weight": 0.80, "calibrated_score": 1.00, "source": "rules"},
        {"id": "DOC-CNN-01", "kind": "risk", "effective_weight": 0.50, "calibrated_score": 0.75, "source": "forensics"},
        {"id": "DOC-FONT-01", "kind": "risk", "effective_weight": 0.30, "calibrated_score": 0.60, "source": "rules"},
        {"id": "DOC-META-02", "kind": "risk", "effective_weight": 0.15, "calibrated_score": 0.50, "source": "metadata"}
    ]
    r_doc = compute_fusion(ev_doc)
    assert abs(r_doc - 0.905) < 0.01

    r_overall = compute_overall_score([r_img, r_doc])
    assert abs(r_overall - 0.882) < 0.01

def test_participation_threshold():
    ev_weak = [
        {"id": "TEST1", "kind": "risk", "effective_weight": 0.05, "calibrated_score": 0.10, "source": "s1"}
    ]
    r = compute_fusion(ev_weak)
    assert r == 0.0

def test_source_caps():
    ev_meta = [
        {"id": "TEST", "kind": "risk", "effective_weight": 1.0, "calibrated_score": 1.0, "source": "metadata"}
    ]
    r = compute_fusion(ev_meta)
    assert abs(r - 0.4) < 0.01

def test_overrides():
    assert apply_overrides(["IMG-C2PA-01"], 0.1, "image") == 0.95
    assert apply_overrides(["ID-QR-04"], 0.1, "overall") == 0.1

def test_confidence():
    assert determine_confidence(["ID-QR-04"], "high") == "medium"
""")

write_file("tests/test_api.py", """
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.detectors.base import run_safely, AnalysisContext

client = TestClient(app)

def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200

def test_mock_upload():
    response = client.post("/api/v1/analyze/image", files={"file": ("test.jpg", b"fake image bytes", "image/jpeg")})
    assert response.status_code == 202
    assert "job_id" in response.json()

def test_upload_too_large():
    # 16 MB dummy payload
    dummy = b"0" * (16 * 1024 * 1024)
    response = client.post("/api/v1/analyze/image", files={"file": ("test.jpg", dummy, "image/jpeg")})
    assert response.status_code == 413

@pytest.mark.asyncio
async def test_run_safely():
    async def crash_det(ctx): raise Exception("Crash")
    async def timeout_det(ctx): await asyncio.sleep(100)
    
    ctx = AnalysisContext()
    res1 = await run_safely(crash_det, ctx, "crash")
    assert res1.status == "failed"
    assert res1.error == "Crash"
    
    res2 = await run_safely(timeout_det, ctx, "timeout")
    assert res2.status == "failed"
    assert res2.error == "timeout"
""")

# Delete old database.py if exists
try: os.remove(os.path.join(BASE_DIR, 'app/db/database.py'))
except: pass
