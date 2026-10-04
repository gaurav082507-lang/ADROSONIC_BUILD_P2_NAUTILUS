# Lucen AI Web

Production-oriented React frontend for Lucen AI. The UI keeps the existing Lucen visual language while separating raw backend calls, response adapters and view-models.

## Setup

```bash
npm install
npx msw init public --save
cp .env.example .env
npm run dev
```

Mock mode is enabled by default with `VITE_USE_MOCKS=1`.

## Real backend integration

1. Put `contract/openapi.json` and `contract/fixtures/*.json` into the project.
2. Run `npm run gen:api`.
3. Run `npm run fixtures:sync`.
4. Run `npm run contract:check` and reconcile only `src/api/raw/` and `src/api/adapters/` for contract changes.
5. Set `VITE_USE_MOCKS=0`.
6. Run `npm run smoke:real` with the backend available.

The provisional contract is documented in the supplied frontend correction brief. The final OpenAPI contract wins when it arrives.

## Commands

- `npm run dev` — local development
- `npm run build` — strict TypeScript + Vite build
- `npm run lint` — ESLint
- `npm run format` — Prettier
- `npm run test` — Vitest
- `npm run gen:api` — generate OpenAPI types
- `npm run contract:check` — contract gate; skips clearly until OpenAPI exists
- `npm run fixtures:sync` — sync backend fixtures
- `npm run smoke:real` — backend health smoke

## Demo click path

Landing → Open console → Investigator → Analyze → Try sample → Analyse → live job steps → result → evidence/why/checks → decision draft → send → History.

Claimant → Claimant portal → policy → story → verification → evidence → consent → status.

## Feature flags (v0.4)

Voice, Network, Analytics and Story review are behind `VITE_FEATURES` (see `INTEGRATION.md`).
For the demo against the real backend use:

```
VITE_USE_MOCKS=0
VITE_FEATURES=voice,network,analytics,story
```

## Integration runbook (v0.5)

1. Backend running on :8000. Copy the latest `docs/openapi.json` to `contract/openapi.json`.
2. `npm run gen:api` – regenerate types. Then `npm run build`: any backend change shows up as a compile error in `src/api/raw` or `src/api/adapters`.
3. `npm run contract:check` – must print `OK`.
4. (Optional) capture real responses with `capture_fixtures.py --out <this>/contract`, then `npm run fixtures:sync` so mock mode serves real data.
5. `.env`: `VITE_USE_MOCKS=0`, `VITE_FEATURES=voice,network,analytics,story`, `VITE_DEMO_*` = the seeded accounts.
6. `npm run smoke:real` – login → analyze → result → signed artifact → PDF → queue → history → network/analytics → claimant checks.
7. `npm run dev` and walk through the demo.
