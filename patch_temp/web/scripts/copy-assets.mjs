/**
 * Copies browser WASM assets into public/ so the claimant liveness guidance and QR check work
 * without any CDN (offline demo). Runs automatically before `npm run dev` and `npm run build`.
 */
import fs from 'node:fs';
import path from 'node:path';

const copies = [
  ['node_modules/@mediapipe/tasks-vision/wasm', 'public/mediapipe/wasm'],
  ['node_modules/zxing-wasm/dist/reader/zxing_reader.wasm', 'public/zxing/zxing_reader.wasm'],
];
for (const [src, dst] of copies) {
  if (!fs.existsSync(src)) {
    console.log(`skip (missing): ${src}`);
    continue;
  }
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.cpSync(src, dst, { recursive: true });
  console.log(`copied ${src} -> ${dst}`);
}
const model = 'public/mediapipe/face_landmarker.task';
if (!fs.existsSync(model)) {
  console.log(
    'NOTE: face_landmarker.task not found locally – run `npm run fetch:models` once (needs internet).',
  );
  console.log('      Until then the app uses the online model, or manual capture if offline.');
}
