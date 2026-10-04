import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
if (fs.existsSync('public/mockServiceWorker.js')) process.exit(0);
try {
  execFileSync(
    process.platform === 'win32' ? 'npx.cmd' : 'npx',
    ['msw', 'init', 'public', '--save'],
    { stdio: 'inherit' },
  );
} catch {
  console.warn('MSW worker is not generated yet. Run: npx msw init public --save');
}
