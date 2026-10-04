import type {
  ActionVM,
  AnalyticsSummaryVM,
  Band,
  ClaimNetworkVM,
  ClaimStatusVM,
  ClaimSummaryVM,
  Confidence,
  EvidenceVM,
  ExtractedFieldsVM,
  GraphVM,
  HistoryRowVM,
  JobVM,
  LivenessSessionVM,
  NodeKind,
  PolicyVM,
  QueueRowVM,
  ResultVM,
  RingDetailVM,
  RingVM,
  ScoreVM,
  StoryVM,
  TranscriptionVM,
  TrendsVM,
  UserVM,
  VoiceLanguageVM,
  VoiceVM,
} from '../../types/vm';
import type {
  ActionRaw,
  AnalyticsSummaryRaw,
  AnalyticsTrendsRaw,
  ClaimNetworkRaw,
  ClaimStatusRaw,
  ClaimSummaryRaw,
  EvidenceRaw,
  EvidenceTimelineRaw,
  GraphRaw,
  HistoryRaw,
  JobRaw,
  LivenessSessionRaw,
  PolicyRaw,
  QueueRaw,
  ResultRaw,
  RingDetailRaw,
  RingRaw,
  StoryRaw,
  TimelineEventRaw,
  TimelineRaw,
  TranscribeRaw,
  UserRaw,
  VoiceExtractedRaw,
  VoiceLanguageRaw,
  VoiceRaw,
} from '../raw/types';

/* ---------- helpers ---------- */

/** Accepts either a bare array or a paginated {items: [...]} envelope. */
export function asList<T>(value: T[] | { items?: T[] } | null | undefined): T[] {
  if (Array.isArray(value)) return value;
  return value?.items ?? [];
}
const BANDS: Band[] = ['LOW', 'MEDIUM', 'HIGH'];
const CONFIDENCES: Confidence[] = ['high', 'medium', 'low'];
export const toBand = (v: unknown, risk?: number): Band => {
  const up = String(v ?? '').toUpperCase();
  if ((BANDS as string[]).includes(up)) return up as Band;
  const r = Number(risk ?? 0);
  return r >= 0.65 ? 'HIGH' : r >= 0.35 ? 'MEDIUM' : 'LOW';
};
const toConfidence = (v: unknown): Confidence => {
  const low = String(v ?? '').toLowerCase();
  return (CONFIDENCES as string[]).includes(low) ? (low as Confidence) : 'low';
};
const num = (v: unknown): number | undefined =>
  typeof v === 'number' && Number.isFinite(v)
    ? v
    : typeof v === 'string' && v.trim() !== '' && !Number.isNaN(Number(v))
      ? Number(v)
      : undefined;
const str = (v: unknown): string | undefined => (typeof v === 'string' && v ? v : undefined);
const rec = (v: unknown): Record<string, unknown> =>
  v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {};

/** Depth-first search for the first string URL whose key matches. */
function findUrl(obj: unknown, keyTest: (key: string) => boolean, depth = 0): string | undefined {
  if (!obj || typeof obj !== 'object' || depth > 3) return undefined;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (typeof v === 'string' && keyTest(k.toLowerCase())) return v;
  }
  for (const v of Object.values(obj as Record<string, unknown>)) {
    const hit = findUrl(v, keyTest, depth + 1);
    if (hit) return hit;
  }
  return undefined;
}

type ScoreLike = {
  risk?: number | null;
  band?: string | null;
  confidence?: string | null;
  status?: string | null;
};
export function score(value?: ScoreLike | null): ScoreVM {
  const risk = Number(value?.risk ?? 0);
  return {
    risk,
    band: toBand(value?.band, risk),
    confidence: toConfidence(value?.confidence),
    analysed:
      Boolean(value) &&
      value?.risk !== undefined &&
      value?.risk !== null &&
      value?.status !== 'not_analysed' &&
      value?.status !== 'not analysed',
  };
}
const optScore = (value?: ScoreLike | null) =>
  value && value.risk !== undefined && value.risk !== null ? score(value) : undefined;

