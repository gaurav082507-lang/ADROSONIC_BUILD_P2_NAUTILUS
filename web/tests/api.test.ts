// @vitest-environment node
import { describe, expect, it, beforeAll, afterAll, afterEach, vi } from 'vitest';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

const server = setupServer(
  http.post('http://localhost/api/v1/analyze/image', async ({ request }) => {
    const form = await request.formData();
    expect(form.get('file')).toBeInstanceOf(File);
    return HttpResponse.json({ job_id: 'JOB-I' }, { status: 202 });
  }),
  http.post('http://localhost/api/v1/analyze/document', async ({ request }) => {
    const form = await request.formData();
    expect(form.get('file')).toBeInstanceOf(File);
    return HttpResponse.json({ job_id: 'JOB-D' }, { status: 202 });
  }),
  http.post('http://localhost/api/v1/analyze/claim', async ({ request }) => {
    const form = await request.formData();
    expect(form.getAll('image').length).toBe(1);
    expect(form.get('document')).toBeInstanceOf(File);
    expect(form.get('id_photo')).toBeInstanceOf(File);
    expect(form.get('selfie')).toBeInstanceOf(File);
    expect(form.get('metadata')).toBe('{"claim_type":"motor"}');
    return HttpResponse.json({ job_id: 'JOB-C' }, { status: 202 });
  }),
);
let raw: typeof import('../src/api/raw/endpoints').raw;
beforeAll(async () => {
  // Node environment: real undici FormData/File, absolute base URL for MSW interception.
  vi.stubEnv('VITE_API_BASE_URL', 'http://localhost/api/v1');
  server.listen({ onUnhandledRequest: 'error' });
  ({ raw } = await import('../src/api/raw/endpoints'));
});
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
const img = () => new File(['x'], 'photo.jpg', { type: 'image/jpeg' });
const pdf = () => new File(['x'], 'bill.pdf', { type: 'application/pdf' });
describe('analysis multipart contract', () => {
  it('posts image to the image endpoint', async () =>
    expect((await raw.analyze('image', { file: img() })).job_id).toBe('JOB-I'));
  it('posts document to the document endpoint', async () =>
    expect((await raw.analyze('document', { file: pdf() })).job_id).toBe('JOB-D'));
  it('posts full claim fields to the claim endpoint', async () =>
    expect(
      (
        await raw.analyze('claim', {
          images: [img()],
          document: pdf(),
          idPhoto: img(),
          selfie: img(),
          metadata: { claim_type: 'motor' },
        })
      ).job_id,
    ).toBe('JOB-C'));
});

describe('prompt 9–10 request contract', () => {
  it('network graph sends focus + defaults as query params', async () => {
    let seen = '';
    server.use(
      http.get('http://localhost/api/v1/network/graph', ({ request }) => {
        seen = new URL(request.url).search;
        return HttpResponse.json({ nodes: [], edges: [], rings: [], truncated: false });
      }),
    );
    await raw.networkGraph({ focusType: 'claim', focusId: 'CLM-1', hops: 3 });
    const q = new URLSearchParams(seen);
    expect(q.get('focus_type')).toBe('claim');
    expect(q.get('focus_id')).toBe('CLM-1');
    expect(q.get('hops')).toBe('3');
    expect(q.get('min_strength')).toBe('0.3');
    expect(q.get('limit')).toBe('300');
  });
  it('network overview omits focus_type when no focus id is given', async () => {
    let seen = '';
    server.use(
      http.get('http://localhost/api/v1/network/graph', ({ request }) => {
        seen = new URL(request.url).search;
        return HttpResponse.json({ nodes: [], edges: [] });
      }),
    );
    await raw.networkGraph({ focusType: 'claim' });
    expect(new URLSearchParams(seen).has('focus_type')).toBe(false);
  });
  it('ring status posts {status, note}', async () => {
    let body: any;
    server.use(
      http.post('http://localhost/api/v1/network/rings/RING-07/status', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ok: true });
      }),
    );
    await raw.ringStatus('RING-07', 'confirmed', 'Verified with bank');
    expect(body).toEqual({ status: 'confirmed', note: 'Verified with bank' });
  });
  it('analytics trends sends range and optional type', async () => {
    let seen = '';
    server.use(
      http.get('http://localhost/api/v1/analytics/trends', ({ request }) => {
        seen = new URL(request.url).search;
        return HttpResponse.json({ daily: [] });
      }),
    );
    await raw.analyticsTrends('90d', 'motor');
    expect(new URLSearchParams(seen).get('range')).toBe('90d');
    expect(new URLSearchParams(seen).get('type')).toBe('motor');
  });
  it('voice transcribe sends file + language (contract field names)', async () => {
    let audio: unknown;
    let language: unknown;
    server.use(
      http.post('http://localhost/api/v1/voice/transcribe', async ({ request }) => {
        const form = await request.formData();
        audio = form.get('file');
        language = form.get('language');
        return HttpResponse.json({ language: 'hi', transcript: 'x', translation_en: 'y' });
      }),
    );
    await raw.voiceTranscribe(new Blob(['a'], { type: 'audio/webm' }), 'hi');
    expect(audio).toBeInstanceOf(Blob);
    expect(language).toBe('hi');
  });
  it('claim with voice sends voice_audio + consent_voice_processing + description_lang', async () => {
    let form: FormData | undefined;
    server.use(
      http.post('http://localhost/api/v1/claims', async ({ request }) => {
        form = await request.formData();
        return HttpResponse.json({ claim_id: 'CLM-NEW', job_id: 'J' }, { status: 202 });
      }),
    );
    await raw.createClaim({
      policyId: 'P1',
      claimType: 'motor',
      peril: 'collision',
      incidentDate: '2026-09-12',
      incidentTime: '19:30',
      location: JSON.stringify({ lat: 23.3, lng: 85.3, text: '' }),
      claimedAmount: '120000',
      damagedItems: ['bumper'],
      description: 'rear-ended',
      consent: true,
      evidence: [{ file: img(), slot: 'damage_closeup', captureSource: 'camera' }],
      voiceAudio: new Blob(['a'], { type: 'audio/webm' }),
      consentVoiceProcessing: true,
      descriptionLang: 'hi',
    });
    expect(form?.get('voice_audio')).toBeInstanceOf(Blob);
    expect(form?.get('consent_voice_processing')).toBe('true');
    expect(form?.get('description_lang')).toBe('hi');
    expect(form?.get('incident_date')).toBe('2026-09-12');
    expect(form?.getAll('evidence')).toHaveLength(1);
    expect(JSON.parse(String(form?.get('slot_names')))).toEqual(['damage_closeup']);
    expect(JSON.parse(String(form?.get('capture_sources')))).toEqual(['camera']);
    expect(JSON.parse(String(form?.get('damaged_items')))).toEqual(['bumper']);
    expect(form?.has('evidence_slot[]')).toBe(false);
  });
});

