/*
 * Raw backend shapes. Wherever the OpenAPI contract defines a schema, the type is taken from
 * the GENERATED file (src/api/generated.d.ts, produced by `npm run gen:api`), so any backend
 * change becomes a compile error here and in the adapters – nowhere else.
 * Blocks the contract leaves untyped (artifacts, location, identity, network, analytics) are
 * described below and handled defensively in the adapters.
 */
import type { components } from '../generated';

type S = components['schemas'];

export interface ApiErrorShape {
  error: { code: string; message: string; details?: unknown };
}

export type JobRaw = Omit<S['JobStatus'], 'error'> & {
  error?: string | { code?: string; message?: string } | null;
};
export type PipelineRaw = S['PipelineScore'];
export type EvidenceRaw = Omit<S['Evidence'], 'details'> & {
  details?: Record<string, unknown> | null;
  /** legacy/provisional aliases */
  p?: number;
  score?: number;
};
export type LivenessRaw = S['LivenessStatus'];
export type AadhaarQrRaw = S['AadhaarQrStatus'];
export type WhyThisScoreRaw = S['WhyThisScore'];
export type WhyItemRaw = S['WhyThisScoreItem'];

/** `identity` is untyped in the contract: it may be a PipelineScore and/or carry face details. */
export interface IdentityRaw extends Partial<PipelineRaw> {
  similarity?: number;
  verdict?: string;
  ai_generated_selfie?: string;
  liveness?: Array<{ name: string; status: string }>;
  details?: Record<string, unknown>;
}
export interface LocationRaw {
  claimed?: { lat: number; lng: number; text?: string } | null;
  photos?: Array<{ lat: number; lng: number; distance_km?: number; image?: string }>;
  max_distance_km?: number | null;
}
export interface TimelineEventRaw {
  id?: string;
  timestamp?: string | null;
  date?: string | null;
  label?: string;
  title?: string;
  source?: string;
  detail?: string;
  evidence_id?: string | null;
  rule_id?: string | null;
  contradiction?: boolean;
}
export interface TimelineRaw {
  events?: TimelineEventRaw[];
  contradictions?: Array<{
    from_event?: string;
    to_event?: string;
    rule_id?: string;
    reason?: string;
  }>;
  undated?: TimelineEventRaw[];
}

export type ResultRaw = Omit<
  S['AnalysisResult'],
  'artifacts' | 'location' | 'identity' | 'voice' | 'story' | 'evidence' | 'quality_warnings'
> & {
  artifacts?: Record<string, unknown>;
  location?: LocationRaw | null;
  identity?: IdentityRaw | null;
  voice?: (Partial<PipelineRaw> & VoiceRaw) | null;
  story?: StoryRaw | null;
  evidence: EvidenceRaw[];
  quality_warnings: Array<S['QualityWarning'] | string>;
  /** additive fields requested from the backend (may be absent) */
  claim_id?: string | null;
  voice_details?: VoiceRaw | null;
  timeline?: TimelineEventRaw[] | TimelineRaw | null;
  summary?: string;
};

export type QueueRaw = S['QueueItem'] & { result_id?: string | null };
export type HistoryRaw = S['HistoryItem'] & { file_names?: string[] };
export type PolicyRaw = S['PolicyItem'];
export type ClaimSummaryRaw = S['ClaimantClaimSummary'];
export type ClaimStatusRaw = S['ClaimantStatusResponse'];
export type EvidenceTimelineRaw = S['ClaimantEvidenceTimelineItem'];
export type ActionRaw = S['ActionItem'];
export type LoginRaw = S['LoginResponse'];
export type UserRaw = S['UserProfile'];
export type LivenessSessionRaw = S['LivenessSessionResponse'];
export type DecisionDraftRaw = S['DecisionDraftResponse'];