/* ---------- auth ---------- */
export function adaptLogin(raw: {
  token?: string;
  access_token?: string;
  user?: UserRaw;
  role?: string;
  user_id?: string;
  name?: string;
}) {
  const user: UserVM = raw.user
    ? {
        id: raw.user.id,
        name: raw.user.name,
        email: raw.user.email,
        role: raw.user.role === 'claimant' ? 'claimant' : 'investigator',
        preferredLang: raw.user.preferred_lang,
      }
    : {
        id: raw.user_id ?? '',
        name: raw.name ?? '',
        email: '',
        role: raw.role === 'claimant' ? 'claimant' : 'investigator',
      };
  return { token: raw.token ?? raw.access_token ?? '', user };
}

/* ---------- jobs ---------- */
export function adaptJob(raw: JobRaw): JobVM {
  const err = raw.error;
  return {
    status: raw.status as JobVM['status'],
    steps: (raw.steps ?? []).map((step) => ({
      name: step.name,
      status: step.status,
      durationMs: step.duration_ms ?? undefined,
    })),
    resultId: raw.result_id ?? undefined,
    error: typeof err === 'string' ? err : (err?.message ?? undefined),
  };
}

/* ---------- evidence ---------- */
export function adaptEvidence(item: EvidenceRaw): EvidenceVM {
  const kind = (['risk', 'warning', 'info'] as const).includes(item.kind as never)
    ? (item.kind as EvidenceVM['kind'])
    : 'risk';
  const severity = (['low', 'medium', 'high'] as const).includes(item.severity as never)
    ? (item.severity as EvidenceVM['severity'])
    : 'low';
  return {
    id: item.id,
    title: item.title ?? item.id,
    reason: item.reason ?? '',
    kind,
    severity,
    score: num(item.calibrated_score) ?? num(item.score) ?? num(item.p) ?? num(item.raw_score),
    weight: num(item.effective_weight) ?? num(item.weight),
    contribution: num(item.contribution),
    contributionPct: num(item.contribution_pct),
    rank: num(item.rank),
    pipeline: (item.pipeline ?? undefined) as EvidenceVM['pipeline'],
    pipelineInput: item.pipeline_input ?? undefined,
    page: num(item.page) ?? num(item.bbox?.page),
    bbox: item.bbox ?? undefined,
    field: item.field ?? undefined,
  };
}

/* ---------- result ---------- */
const PIPELINES = ['image', 'document', 'identity', 'voice', 'claim'] as const;

function adaptArtifacts(a: Record<string, unknown> = {}): ResultVM['artifacts'] {
  const pagesRaw = (a.pages ?? a.document_pages ?? []) as unknown[];
  const pages = (Array.isArray(pagesRaw) ? pagesRaw : []).map((p, i) => {
    if (typeof p === 'string') return { page: i + 1, widthPt: 0, heightPt: 0, imageUrl: p };
    const o = rec(p);
    return {
      page: num(o.page) ?? i + 1,
      widthPt: num(o.width_pt) ?? 0,
      heightPt: num(o.height_pt) ?? 0,
      imageUrl: str(o.image_url) ?? str(o.url) ?? str(o.boxes_url) ?? '',
    };
  });
  const face = a.identity_face_comparison;
  const previews = Array.isArray(a.previews)
    ? (a.previews as unknown[]).filter((x): x is string => typeof x === 'string')
    : undefined;
  return {
    heatmap: str(a.heatmap) ?? str(a.image_heatmap) ?? findUrl(a, (k) => k.includes('heatmap')),
    overlay: str(a.overlay) ?? str(a.image_overlay) ?? findUrl(a, (k) => k.includes('overlay')),
    pages: pages.filter((p) => p.imageUrl),
    previews,
    identityFaceComparison:
      typeof face === 'string'
        ? { idFace: face }
        : face
          ? { idFace: str(rec(face).id_face), selfie: str(rec(face).selfie) }
          : undefined,
  };
}

