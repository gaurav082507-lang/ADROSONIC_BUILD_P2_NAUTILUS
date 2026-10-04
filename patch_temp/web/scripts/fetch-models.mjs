/** One-time download of the MediaPipe face landmarker model into public/ for offline demos. */
import fs from 'node:fs';

const url =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';
const out = 'public/mediapipe/face_landmarker.task';
fs.mkdirSync('public/mediapipe', { recursive: true });
const r = await fetch(url);
if (!r.ok) {
  console.error(`FAIL ${r.status} downloading ${url}`);
  process.exit(1);
}
fs.writeFileSync(out, Buffer.from(await r.arrayBuffer()));
console.log(`saved ${out} (${fs.statSync(out).size} bytes)`);
