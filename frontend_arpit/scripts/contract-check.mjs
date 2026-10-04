/**
 * contract:check – verifies that every request the frontend makes (src/api/raw/endpoints.ts)
 * exists in contract/openapi.json with the same method, query parameters, multipart fields and
 * JSON body keys, and that captured fixtures carry the required top-level fields.
 *
 * ERROR  = will break at runtime (unknown path/method, missing required field, multipart field
 *          the backend silently drops, unknown query parameter).
 * WARN   = harmless but worth knowing (extra JSON key the backend ignores).
 * Exit code 1 when any ERROR is found.
 */
import fs from 'node:fs';
import path from 'node:path';

const SPEC = 'contract/openapi.json';
if (!fs.existsSync(SPEC)) {
  console.log('SKIP: contract/openapi.json not present. Provisional contract is active.');
  process.exit(0);
}
const spec = JSON.parse(fs.readFileSync(SPEC, 'utf8'));
const BASE = '/api/v1';
const src = fs.readFileSync('src/api/raw/endpoints.ts', 'utf8');
const errors = [];
const warns = [];
const oks = [];

const deref = (schema) => {
  if (!schema) return {};
  if (schema.$ref) return spec.components.schemas[schema.$ref.split('/').pop()] ?? {};
  if (schema.allOf) {
    // FastAPI wraps bodies as {allOf: [{$ref}]} – merge the parts.
    return schema.allOf.map(deref).reduce(
      (acc, part) => ({
        properties: { ...acc.properties, ...(part.properties ?? {}) },
        required: [...acc.required, ...(part.required ?? [])],
      }),
      { properties: {}, required: [] },
    );
  }
  return schema;
};

// Split endpoints.ts into `name: (...) => ...` members of the `raw` object.
const starts = [];
const re = /\n {2}([a-zA-Z]\w*): /g;
let m;
while ((m = re.exec(src))) starts.push({ name: m[1], index: m.index });
const members = starts.map((s, i) => ({
  name: s.name,
  body: src.slice(s.index, starts[i + 1]?.index ?? src.length),
}));

const specPaths = Object.keys(spec.paths);
function findSpecPath(template) {
  const clean = template.split('?')[0].replace(/\$\{qs\([\s\S]*$/, '');
  const tryMatch = (t) => {
    const escaped = (BASE + t).replace(/[.+^()|[\]\\]/g, '\\$&');
    const rx = new RegExp('^' + escaped.replace(/\$\{[^}]*\}/g, '[^/]+') + '$');
    return specPaths.filter((p) => rx.test(p.replace(/\{[^}]+\}/g, 'X')));
  };
  const hits = tryMatch(clean);
  // a trailing `${q}` is a pre-built query string, not a path segment
  return hits.length ? hits : tryMatch(clean.replace(/\$\{[^}]*\}$/, ''));
}

