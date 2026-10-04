# Lucen web – claimant identity step patch (live face scan + Aadhaar QR check)

Fixes two live-demo issues in the claimant wizard (step 3 "Verify your identity"):

1. **Live face scan not appearing.** The camera used to start only AFTER the MediaPipe guidance
   model downloaded from two CDNs and the liveness session was created; any failure silently
   switched to "camera blocked". Now:
   - the camera starts FIRST, independently;
   - the liveness session has a visible "Try again";
   - the guidance model loads from local files first (CDN fallback), and if it fails the user
     still captures each challenge manually;
   - a failed verification restarts with new prompts instead of abandoning the camera;
   - specific messages for: not localhost/https (e.g. opened via 192.168.x.x), permission
     denied, no camera, camera in use by another app.
2. **No QR feedback.** After the ID card photo is taken/uploaded, the QR code is read in the
   browser (zxing-wasm, served locally) and the claimant sees "✓ Aadhaar Secure QR found – it
   will be verified securely" or "couldn't read a QR – retake". This is a readability
   pre-check only; the cryptographic verification still happens on the server and appears in
   the investigator's Identity tab. Claimant-safe wording (verified by the safety test).

Verified: npm run build ✅ · npm run lint 0 errors ✅ · npm run test 73/73 ✅ · Playwright with a
fake camera: video plays (640 px) with the CDN blocked, and a synthetic ID card's dense QR is
decoded ("Aadhaar Secure QR found").

## Files
NEW:      src/features/claims/IdCardInput.tsx, src/lib/cameraErrors.ts,
          src/lib/mediapipeAssets.ts, src/lib/qrCheck.ts, scripts/copy-assets.mjs,
          scripts/fetch-models.mjs, tests/verify-step.test.tsx
REPLACED: src/features/claims/VerifyStep.tsx
MERGE:    i18n_keys_to_merge.json → add the "en" keys to src/i18n/en.json and the "hi" keys to
          src/i18n/hi.json (add only; keep existing keys)
EDIT:
- package.json: dependency `"zxing-wasm": "^2.2.4"`; scripts `"predev": "node
  scripts/copy-assets.mjs"`, `"prebuild": "node scripts/copy-assets.mjs"`,
  `"fetch:models": "node scripts/fetch-models.mjs"`
- eslint.config.js: add `'public/mediapipe/**', 'public/zxing/**'` to `ignores`
- .gitignore: add `public/mediapipe/wasm/` and `public/zxing/`
- tests/setup.ts: add `if (!URL.createObjectURL) { URL.createObjectURL = () => 'blob:mock'; }`

## After applying (in web/)
npm install
npm run fetch:models     # one-time, needs internet: offline face guidance model
npm run build && npm run lint && npm run test
npm run dev              # predev copies the WASM assets automatically

## Demo tips
- Open http://localhost:5173 on the demo laptop itself (not an IP address) – browsers block
  the camera on plain-http network addresses.
- Allow the camera when Chrome asks; close Zoom/Teams before the demo.
- For the ID card, photograph the QR side flat and in good light.