/* ---------- Voice (Prompt 9) ---------- */
export interface VoiceExtractedRaw {
  incident_type?: string | null;
  peril?: string | null;
  incident_date?: string | null;
  incident_time?: string | null;
  location_text?: string | null;
  vehicle_registration?: string | null;
  damaged_items?: string[];
  amount_claimed?: number | null;
  /** provisional alias */
  amount?: number | null;
}
export interface VoiceRaw {
  language?: string;
  duration_s?: number;
  transcript?: string;
  translation_en?: string;
  extracted?: VoiceExtractedRaw;
  spoof?: {
    probability?: number;
    band?: 'LOW' | 'MEDIUM' | 'HIGH';
    segments?: Array<{ start_s: number; end_s: number; score?: number }>;
  };
  quality?: Record<string, unknown>;
  status?: string;
}
export interface TranscribeRaw {
  language: string;
  duration_s?: number;
  transcript?: string;
  translation_en?: string;
  extracted?: VoiceExtractedRaw;
  source?: string;
  quality?: Record<string, unknown>;
}
export interface VoiceLanguageRaw {
  code: string;
  name?: string;
  native?: string;
  /** provisional alias */
  native_name?: string;
}

/* ---------- Story review (Prompt 10) ---------- */
export interface StoryRaw {
  contradictions?: Array<
    string | { text?: string; reason?: string; sources?: string[]; evidence_ids?: string[] }
  >;
  consistent_points?: Array<string | { text?: string }>;
  source?: 'rules' | 'llm' | string;
  note?: string;
}

/* ---------- Network (Prompt 10) ---------- */
export type DataSource = 'live' | 'synthetic_history' | string;
export interface GraphNodeRaw {
  id: string;
  type: 'claim' | 'claimant' | 'identifier' | 'ring' | string;
  label: string;
  band?: 'LOW' | 'MEDIUM' | 'HIGH';
  risk?: number;
  flags?: string[];
  data_source?: DataSource;
}
export interface GraphEdgeRaw {
  id: string;
  source: string;
  target: string;
  type: string;
  strength: number;
  label?: string;
  evidence_ids?: string[];
}
export interface GraphRaw {
  nodes: GraphNodeRaw[];
  edges: GraphEdgeRaw[];
  rings?: Array<{ ring_id: string; ring_score: number; member_ids: string[] }>;
  truncated?: boolean;
}
export interface RingRaw {
  ring_id: string;
  ring_score: number;
  band?: 'LOW' | 'MEDIUM' | 'HIGH';
  claims_count: number;
  claimants_count: number;
  shared?: Array<{ type: string; label: string; count: number }>;
  total_claimed_amount?: number;
  first_seen?: string;
  last_seen?: string;
  status: 'open' | 'under_review' | 'confirmed' | 'dismissed' | string;
  reasons?: string[];
  data_source?: DataSource;
}
export interface RingListRaw {
  items: RingRaw[];
  total: number;
}
export interface RingDetailRaw extends RingRaw {
  claims?: Array<{
    claim_id: string;
    band?: 'LOW' | 'MEDIUM' | 'HIGH';
    amount?: number;
    submitted_at?: string;
  }>;
  timeline?: Array<{ date: string; event: string }>;
  graph?: GraphRaw;
  audit?: Array<{ at?: string; actor?: string; action?: string; note?: string }>;
}
export interface ClaimNetworkRaw {
  rings?: Array<{ ring_id: string; ring_score: number; band?: 'LOW' | 'MEDIUM' | 'HIGH' }>;
  shared_identifiers?: Array<{ type: string; label: string; other_claims: number }>;
  evidence?: EvidenceRaw[];
}

/* ---------- Analytics (Prompt 10) ---------- */
export interface AnalyticsSummaryRaw {
  claims_today: number;
  fast_tracked: number;
  flagged: number;
  flagged_rate: number;
  top_reasons?: Array<{ id: string; title: string; count: number }>;
  sparkline_7d?: number[];
  open_rings?: number;
}
export interface AnalyticsTrendsRaw {
  daily: Array<{
    date: string;
    low: number;
    medium: number;
    high: number;
    flagged_rate: number;
    avg_risk: number;
  }>;
  top_signals?: Array<{ id: string; title: string; count: number }>;
  by_type?: Array<{ type: string; total: number; flagged: number }>;
  by_modality?: Array<{ modality: string; flagged: number }>;
  recycled_evidence_weekly?: Array<{ week: string; count: number }>;
  rings_weekly?: Array<{ week: string; count: number }>;
  decisions_weekly?: Array<{ week: string; approved: number; rejected: number; requested: number }>;
  spike?: { detected: boolean; message?: string };
}
