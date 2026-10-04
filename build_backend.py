import os
import textwrap

BASE_DIR = r"c:\Users\gaura\Desktop\LUCENAI"
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

def write_file(path, content):
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).strip() + "\n")

# 1. Top level files
write_file("README.md", """
# Lucen AI

AI-Powered Synthetic Identity and Deepfake Claim Detection System
""")

write_file("Makefile", """
.PHONY: dev test openapi

dev:
\t@echo "Starting backend and frontend..."
\t@start cmd /c "cd backend && uvicorn app.main:app --reload --port 8000"
\t@start cmd /c "cd frontend && npm run dev"

openapi:
\t@python backend/scripts/export_openapi.py

test:
\t@echo "Tests not implemented yet"
""")

write_file(".env.example", """
CORS_ORIGINS=http://localhost:5173
AUTH_SECRET=
AUTH_TOKEN_HOURS=8
ENTITY_HASH_SALT=
DEMO_MODE=1
MOCK_ANALYSIS=1
LLM_ENABLED=false
LLM_PROVIDER=
LLM_API_KEY=
BHASHINI_API_KEY=
BHASHINI_USER_ID=
AADHAAR_QR_MODE=demo_key
DEMO_QR_PUBKEY_PATH=models/demo_qr_public.pem
MAX_CONCURRENT_JOBS=1
DETECTOR_TIMEOUT_S=30
MAX_UPLOAD_MB=15
MAX_PDF_PAGES=10
RETENTION_HOURS=24
IMAGE_MODEL_ID=Ateeqq/ai-vs-human-image-detector
OCR_ENGINE=paddle
BAND_LOW_MAX=0.35
BAND_MED_MAX=0.65
MODELS_DIR=models/
SEED_ON_START=1
LAZY_LOAD_BONUS_MODELS=true
""")

write_file(".gitignore", """
node_modules/
__pycache__/
*.pyc
.env
data/runtime/
data/synthetic/
models/*.keras
.venv/
""")

write_file(".editorconfig", """
root = true
[*]
charset = utf-8
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true
[*.py]
indent_size = 4
""")

write_file("backend/requirements.txt", """
fastapi==0.110.0
uvicorn[standard]==0.27.1
pydantic==2.6.3
pydantic-settings==2.2.1
python-multipart==0.0.9
httpx==0.27.0
""")

# core/config.py
write_file("backend/app/core/config.py", """
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MAX_UPLOAD_MB: int = 15
    MAX_PDF_PAGES: int = 10
    RETENTION_HOURS: int = 24
    MAX_CONCURRENT_JOBS: int = 1
    DETECTOR_TIMEOUT_S: int = 30
    BAND_LOW_MAX: float = 0.35
    BAND_MED_MAX: float = 0.65
    IMAGE_MODEL_ID: str = "Ateeqq/ai-vs-human-image-detector"
    MODELS_DIR: str = "models/"
    OCR_ENGINE: str = "paddle"
    LLM_PROVIDER: str = ""
    LLM_API_KEY: str = ""
    LLM_ENABLED: bool = True
    MOCK_ANALYSIS: bool = True
    CORS_ORIGINS: str = "http://localhost:5173"
    AUTH_SECRET: str = "supersecret"
    AUTH_TOKEN_HOURS: int = 8
    ENTITY_HASH_SALT: str = "salt"
    DEMO_MODE: bool = True
    BHASHINI_API_KEY: str = ""
    BHASHINI_USER_ID: str = ""
    AADHAAR_QR_MODE: str = "demo_key"
    DEMO_QR_PUBKEY_PATH: str = "models/demo_qr_public.pem"
    SEED_ON_START: bool = True
    LAZY_LOAD_BONUS_MODELS: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
""")

# schemas
write_file("backend/app/schemas/base.py", """
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

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

class DetectorStatus(BaseModel):
    detector: str
    status: str
    duration_ms: int
    error: Optional[str] = None

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
    identity: Optional[Any] = None  # To be detailed later if needed
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

class ErrorDetail(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
""")