function adaptWhy(raw: ResultRaw, evidence: EvidenceVM[]) {
  const pipelineOf = new Map(evidence.map((e) => [e.id, e.pipeline ?? 'overall']));
  const rows: ResultVM['whyThisScore'] = [];
  const formulas: ResultVM['whyDetail']['formulas'] = [];
  const overrides = new Set<string>();
  const gates: ResultVM['whyDetail']['gates'] = [];
  const why = raw.why_this_score as unknown;
  if (Array.isArray(why)) {
    // provisional flat shape
    for (const item of why as Array<Record<string, unknown>>) {
      rows.push({
        pipeline: String(item.pipeline ?? 'overall'),
        w: Number(item.w ?? 0),
        p: Number(item.p ?? 0),
        push: Number(item.push ?? 0),
        contributionPct: Number(item.contribution_pct ?? 0),
        evidenceId: str(item.evidence_id),
        title: str(item.title),
      });
    }
  } else if (why && typeof why === 'object') {
    const w = raw.why_this_score!;
    for (const key of PIPELINES) {
      const pw = w[key];
      if (!pw) continue;
      if (pw.formula) formulas.push({ pipeline: key, formula: pw.formula });
      (pw.overrides_applied ?? []).forEach((o) => overrides.add(o));
      (pw.quality_gates_applied ?? []).forEach((g) => gates.push(g));
      for (const c of pw.evidence_contributions ?? []) {
        rows.push({
          pipeline: key,
          w: c.w,
          p: c.p,
          push: c.push,
          contributionPct: c.contribution_pct,
          evidenceId: c.evidence_id,
          title: c.title,
        });
      }
    }
    if (w.overall?.formula) formulas.push({ pipeline: 'overall', formula: w.overall.formula });
    (w.overall?.overrides_applied ?? []).forEach((o) => overrides.add(o));
  }
  if (!rows.length) {
    const items = (raw.why_this_score?.items ?? raw.why_this_score_items ?? []) as Array<{
      evidence_id: string;
      title: string;
      w: number;
      p: number;
      push: number;
      contribution_pct: number;
    }>;
    for (const c of items) {
      rows.push({
        pipeline: String(pipelineOf.get(c.evidence_id) ?? 'overall'),
        w: c.w,
        p: c.p,
        push: c.push,
        contributionPct: c.contribution_pct,
        evidenceId: c.evidence_id,
        title: c.title,
      });
    }
  }
  return { rows, detail: { formulas, overrides: [...overrides], gates } };
}

function adaptIdentity(raw: ResultRaw, evidence: EvidenceRaw[]): ResultVM['identityDetails'] {
  const ident = raw.identity ?? undefined;
  const face = evidence.find((e) => e.id.startsWith('ID-FACE'));
  const selfieAi = evidence.find((e) => e.id === 'ID-DEEP-01' || e.id.startsWith('ID-AI'));
  const liveness = raw.liveness ?? undefined;
  const qr = raw.aadhaar_qr ?? undefined;
  if (!ident && !face && !liveness && !qr && !selfieAi) return undefined;
  const faceDetails = rec(face?.details);
  const similarity =
    num(ident?.similarity) ??
    num(faceDetails.similarity) ??
    num(faceDetails.cosine) ??
    num(rec(ident?.details).similarity);
  const challenges = liveness
    ? liveness.challenges.map((c) => ({ name: c.name, status: c.ok ? 'passed' : 'failed' }))
    : (ident?.liveness ?? []);
  const rows = qr?.comparisons.map((c) => ({
    field: c.field,
    printed: c.printed,
    signed: c.qr,
    match: c.match,
  }));
  return {
    similarity,
    verdict: ident?.verdict ?? face?.title ?? undefined,
    aiGeneratedSelfie:
      ident?.ai_generated_selfie ??
      (selfieAi
        ? `${Math.round(Number(selfieAi.calibrated_score ?? 0) * 100)}% likelihood · ${selfieAi.title ?? ''}`.trim()
        : undefined),
    livenessPerformed: liveness?.performed,
    livenessPassed: liveness?.passed,
    challenges,
    aadhaarQr: qr
      ? {
          printed: Object.fromEntries((rows ?? []).map((r) => [r.field, r.printed])),
          signed: Object.fromEntries((rows ?? []).map((r) => [r.field, r.signed])),
          mismatches: (rows ?? []).filter((r) => !r.match).map((r) => r.field),
          signatureStatus: !qr.found ? 'QR not found' : qr.signature_valid ? 'valid' : 'invalid',
          testKey: /test|demo/i.test(qr.mode ?? ''),
          photoSimilarity: qr.photo_similarity,
          rows,
        }
      : undefined,
  };
}

