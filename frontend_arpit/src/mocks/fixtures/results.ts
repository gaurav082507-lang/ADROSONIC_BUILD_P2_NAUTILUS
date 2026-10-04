/*
 * PROVISIONAL mock results in the REAL backend shape (contract/openapi.json → AnalysisResult).
 * `npm run fixtures:sync` replaces them with captured backend responses.
 */
import type { EvidenceRaw, PipelineRaw, ResultRaw, TimelineRaw } from '../../api/raw/types';

type Band = 'LOW' | 'MEDIUM' | 'HIGH';
export function ev(
  p: Partial<EvidenceRaw> & { id: string; title: string; reason: string },
): EvidenceRaw {
  return {
    kind: 'risk',
    raw_score: p.calibrated_score ?? 0,
    calibrated_score: 0,
    weight: 0,
    effective_weight: p.weight ?? 0,
    severity: 'low',
    ...p,
  } as EvidenceRaw;
}
export function pipe(
  pipeline: string,
  risk: number,
  band: Band,
  confidence: string,
  ids: string[],
): PipelineRaw {
  return {
    pipeline,
    risk,
    authenticity: Number((1 - risk).toFixed(3)),
    band,
    confidence,
    evidence_ids: ids,
  };
}
const signed = (name: string, id: string) =>
  `/api/v1/artifacts/${id}/${name}?exp=4102444800&sig=mock`;

export const low: ResultRaw = {
  id: 'RES-DEMO-LOW',
  mode: 'image',
  created_at: '2026-10-03T09:12:00Z',
  overall: {
    risk: 0.12,
    band: 'LOW',
    confidence: 'high',
    summary:
      'LOW fraud likelihood (12%). No material manipulation signal was found in the submitted image.',
  },
  image: pipe('image', 0.12, 'LOW', 'high', ['IMG-AI-01']),
  evidence: [
    ev({
      id: 'IMG-AI-01',
      title: 'AI-generated image patterns',
      reason: 'The AI-image detector found no strong generative patterns (8% after calibration).',
      calibrated_score: 0.08,
      raw_score: 0.08,
      weight: 0.65,
      effective_weight: 0.65,
      contribution: 0.052,
      contribution_pct: 100,
      rank: 1,
      pipeline: 'image',
      pipeline_input: 'img_1',
    }),
  ],
  detector_status: [],
  quality_warnings: [],
  artifacts: { heatmap: signed('ela_heatmap.png', 'RES-DEMO-LOW') },
  versions: { ai_detector: 'siglip', calibration: '2026-10-03' },
  why_this_score: {
    image: {
      evidence_contributions: [
        {
          evidence_id: 'IMG-AI-01',
          title: 'AI-generated image patterns',
          w: 0.65,
          p: 0.08,
          push: 0.052,
          contribution_pct: 100,
        },
      ],
      formula: '1 − (1 − 0.052) = 0.052',
      overrides_applied: [],
      quality_gates_applied: [],
    },
  },
  checks_run: [
    { detector: 'preprocess', status: 'ok', duration_ms: 41, reason: null },
    { detector: 'ai_detector', status: 'ok', duration_ms: 812, reason: null },
    { detector: 'ela', status: 'ok', duration_ms: 120, reason: null },
  ],
  top_reasons: ['No material manipulation signal was found.'],
  recommended_action: 'Proceed with normal processing; eligible for fast-track.',
  summary_source: 'template',
};

