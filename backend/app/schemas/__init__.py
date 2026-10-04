from .evidence import Evidence, BBox, EvidenceKind
from .result import (
    PipelineScore,
    OverallScore,
    QualityWarning,
    DetectorStatus,
    ChallengeStatus,
    LivenessStatus,
    QrComparison,
    AadhaarQrStatus,
    StoryStatus,
    Link,
    Decision,
    AnalysisResult,
    WhyThisScoreItem,
    QualityGateApplied,
    PipelineWhy,
    OverallWhy,
    WhyThisScore,
    CheckRunItem,
    PageInfo,
    HistoryItem,
    HistoryResponse,
)
from .job import StepStatus, JobStatus
from .requests import ClaimMetadata
from .auth import LoginRequest, TokenResponse, User
from .claims import ClaimCreate, ClaimStatus
from .decisions import DecisionRequest, DecisionDraft
from .timeline import TimelineEvent, Contradiction, ClaimantTimelineItem
from .analytics import TrendsResponse
from .network import Node, Edge
from typing import Optional, Dict, Any
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

__all__ = [
    "Evidence",
    "BBox",
    "EvidenceKind",
    "PipelineScore",
    "OverallScore",
    "QualityWarning",
    "DetectorStatus",
    "ChallengeStatus",
    "LivenessStatus",
    "QrComparison",
    "AadhaarQrStatus",
    "StoryStatus",
    "Link",
    "Decision",
    "AnalysisResult",
    "StepStatus",
    "JobStatus",
    "ClaimMetadata",
    "LoginRequest",
    "TokenResponse",
    "User",
    "ClaimCreate",
    "ClaimStatus",
    "DecisionRequest",
    "DecisionDraft",
    "TimelineEvent",
    "Contradiction",
    "ClaimantTimelineItem",
    "TrendsResponse",
    "Node",
    "Edge",
    "ErrorDetail",
]