function adaptDuplicate(raw: ResultRaw, evidence: EvidenceRaw[]): ResultVM['duplicate'] {
  const legacy = (raw as unknown as { duplicate?: Record<string, unknown> }).duplicate;
  if (legacy)
    return {
      matchType: String(legacy.match_type ?? 'match'),
      similarity: Number(legacy.similarity ?? 0),
      earlierClaim: String(legacy.earlier_claim ?? '—'),
      thumbnailUrl: str(legacy.thumbnail_url),
    };
  const dup = evidence.find((e) => e.id.startsWith('IMG-DUP') && e.kind !== 'info');
  if (!dup) return undefined;
  const d = rec(dup.details);
  return {
    matchType: String(
      d.match_type ?? (dup.id === 'IMG-DUP-01' ? 'exact or resized copy' : 'near-duplicate'),
    ),
    similarity: num(d.similarity) ?? num(d.cosine) ?? num(dup.calibrated_score) ?? 0,
    earlierClaim: String(
      d.earlier_claim ??
        d.matched_claim_id ??
        d.match_claim_id ??
        d.claim_id ??
        d.matched_result_id ??
        '—',
    ),
    thumbnailUrl: str(d.thumbnail_url) ?? str(d.matched_thumbnail_url) ?? str(dup.artifact),
  };
}

export function adaptTimeline(
  raw: TimelineRaw | TimelineEventRaw[] | null | undefined,
): NonNullable<ResultVM['timeline']> {
  if (!raw) return [];
  const map = (e: TimelineEventRaw) => ({
    date: str(e.timestamp) ?? str(e.date),
    title: e.title ?? e.label ?? e.evidence_id ?? 'Event',
    detail: e.detail ?? e.source,
    ruleId: e.rule_id ?? undefined,
    contradiction: Boolean(e.contradiction),
  });
  if (Array.isArray(raw)) return raw.map(map);
  const events = (raw.events ?? []).map(map);
  const contradictions = (raw.contradictions ?? []).map((c) => ({
    date: undefined,
    title: `Contradiction${c.rule_id ? ` (${c.rule_id})` : ''}`,
    detail: c.reason ?? [c.from_event, c.to_event].filter(Boolean).join(' ↔ '),
    ruleId: c.rule_id,
    contradiction: true,
  }));
  const undated = (raw.undated ?? []).map((e) => ({ ...map(e), date: undefined }));
  return [...events, ...contradictions, ...undated];
}

function voiceSource(raw: ResultRaw, evidence: EvidenceRaw[]): VoiceRaw | undefined {
  if (raw.voice_details) return raw.voice_details;
  if (raw.voice && (raw.voice.transcript || raw.voice.translation_en)) return raw.voice;
  const art = rec(rec(raw.artifacts).voice);
  if (art.transcript || art.translation_en) return art as VoiceRaw;
  const ev = evidence.find(
    (e) => e.id.startsWith('VOI-') && (rec(e.details).transcript || rec(e.details).translation_en),
  );
  if (ev) return rec(ev.details) as VoiceRaw;
  const spoof = evidence.find((e) => e.id === 'VOI-SPOOF-01');
  if (raw.voice || spoof)
    return {
      status: spoof?.kind === 'info' ? 'uncalibrated (information only)' : 'analysed',
      spoof: spoof ? { probability: num(spoof.calibrated_score) } : undefined,
    };
  return undefined;
}

