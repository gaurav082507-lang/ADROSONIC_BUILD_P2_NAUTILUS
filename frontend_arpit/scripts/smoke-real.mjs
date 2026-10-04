/**
 * smoke:real – end-to-end check against the RUNNING backend (default http://localhost:8000).
 * Uses the same paths and fields as the frontend. Prints PASS/FAIL per step; exit 1 on failure.
 *
 * Env: SMOKE_BASE_URL, SMOKE_INV_EMAIL, SMOKE_CLAIMANT_EMAIL, SMOKE_PASSWORD
 * (falls back to the frontend demo defaults in .env: VITE_DEMO_*).
 */
import fs from 'node:fs';

const env = Object.fromEntries(
  (fs.existsSync('.env') ? fs.readFileSync('.env', 'utf8') : '')
    .split(/\r?\n/)
    .filter((l) => l.includes('=') && !l.trim().startsWith('#'))
    .map((l) => [l.slice(0, l.indexOf('=')).trim(), l.slice(l.indexOf('=') + 1).trim()]),
);
const BASE = (process.env.SMOKE_BASE_URL || 'http://localhost:8000') + '/api/v1';
const INV =
  process.env.SMOKE_INV_EMAIL || env.VITE_DEMO_INVESTIGATOR_EMAIL || 'investigator@demo.in';
const CLA = process.env.SMOKE_CLAIMANT_EMAIL || env.VITE_DEMO_CLAIMANT_EMAIL || 'ravi@demo.in';
const PWD = process.env.SMOKE_PASSWORD || env.VITE_DEMO_PASSWORD || 'demo';

let failed = 0;
const pass = (m) => console.log(`PASS ${m}`);
const fail = (m) => {
  failed++;
  console.log(`FAIL ${m}`);
};
async function call(path, { token, ...init } = {}) {
  const headers = new Headers(init.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData))
    headers.set('Content-Type', 'application/json');
  const r = await fetch(BASE + path, { ...init, headers });
  const type = r.headers.get('content-type') || '';
  const body = type.includes('json') ? await r.json() : await r.arrayBuffer();
  return { status: r.status, body };
}
async function login(email) {
  const r = await call('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password: PWD }),
  });
  const token = r.body?.token ?? r.body?.access_token;
  if (r.status !== 200 || !token)
    throw new Error(`login ${email} → HTTP ${r.status} ${JSON.stringify(r.body).slice(0, 160)}`);
  return token;
}

try {
  const h = await fetch(BASE + '/health').catch(() => null);
  if (!h) throw new Error(`backend unreachable at ${BASE}`);
  pass(`health (${h.status})`);

  const inv = await login(INV);
  pass(`investigator login (${INV})`);

  const sample = ['public/samples/ai_car.jpg', 'public/samples/genuine_car.jpg'].find((f) =>
    fs.existsSync(f),
  );
  if (!sample) throw new Error('no sample image in public/samples');
  const form = new FormData();
  form.append(
    'file',
    new Blob([fs.readFileSync(sample)], { type: 'image/jpeg' }),
    sample.split('/').pop(),
  );
  const started = await call('/analyze/image', { method: 'POST', body: form, token: inv });
  if (started.status !== 202 || !started.body?.job_id)
    throw new Error(
      `analyze/image → ${started.status} ${JSON.stringify(started.body).slice(0, 160)}`,
    );
  pass(`analyze/image accepted (job ${started.body.job_id})`);

  let job;
  const t0 = Date.now();
  for (let i = 0; i < 120; i++) {
    job = (await call(`/jobs/${started.body.job_id}`, { token: inv })).body;
    if (job.status === 'done' || job.status === 'failed') break;
    await new Promise((r) => setTimeout(r, 1000));
  }
  if (job?.status !== 'done')
    throw new Error(`job ended as ${job?.status}: ${JSON.stringify(job?.error)}`);
  pass(`job done in ${((Date.now() - t0) / 1000).toFixed(1)} s (${job.steps?.length ?? 0} steps)`);

  const res = await call(`/results/${job.result_id}`, { token: inv });
  const r = res.body;
  const required = ['id', 'mode', 'overall', 'evidence', 'artifacts'];
  const missing = required.filter((k) => !(k in (r ?? {})));
  if (res.status !== 200 || missing.length)
    fail(`result shape (HTTP ${res.status}, missing ${missing.join(', ')})`);
  else
    pass(
      `result ${r.id}: ${r.overall.band} ${Math.round(r.overall.risk * 100)}% · ${r.evidence.length} evidence · why_this_score ${r.why_this_score ? 'yes' : 'no'} · checks_run ${r.checks_run?.length ?? 0}`,
    );

  const urls = JSON.stringify(r.artifacts ?? {}).match(/\/api\/v1\/artifacts\/[^"]+/g) ?? [];
  if (urls.length) {
    const a = await fetch(
      (process.env.SMOKE_BASE_URL || 'http://localhost:8000') + urls[0].replace(/\\u0026/g, '&'),
    );
    if (a.ok) pass(`signed artifact loads without auth header (${a.status})`);
    else fail(`signed artifact → HTTP ${a.status}`);
  } else console.log('INFO no artifact URL in this result');

  const pdf = await call(`/results/${r.id}/report.pdf`, { token: inv });
  if (pdf.status === 200) pass('report.pdf');
  else fail(`report.pdf → ${pdf.status}`);
  const q = await call('/queue?limit=5', { token: inv });
  if (q.status === 200 && Array.isArray(q.body?.items)) pass(`queue (${q.body.items.length} rows)`);
  else fail(`queue → ${q.status}`);
  const hist = await call('/history?page=1&page_size=5', { token: inv });
  if (hist.status === 200 && Array.isArray(hist.body?.items))
    pass(`history (${hist.body.items.length} rows)`);
  else fail(`history → ${hist.status}`);
  for (const p of [
    '/analytics/summary',
    '/analytics/trends?range=7d',
    '/network/rings',
    '/network/graph',
  ]) {
    const x = await call(p, { token: inv });
    if (x.status === 200) pass(p);
    else fail(`${p} → ${x.status}`);
  }

  const cla = await login(CLA);
  pass(`claimant login (${CLA})`);
  const mine = await call('/claims/mine', { token: cla });
  if (mine.status === 200) pass(`claims/mine (${(mine.body?.items ?? mine.body)?.length ?? 0})`);
  else fail(`claims/mine → ${mine.status}`);
  const pol = await call('/policies/mine', { token: cla });
  if (pol.status === 200) pass(`policies/mine (${(pol.body?.items ?? pol.body)?.length ?? 0})`);
  else fail(`policies/mine → ${pol.status}`);
  const forbidden = await call('/queue', { token: cla });
  if (forbidden.status === 403) pass('claimant blocked from /queue (403)');
  else fail(`claimant /queue → ${forbidden.status} (expected 403)`);
} catch (e) {
  fail(e.message);
}
console.log(failed ? `\n${failed} step(s) failed.` : '\nAll smoke steps passed.');
process.exit(failed ? 1 : 0);
