import type {
  AnalyticsSummaryRaw,
  AnalyticsTrendsRaw,
  ClaimNetworkRaw,
  GraphRaw,
  RingDetailRaw,
  RingRaw,
} from '../../api/raw/types';
import { ev } from './results';

/*
 * PROVISIONAL – replace with contract/fixtures via `npm run fixtures:sync`.
 * Scenarios: (a) a ring of 3 claimants sharing one bank account + a reused damage photo;
 * (b) two claimants sharing only the same garage (weak link, NOT a ring); (c) a clean claim.
 */
export const graph: GraphRaw = {
  nodes: [
    {
      id: 'CLM-DEMO-HIGH',
      type: 'claim',
      label: 'CLM-DEMO-HIGH',
      band: 'HIGH',
      risk: 0.88,
      flags: ['ring'],
      data_source: 'live',
    },
    {
      id: 'CLM-R2',
      type: 'claim',
      label: 'CLM-R2',
      band: 'HIGH',
      risk: 0.74,
      flags: ['ring'],
      data_source: 'live',
    },
    {
      id: 'CLM-R3',
      type: 'claim',
      label: 'CLM-R3',
      band: 'MEDIUM',
      risk: 0.52,
      flags: ['ring'],
      data_source: 'live',
    },
    {
      id: 'CLM-G1',
      type: 'claim',
      label: 'CLM-G1',
      band: 'LOW',
      risk: 0.12,
      flags: [],
      data_source: 'live',
    },
    {
      id: 'CLM-G2',
      type: 'claim',
      label: 'CLM-G2',
      band: 'LOW',
      risk: 0.09,
      flags: [],
      data_source: 'live',
    },
    { id: 'CLT-A', type: 'claimant', label: 'Claimant A.K.', data_source: 'live' },
    { id: 'CLT-B', type: 'claimant', label: 'Claimant S.M.', data_source: 'live' },
    { id: 'CLT-C', type: 'claimant', label: 'Claimant R.P.', data_source: 'live' },
    { id: 'CLT-D', type: 'claimant', label: 'Claimant N.T.', data_source: 'live' },
    { id: 'CLT-E', type: 'claimant', label: 'Claimant V.S.', data_source: 'live' },
    { id: 'ID-BANK-4417', type: 'identifier', label: 'Bank ****4417', data_source: 'live' },
    { id: 'ID-IMG-07', type: 'identifier', label: 'Damage photo cluster #07', data_source: 'live' },
    { id: 'ID-GARAGE-12', type: 'identifier', label: 'Garage: City Motors', data_source: 'live' },
  ],
  edges: [
    {
      id: 'e1',
      source: 'CLM-DEMO-HIGH',
      target: 'CLT-A',
      type: 'filed_by',
      strength: 1,
      label: 'filed by',
    },
    {
      id: 'e2',
      source: 'CLM-R2',
      target: 'CLT-B',
      type: 'filed_by',
      strength: 1,
      label: 'filed by',
    },
    {
      id: 'e3',
      source: 'CLM-R3',
      target: 'CLT-C',
      type: 'filed_by',
      strength: 1,
      label: 'filed by',
    },
    {
      id: 'e4',
      source: 'CLM-G1',
      target: 'CLT-D',
      type: 'filed_by',
      strength: 1,
      label: 'filed by',
    },
    {
      id: 'e5',
      source: 'CLM-G2',
      target: 'CLT-E',
      type: 'filed_by',
      strength: 1,
      label: 'filed by',
    },
    {
      id: 'e6',
      source: 'CLM-DEMO-HIGH',
      target: 'ID-BANK-4417',
      type: 'bank',
      strength: 1,
      label: 'same bank account',
      evidence_ids: ['CLM-NET-01'],
    },
    {
      id: 'e7',
      source: 'CLM-R2',
      target: 'ID-BANK-4417',
      type: 'bank',
      strength: 1,
      label: 'same bank account',
      evidence_ids: ['CLM-NET-01'],
    },
    {
      id: 'e8',
      source: 'CLM-R3',
      target: 'ID-BANK-4417',
      type: 'bank',
      strength: 1,
      label: 'same bank account',
      evidence_ids: ['CLM-NET-01'],
    },
    {
      id: 'e9',
      source: 'CLM-DEMO-HIGH',
      target: 'ID-IMG-07',
      type: 'image_cluster',
      strength: 1,
      label: 'reused damage photo',
      evidence_ids: ['IMG-DUP-01'],
    },
    {
      id: 'e10',
      source: 'CLM-R2',
      target: 'ID-IMG-07',
      type: 'image_cluster',
      strength: 1,
      label: 'reused damage photo',
      evidence_ids: ['IMG-DUP-01'],
    },
    {
      id: 'e11',
      source: 'CLM-G1',
      target: 'ID-GARAGE-12',
      type: 'provider',
      strength: 0.3,
      label: 'same garage',
    },
    {
      id: 'e12',
      source: 'CLM-G2',
      target: 'ID-GARAGE-12',
      type: 'provider',
      strength: 0.3,
      label: 'same garage',
    },
  ],
  rings: [
    { ring_id: 'RING-07', ring_score: 0.91, member_ids: ['CLM-DEMO-HIGH', 'CLM-R2', 'CLM-R3'] },
  ],
  truncated: false,
};

