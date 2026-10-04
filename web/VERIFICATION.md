# Verification log – v0.5.0 (2026-10-04, aligned to the real backend contract)

| Check | Result |
|---|---|
| `npm run gen:api` | Types generated from contract/openapi.json (41 endpoints) |
| `npm run build` | PASS, 0 TypeScript errors |
| `npm run lint` | PASS, 0 errors |
| `npm run test` | PASS – 10 files, 68 tests |
| `npm run contract:check` | PASS – every path, method, query param, multipart field and required field matches the contract (2 harmless warnings: extra EN/HI decision fields the backend ignores) |
| Browser walkthrough (mock mode serving real-contract shapes) | Login both roles · dashboard · queue → result · all 12 result tabs · history · claimant My claims + status (resubmit) · 0 page errors |

## v0.5 changes (real-contract alignment)
- Raw types derived from the generated OpenAPI types; ~20 field/shape differences adapted (see INTEGRATION.md).
- Real bugs fixed: liveness sent 3 frames (backend requires 8–40) → 4-frame burst per challenge; runtime validator would have rejected every real result → rewritten for the real contract.
- New: Aadhaar QR table + TEST-key badge, timeline from its endpoint, formulas/overrides/gates, decision + related-analysis banners, evidence cards with id/severity/score/weight, resubmit only when requested, editable login with VITE_DEMO_*.
- Integration tooling made real: `contract:check` (proved to catch wrong fields), `fixtures:sync` (captured responses now feed the mock server), `smoke:real` (live end-to-end flow).

## Integration runbook
1. `contract/openapi.json` + `contract/fixtures/*.json` from the running backend (capture_fixtures.py).
2. `npm run gen:api` → `npm run fixtures:sync` → `npm run contract:check`.
3. `.env`: `VITE_USE_MOCKS=0`, `VITE_FEATURES=voice,network,analytics,story`, `VITE_DEMO_*` = backend seed accounts.
4. Backend on :8000 → `npm run smoke:real` → `npm run dev` → demo click-path.
