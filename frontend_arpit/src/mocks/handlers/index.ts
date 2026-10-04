import type { JsonBodyType } from 'msw';
import { http, HttpResponse } from 'msw';
import type { JobRaw, ResultRaw } from '../../api/raw/types';
import { high, highTimeline, medium, low } from '../fixtures/results';
import {
  actions,
  claimStatus,
  claimsMine,
  evidenceTimeline,
  history,
  policies,
  queue,
} from '../fixtures/lists';
import { captured, capturedResults } from '../fixtures/captured';
const results: Record<string, ResultRaw> = { [high.id]: high, [medium.id]: medium, [low.id]: low };
for (const r of capturedResults<ResultRaw>()) results[r.id] = r;
const realHigh = captured<ResultRaw>('result_high');
import {
  analyticsSummary,
  claimNetwork,
  graph,
  historicRing,
  ring,
  ringDetail,
  trends,
  voiceLanguages,
} from '../fixtures/network';
const jobs: Record<string, { n: number; result: string }> = {};
const json = (data: unknown, status = 200) => HttpResponse.json(data as JsonBodyType, { status });
const ringStatuses: Record<string, string> = {};
const artifactSample = (name: string) =>
  /page_/.test(name)
    ? '/images/hero-heatmap.svg'
    : /heatmap|overlay/.test(name)
      ? '/images/hero-heatmap.svg'
      : '/samples/selfie.jpg';
