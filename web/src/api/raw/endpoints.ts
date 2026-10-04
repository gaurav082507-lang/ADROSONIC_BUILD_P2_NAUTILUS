import { api } from '../client';
import {
  analyticsSummarySchema,
  analyticsTrendsSchema,
  claimNetworkSchema,
  graphSchema,
  jobSchema,
  resultSchema,
  ringDetailSchema,
  ringListSchema,
  transcribeSchema,
} from '../schemas';
import type {
  ActionRaw,
  ClaimStatusRaw,
  ClaimSummaryRaw,
  DecisionDraftRaw,
  EvidenceTimelineRaw,
  HistoryRaw,
  JobRaw,
  LivenessSessionRaw,
  LoginRaw,
  PolicyRaw,
  QueueRaw,
  ResultRaw,
  TimelineRaw,
  UserRaw,
  AnalyticsSummaryRaw,
  AnalyticsTrendsRaw,
  ClaimNetworkRaw,
  GraphRaw,
  RingDetailRaw,
  RingListRaw,
  TranscribeRaw,
} from './types';

/** Builds a query string, skipping empty values. */
export function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value));
  });
  const text = search.toString();
  return text ? `?${text}` : '';
}
export const raw = {
  login: (email: string, password: string) =>
    api.post<LoginRaw>('/auth/login', { email, password }),
  me: () => api.get<{ user: UserRaw }>('/auth/me'),
  health: () => api.get<any>('/health'),
  analyze: (
    mode: 'image' | 'document' | 'claim',
    files: {
      file?: File;
      images?: File[];
      document?: File;
      idPhoto?: File;
      selfie?: File;
      metadata?: Record<string, unknown>;
    },
  ) => {
    const f = new FormData();
    if (mode === 'claim') {
      files.images?.forEach((x) => f.append('image', x));
      if (files.document) f.append('document', files.document);
      if (files.idPhoto) f.append('id_photo', files.idPhoto);
      if (files.selfie) f.append('selfie', files.selfie);
      if (files.metadata) f.append('metadata', JSON.stringify(files.metadata));
    } else if (files.file) f.append('file', files.file);
    return api.post<any>(`/analyze/${mode}`, f);
  },
  job: (id: string) => api.get<JobRaw>(`/jobs/${id}`, jobSchema as any),
  result: (id: string) => api.get<ResultRaw>(`/results/${id}`, resultSchema as any),
  evidence: (id: string, q = '') => api.get<any>(`/results/${id}/evidence${q}`),
  timeline: (id: string) => api.get<TimelineRaw>(`/results/${id}/timeline`),
  /** contract: page (1-based) + page_size */
  history: (params: { page?: number; pageSize?: number; mode?: string; band?: string } = {}) =>
    api.get<{ items: HistoryRaw[]; total: number }>(
      `/history${qs({ page: params.page ?? 1, page_size: params.pageSize ?? 20, mode: params.mode, band: params.band })}`,
    ),
  /** contract: band, type, status, q, limit, offset */
  queue: (
    params: {
      band?: string;
      type?: string;
      status?: string;
      q?: string;
      limit?: number;
      offset?: number;
    } = {},
  ) =>
    api.get<{ items: QueueRaw[]; total: number }>(
      `/queue${qs({ band: params.band, type: params.type, status: params.status, q: params.q, limit: params.limit ?? 50, offset: params.offset ?? 0 })}`,
    ),
  report: (id: string, format: 'pdf' | 'json') => api.get<Blob>(`/results/${id}/report.${format}`),
  deleteResult: (id: string) => api.del<void>(`/results/${id}`),
  decisionDraft: (id: string, input: { action: string; reasonCategory: string; note?: string }) =>
    api.post<DecisionDraftRaw>(`/results/${id}/decision/draft`, {
      action: input.action,
      reason_category: input.reasonCategory,
      investigator_note: input.note || null,
    }),
  /** contract: claimant_message (single text). EN/HI variants are sent as extra fields. */
  decision: (
    id: string,
    input: {
      action: string;
      reasonCategory: string;
      messageEn: string;
      messageHi: string;
      language?: 'en' | 'hi';
      internalNote?: string;
      slotsToResubmit?: string[];
    },
  ) =>
    api.post<any>(`/results/${id}/decision`, {
      action: input.action,
      reason_category: input.reasonCategory,
      claimant_message: input.language === 'hi' ? input.messageHi : input.messageEn,
      claimant_message_en: input.messageEn,
      claimant_message_hi: input.messageHi,
      internal_note: input.internalNote || null,
      slots_to_resubmit: input.slotsToResubmit ?? [],
    }),
  fastTrack: (id: string) => api.post<any>(`/claims/${id}/fast-track`, {}),
  undoFastTrack: (id: string) => api.post<any>(`/claims/${id}/fast-track/undo`, {}),
  actions: (id: string) => api.get<ActionRaw[]>(`/claims/${id}/actions`),
  entities: (id: string) => api.get<any>(`/claims/${id}/entities`),
  policies: () => api.get<PolicyRaw[]>('/policies/mine'),
  claimsMine: () => api.get<ClaimSummaryRaw[]>('/claims/mine'),
  claimStatus: (id: string) => api.get<ClaimStatusRaw>(`/claims/${id}/status`),
  claimTimeline: (id: string) => api.get<EvidenceTimelineRaw[]>(`/claims/${id}/evidence-timeline`),
  createClaim: (input: {
    policyId: string;
    claimType: string;
    peril: string;
    incidentDate: string;
    incidentTime: string;
    location: string;
    claimedAmount: string;
    damagedItems: string[];
    description: string;
    consent: boolean;
    evidence: Array<{ file: File; slot: string; captureSource: 'camera' | 'upload' }>;
    idPhoto?: File;
    idCaptureSource?: 'camera' | 'upload';
    selfie?: File;
    selfieCaptureSource?: 'camera' | 'upload';
    voiceAudio?: Blob;
    consentVoiceProcessing?: boolean;
    descriptionLang?: string;
    livenessSessionId?: string;
  }) => {
    const f = new FormData();
    f.append('policy_id', input.policyId);
    f.append('claim_type', input.claimType);
    f.append('peril', input.peril);
    f.append('incident_date', input.incidentDate);
    if (input.incidentTime) f.append('incident_time', input.incidentTime);
    if (input.location) f.append('location', input.location);
    f.append('claimed_amount', String(Number(input.claimedAmount || 0)));
    f.append('damaged_items', JSON.stringify(input.damagedItems));
    f.append('description_text', input.description);
    f.append('description_lang', input.descriptionLang ?? 'en');
    f.append('consent', String(input.consent));
    // contract: repeated `evidence` files + parallel slot_names / capture_sources (JSON arrays)
    input.evidence.forEach((x) => f.append('evidence', x.file, x.file.name));
    f.append('slot_names', JSON.stringify(input.evidence.map((x) => x.slot)));
    f.append('capture_sources', JSON.stringify(input.evidence.map((x) => x.captureSource)));
    f.append(
      'evidence_metadata',
      JSON.stringify(
        input.evidence.map((x) => ({
          filename: x.file.name,
          slot: x.slot,
          capture_source: x.captureSource,
        })),
      ),
    );
    if (input.idPhoto) {
      f.append('id_photo', input.idPhoto);
      f.append('id_capture_source', input.idCaptureSource ?? 'upload');
    }
    if (input.selfie) {
      f.append('selfie', input.selfie);
      f.append('selfie_capture_source', input.selfieCaptureSource ?? 'camera');
    }
    if (input.voiceAudio) {
      f.append('voice_audio', input.voiceAudio, 'statement.webm');
      f.append('consent_voice_processing', String(Boolean(input.consentVoiceProcessing)));
    }
    if (input.livenessSessionId) f.append('liveness_session_id', input.livenessSessionId);
    return api.post<{ claim_id?: string; id?: string; job_id?: string }>('/claims', f);
  },
  resubmit: (id: string, evidence: File[]) => {
    const f = new FormData();
    evidence.forEach((x) => f.append('evidence', x));
    return api.post<any>(`/claims/${id}/resubmit`, f);
  },
  livenessSession: () => api.post<LivenessSessionRaw>('/identity/liveness/session', {}),
  /** contract: session_id, nonce, frames (repeated), frame_metadata (JSON array aligned with frames) */
  livenessVerify: (input: {
    sessionId: string;
    nonce: string;
    frames: Array<{ frame: Blob; timestamp: number; challenge: string }>;
  }) => {
    const f = new FormData();
    f.append('session_id', input.sessionId);
    f.append('nonce', input.nonce);
    input.frames.forEach((x, i) => f.append('frames', x.frame, `frame-${i}.jpg`));
    f.append(
      'frame_metadata',
      JSON.stringify(
        input.frames.map((x, i) => ({ index: i, timestamp: x.timestamp, challenge: x.challenge })),
      ),
    );
    return api.post<{ passed?: boolean; best_frame?: string; reasons?: string[] }>(
      '/identity/liveness/verify',
      f,
    );
  },

  /* ---------- Voice (Prompt 9) ---------- */
  voiceLanguages: () => api.get<any>('/voice/languages'),
  /** contract: file + language (text allowed for translation-only) */
  voiceTranscribe: (audio: Blob, sourceLanguage: string) => {
    const f = new FormData();
    f.append('file', audio, 'statement.webm');
    f.append('language', sourceLanguage);
    return api.post<TranscribeRaw>('/voice/transcribe', f, transcribeSchema as any);
  },

  /* ---------- Network (Prompt 10) ---------- */
  networkGraph: (params: {
    focusType?: 'claim' | 'claimant' | 'ring';
    focusId?: string;
    hops?: number;
    minStrength?: number;
    limit?: number;
  }) =>
    api.get<GraphRaw>(
      `/network/graph${qs({
        focus_type: params.focusId ? params.focusType : undefined,
        focus_id: params.focusId,
        hops: params.hops ?? 2,
        min_strength: params.minStrength ?? 0.3,
        limit: params.limit ?? 300,
      })}`,
      graphSchema as any,
    ),
  rings: (params: { minScore?: number; status?: string; limit?: number; offset?: number } = {}) =>
    api.get<RingListRaw>(
      `/network/rings${qs({
        min_score: params.minScore,
        status: params.status,
        limit: params.limit ?? 50,
        offset: params.offset ?? 0,
      })}`,
      ringListSchema as any,
    ),
  ring: (ringId: string) =>
    api.get<RingDetailRaw>(`/network/rings/${encodeURIComponent(ringId)}`, ringDetailSchema as any),
  ringStatus: (ringId: string, status: string, note: string) =>
    api.post<any>(`/network/rings/${encodeURIComponent(ringId)}/status`, { status, note }),
  ringReport: (ringId: string, format: 'pdf' | 'json') =>
    api.get<Blob>(`/network/rings/${encodeURIComponent(ringId)}/report.${format}`),
  claimNetwork: (claimId: string) =>
    api.get<ClaimNetworkRaw>(
      `/claims/${encodeURIComponent(claimId)}/network`,
      claimNetworkSchema as any,
    ),

  /* ---------- Analytics (Prompt 10) ---------- */
  analyticsSummary: () =>
    api.get<AnalyticsSummaryRaw>('/analytics/summary', analyticsSummarySchema as any),
  analyticsTrends: (range: '7d' | '30d' | '90d', type?: string) =>
    api.get<AnalyticsTrendsRaw>(
      `/analytics/trends${qs({ range, type })}`,
      analyticsTrendsSchema as any,
    ),
  analyticsBusiness: (range: '7d' | '30d' | '90d' | 'all') =>
    api.get<any>(`/analytics/business${qs({ range })}`),
};