export const medium: ResultRaw = {
  id: 'RES-DEMO-MEDIUM',
  mode: 'document',
  created_at: '2026-10-02T15:40:00Z',
  overall: {
    risk: 0.54,
    band: 'MEDIUM',
    confidence: 'medium',
    summary:
      'MEDIUM fraud likelihood (54%). The invoice total uses a different font from the other amounts.',
  },
  document: pipe('document', 0.54, 'MEDIUM', 'medium', ['DOC-FONT-01', 'DOC-ANOM-01']),
  evidence: [
    ev({
      id: 'DOC-FONT-01',
      title: 'Font differs within the amounts column',
      reason: 'The total ₹1,20,000.00 is set in Times-Bold while other amounts use Helvetica.',
      calibrated_score: 0.9,
      weight: 0.4,
      effective_weight: 0.4,
      severity: 'medium',
      contribution: 0.36,
      contribution_pct: 100,
      rank: 1,
      pipeline: 'document',
      pipeline_input: 'doc',
      page: 1,
      field: 'total',
      bbox: { page: 1, x: 0.62, y: 0.71, w: 0.22, h: 0.04 },
    }),
    ev({
      id: 'DOC-ANOM-01',
      kind: 'info',
      title: 'Unusual word style (experimental)',
      reason: 'The digit "2" in the total is thicker than its neighbours. Shown as context only.',
      calibrated_score: 0.6,
      weight: 0.3,
      effective_weight: 0,
      pipeline: 'document',
      page: 1,
      bbox: { page: 1, x: 0.7, y: 0.71, w: 0.04, h: 0.04 },
    }),
  ],
  detector_status: [],
  quality_warnings: [
    { code: 'DOC-QUAL-01', message: 'Scan quality is moderate; OCR confidence 82%.' },
  ],
  artifacts: {
    pages: [
      {
        page: 1,
        width_pt: 595,
        height_pt: 842,
        image_url: signed('page_1_boxes.png', 'RES-DEMO-MEDIUM'),
      },
    ],
  },
  versions: {},
  why_this_score: {
    document: {
      evidence_contributions: [
        {
          evidence_id: 'DOC-FONT-01',
          title: 'Font differs within the amounts column',
          w: 0.4,
          p: 0.9,
          push: 0.36,
          contribution_pct: 100,
        },
      ],
      formula: '1 − (1 − 0.36) = 0.36',
      overrides_applied: [],
      quality_gates_applied: [{ detector: 'ocr', factor: 0.9, reason: 'moderate scan quality' }],
    },
  },
  checks_run: [
    { detector: 'ocr', status: 'ok', duration_ms: 2140, reason: null },
    { detector: 'rules', status: 'ok', duration_ms: 35, reason: null },
    { detector: 'tamper_cnn', status: 'ok', duration_ms: 1210, reason: null },
  ],
  top_reasons: ['The total uses a different font from the other amounts.'],
  recommended_action: 'Request the original invoice from the issuer.',
  summary_source: 'template',
};