export const ring: RingRaw = {
  ring_id: 'RING-07',
  ring_score: 0.91,
  band: 'HIGH',
  claims_count: 3,
  claimants_count: 3,
  shared: [
    { type: 'bank', label: 'Bank ****4417', count: 3 },
    { type: 'image_cluster', label: 'Damage photo cluster #07', count: 2 },
  ],
  total_claimed_amount: 485000,
  first_seen: '2026-09-02',
  last_seen: '2026-10-01',
  status: 'open',
  reasons: [
    '3 claimants share bank account ****4417',
    'Same damage photo reused in 2 claims',
    'Total claimed ₹4,85,000',
  ],
  data_source: 'live',
};
export const historicRing: RingRaw = {
  ring_id: 'RING-H12',
  ring_score: 0.58,
  band: 'MEDIUM',
  claims_count: 4,
  claimants_count: 2,
  shared: [{ type: 'phone', label: 'Phone ****2210', count: 4 }],
  total_claimed_amount: 212000,
  first_seen: '2026-07-11',
  last_seen: '2026-08-20',
  status: 'under_review',
  reasons: ['2 claimants share phone ****2210 across 4 claims'],
  data_source: 'synthetic_history',
};
export const ringDetail: RingDetailRaw = {
  ...ring,
  claims: [
    { claim_id: 'CLM-DEMO-HIGH', band: 'HIGH', amount: 145000, submitted_at: '2026-10-01' },
    { claim_id: 'CLM-R2', band: 'HIGH', amount: 210000, submitted_at: '2026-09-18' },
    { claim_id: 'CLM-R3', band: 'MEDIUM', amount: 130000, submitted_at: '2026-09-02' },
  ],
  timeline: [
    { date: '2026-09-02', event: 'CLM-R3 submitted (bank ****4417)' },
    { date: '2026-09-18', event: 'CLM-R2 submitted – same bank account, damage photo #07' },
    { date: '2026-10-01', event: 'CLM-DEMO-HIGH submitted – damage photo #07 reused' },
  ],
  graph: {
    nodes: graph.nodes.filter(
      (n) => !['CLM-G1', 'CLM-G2', 'CLT-D', 'CLT-E', 'ID-GARAGE-12'].includes(n.id),
    ),
    edges: graph.edges.filter((e) => !['e4', 'e5', 'e11', 'e12'].includes(e.id)),
    rings: graph.rings,
    truncated: false,
  },
  audit: [{ at: '2026-10-01 18:04', actor: 'system', action: 'ring_detected' }],
};

