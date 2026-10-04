export type Band = 'LOW' | 'MEDIUM' | 'HIGH';
export type Confidence = 'high' | 'medium' | 'low';
export type Pipeline = 'image' | 'document' | 'identity' | 'voice' | 'claim';
export type JobState = 'queued' | 'running' | 'done' | 'failed';

export interface ScoreVM {
  risk: number;
  band: Band;
  confidence: Confidence;
  analysed: boolean;
}
export interface EvidenceVM {
  id: string;
  title: string;
  reason: string;
  kind: 'risk' | 'warning' | 'info';
  severity: 'low' | 'medium' | 'high';
  score?: number;
  weight?: number;
  contribution?: number;
  contributionPct?: number;
  rank?: number;
  pipeline?: Pipeline;
  pipelineInput?: string;
  page?: number;
  bbox?: { page?: number; x: number; y: number; w: number; h: number };
  field?: string;
}
export interface ResultVM {
  id: string;
  /** claim this analysis belongs to (needed for network, actions, entities); absent for ad-hoc analyses */
  claimId?: string;
  createdAt?: string;
  topReasons: string[];
  decision?: {
    status: string;
    by: string;
    at: string;
    reasonCode: string;
    claimantMessage: string;
  };
  links: { resultId: string; reason: string }[];
  whyDetail: {
    formulas: { pipeline: string; formula: string }[];
    overrides: string[];
    gates: { detector: string; factor: number; reason: string }[];
  };
  mode: 'image' | 'document' | 'claim';
  overall: ScoreVM;
  image?: ScoreVM;
  document?: ScoreVM;
  identity?: ScoreVM;
  claim?: ScoreVM;
  voice?: ScoreVM;
  summary: string;
  recommendedAction: string;
  summarySource?: string;
  qualityWarnings: string[];
  evidence: EvidenceVM[];
  imageResults: { label: string; url?: string }[];
  artifacts: {
    heatmap?: string;
    overlay?: string;
    pages: { page: number; widthPt: number; heightPt: number; imageUrl: string }[];
    previews?: string[];
    identityFaceComparison?: { idFace?: string; selfie?: string };
  };
  whyThisScore: {
    pipeline: string;
    w: number;
    p: number;
    push: number;
    contributionPct: number;
    evidenceId?: string;
    title?: string;
  }[];
  checksRun: {
    detector: string;
    status: 'ok' | 'skipped' | 'failed';
    durationMs?: number;
    reason?: string;
  }[];
  duplicate?: {
    matchType: string;
    similarity: number;
    earlierClaim: string;
    thumbnailUrl?: string;
  };
  location?: {
    claimed?: { lat: number; lng: number };
    photos: { lat: number; lng: number; distanceKm?: number }[];
    maxDistanceKm?: number;
  };
  identityDetails?: {
    similarity?: number;
    verdict?: string;
    aiGeneratedSelfie?: string;
    livenessPerformed?: boolean;
    livenessPassed?: boolean;
    challenges: { name: string; status: string }[];
    aadhaarQr?: {
      printed?: Record<string, unknown>;
      signed?: Record<string, unknown>;
      mismatches?: string[];
      signatureStatus?: string;
      testKey?: boolean;
      photoSimilarity?: number;
      rows?: { field: string; printed: string; signed: string; match: boolean }[];
    };
  };
  claimChecks?: { name: string; status: 'passed' | 'flagged' | 'skipped'; reason?: string }[];
  timeline?: {
    date?: string;
    title: string;
    detail?: string;
    ruleId?: string;
    contradiction?: boolean;
  }[];
  voiceDetails?: VoiceVM;
  story?: StoryVM;
}
export interface JobVM {
  status: JobState;
  steps: { name: string; status: string; durationMs?: number }[];
  resultId?: string;
  error?: string;
}
export interface QueueRowVM {
  id: string;
  /** result to open; falls back to the claim id when the backend omits result_id */
  resultId: string;
  claimantMasked: string;
  type: string;
  submitted: string;
  band: Band;
  risk: number;
  topReason: string;
  status: string;
  eligibleFastTrack: boolean;
}
export interface HistoryRowVM {
  id: string;
  date: string;
  mode: string;
  fileNames: string[];
  band: Band;
  risk: number;
  topReason?: string;
  evidenceCount?: number;
  thumbnailUrl?: string;
}
export interface PolicyVM {
  id: string;
  policyNumber: string;
  claimType: string;
  asset: string;
  validFrom: string;
  validTo: string;
  sumInsured?: number;
}
export interface ClaimSummaryVM {
  id: string;
  policyLabel: string;
  claimType: string;
  submittedAt: string;
  status: string;
  lastUpdate?: string;
}
export interface ActionVM {
  at: string;
  actor: string;
  action: string;
  note?: string;
}
export interface ClaimStatusVM {
  id: string;
  status: string;
  message?: string;
  outcome?: string;
  reasonLabel?: string;
  canResubmit: boolean;
  slotsToResubmit: string[];
  nextSteps: string[];
  evidence: { slot: string; status: string; label?: string; updatedAt?: string }[];
  timeline: { status: string; date?: string; detail?: string }[];
}
export interface UserVM {
  id: string;
  name: string;
  email: string;
  role: 'claimant' | 'investigator';
  preferredLang?: string;
}
export interface LivenessSessionVM {
  sessionId: string;
  nonce: string;
  challenges: string[];
  spokenCode?: string;
  expiresAt?: string;
}