for (const { name, body } of members) {
  const call = /api\.(get|post|del)\b[^(]*\(\s*[`']([^`']*)[`']/.exec(body);
  if (!call) continue;
  const method = call[1] === 'del' ? 'delete' : call[1];
  const template = call[2];
  const matches = findSpecPath(template);
  if (!matches.length) {
    errors.push(
      `${name}: ${method.toUpperCase()} ${BASE}${template.split('$')[0]}… – path not in contract`,
    );
    continue;
  }
  const ops = matches.map((p) => ({ p, op: spec.paths[p][method] })).filter((x) => x.op);
  if (!ops.length) {
    errors.push(`${name}: method ${method.toUpperCase()} not allowed on ${matches.join(', ')}`);
    continue;
  }
  const unionProps = new Set(
    ops.flatMap(({ op }) =>
      Object.keys(deref(op.requestBody?.content?.['multipart/form-data']?.schema).properties ?? {}),
    ),
  );
  for (const { p, op } of ops) {
    const label = `${name}: ${method.toUpperCase()} ${p}`;
    const qsBlock = /qs\(\{([\s\S]*?)\}\)/.exec(body);
    if (qsBlock) {
      const sent = [...qsBlock[1].matchAll(/(?:^|[{,])\s*(\w+)\s*:/g)].map((x) => x[1]);
      const allowed = (op.parameters ?? []).filter((x) => x.in === 'query').map((x) => x.name);
      sent
        .filter((k) => !allowed.includes(k))
        .forEach((k) =>
          errors.push(
            `${label} – unknown query param "${k}" (allowed: ${allowed.join(', ') || 'none'})`,
          ),
        );
    }
    const content = op.requestBody?.content ?? {};
    if (content['multipart/form-data']) {
      const schema = deref(content['multipart/form-data'].schema);
      const props = Object.keys(schema.properties ?? {});
      const sent = [...new Set([...body.matchAll(/append\(\s*'([^']+)'/g)].map((x) => x[1]))];
      sent
        .filter((k) => !props.includes(k) && !(ops.length > 1 && unionProps.has(k)))
        .forEach((k) =>
          errors.push(`${label} – multipart field "${k}" is not accepted (backend drops it)`),
        );
      (schema.required ?? [])
        .filter((k) => !sent.includes(k))
        .forEach((k) => errors.push(`${label} – required multipart field "${k}" is never sent`));
    }
    if (content['application/json']) {
      const schema = deref(content['application/json'].schema);
      const props = Object.keys(schema.properties ?? {});
      const obj = /api\.post\b[^(]*\(\s*[`'][^`']*[`'],\s*\{([\s\S]*?)\}\s*\)/.exec(body);
      const keys = obj
        ? [
            ...new Set([
              ...[...obj[1].matchAll(/(?:^|[{,])\s*([a-z_]+)\s*:/g)].map((x) => x[1]),
              // shorthand properties: { email, password }
              ...[...obj[1].matchAll(/(?:^|[{,])\s*([a-z_]+)\s*(?=,|$)/g)].map((x) => x[1]),
            ]),
          ]
        : [];
      keys
        .filter((k) => !props.includes(k))
        .forEach((k) => warns.push(`${label} – JSON key "${k}" is ignored by the backend`));
      (schema.required ?? [])
        .filter((k) => !keys.includes(k))
        .forEach((k) => errors.push(`${label} – required JSON key "${k}" is never sent`));
    }
    oks.push(label);
  }
}

// Fixture shape check (top-level required keys).
const FIXTURE_SCHEMA = [
  [/^result_/, 'AnalysisResult'],
  [/^job_/, 'JobStatus'],
  [/^queue$/, 'QueueResponse'],
  [/^history$/, 'HistoryResponse'],
  [/^login_/, 'LoginResponse'],
  [/^claim_status$/, 'ClaimantStatusResponse'],
  [/^decision_draft$/, 'DecisionDraftResponse'],
];
const fixtureDir = 'contract/fixtures';
if (fs.existsSync(fixtureDir)) {
  for (const file of fs.readdirSync(fixtureDir).filter((f) => f.endsWith('.json'))) {
    const base = path.basename(file, '.json');
    const hit = FIXTURE_SCHEMA.find(([rx]) => rx.test(base));
    if (!hit) continue;
    const schema = spec.components.schemas[hit[1]];
    const data = JSON.parse(fs.readFileSync(path.join(fixtureDir, file), 'utf8'));
    (schema?.required ?? [])
      .filter((k) => !(k in data))
      .forEach((k) => errors.push(`fixture ${file}: missing required "${k}" (${hit[1]})`));
    oks.push(`fixture ${file} ↔ ${hit[1]}`);
  }
}

console.log(`contract:check – ${oks.length} request/fixture checks against ${SPEC}`);
warns.forEach((w) => console.log('  WARN  ' + w));
errors.forEach((e) => console.log('  ERROR ' + e));
if (errors.length) {
  console.log(
    `\n${errors.length} error(s). Fix src/api/raw/ (or ask the backend to accept the field).`,
  );
  process.exit(1);
}
console.log(
  `OK – every frontend request matches the contract${warns.length ? ` (${warns.length} warning(s))` : ''}.`,
);