export const claimNetwork: ClaimNetworkRaw = {
  rings: [{ ring_id: 'RING-07', ring_score: 0.91, band: 'HIGH' }],
  shared_identifiers: [
    { type: 'bank', label: 'Bank ****4417', other_claims: 2 },
    { type: 'image_cluster', label: 'Damage photo cluster #07', other_claims: 1 },
  ],
  evidence: [
    ev({
      id: 'CLM-NET-01',
      title: 'Shares a bank account with other claimants',
      reason: 'Bank account ****4417 also appears on 2 claims from 2 other claimants.',
      kind: 'risk',
      severity: 'medium',
      calibrated_score: 1,
      weight: 0.35,
      pipeline: 'claim',
    }),
    ev({
      id: 'CLM-NET-02',
      title: 'Member of a detected ring',
      reason: 'Member of ring RING-07 (ring score 91%).',
      kind: 'risk',
      severity: 'high',
      calibrated_score: 0.91,
      weight: 0.35,
      pipeline: 'claim',
    }),
  ],
};

export const analyticsSummary: AnalyticsSummaryRaw = {
  claims_today: 18,
  fast_tracked: 7,
  flagged: 5,
  flagged_rate: 0.28,
  top_reasons: [
    { id: 'IMG-AI-01', title: 'AI-generated image patterns', count: 9 },
    { id: 'DOC-LOGIC-01', title: 'Line items do not add up', count: 6 },
    { id: 'CLM-NET-01', title: 'Shared identifier with other claimants', count: 4 },
  ],
  sparkline_7d: [12, 15, 11, 19, 14, 21, 18],
  open_rings: 2,
};

function day(offset: number) {
  const d = new Date(Date.UTC(2026, 9, 3));
  d.setUTCDate(d.getUTCDate() - offset);
  return d.toISOString().slice(0, 10);
}
export function trends(range: '7d' | '30d' | '90d'): AnalyticsTrendsRaw {
  const days = range === '7d' ? 7 : range === '30d' ? 30 : 90;
  const daily = Array.from({ length: days }, (_, i) => {
    const offset = days - 1 - i;
    const wave = Math.round(3 * Math.sin(i / 3));
    const low = 10 + wave + (i % 4);
    const medium = 3 + (i % 3);
    const high = 1 + (i % 5 === 0 ? 3 : 1) + (offset === 1 ? 5 : 0);
    const total = low + medium + high;
    return {
      date: day(offset),
      low,
      medium,
      high,
      flagged_rate: Number(((medium + high) / total).toFixed(3)),
      avg_risk: Number((0.22 + (medium * 0.5 + high) / (total * 2)).toFixed(3)),
    };
  });
  const weeks = Math.max(1, Math.ceil(days / 7));
  const week = (i: number) => `W${String(40 - (weeks - 1 - i)).padStart(2, '0')}`;
  return {
    daily,
    top_signals: analyticsSummary.top_reasons ?? [],
    by_type: [
      { type: 'motor', total: 140, flagged: 36 },
      { type: 'health', total: 96, flagged: 21 },
      { type: 'property', total: 41, flagged: 7 },
    ],
    by_modality: [
      { modality: 'image', flagged: 31 },
      { modality: 'document', flagged: 22 },
      { modality: 'identity', flagged: 6 },
      { modality: 'voice', flagged: 2 },
      { modality: 'network', flagged: 5 },
    ],
    recycled_evidence_weekly: Array.from({ length: weeks }, (_, i) => ({
      week: week(i),
      count: (i * 2) % 5,
    })),
    rings_weekly: Array.from({ length: weeks }, (_, i) => ({
      week: week(i),
      count: i % 3 === 0 ? 1 : 0,
    })),
    decisions_weekly: Array.from({ length: weeks }, (_, i) => ({
      week: week(i),
      approved: 40 + i,
      rejected: 3 + (i % 3),
      requested: 6 + (i % 4),
    })),
    spike: {
      detected: true,
      message: 'HIGH-risk claims yesterday were 3× the 7-day average.',
    },
  };
}

export const voiceLanguages = [
  { code: 'hi', name: 'Hindi', native_name: 'हिंदी' },
  { code: 'en', name: 'English', native_name: 'English' },
  { code: 'bn', name: 'Bengali', native_name: 'বাংলা' },
  { code: 'ta', name: 'Tamil', native_name: 'தமிழ்' },
  { code: 'te', name: 'Telugu', native_name: 'తెలుగు' },
  { code: 'mr', name: 'Marathi', native_name: 'मराठी' },
];