function adaptClaimChecks(raw: ResultRaw, evidence: EvidenceVM[]): ResultVM['claimChecks'] {
  const legacy = (raw as unknown as { claim_checks?: ResultVM['claimChecks'] }).claim_checks;
  if (legacy) return legacy;
  return evidence
    .filter(
      (e) =>
        e.id.startsWith('CLM-') && !e.id.startsWith('CLM-STORY') && !e.id.startsWith('CLM-NET'),
    )
    .map((e) => ({
      name: `${e.title} (${e.id})`,
      status: e.kind === 'info' ? ('skipped' as const) : ('flagged' as const),
      reason: e.reason,
    }));
}

export function adaptResult(raw: ResultRaw): ResultVM {
  const evidenceRaw = raw.evidence ?? [];
  const evidence = evidenceRaw.map(adaptEvidence);
  const why = adaptWhy(raw, evidence);
  const voiceRaw = voiceSource(raw, evidenceRaw);
  const checks = (raw.checks_run ?? raw.detector_status ?? []) as Array<{
    detector: string;
    status: string;
    duration_ms?: number | null;
    reason?: string | null;
    error?: string | null;
  }>;
  return {
    id: raw.id,
    claimId: raw.claim_id ?? undefined,
    createdAt: raw.created_at,
    mode: (['image', 'document', 'claim'].includes(raw.mode)
      ? raw.mode
      : 'claim') as ResultVM['mode'],
    overall: score(raw.overall),
    image: optScore(raw.image),
    document: optScore(raw.document),
    identity: optScore(raw.identity),
    claim: optScore(raw.claim),
    voice: optScore(raw.voice),
    summary: raw.overall?.summary || raw.summary || 'No summary returned.',
    recommendedAction: raw.recommended_action ?? 'Review the available evidence.',
    summarySource: raw.summary_source ?? undefined,
    topReasons: raw.top_reasons ?? [],
    qualityWarnings: (raw.quality_warnings ?? []).map((q) =>
      typeof q === 'string' ? q : q.message,
    ),
    evidence,
    imageResults: (raw.image_results ?? []).map((r, i) => {
      const o = rec(r);
      return {
        label:
          str(o.label) ??
          `Image ${i + 1}${num(o.risk) !== undefined ? ` · ${Math.round(Number(o.risk) * 100)}%` : ''}`,
        url: str(o.url),
      };
    }),
    artifacts: adaptArtifacts(raw.artifacts),
    whyThisScore: why.rows,
    whyDetail: why.detail,
    checksRun: checks.map((item) => ({
      detector: item.detector,
      status: (['ok', 'skipped', 'failed'].includes(item.status) ? item.status : 'failed') as
        'ok' | 'skipped' | 'failed',
      durationMs: item.duration_ms ?? undefined,
      reason: item.reason ?? item.error ?? undefined,
    })),
    duplicate: adaptDuplicate(raw, evidenceRaw),
    location: raw.location
      ? {
          claimed: raw.location.claimed ?? undefined,
          photos: (raw.location.photos ?? []).map((photo) => ({
            lat: photo.lat,
            lng: photo.lng,
            distanceKm: photo.distance_km,
          })),
          maxDistanceKm: raw.location.max_distance_km ?? undefined,
        }
      : undefined,
    identityDetails: adaptIdentity(raw, evidenceRaw),
    claimChecks: adaptClaimChecks(raw, evidence),
    timeline: raw.timeline ? adaptTimeline(raw.timeline as TimelineRaw) : undefined,
    voiceDetails: voiceRaw ? adaptVoice(voiceRaw) : undefined,
    story: raw.story ? adaptStory(raw.story) : undefined,
    decision: raw.decision
      ? {
          status: raw.decision.status,
          by: raw.decision.by,
          at: raw.decision.at,
          reasonCode: raw.decision.reason_code,
          claimantMessage: raw.decision.claimant_message,
        }
      : undefined,
    links: (raw.links ?? []).map((l) => ({ resultId: l.result_id, reason: l.reason })),
  };
}

