import { describe, expect, it } from 'vitest';
import {
  adaptActions,
  adaptClaimStatus,
  adaptClaimsMine,
  adaptHistory,
  adaptJob,
  adaptLogin,
  adaptPolicies,
  adaptQueue,
  adaptResult,
  adaptTimeline,
  adaptTranscription,
} from '../src/api/adapters';
import { high, highTimeline, low, medium } from '../src/mocks/fixtures/results';
import {
  actions,
  claimStatus,
  claimsMine,
  evidenceTimeline,
  history,
  policies,
  queue,
} from '../src/mocks/fixtures/lists';

describe('real-contract adapters', () => {
  it('login: {token, user} and the legacy {access_token, role} both work', () => {
    expect(
      adaptLogin({
        token: 't',
        user: { id: 'u', name: 'P', email: 'e', role: 'investigator', preferred_lang: 'en' },
      }).token,
    ).toBe('t');
    const legacy = adaptLogin({ access_token: 'a', role: 'claimant', user_id: 'c', name: 'R' });
    expect(legacy.token).toBe('a');
    expect(legacy.user.role).toBe('claimant');
  });
  it('job error may be a string', () => {
    expect(
      adaptJob({ job_id: 'j', mode: 'image', status: 'failed', steps: [], error: 'boom' }).error,
    ).toBe('boom');
  });
  it('result: summary comes from overall, warnings are objects, scores from PipelineScore', () => {
    const r = adaptResult(medium);
    expect(r.summary).toMatch(/MEDIUM fraud likelihood/);
    expect(r.qualityWarnings[0]).toMatch(/OCR confidence/);
    expect(r.document?.analysed).toBe(true);
    expect(r.image).toBeUndefined();
    expect(r.artifacts.pages[0].imageUrl).toContain('sig=');
  });
  it('evidence uses calibrated_score and effective_weight', () => {
    const e = adaptResult(medium).evidence.find((x) => x.id === 'DOC-ANOM-01')!;
    expect(e.score).toBe(0.6);
    expect(e.weight).toBe(0);
    expect(e.kind).toBe('info');
  });
  it('why-this-score flattens per-pipeline contributions and keeps formulas', () => {
    const r = adaptResult(high);
    expect(r.whyThisScore.map((x) => x.pipeline)).toEqual(['image', 'image', 'document']);
    expect(r.whyDetail.formulas.map((f) => f.pipeline)).toContain('overall');
  });
  it('why-this-score falls back to flat items when per-pipeline blocks are absent', () => {
    const r = adaptResult({
      ...low,
      why_this_score: {
        items: [
          {
            evidence_id: 'IMG-AI-01',
            title: 'AI',
            w: 0.65,
            p: 0.08,
            push: 0.05,
            contribution_pct: 100,
          },
        ],
      },
    });
    expect(r.whyThisScore[0].pipeline).toBe('image');
  });
  it('identity: liveness + Aadhaar QR + face similarity are assembled', () => {
    const id = adaptResult(high).identityDetails!;
    expect(id.similarity).toBe(0.71);
    expect(id.livenessPassed).toBe(true);
    expect(id.challenges[0]).toEqual({ name: 'blink', status: 'passed' });
    expect(id.aadhaarQr?.signatureStatus).toBe('valid');
    expect(id.aadhaarQr?.testKey).toBe(true);
    expect(id.aadhaarQr?.rows).toHaveLength(3);
  });
  it('duplicate is derived from IMG-DUP evidence details', () => {
    const d = adaptResult(high).duplicate!;
    expect(d.earlierClaim).toBe('CLM-0991');
    expect(d.similarity).toBe(0.93);
  });
  it('claim checks are derived from CLM-X evidence (network/story excluded)', () => {
    const names = adaptResult(high).claimChecks!.map((c) => c.name);
    expect(names.some((n) => n.includes('CLM-X-01'))).toBe(true);
    expect(names.some((n) => n.includes('CLM-NET'))).toBe(false);
  });
  it('voice details come from voice_details; claimId is carried', () => {
    const r = adaptResult(high);
    expect(r.voiceDetails?.transcript).toMatch(/रांची/);
    expect(r.claimId).toBe('CLM-DEMO-HIGH');
    expect(adaptResult(low).voiceDetails).toBeUndefined();
  });
  it('timeline endpoint shape: events + contradictions + undated', () => {
    const t = adaptTimeline(highTimeline);
    expect(t.filter((x) => x.contradiction)).toHaveLength(1);
    expect(t.filter((x) => !x.date && !x.contradiction)).toHaveLength(1);
  });
  it('queue rows: claim_id, result_id, can_fast_track, overall_risk', () => {
    const rows = adaptQueue({ items: queue });
    expect(rows[0]).toMatchObject({
      id: 'CLM-DEMO-HIGH',
      resultId: 'RES-DEMO-HIGH',
      risk: 0.88,
      band: 'HIGH',
    });
    expect(rows[2].eligibleFastTrack).toBe(true);
    // falls back to claim id when result_id is absent
    const { result_id: _omit, ...noResult } = queue[0];
    void _omit;
    expect(adaptQueue([noResult])[0].resultId).toBe('CLM-DEMO-HIGH');
  });
  it('history, policies, claims, status, actions', () => {
    expect(adaptHistory({ items: history })[0]).toMatchObject({
      band: 'HIGH',
      risk: 0.88,
      topReason: 'AI-generated image patterns',
    });
    expect(adaptPolicies(policies)[0]).toMatchObject({
      id: 'MTR/2026/1001',
      asset: 'Hyundai Creta · JH01AB1234',
      sumInsured: 800000,
    });
    expect(adaptClaimsMine(claimsMine)[0].id).toBe('CLM-DEMO-CLAIMANT');
    const st = adaptClaimStatus(claimStatus, evidenceTimeline);
    expect(st.canResubmit).toBe(true);
    expect(st.slotsToResubmit).toEqual(['damage_closeup']);
    expect(st.evidence.find((e) => e.slot === 'damage_closeup')?.status).toBe('needs_replacing');
    expect(adaptActions(actions)[0].action).toContain('submitted → under_review');
  });
  it('transcription uses amount_claimed', () => {
    const t = adaptTranscription({
      language: 'hi',
      duration_s: 5,
      transcript: 'x',
      translation_en: 'y',
      extracted: { amount_claimed: 150000, damaged_items: [] } as never,
      source: 'bhashini',
    });
    expect(t.extracted.amount).toBe(150000);
  });
});
