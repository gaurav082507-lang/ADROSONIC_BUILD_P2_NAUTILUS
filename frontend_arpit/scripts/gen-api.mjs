import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
if (!fs.existsSync('contract/openapi.json')) {
  console.log('SKIP: contract/openapi.json is not present yet. Add it, then run npm run gen:api.');
  process.exit(0);
}
fs.mkdirSync('src/api', { recursive: true });
execFileSync(
  process.platform === 'win32' ? 'npx.cmd' : 'npx',
  ['openapi-typescript', 'contract/openapi.json', '-o', 'src/api/generated.d.ts'],
  { stdio: 'inherit' },
);