export const handlers = [
  /* Mock-only: signed artifact URLs point at bundled sample images. */
  http.get('/api/v1/artifacts/:resultId/:name', ({ params, request }) =>
    Response.redirect(new URL(artifactSample(String(params.name)), request.url).toString(), 302),
  ),
  /* ---------- Network ---------- */
  http.get('/api/v1/network/graph', ({ request }) => {
    const url = new URL(request.url);
    const focus = url.searchParams.get('focus_id');
    const minStrength = Number(url.searchParams.get('min_strength') ?? 0);
    const edges = graph.edges.filter((e) => e.strength >= minStrength);
    if (focus && !graph.nodes.some((n) => n.id === focus) && focus !== 'RING-07')
      return json({ error: { code: 'NOT_FOUND', message: 'Nothing found for that id' } }, 404);
    return json({ ...graph, edges });
  }),
  http.get('/api/v1/network/rings', () => {
    const items = [ring, historicRing].map((r) => ({
      ...r,
      status: ringStatuses[r.ring_id] ?? r.status,
    }));
    return json({ items, total: items.length });
  }),
  http.get('/api/v1/network/rings/:id', ({ params }) => {
    const id = String(params.id);
    if (id !== ring.ring_id && id !== historicRing.ring_id)
      return json({ error: { code: 'NOT_FOUND', message: 'Ring not found' } }, 404);
    const base =
      id === ring.ring_id ? ringDetail : { ...historicRing, claims: [], timeline: [], audit: [] };
    return json({ ...base, status: ringStatuses[id] ?? base.status });
  }),
  http.post('/api/v1/network/rings/:id/status', async ({ params, request }) => {
    const body = (await request.json()) as { status: string; note?: string };
    if (['confirmed', 'dismissed'].includes(body.status) && !body.note?.trim())
      return json(
        { error: { code: 'NOTE_REQUIRED', message: 'A note is required for this status.' } },
        422,
      );
    ringStatuses[String(params.id)] = body.status;
    return json({ ring_id: params.id, status: body.status });
  }),
  http.get(
    '/api/v1/network/rings/:id/report.pdf',
    () =>
      new HttpResponse(
        new Blob(['Lucen AI provisional ring case file'], { type: 'application/pdf' }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/pdf' },
        },
      ),
  ),
  http.get('/api/v1/network/rings/:id/report.json', () => json(ringDetail)),
  http.get('/api/v1/claims/:id/network', ({ params }) =>
    json(
      [high.id, high.claim_id].includes(String(params.id))
        ? claimNetwork
        : { rings: [], shared_identifiers: [], evidence: [] },
    ),
  ),
  /* ---------- Analytics ---------- */
  http.get('/api/v1/analytics/summary', () => json(analyticsSummary)),
  http.get('/api/v1/analytics/trends', ({ request }) => {
    const range = (new URL(request.url).searchParams.get('range') ?? '30d') as '7d' | '30d' | '90d';
    return json(trends(range));
  }),
  /* ---------- Voice ---------- */
  http.get('/api/v1/voice/languages', () =>
    json(voiceLanguages.map((l) => ({ code: l.code, name: l.name, native: l.native_name }))),
  ),
  http.post('/api/v1/voice/transcribe', async ({ request }) => {
    const form = await request.formData();
    const language = String(form.get('language') ?? 'hi');
    return json({
      language,
      duration_s: 9.6,
      transcript:
        'मेरी गाड़ी को 12 सितंबर को रांची में टक्कर लगी, नुकसान लगभग एक लाख बीस हज़ार का है।',
      translation_en:
        'My car was hit in Ranchi on 12 September; the damage is about one lakh twenty thousand.',
      extracted: {
        incident_date: '2026-09-12',
        incident_time: null,
        amount_claimed: 120000,
        damaged_items: ['bumper'],
        location_text: 'Ranchi',
      },
      source: 'bhashini',
    });
  }),

  http.get('/api/v1/health', () => json({ status: 'ok' })),
  http.post('/api/v1/auth/login', async ({ request }) => {
    const body = (await request.json()) as { email?: string };
    const email = String(body.email ?? '');
    const role = /ravi|sunita|claimant/.test(email) ? 'claimant' : 'investigator';
    return json({
      token: `mock-${role}-token`,
      user: {
        id: role === 'claimant' ? 'USR-CLAIM' : 'USR-INV',
        name: role === 'claimant' ? 'Ravi Kumar' : 'Priya Sharma',
        email,
        role,
        preferred_lang: 'en',
      },
    });
  }),
  http.get('/api/v1/auth/me', ({ request }) => {
    const claimant = (request.headers.get('authorization') ?? '').includes('claimant');
    return json({
      user: {
        id: claimant ? 'USR-CLAIM' : 'USR-INV',
        name: claimant ? 'Ravi Kumar' : 'Priya Sharma',
        email: claimant ? 'ravi@demo.in' : 'investigator@demo.in',
        role: claimant ? 'claimant' : 'investigator',
        preferred_lang: 'en',
      },
    });
  }),
  http.post('/api/v1/analyze/:mode', async ({ params }) => {
    const mode = String(params.mode);
    const pick = (name: string, fallback: string) => captured<ResultRaw>(name)?.id ?? fallback;
    const id =
      mode === 'document'
        ? pick('result_document_high', medium.id)
        : mode === 'image'
          ? pick('result_image_low', low.id)
          : (realHigh?.id ?? high.id);
    const jobId = `JOB-${Date.now()}`;
    jobs[jobId] = { n: 0, result: id };
    return json({ job_id: jobId }, 202);
  }),
  http.get('/api/v1/jobs/:id', ({ params }) => {
    const job = jobs[String(params.id)];
    if (!job) return json({ error: { code: 'JOB_NOT_FOUND', message: 'Job not found' } }, 404);
    job.n++;
    const done = job.n >= 3;
    const response: JobRaw = {
      job_id: String(params.id),
      mode: 'claim',
      status: done ? 'done' : 'running',
      result_id: done ? job.result : null,
      error: null,
      steps: [
        { name: 'img_1:preprocess', status: 'done', duration_ms: 182 },
        { name: 'img_1:ai_detector', status: done ? 'done' : 'running', duration_ms: 812 },
        { name: 'doc:ocr', status: done ? 'done' : 'queued', duration_ms: 734 },
      ],
    };
    return json(response);
  }),
  http.get('/api/v1/results/:id', ({ params }) => {
    const id = String(params.id);
    const result = results[id];
    if (!result)
      return json({ error: { code: 'RESULT_NOT_FOUND', message: 'Result not found' } }, 404);
    return json(result);
  }),
  http.get('/api/v1/results/:id/timeline', ({ params }) =>
    json(
      captured('timeline') ??
        (String(params.id) === high.id
          ? highTimeline
          : { events: [], contradictions: [], undated: [] }),
    ),
  ),
  http.get('/api/v1/results/:id/evidence', ({ params }) =>
    json(results[String(params.id)]?.evidence ?? []),
  ),
  http.get(
    '/api/v1/results/:id/report.pdf',
    () =>
      new HttpResponse(new Blob(['Lucen AI provisional report'], { type: 'application/pdf' }), {
        status: 200,
        headers: { 'Content-Type': 'application/pdf' },
      }),
  ),
  http.get('/api/v1/results/:id/report.json', ({ params }) =>
    json(results[String(params.id)] ?? high),
  ),
  http.delete('/api/v1/results/:id', () => new HttpResponse(null, { status: 204 })),
  http.post('/api/v1/results/:id/decision/draft', async ({ request }) => {
    const body = (await request.json()) as { action: string };
    return json({
      claimant_message_en:
        body.action === 'request_evidence'
          ? 'The photo of the damaged area is not clear enough. Please upload a new close-up photo taken in daylight.'
          : 'We have reviewed your claim. Please see the next steps below.',
      claimant_message_hi:
        body.action === 'request_evidence'
          ? 'क्षतिग्रस्त हिस्से की फ़ोटो साफ़ नहीं है। कृपया दिन की रोशनी में ली गई नई क्लोज़-अप फ़ोटो अपलोड करें।'
          : 'हमने आपके दावे की समीक्षा कर ली है। कृपया आगे के कदम देखें।',
      next_steps: ['Upload a new close-up photo of the damage'],
      slots_to_resubmit: body.action === 'request_evidence' ? ['damage_closeup'] : [],
      source: 'template',
    });
  }),
  http.post('/api/v1/results/:id/decision', () => json({ status: 'recorded' })),
  http.get('/api/v1/queue', ({ request }) => {
    const band = new URL(request.url).searchParams.get('band');
    const items = band ? queue.filter((r) => r.band === band) : queue;
    const real = captured<{ items: unknown[] }>('queue');
    if (real && !band) return json(real);
    return json({ items, total: items.length, limit: 50, offset: 0 });
  }),
  http.get('/api/v1/history', ({ request }) => {
    const band = new URL(request.url).searchParams.get('band');
    const items = band ? history.filter((r) => r.overall_band === band) : history;
    const real = captured<{ items: unknown[] }>('history');
    if (real && !band) return json(real);
    return json({ items, total: items.length, page: 1, page_size: 20 });
  }),
  http.post('/api/v1/claims/:id/fast-track', () => json({ status: 'approved', fast_track: true })),
  http.post('/api/v1/claims/:id/fast-track/undo', () => json({ status: 'under_review' })),
  http.get('/api/v1/claims/:id/actions', () => json(captured('claim_actions') ?? actions)),
  http.get('/api/v1/claims/:id/entities', () =>
    json([
      { type: 'bank', value: '****4417', matches: 2 },
      { type: 'phone', value: '****2210', matches: 1 },
    ]),
  ),
  http.get('/api/v1/policies/mine', () => json(captured('policies') ?? policies)),
  http.get('/api/v1/claims/mine', () => json(captured('claims_mine') ?? claimsMine)),
  http.get('/api/v1/claims/:id/status', ({ params }) =>
    json(captured('claim_status') ?? { ...claimStatus, claim_id: String(params.id) }),
  ),
  http.get('/api/v1/claims/:id/evidence-timeline', () =>
    json(captured('evidence_timeline') ?? evidenceTimeline),
  ),
  http.post('/api/v1/claims', () =>
    json({ claim_id: 'CLM-DEMO-CLAIMANT', job_id: 'JOB-CLAIM', status: 'submitted' }, 202),
  ),
  http.post('/api/v1/claims/:id/resubmit', () => json({ status: 'resubmitted' }, 202)),
  http.post('/api/v1/identity/liveness/session', () =>
    json({
      session_id: 'LIV-001',
      nonce: 'TEST-NONCE',
      challenges: ['blink', 'turn_left', 'look_up'],
      spoken_code: '4 7 2 9',
      expires_at: '2026-10-03T20:30:00Z',
    }),
  ),
  http.post('/api/v1/identity/liveness/verify', () =>
    json({ passed: true, best_frame: '/samples/selfie.jpg', reasons: [] }),
  ),
];
