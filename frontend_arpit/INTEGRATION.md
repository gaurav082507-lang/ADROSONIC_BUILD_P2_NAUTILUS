# Lucen AI integration matrix (aligned to contract/openapi.json – 2026-10-04)

**Status:** raw types are generated from the backend contract (`src/api/generated.d.ts`),
`npm run contract:check` passes with 0 errors, and the mock server serves real-contract shapes.
See MISSING_API.md for the few additive backend fields still needed.

## Contract differences already handled
| Area | Real contract | Frontend now |
|---|---|---|
| Login | `{token, user:{id,name,email,role,preferred_lang}}` | `adaptLogin` (also accepts legacy `{access_token, role}`) |
| Job | `error` is a string | `adaptJob` accepts string or object |
| Result summary | `overall.summary` | read from `overall` |
| Pipeline scores | `PipelineScore {pipeline, risk, authenticity, band, confidence, evidence_ids}` | `score()`; null = "Not analysed" |
| Evidence | `calibrated_score`, `effective_weight`, `details` | mapped to score / weight |
| Quality warnings | `[{code, message}]` | messages shown |
| Why this score | per-pipeline `evidence_contributions` + `formula`, `overrides_applied`, `quality_gates_applied`; flat `items` | table + formulas + overrides + gates |
| Checks run | `checks_run` (fallback `detector_status`) | ok/skipped/failed table |
| Identity | `liveness {performed, passed, challenges[{name, ok, ms}]}`, `aadhaar_qr {found, signature_valid, mode, comparisons[{field, printed, qr, match}], photo_similarity}`, face similarity from `ID-FACE-*` details | Identity tab with QR table + TEST-key badge |
| Duplicate | from `IMG-DUP-*` evidence details | banner |
| Claim checks | from `CLM-X-*` / `CLM-*` evidence | Claim checks tab |
| Timeline | `GET /results/{id}/timeline` `{events, contradictions, undated}` | Timeline tab fetches it |
| Queue | `{items:[{claim_id, claimant_name, type, submitted_at, band, overall_risk, top_reason, status, can_fast_track}]}` | `adaptQueue` |
| History | `page`, `page_size`; items `{id, created_at, mode, overall_risk, overall_band, top_reason, evidence_count}` | `adaptHistory` |
| Policies | `{policy_number, claim_type, sum_insured, start_date, end_date, vehicle_or_asset}` (no `id`) | `id = policy_number` |
| Claimant | `/claims/mine` `{claim_id, policy_label, …}`; `/status` `{claim_id, status, timeline[{name,status,date}], decision{outcome, reason_category_label, claimant_message, next_steps, can_resubmit, slots_to_resubmit}}`; `/evidence-timeline` | merged status view; resubmit only when requested |
| Create claim | `evidence` (repeated), `slot_names`, `capture_sources`, `evidence_metadata`, `id_capture_source`, `selfie_capture_source`, `consent_voice_processing` | sent exactly |
| Liveness | session has `spoken_code`; verify = `frames` + `frame_metadata` | burst capture, code shown |
| Voice | transcribe = `file` + `language`; `extracted.amount_claimed`; languages `{code, name, native}` | aligned |
| Decision | `claimant_message` (single) + `internal_note` + `slots_to_resubmit` | message in the chosen language |
| Actions | `ActionItem {created_at, actor, action, from_status, to_status, internal_note}` | audit log |

