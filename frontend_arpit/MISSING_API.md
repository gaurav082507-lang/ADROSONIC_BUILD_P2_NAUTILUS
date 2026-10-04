# Backend items needed for a perfect fit (checked against contract/openapi.json, 2026-10-04)

`npm run contract:check` passes: every request the frontend sends matches the contract. These are
**additive** backend items the contract does not provide yet. The UI already handles their absence
gracefully, but these features stay incomplete until they exist:

| # | Needed | Why | UI behaviour until then |
|---|---|---|---|
| 1 | `result_id` on each `QueueItem` | The queue links to `/results/{result_id}`; the queue only has `claim_id` | Falls back to `claim_id` (works only if the backend accepts a claim id there) |
| 2 | `claim_id` on `AnalysisResult` | Network tab, audit log and entities need the claim | These panels show "not linked to a claim" |
| 3 | Voice details on the result (`voice_details: {language, transcript, translation_en, extracted, spoof}`) | The contract's `voice` is only a score | Voice tab shows score/status only |
| 4 | Confirm `slot_names` / `capture_sources` accept a **JSON array string**; `evidence_metadata` = JSON list of `{filename, slot, capture_source}` | Untyped strings in the contract | Frontend sends JSON arrays |
| 5 | Confirm `frame_metadata` = JSON list `[{index, timestamp, challenge}]` aligned with `frames` | Untyped string in the contract | Frontend sends that shape; 4 frames per challenge (12 total) |
| 6 | Confirm `damaged_items` accepts a JSON array string, `location` a JSON object string | Untyped strings | Frontend sends JSON |
| 7 | Typed response schemas for `artifacts`, `location`, `/results/{id}/timeline`, `/claims/{id}/network`, network + analytics endpoints | Currently `{}` in the contract | Adapters read the Prompt 8/10 field names defensively |
| 8 | Decision `action` values: frontend sends `approve`, `reject`, `request_evidence`, `escalate` | Contract types `action` as a free string | Confirm the backend accepts these lowercase values |
| 9 | Demo account emails/password | Docs disagree (`investigator@demo.in`/`demo` vs `investigator@lucen.ai`/`Password123!`) | Set `VITE_DEMO_*` in `.env`; the login form is editable |
