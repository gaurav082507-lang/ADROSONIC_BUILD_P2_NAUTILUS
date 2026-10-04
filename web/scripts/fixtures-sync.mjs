/**
 * fixtures:sync – copies captured backend responses (contract/fixtures/*.json, produced by
 * capture_fixtures.py) into src/mocks/fixtures/captured/. The mock server then serves these
 * REAL responses instead of the provisional ones (see src/mocks/fixtures/captured.ts).
 */
import fs from 'node:fs';
import path from 'node:path';

const src = 'contract/fixtures';
const dst = 'src/mocks/fixtures/captured';
if (!fs.existsSync(src)) {
  console.log('SKIP: contract/fixtures not present. Provisional fixtures remain active.');
  process.exit(0);
}
fs.mkdirSync(dst, { recursive: true });
const files = fs.readdirSync(src).filter((x) => x.endsWith('.json'));
for (const f of files) {
  fs.copyFileSync(path.join(src, f), path.join(dst, f));
  console.log(`SYNC ${f}`);
}
const used = [
  'login_investigator',
  'login_claimant',
  'job_done',
  'job_running',
  'result_high',
  'result_low',
  'result_image_high',
  'result_image_low',
  'result_document_high',
  'result_identity',
  'queue',
  'history',
  'policies',
  'claims_mine',
  'claim_status',
  'evidence_timeline',
  'claim_actions',
  'timeline',
  'decision_draft',
];
const missing = used.filter((u) => !files.includes(`${u}.json`));
console.log(`\n${files.length} fixture(s) synced.`);
if (missing.length) console.log(`Still provisional (no captured file): ${missing.join(', ')}`);