## Screen → endpoint map
| Screen | Hook / action | Raw endpoint | Adapter / VM | Status |
|---|---|---|---|---|
| Login | `useLogin` | `POST /auth/login` | session + UserVM | wired provisional |
| Investigator shell | auth session | `GET /auth/me` | session role | wired provisional |
| Analyze image | `useJobPolling` | `POST /analyze/image`, `GET /jobs/{id}` | JobVM | wired provisional |
| Analyze document | `useJobPolling` | `POST /analyze/document`, `GET /jobs/{id}` | JobVM | wired provisional |
| Analyze full claim | `useJobPolling` | `POST /analyze/claim`, `GET /jobs/{id}` | JobVM | wired provisional |
| Result | `useResult` | `GET /results/{id}` | ResultVM | wired provisional |
| Result evidence | raw download/result blocks | `GET /results/{id}/evidence` | EvidenceVM | wired provisional |
| Result timeline | result block | `GET /results/{id}/timeline` | TimelineVM | wired provisional |
| Reports | download helper | `GET /results/{id}/report.pdf|json` | Blob | wired provisional |
| Delete result | mutation | `DELETE /results/{id}` | none | wired provisional |
| Decisions | `DecisionDialog` | `POST /results/{id}/decision/draft`, `POST /results/{id}/decision` | draft VM | wired provisional |
| Queue | `useQueue` | `GET /queue` | QueueRowVM | wired provisional |
| Fast-track | mutation | `POST /claims/{id}/fast-track` | none | wired provisional |
| History | `useHistory` | `GET /history` | HistoryRowVM | wired provisional |
| Dashboard | queue + history | `GET /queue`, `GET /history` | derived recent-claim KPIs | wired provisional |
| Claimant policy | `usePolicies` | `GET /policies/mine` | PolicyVM | wired provisional |
| Claimant submit | raw mutation | `POST /claims` | Claim status | wired provisional |
| Claimant status | `useClaimStatus` | `GET /claims/{id}/status` | ClaimStatusVM | wired provisional |
| Claimant evidence timeline | raw | `GET /claims/{id}/evidence-timeline` | ClaimStatusVM timeline | wired provisional |
| Identity session | raw | `POST /identity/liveness/session` | session data | wired provisional |
| Identity verify | raw | `POST /identity/liveness/verify` | server result | wired provisional |
| Dashboard KPIs (analytics on) | `useAnalyticsSummary` | `GET /analytics/summary` | AnalyticsSummaryVM | wired provisional (flag `analytics`) |
| Analytics page | `useAnalyticsTrends` | `GET /analytics/trends?range=&type=` | TrendsVM | wired provisional (flag `analytics`) |
| Network graph | `useNetworkGraph` | `GET /network/graph?focus_type=&focus_id=&hops=&min_strength=&limit=` | GraphVM | wired provisional (flag `network`) |
| Ring list | `useRings` | `GET /network/rings` | RingVM[] | wired provisional (flag `network`) |
| Ring detail drawer | `useRing` | `GET /network/rings/{ring_id}` | RingDetailVM | wired provisional (flag `network`) |
| Ring status | `useRingStatus` | `POST /network/rings/{ring_id}/status` `{status, note}` | none | wired provisional (note required for confirmed/dismissed) |
| Ring case file | download helper | `GET /network/rings/{ring_id}/report.pdf|json` | Blob | wired provisional |
| Result → Network tab | `useClaimNetwork` | `GET /claims/{id}/network` | ClaimNetworkVM | wired provisional (flag `network`) |
| Result → Story review tab | result block | `result.story` in `GET /results/{id}` | StoryVM | wired provisional (flag `story`) |
| Result → Voice tab | result block | `result.voice` in `GET /results/{id}` | VoiceVM | wired provisional (flag `voice`) |
| Wizard step 2 transcription | `useTranscribe`, `useVoiceLanguages` | `POST /voice/transcribe`, `GET /voice/languages` | TranscriptionVM | wired provisional (flag `voice`) |
| Claim submit with voice | raw | `POST /claims` + `voice_audio`, `consent_voice_processing`, `description_lang` | – | wired provisional |

## OpenAPI integration

When `contract/openapi.json` arrives:

1. Put it at `contract/openapi.json`.
2. Put captured fixtures under `contract/fixtures/`.
3. Run `npm run gen:api`.
4. Run `npm run fixtures:sync`.
5. Run `npm run contract:check`.
6. Reconcile only `src/api/raw/`, `src/api/schemas/`, adapters and provisional fixtures.
7. Set `VITE_USE_MOCKS=0`.
8. Run `npm run smoke:real` against the backend on port 8000.

## Feature flags

`VITE_FEATURES` is a comma list: `voice,network,analytics,story`.
- Mock mode (`VITE_USE_MOCKS=1`) with `VITE_FEATURES` empty: all features on.
- Real mode with `VITE_FEATURES` empty: all four off (their pages show a "not enabled" card, never fabricated data).
- Integration day: set `VITE_FEATURES=voice,network,analytics,story` once the backend exposes those endpoints.

## Resilience built into the adapters
- List endpoints accept either a bare array or a `{items, total}` envelope (`asList`).
- The result schema keeps unknown backend fields (`.passthrough()`), so new blocks never disappear silently.
- `result.voice` may or may not carry a pipeline score; the voice score card shows only when `risk` is present, the Voice tab shows whatever details exist.
- Graph edges pointing outside a truncated subgraph are dropped instead of crashing the canvas.
