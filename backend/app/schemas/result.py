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

class StoryContradiction(BaseModel):
    text: str
    sources: List[str] = []
    evidence_ids: List[str] = []

class StoryConsistentPoint(BaseModel):
    statement_quote: str = ""
    evidence_ref: str = ""
    detail: Optional[str] = None

class StoryStatus(BaseModel):
    contradictions: List[Any] = []
    consistent_points: List[Any] = []
    source: str = "rules"
    note: str = "For investigator review, not part of the score"


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

class WhyThisScoreItem(BaseModel):
    evidence_id: str
    title: str
    w: float
    p: float
    push: float  # w * p
    contribution_pct: float

class QualityGateApplied(BaseModel):
    detector: str
    factor: float
    reason: str

class PipelineWhy(BaseModel):
    evidence_contributions: List[WhyThisScoreItem] = []
    formula: str = ""
    overrides_applied: List[str] = []
    quality_gates_applied: List[QualityGateApplied] = []

class OverallWhy(BaseModel):
    formula: str = ""
    pipeline_risks: Dict[str, float] = {}
    overrides_applied: List[str] = []

class WhyThisScore(BaseModel):
    image: Optional[PipelineWhy] = None
    document: Optional[PipelineWhy] = None
    identity: Optional[PipelineWhy] = None
    voice: Optional[PipelineWhy] = None
    claim: Optional[PipelineWhy] = None
    overall: Optional[OverallWhy] = None
    items: Optional[List[WhyThisScoreItem]] = None

class CheckRunItem(BaseModel):
    detector: str
    status: str  # "ok" | "skipped" | "failed"
    duration_ms: int
    reason: Optional[str] = None

class PageInfo(BaseModel):
    page: int
    width_pt: float = 595.0
    height_pt: float = 842.0
    image_url: str
    annotated_url: Optional[str] = None
    tamper_heatmap_url: Optional[str] = None

class HistoryItem(BaseModel):
    id: str
    created_at: str
    mode: str
    overall_risk: float
    overall_band: str
    thumbnail_url: Optional[str] = None
    evidence_count: int = 0
    top_reason: Optional[str] = None

class HistoryResponse(BaseModel):
    items: List[HistoryItem]
    total: int
    page: int
    page_size: int

class VoiceExtracted(BaseModel):
    incident_date: Optional[str] = None
    incident_time: Optional[str] = None
    amount_claimed: Optional[float] = None
    damaged_items: Optional[List[str]] = None
    location_text: Optional[str] = None
    vehicle_registration: Optional[str] = None
    peril: Optional[str] = None

class VoiceSpoofSegment(BaseModel):
    start_s: float
    end_s: float
    score: float

class VoiceSpoof(BaseModel):
    probability: Optional[float] = None
    band: Optional[str] = None
    segments: Optional[List[VoiceSpoofSegment]] = None

class VoiceDetails(BaseModel):
    language: Optional[str] = None
    duration_s: Optional[float] = None
    transcript: Optional[str] = None
    translation_en: Optional[str] = None
    extracted: Optional[VoiceExtracted] = None
    spoof: Optional[VoiceSpoof] = None
    status: Optional[str] = None

class AnalysisResult(BaseModel):
    id: str
    claim_id: Optional[str] = None
    mode: str
    created_at: str
    image: Optional[PipelineScore] = None
    document: Optional[PipelineScore] = None
    identity: Optional[Any] = None
    claim: Optional[PipelineScore] = None
    overall: OverallScore
    evidence: List[Evidence]
    detector_status: List[DetectorStatus]
    quality_warnings: List[QualityWarning]
    artifacts: Dict[str, Any]
    versions: Dict[str, str]
    location: Optional[Dict[str, Any]] = None
    # v2 blocks
    voice: Optional[PipelineScore] = None
    voice_details: Optional[VoiceDetails] = None
    liveness: Optional[LivenessStatus] = None
    aadhaar_qr: Optional[AadhaarQrStatus] = None
    story: Optional[StoryStatus] = None
    links: Optional[List[Link]] = None
    decision: Optional[Decision] = None
    # Prompt 5 additions
    image_results: Optional[List[PipelineScore]] = None
    why_this_score: Optional[WhyThisScore] = None
    why_this_score_items: Optional[List[WhyThisScoreItem]] = None
    checks_run: Optional[List[CheckRunItem]] = None
    top_reasons: Optional[List[str]] = None
    recommended_action: Optional[str] = None
    summary_source: Optional[str] = "template"