write_file("backend/app/schemas/__init__.py", "from .base import *\n")

# db models
write_file("backend/app/db/database.py", """
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../../data/runtime/lucen.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
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

# Error handlers
write_file("backend/app/core/errors.py", """
from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging
from ..schemas.base import ErrorDetail

logger = logging.getLogger(__name__)

async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    err = ErrorDetail(
        error="internal_error",
        message="An unexpected error occurred",
        details={"path": request.url.path}
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=err.model_dump())
""")

# API
write_file("backend/app/api/v1/health.py", """
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok", "models": {"ai_detector": "mocked" if True else "loaded"}}
""")

write_file("backend/app/api/v1/analyze.py", """
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from ...schemas import JobStatus
import uuid
import time
import asyncio

router = APIRouter()

async def mock_job_runner(job_id: str):
    await asyncio.sleep(3)

@router.post("/analyze/image", status_code=202)
async def analyze_image(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(mock_job_runner, job_id)
    return {"job_id": job_id}

@router.post("/analyze/document", status_code=202)
async def analyze_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(mock_job_runner, job_id)
    return {"job_id": job_id}

@router.post("/analyze/claim", status_code=202)
async def analyze_claim(background_tasks: BackgroundTasks, metadata: str = Form(None)):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(mock_job_runner, job_id)
    return {"job_id": job_id}
""")

write_file("backend/app/api/v1/jobs.py", """
from fastapi import APIRouter
from ...schemas import JobStatus, StepStatus

router = APIRouter()

@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    # Mock response
    return JobStatus(
        job_id=job_id,
        status="done",
        mode="claim",
        steps=[
            StepStatus(name="validate", status="done", duration_ms=40),
            StepStatus(name="image_metadata", status="done", duration_ms=25),
            StepStatus(name="ai_detector", status="done", duration_ms=100),
            StepStatus(name="ocr", status="done", duration_ms=200)
        ],
        result_id="result_" + job_id
    )
""")

write_file("backend/app/api/v1/results.py", """
from fastapi import APIRouter
from ...schemas import AnalysisResult, OverallScore, PipelineScore, Evidence, DetectorStatus

router = APIRouter()

@router.get("/results/{result_id}", response_model=AnalysisResult)
def get_result(result_id: str):
    return AnalysisResult(
        id=result_id,
        mode="claim",
        created_at="2026-10-03T00:00:00Z",
        overall=OverallScore(
            risk=0.88,
            band="HIGH",
            confidence="high",
            summary="High fraud likelihood mock summary."
        ),
        image=PipelineScore(pipeline="image", risk=0.9, authenticity=0.1, band="HIGH", confidence="high", evidence_ids=["IMG-AI-01"]),
        evidence=[
            Evidence(id="IMG-AI-01", kind="risk", raw_score=0.9, calibrated_score=0.9, weight=0.8, effective_weight=0.8, severity="high", title="AI Generated", reason="Image shows strong signs of AI generation", artifact="image_heatmap.png")
        ],
        detector_status=[
            DetectorStatus(detector="ai_detector", status="ok", duration_ms=150)
        ],
        quality_warnings=[],
        artifacts={"image_heatmap": "/api/v1/artifacts/mock/image_heatmap.png"},
        versions={"detector": "mock"}
    )
""")

# main.py
write_file("backend/app/main.py", """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .core.config import settings
from .db.database import init_db
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

# export_openapi.py
write_file("backend/scripts/export_openapi.py", """
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from fastapi.openapi.utils import get_openapi

def export():
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    docs_path = os.path.join(os.path.dirname(__file__), "../../docs")
    os.makedirs(docs_path, exist_ok=True)
    with open(os.path.join(docs_path, "openapi.json"), "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print("Exported openapi.json")

if __name__ == "__main__":
    export()
""")