describe('real-contract request shapes', () => {
  it('history uses page/page_size and queue uses limit/offset', async () => {
    const seen: Record<string, string> = {};
    server.use(
      http.get('http://localhost/api/v1/history', ({ request }) => {
        seen.history = new URL(request.url).search;
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 });
      }),
      http.get('http://localhost/api/v1/queue', ({ request }) => {
        seen.queue = new URL(request.url).search;
        return HttpResponse.json({ items: [], total: 0, limit: 50, offset: 0 });
      }),
    );
    await raw.history({ page: 2, pageSize: 10, band: 'HIGH' });
    await raw.queue({ band: 'LOW', q: 'CLM' });
    const h = new URLSearchParams(seen.history);
    expect([h.get('page'), h.get('page_size'), h.get('band')]).toEqual(['2', '10', 'HIGH']);
    expect(h.has('limit')).toBe(false);
    const q = new URLSearchParams(seen.queue);
    expect([q.get('band'), q.get('q'), q.get('limit'), q.get('offset')]).toEqual([
      'LOW',
      'CLM',
      '50',
      '0',
    ]);
  });
  it('liveness verify sends repeated frames + aligned frame_metadata JSON', async () => {
    let form: FormData | undefined;
    server.use(
      http.post('http://localhost/api/v1/identity/liveness/verify', async ({ request }) => {
        form = await request.formData();
        return HttpResponse.json({ passed: true, best_frame: '/x.jpg' });
      }),
    );
    const frame = () => new Blob(['f'], { type: 'image/jpeg' });
    await raw.livenessVerify({
      sessionId: 'S',
      nonce: 'N',
      frames: [
        { frame: frame(), timestamp: 1, challenge: 'blink' },
        { frame: frame(), timestamp: 2, challenge: 'blink' },
      ],
    });
    expect(form?.get('session_id')).toBe('S');
    expect(form?.get('nonce')).toBe('N');
    expect(form?.getAll('frames')).toHaveLength(2);
    expect(JSON.parse(String(form?.get('frame_metadata')))).toEqual([
      { index: 0, timestamp: 1, challenge: 'blink' },
      { index: 1, timestamp: 2, challenge: 'blink' },
    ]);
  });
  it('decision sends the single claimant_message the contract requires', async () => {
    let body: any;
    server.use(
      http.post('http://localhost/api/v1/results/R1/decision', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ status: 'recorded' });
      }),
    );
    await raw.decision('R1', {
      action: 'request_evidence',
      reasonCategory: 'photo_unclear',
      messageEn: 'Please upload a clearer photo.',
      messageHi: 'कृपया साफ़ फ़ोटो अपलोड करें।',
      language: 'hi',
      slotsToResubmit: ['damage_closeup'],
    });
    expect(body.claimant_message).toBe('कृपया साफ़ फ़ोटो अपलोड करें।');
    expect(body.reason_category).toBe('photo_unclear');
    expect(body.slots_to_resubmit).toEqual(['damage_closeup']);
  });
});