/* ---------- Voice ---------- */
export interface ExtractedFieldsVM {
  incidentType?: string;
  peril?: string;
  vehicleRegistration?: string;
  incidentDate?: string;
  incidentTime?: string;
  amount?: number;
  damagedItems: string[];
  locationText?: string;
}
export interface VoiceVM {
  language?: string;
  durationS?: number;
  transcript?: string;
  translationEn?: string;
  extracted: ExtractedFieldsVM;
  spoof?: {
    probability?: number;
    band?: Band;
    segments: { startS: number; endS: number; score?: number }[];
  };
  status?: string;
}
export interface TranscriptionVM {
  language: string;
  transcript: string;
  translationEn: string;
  extracted: ExtractedFieldsVM;
}
export interface VoiceLanguageVM {
  code: string;
  label: string;
}

/* ---------- Story review ---------- */
export interface StoryVM {
  contradictions: { text: string; sources: string[]; evidenceIds: string[] }[];
  consistentPoints: string[];
  source: string;
  note: string;
}

/* ---------- Network ---------- */
export type NodeKind = 'claim' | 'claimant' | 'identifier' | 'ring' | 'other';
export interface GraphNodeVM {
  id: string;
  kind: NodeKind;
  label: string;
  band?: Band;
  risk?: number;
  flags: string[];
  synthetic: boolean;
}
export interface GraphEdgeVM {
  id: string;
  source: string;
  target: string;
  type: string;
  strength: number;
  weak: boolean;
  label: string;
  evidenceIds: string[];
}
export interface GraphVM {
  nodes: GraphNodeVM[];
  edges: GraphEdgeVM[];
  rings: { ringId: string; ringScore: number; memberIds: string[] }[];
  truncated: boolean;
}
export type RingStatus = 'open' | 'under_review' | 'confirmed' | 'dismissed';
export interface RingVM {
  ringId: string;
  ringScore: number;
  band: Band;
  claimsCount: number;
  claimantsCount: number;
  shared: { type: string; label: string; count: number }[];
  totalClaimedAmount?: number;
  firstSeen?: string;
  lastSeen?: string;
  status: RingStatus | string;
  reasons: string[];
  synthetic: boolean;
}
export interface RingDetailVM extends RingVM {
  claims: { claimId: string; band?: Band; amount?: number; submittedAt?: string }[];
  timeline: { date: string; event: string }[];
  graph?: GraphVM;
  audit: { at?: string; actor?: string; action?: string; note?: string }[];
}
export interface ClaimNetworkVM {
  rings: { ringId: string; ringScore: number; band?: Band }[];
  sharedIdentifiers: { type: string; label: string; otherClaims: number }[];
  evidence: EvidenceVM[];
}

/* ---------- Analytics ---------- */
export interface AnalyticsSummaryVM {
  claimsToday: number;
  fastTracked: number;
  flagged: number;
  flaggedRate: number;
  topReasons: { id: string; title: string; count: number }[];
  sparkline: number[];
  openRings?: number;
}
export interface TrendsVM {
  daily: {
    date: string;
    low: number;
    medium: number;
    high: number;
    flaggedRate: number;
    avgRisk: number;
  }[];
  topSignals: { id: string; title: string; count: number }[];
  byType: { type: string; total: number; flagged: number }[];
  byModality: { modality: string; flagged: number }[];
  recycledWeekly: { week: string; count: number }[];
  ringsWeekly: { week: string; count: number }[];
  decisionsWeekly: { week: string; approved: number; rejected: number; requested: number }[];
  spike: { detected: boolean; message?: string };
}