export const high: ResultRaw = {
  id: 'RES-DEMO-HIGH',
  claim_id: 'CLM-DEMO-HIGH',
  mode: 'claim',
  created_at: '2026-10-03T08:05:00Z',
  overall: {
    risk: 0.88,
    band: 'HIGH',
    confidence: 'high',
    summary:
      'HIGH fraud likelihood (88%). The damage photo shows patterns typical of AI-generated images, and the invoice line items do not add up to the stated total.',
  },
  image: pipe('image', 0.78, 'HIGH', 'high', ['IMG-AI-01', 'IMG-DUP-02']),
  document: pipe('document', 0.81, 'HIGH', 'high', ['DOC-LOGIC-01']),
  identity: { ...pipe('identity', 0.21, 'LOW', 'high', ['ID-FACE-00', 'ID-QR-00']) },
  claim: pipe('claim', 0.44, 'MEDIUM', 'medium', ['CLM-X-01', 'CLM-NET-01']),
  voice: pipe('voice', 0.0, 'LOW', 'low', ['VOI-SPOOF-01']),
  evidence: [
    ev({
      id: 'IMG-AI-01',
      title: 'AI-generated image patterns',
      reason: 'The photo shows patterns typical of AI-generated images (91% after calibration).',
      calibrated_score: 0.91,
      raw_score: 0.97,
      weight: 0.65,
      effective_weight: 0.65,
      severity: 'high',
      contribution: 0.59,
      contribution_pct: 62,
      rank: 1,
      pipeline: 'image',
      pipeline_input: 'img_1',
      bbox: { page: 1, x: 0.18, y: 0.22, w: 0.46, h: 0.38 },
    }),
    ev({
      id: 'IMG-DUP-02',
      title: 'Near-duplicate photo in another claim',
      reason:
        'A cropped, recoloured copy of this photo was submitted in claim CLM-0991 by a different claimant.',
      calibrated_score: 0.93,
      weight: 0.85,
      effective_weight: 0.85,
      severity: 'high',
      contribution: 0.36,
      contribution_pct: 38,
      rank: 2,
      pipeline: 'image',
      pipeline_input: 'img_1',
      details: {
        similarity: 0.93,
        matched_claim_id: 'CLM-0991',
        match_type: 'cropped / recoloured',
      },
    }),
    ev({
      id: 'DOC-LOGIC-01',
      title: 'Line items do not add up',
      reason: 'Line items add up to ₹1,00,000.00 but the stated total is ₹1,20,000.00.',
      calibrated_score: 1,
      weight: 0.8,
      effective_weight: 0.8,
      severity: 'high',
      contribution: 0.8,
      contribution_pct: 100,
      rank: 1,
      pipeline: 'document',
      pipeline_input: 'doc',
      page: 1,
      field: 'total',
      bbox: { page: 1, x: 0.62, y: 0.71, w: 0.22, h: 0.04 },
    }),
    ev({
      id: 'ID-FACE-00',
      kind: 'info',
      title: 'Selfie matches the ID photo',
      reason: 'Face similarity 0.71 (match threshold 0.363).',
      calibrated_score: 0.1,
      pipeline: 'identity',
      details: { similarity: 0.71 },
    }),
    ev({
      id: 'ID-QR-00',
      kind: 'info',
      title: 'Aadhaar QR verified (TEST key – demo)',
      reason: 'Signature valid with the demo test key; printed details match the signed data.',
      pipeline: 'identity',
    }),
    ev({
      id: 'CLM-X-01',
      title: 'Photo taken before the incident',
      reason: 'Photo taken 12 Sep 2026, 6 days before the stated incident on 18 Sep 2026.',
      calibrated_score: 1,
      weight: 0.4,
      effective_weight: 0.4,
      severity: 'medium',
      contribution: 0.4,
      contribution_pct: 71,
      pipeline: 'claim',
    }),
    ev({
      id: 'CLM-NET-01',
      title: 'Shares a bank account with other claimants',
      reason: 'Bank account ****4417 also appears on 2 claims from 2 other claimants.',
      calibrated_score: 1,
      weight: 0.35,
      effective_weight: 0.35,
      severity: 'medium',
      contribution: 0.16,
      contribution_pct: 29,
      pipeline: 'claim',
    }),
    ev({
      id: 'VOI-SPOOF-01',
      kind: 'info',
      title: 'Synthetic-voice check (uncalibrated)',
      reason: 'Information only until the voice detector is calibrated.',
      calibrated_score: 0.18,
      pipeline: 'voice',
    }),
  ],
  detector_status: [],
  quality_warnings: [],
  artifacts: {
    heatmap: signed('ela_heatmap.png', 'RES-DEMO-HIGH'),
    overlay: signed('overlay.png', 'RES-DEMO-HIGH'),
    pages: [
      {
        page: 1,
        width_pt: 595,
        height_pt: 842,
        image_url: signed('page_1_boxes.png', 'RES-DEMO-HIGH'),
      },
    ],
    identity_face_comparison: signed('identity_face_comparison.jpg', 'RES-DEMO-HIGH'),
  },
  versions: { ai_detector: 'siglip', calibration: '2026-10-03' },
  location: {
    claimed: { lat: 23.3441, lng: 85.3096, text: 'Ranchi' },
    photos: [{ lat: 23.36, lng: 85.33, distance_km: 2.7 }],
    max_distance_km: 2.7,
  },
  liveness: {
    performed: true,
    passed: true,
    code_match: true,
    challenges: [
      { name: 'blink', ok: true, ms: 1840 },
      { name: 'turn_left', ok: true, ms: 2210 },
      { name: 'look_up', ok: true, ms: 1950 },
    ],
  },
  aadhaar_qr: {
    found: true,
    signature_valid: true,
    mode: 'test_key',
    photo_similarity: 0.68,
    comparisons: [
      { field: 'name', printed: 'Ravi Kumar', qr: 'Ravi Kumar', match: true },
      { field: 'dob', printed: '14-02-1990', qr: '14-02-1990', match: true },
      { field: 'gender', printed: 'M', qr: 'M', match: true },
    ],
  },
  story: {
    contradictions: [
      {
        text: 'Voice statement says the incident happened on 12 Sep 2026, but the claim form says 18 Sep 2026.',
        sources: ['voice', 'form'],
        evidence_ids: ['CLM-X-01'],
      },
    ],
    consistent_points: ['Location (Ranchi) matches across voice, form and photo GPS.'],
    source: 'rules',
    note: 'For investigator review, not part of the score',
  },
  voice_details: {
    language: 'hi',
    duration_s: 18.4,
    transcript: 'मेरी गाड़ी को 12 सितंबर की शाम को रांची में पीछे से टक्कर लगी।',
    translation_en: 'My car was hit from behind in Ranchi on the evening of 12 September.',
    extracted: {
      incident_date: '2026-09-12',
      incident_time: '19:30',
      amount_claimed: 120000,
      damaged_items: ['rear bumper', 'tail light'],
      location_text: 'Ranchi',
    },
    spoof: {
      probability: 0.18,
      band: 'LOW',
      segments: [{ start_s: 4.2, end_s: 6.1, score: 0.31 }],
    },
    status: 'uncalibrated (information only)',
  },
  links: [{ result_id: 'RES-0991', reason: 'Near-duplicate photo (IMG-DUP-02)' }],
  image_results: [pipe('image', 0.78, 'HIGH', 'high', ['IMG-AI-01', 'IMG-DUP-02'])],
  why_this_score: {
    image: {
      evidence_contributions: [
        {
          evidence_id: 'IMG-AI-01',
          title: 'AI-generated image patterns',
          w: 0.65,
          p: 0.91,
          push: 0.59,
          contribution_pct: 62,
        },
        {
          evidence_id: 'IMG-DUP-02',
          title: 'Near-duplicate photo in another claim',
          w: 0.85,
          p: 0.93,
          push: 0.79,
          contribution_pct: 38,
        },
      ],
      formula: '1 − (1 − 0.59)(1 − 0.79) = 0.914 → capped by quality gate = 0.78',
      overrides_applied: [],
      quality_gates_applied: [],
    },
    document: {
      evidence_contributions: [
        {
          evidence_id: 'DOC-LOGIC-01',
          title: 'Line items do not add up',
          w: 0.8,
          p: 1,
          push: 0.8,
          contribution_pct: 100,
        },
      ],
      formula: '1 − (1 − 0.80) = 0.80',
      overrides_applied: [],
      quality_gates_applied: [],
    },
    overall: {
      formula: '0.7 × max(0.78, 0.81, 0.21, 0.44) + 0.3 × mean(…) = 0.88',
      pipeline_risks: { image: 0.78, document: 0.81, identity: 0.21, claim: 0.44 },
      overrides_applied: [],
    },
  },
  checks_run: [
    { detector: 'img_1:ai_detector', status: 'ok', duration_ms: 812, reason: null },
    { detector: 'img_1:duplicates', status: 'ok', duration_ms: 140, reason: null },
    { detector: 'doc:ocr', status: 'ok', duration_ms: 2140, reason: null },
    { detector: 'doc:rules', status: 'ok', duration_ms: 35, reason: null },
    {
      detector: 'voice:asr',
      status: 'skipped',
      duration_ms: 0,
      reason: 'mock mode – Bhashini not called',
    },
  ],
  top_reasons: [
    'The damage photo shows patterns typical of AI-generated images.',
    'Invoice line items do not add up to the stated total.',
  ],
  recommended_action: 'Escalate to the fraud investigation team before any payout.',
  summary_source: 'template',
  decision: null,
};

export const highTimeline: TimelineRaw = {
  events: [
    {
      id: 'e1',
      timestamp: '2026-09-12T10:04:00+05:30',
      label: 'Damage photo captured (EXIF)',
      source: 'image',
      evidence_id: 'CLM-X-01',
    },
    { id: 'e2', timestamp: '2026-09-18', label: 'Stated incident date', source: 'form' },
    { id: 'e3', timestamp: '2026-09-20', label: 'Repair invoice dated', source: 'document' },
    { id: 'e4', timestamp: '2026-10-01T18:00:00+05:30', label: 'Claim submitted', source: 'claim' },
  ],
  contradictions: [
    {
      from_event: 'e1',
      to_event: 'e2',
      rule_id: 'CLM-X-01',
      reason: 'Photo was taken 6 days before the stated incident.',
    },
  ],
  undated: [{ id: 'u1', label: 'Garage estimate (no date printed)', source: 'document' }],
};