/* ---------- lists ---------- */
type Legacy = Record<string, unknown>;
export const adaptQueue = (rows: QueueRaw[] | { items?: QueueRaw[] }): QueueRowVM[] =>
  asList(rows).map((row) => {
    const r = row as QueueRaw & Legacy;
    const id = String(r.claim_id ?? r.id ?? '');
    const risk = Number(r.overall_risk ?? r.risk ?? 0);
    return {
      id,
      resultId: String(r.result_id ?? r.id ?? id),
      claimantMasked: String(r.claimant_name ?? r.claimant_masked ?? '—'),
      type: String(r.type ?? '—'),
      submitted: String(r.submitted_at ?? r.submitted ?? '—'),
      band: toBand(r.band, risk),
      risk,
      topReason: String(r.top_reason ?? '—'),
      status: String(r.status ?? '—'),
      eligibleFastTrack: Boolean(r.can_fast_track ?? r.eligible_fast_track),
    };
  });

export const adaptHistory = (rows: HistoryRaw[] | { items?: HistoryRaw[] }): HistoryRowVM[] =>
  asList(rows).map((row) => {
    const r = row as HistoryRaw & Legacy;
    const risk = Number(r.overall_risk ?? r.risk ?? 0);
    return {
      id: String(r.id),
      date: String(r.created_at ?? r.date ?? ''),
      mode: String(r.mode ?? ''),
      fileNames: (r.file_names as string[] | undefined) ?? [],
      band: toBand(r.overall_band ?? r.band, risk),
      risk,
      topReason: str(r.top_reason),
      evidenceCount: num(r.evidence_count),
      thumbnailUrl: str(r.thumbnail_url),
    };
  });

export const adaptPolicies = (rows: PolicyRaw[] | { items?: PolicyRaw[] }): PolicyVM[] =>
  asList(rows).map((row) => {
    const r = row as PolicyRaw & Legacy;
    return {
      id: String(r.id ?? r.policy_number),
      policyNumber: String(r.policy_number),
      claimType: String(r.claim_type),
      asset: String(r.vehicle_or_asset ?? r.asset ?? ''),
      validFrom: String(r.start_date ?? r.valid_from ?? ''),
      validTo: String(r.end_date ?? r.valid_to ?? ''),
      sumInsured: num(r.sum_insured),
    };
  });

export const adaptClaimsMine = (
  rows: ClaimSummaryRaw[] | { items?: ClaimSummaryRaw[] },
): ClaimSummaryVM[] =>
  asList(rows).map((row) => {
    const r = row as ClaimSummaryRaw & Legacy;
    return {
      id: String(r.claim_id ?? r.id),
      policyLabel: String(r.policy_label ?? ''),
      claimType: String(r.claim_type ?? r.type ?? ''),
      submittedAt: String(r.submitted_at ?? r.submitted ?? ''),
      status: String(r.status ?? ''),
      lastUpdate: str(r.last_update),
    };
  });

export function adaptClaimStatus(
  raw: ClaimStatusRaw | Legacy,
  evidence: EvidenceTimelineRaw[] = [],
): ClaimStatusVM {
  const r = raw as ClaimStatusRaw & Legacy;
  const d = r.decision ?? undefined;
  const legacyEvidence = (r.evidence as Array<{ slot: string; status: string }> | undefined) ?? [];
  return {
    id: String(r.claim_id ?? r.id ?? ''),
    status: String(r.status ?? ''),
    message: d?.claimant_message ?? str(r.message),
    outcome: d?.outcome,
    reasonLabel: d?.reason_category_label,
    canResubmit: Boolean(d?.can_resubmit),
    slotsToResubmit: d?.slots_to_resubmit ?? [],
    nextSteps: d?.next_steps ?? (r.next_steps as string[] | undefined) ?? [],
    evidence: evidence.length
      ? evidence.map((e) => ({
          slot: e.slot,
          status: e.state,
          label: e.file_label,
          updatedAt: e.updated_at,
        }))
      : legacyEvidence,
    timeline: (r.timeline ?? []).map((t: Record<string, unknown>) => ({
      status: String(t.name ?? t.status ?? ''),
      date: str(t.date),
      detail: t.name ? str(t.status) : str(t.detail),
    })),
  };
}

