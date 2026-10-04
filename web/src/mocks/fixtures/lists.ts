/* PROVISIONAL list fixtures in the REAL backend shapes (QueueItem, HistoryItem, PolicyItem, …). */
import type {
  ActionRaw,
  ClaimStatusRaw,
  ClaimSummaryRaw,
  EvidenceTimelineRaw,
  HistoryRaw,
  PolicyRaw,
  QueueRaw,
} from '../../api/raw/types';

export const queue: QueueRaw[] = [
  {
    claim_id: 'CLM-DEMO-HIGH',
    result_id: 'RES-DEMO-HIGH',
    claimant_name: 'R•••• K••••',
    type: 'motor',
    submitted_at: '2026-10-03T08:05:00Z',
    band: 'HIGH',
    overall_risk: 0.88,
    top_reason: 'AI-generated image patterns',
    status: 'under_review',
    can_fast_track: false,
  },
  {
    claim_id: 'CLM-1039',
    result_id: 'RES-DEMO-MEDIUM',
    claimant_name: 'A•••• V••••',
    type: 'health',
    submitted_at: '2026-10-02T15:40:00Z',
    band: 'MEDIUM',
    overall_risk: 0.54,
    top_reason: 'Font differs within the amounts column',
    status: 'needs_evidence',
    can_fast_track: false,
  },
  {
    claim_id: 'CLM-1038',
    result_id: 'RES-DEMO-LOW',
    claimant_name: 'S•••• P••••',
    type: 'property',
    submitted_at: '2026-10-03T09:12:00Z',
    band: 'LOW',
    overall_risk: 0.12,
    top_reason: 'No material signals',
    status: 'under_review',
    can_fast_track: true,
  },
];

export const history: HistoryRaw[] = [
  {
    id: 'RES-DEMO-HIGH',
    created_at: '2026-10-03T08:05:00Z',
    mode: 'claim',
    overall_risk: 0.88,
    overall_band: 'HIGH',
    thumbnail_url: null,
    evidence_count: 8,
    top_reason: 'AI-generated image patterns',
  },
  {
    id: 'RES-DEMO-LOW',
    created_at: '2026-10-03T09:12:00Z',
    mode: 'image',
    overall_risk: 0.12,
    overall_band: 'LOW',
    thumbnail_url: null,
    evidence_count: 1,
    top_reason: 'No material signals',
  },
  {
    id: 'RES-DEMO-MEDIUM',
    created_at: '2026-10-02T15:40:00Z',
    mode: 'document',
    overall_risk: 0.54,
    overall_band: 'MEDIUM',
    thumbnail_url: null,
    evidence_count: 2,
    top_reason: 'Font differs within the amounts column',
  },
];

export const policies: PolicyRaw[] = [
  {
    policy_number: 'MTR/2026/1001',
    claim_type: 'motor',
    sum_insured: 800000,
    start_date: '2026-01-01',
    end_date: '2026-12-31',
    vehicle_or_asset: 'Hyundai Creta · JH01AB1234',
    details: null,
  },
  {
    policy_number: 'PRP/2026/2002',
    claim_type: 'property',
    sum_insured: 2500000,
    start_date: '2026-01-01',
    end_date: '2026-12-31',
    vehicle_or_asset: 'Residential property · Ranchi',
    details: null,
  },
];

export const claimsMine: ClaimSummaryRaw[] = [
  {
    claim_id: 'CLM-DEMO-CLAIMANT',
    policy_label: 'MTR/2026/1001 · Hyundai Creta',
    claim_type: 'motor',
    submitted_at: '2026-10-03T08:05:00Z',
    status: 'needs_evidence',
    last_update: '2026-10-03T12:30:00Z',
  },
];

export const claimStatus: ClaimStatusRaw = {
  claim_id: 'CLM-DEMO-CLAIMANT',
  status: 'needs_evidence',
  timeline: [
    { name: 'Submitted', status: 'done', date: '2026-10-03T08:05:00Z' },
    { name: 'Under review', status: 'done', date: '2026-10-03T08:06:00Z' },
    { name: 'More information needed', status: 'current', date: '2026-10-03T12:30:00Z' },
  ],
  decision: {
    outcome: 'needs_evidence',
    reason_category_label: 'Photo clarity check',
    claimant_message:
      'The photo of the damaged area is not clear enough. Please upload a new close-up photo taken in daylight.',
    next_steps: ['Take a close-up photo of the damage in daylight', 'Upload it below'],
    can_resubmit: true,
    slots_to_resubmit: ['damage_closeup'],
  },
};

export const evidenceTimeline: EvidenceTimelineRaw[] = [
  {
    slot: 'full_vehicle',
    file_label: 'Full vehicle photo',
    state: 'checked',
    updated_at: '2026-10-03T08:06:00Z',
  },
  {
    slot: 'damage_closeup',
    file_label: 'Damage close-up',
    state: 'needs_replacing',
    updated_at: '2026-10-03T12:30:00Z',
  },
  {
    slot: 'repair_estimate',
    file_label: 'Repair estimate',
    state: 'checked',
    updated_at: '2026-10-03T08:06:00Z',
  },
];

export const actions: ActionRaw[] = [
  {
    id: 1,
    claim_id: 'CLM-DEMO-HIGH',
    result_id: 'RES-DEMO-HIGH',
    actor: 'system',
    action: 'analysis_completed',
    from_status: 'submitted',
    to_status: 'under_review',
    reason_category: null,
    claimant_message: null,
    internal_note: null,
    slots_to_resubmit: [],
    created_at: '2026-10-03T08:06:00Z',
  },
];