export const adaptActions = (rows: ActionRaw[] | { items?: ActionRaw[] }): ActionVM[] =>
  asList(rows).map((row) => {
    const r = row as ActionRaw & Legacy;
    const transition =
      r.from_status || r.to_status ? ` (${r.from_status ?? '—'} → ${r.to_status ?? '—'})` : '';
    return {
      at: String(r.created_at ?? r.at ?? ''),
      actor: String(r.actor ?? ''),
      action: `${String(r.action ?? '')}${transition}`,
      note: str(r.internal_note) ?? str(r.note),
    };
  });

export function adaptLivenessSession(raw: LivenessSessionRaw): LivenessSessionVM {
  return {
    sessionId: raw.session_id,
    nonce: raw.nonce,
    challenges: raw.challenges ?? [],
    spokenCode: raw.spoken_code,
    expiresAt: raw.expires_at,
  };
}

/* ---------- Voice ---------- */
export function adaptExtracted(raw?: VoiceExtractedRaw): ExtractedFieldsVM {
  return {
    incidentType: raw?.incident_type ?? undefined,
    peril: raw?.peril ?? undefined,
    vehicleRegistration: raw?.vehicle_registration ?? undefined,
    incidentDate: raw?.incident_date ?? undefined,
    incidentTime: raw?.incident_time ?? undefined,
    amount: raw?.amount_claimed ?? raw?.amount ?? undefined,
    damagedItems: raw?.damaged_items ?? [],
    locationText: raw?.location_text ?? undefined,
  };
}
export function adaptVoice(raw: VoiceRaw): VoiceVM {
  return {
    language: raw.language,
    durationS: raw.duration_s,
    transcript: raw.transcript,
    translationEn: raw.translation_en,
    extracted: adaptExtracted(raw.extracted),
    spoof: raw.spoof
      ? {
          probability: raw.spoof.probability,
          band: raw.spoof.band,
          segments: (raw.spoof.segments ?? []).map((x) => ({
            startS: x.start_s,
            endS: x.end_s,
            score: x.score,
          })),
        }
      : undefined,
    status: raw.status,
  };
}
export function adaptTranscription(raw: TranscribeRaw): TranscriptionVM {
  return {
    language: raw.language,
    transcript: raw.transcript ?? '',
    translationEn: raw.translation_en ?? '',
    extracted: adaptExtracted(raw.extracted),
  };
}
export function adaptLanguages(
  raw: VoiceLanguageRaw[] | { items?: VoiceLanguageRaw[]; languages?: VoiceLanguageRaw[] },
): VoiceLanguageVM[] {
  const list = Array.isArray(raw) ? raw : (raw.languages ?? raw.items ?? []);
  return list.map((x) => {
    const native = x.native ?? x.native_name;
    return { code: x.code, label: native && x.name ? `${x.name} · ${native}` : (x.name ?? x.code) };
  });
}

/* ---------- Story ---------- */
export function adaptStory(raw: StoryRaw): StoryVM {
  return {
    contradictions: (raw.contradictions ?? []).map((x) =>
      typeof x === 'string'
        ? { text: x, sources: [], evidenceIds: [] }
        : {
            text: x.text ?? x.reason ?? '',
            sources: x.sources ?? [],
            evidenceIds: x.evidence_ids ?? [],
          },
    ),
    consistentPoints: (raw.consistent_points ?? []).map((x) =>
      typeof x === 'string' ? x : (x.text ?? ''),
    ),
    source: raw.source ?? 'rules',
    note: raw.note ?? 'For investigator review, not part of the score',
  };
}

/* ---------- Network ---------- */
const KNOWN_KINDS: NodeKind[] = ['claim', 'claimant', 'identifier', 'ring'];
const WEAK_EDGE_MAX = 0.3;
export function adaptGraph(raw: GraphRaw): GraphVM {
  const ids = new Set(raw.nodes.map((n) => n.id));
  return {
    nodes: raw.nodes.map((n) => ({
      id: n.id,
      kind: (KNOWN_KINDS as string[]).includes(n.type) ? (n.type as NodeKind) : 'other',
      label: n.label,
      band: n.band,
      risk: n.risk,
      flags: n.flags ?? [],
      synthetic: n.data_source === 'synthetic_history',
    })),
    // Drop edges that point at nodes outside a truncated subgraph.
    edges: raw.edges
      .filter((e) => ids.has(e.source) && ids.has(e.target))
      .map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.type,
        strength: e.strength,
        weak: e.strength <= WEAK_EDGE_MAX,
        label: e.label ?? e.type,
        evidenceIds: e.evidence_ids ?? [],
      })),
    rings: (raw.rings ?? []).map((r) => ({
      ringId: r.ring_id,
      ringScore: r.ring_score,
      memberIds: r.member_ids,
    })),
    truncated: Boolean(raw.truncated),
  };
}
const bandFromScore = (value: number) =>
  value >= 0.65 ? 'HIGH' : value >= 0.35 ? 'MEDIUM' : 'LOW';
export function adaptRing(raw: RingRaw): RingVM {
  return {
    ringId: raw.ring_id,
    ringScore: raw.ring_score,
    band: raw.band ?? bandFromScore(raw.ring_score),
    claimsCount: raw.claims_count,
    claimantsCount: raw.claimants_count,
    shared: raw.shared ?? [],
    totalClaimedAmount: raw.total_claimed_amount,
    firstSeen: raw.first_seen,
    lastSeen: raw.last_seen,
    status: raw.status,
    reasons: raw.reasons ?? [],
    synthetic: raw.data_source === 'synthetic_history',
  };
}
export const adaptRings = (raw: { items?: RingRaw[] } | RingRaw[]) => asList(raw).map(adaptRing);
export function adaptRingDetail(raw: RingDetailRaw): RingDetailVM {
  return {
    ...adaptRing(raw),
    claims: (raw.claims ?? []).map((c) => ({
      claimId: c.claim_id,
      band: c.band,
      amount: c.amount,
      submittedAt: c.submitted_at,
    })),
    timeline: raw.timeline ?? [],
    graph: raw.graph ? adaptGraph(raw.graph) : undefined,
    audit: raw.audit ?? [],
  };
}
export function adaptClaimNetwork(raw: ClaimNetworkRaw): ClaimNetworkVM {
  return {
    rings: (raw.rings ?? []).map((r) => ({
      ringId: r.ring_id,
      ringScore: r.ring_score,
      band: r.band,
    })),
    sharedIdentifiers: (raw.shared_identifiers ?? []).map((s) => ({
      type: s.type,
      label: s.label,
      otherClaims: s.other_claims,
    })),
    evidence: (raw.evidence ?? []).map(adaptEvidence),
  };
}

/* ---------- Analytics ---------- */
export function adaptSummary(raw: AnalyticsSummaryRaw): AnalyticsSummaryVM {
  return {
    claimsToday: raw.claims_today,
    fastTracked: raw.fast_tracked,
    flagged: raw.flagged,
    flaggedRate: raw.flagged_rate,
    topReasons: raw.top_reasons ?? [],
    sparkline: raw.sparkline_7d ?? [],
    openRings: raw.open_rings,
  };
}
export function adaptTrends(raw: AnalyticsTrendsRaw): TrendsVM {
  return {
    daily: raw.daily.map((d) => ({
      date: d.date,
      low: d.low,
      medium: d.medium,
      high: d.high,
      flaggedRate: d.flagged_rate,
      avgRisk: d.avg_risk,
    })),
    topSignals: raw.top_signals ?? [],
    byType: raw.by_type ?? [],
    byModality: raw.by_modality ?? [],
    recycledWeekly: raw.recycled_evidence_weekly ?? [],
    ringsWeekly: raw.rings_weekly ?? [],
    decisionsWeekly: raw.decisions_weekly ?? [],
    spike: raw.spike ?? { detected: false },
  };
}
