# Lucen AI: Frontend Specification

Put this file at `docs/LUCEN_AI_FRONTEND_SPEC.md`. It is the single brief for anyone building or replacing the Lucen AI user interface. The backend is the source of truth: every request and response shape is in `docs/openapi.json`, and this file explains **what each screen shows, which endpoint it calls, and how it behaves**.

Companion files: `LUCEN_AI_ARCHITECTURE.md` (§ numbers below), `LUCEN_AI_FEATURES.md` (F numbers below), `docs/API.md`, `docs/openapi.json`.

---

## 0. Rules that apply to every screen

1. **The backend decides, the UI displays.** The UI never computes a score, band, confidence or reason. It renders what the API returns.
2. **Band is never colour alone.** Every band shows the word (LOW / MEDIUM / HIGH), an icon and a colour.
3. **The three required scores come first and largest:** Image authenticity, Document authenticity, Overall fraud likelihood. Identity and Voice are smaller cards below.
4. **Claimants never see scores, bands, evidence ids, heatmaps, percentages or detector names.** They see status, the decision, the reason category and next steps only (§7.6).
5. **Every screen has four designed states:** loading, empty, error (with retry), success.
6. **Boxes are normalised.** Every `bbox` is `{page, x, y, w, h}` as fractions of the page/image. Multiply by the rendered width/height; recompute on resize (§8.7).
7. **One error handler.** All errors arrive as `{ "error": { "code", "message", "details" } }`. Show `message`; map `code` to a friendly action (table in §3.4).
8. **Accessible:** keyboard reachable, visible focus, text contrast ≥ 4.5:1, real `<input type="file">` behind every dropzone, `prefers-reduced-motion` respected.
9. **Bilingual claimant portal:** English and हिंदी switch on every claimant screen.

---

## 1. Recommended stack

| Concern | Choice |
|---|---|
| Framework | React 18 + Vite (JavaScript or TypeScript) |
| Styling | Tailwind CSS + shadcn/ui |
| Server state | TanStack Query (job polling, caching, retries) |
| Routing | react-router-dom |
| Uploads | react-dropzone |
| PDF view | react-pdf (pdf.js), or the backend's rendered page images |
| Charts | Recharts |
| Map | react-leaflet + OpenStreetMap |
| Network graph | react-force-graph-2d |
| Liveness camera | @mediapipe/tasks-vision (Face Landmarker) |
| Icons | lucide-react |

Any stack works if it follows the API contract and the rules above.

---

## 2. Design system

| Element | Investigator portal | Claimant portal |
|---|---|---|
| Background | Light slate | White |
| Text | Ink blue | Ink blue |
| Accent | Evidence yellow, used for numbered evidence markers pinned on images and documents | Primary action colour only |
| Layout | Left sidebar (Dashboard, Queue, Analyze, Analytics, Network) + top bar with claim search; 12-column grid, max width ~1200 px | No sidebar, mobile-first, one main action per screen |
| Typography | Large numerals for scores | Large, simple text |

**Band tokens**

| Band | Colour | Icon | Word | Default range |
|---|---|---|---|---|
| LOW | Green | check-circle | LOW | risk < 0.35 |
| MEDIUM | Amber | alert-triangle | MEDIUM | 0.35 ≤ risk < 0.65 |
| HIGH | Red | octagon-alert | HIGH | risk ≥ 0.65 |

**Severity tokens** (evidence cards and boxes): low / medium / high, same colour family as bands, always with the word.

**Confidence** (`high | medium | low`) is shown as a separate pill next to the band, never merged into it. When confidence is not high, show a one-line caveat: "Some checks were limited, see Checks run."

---

## 3. API conventions

### 3.1 Base

- Base path: `/api/v1`. In dev, Vite proxies `/api` to `http://localhost:8000`. In production, `VITE_API_BASE_URL`.
- Uploads are `multipart/form-data`; everything else JSON.
- Auth (from backend Prompt 6 onward): `Authorization: Bearer <token>` from `POST /auth/login`. Store the token in memory plus `sessionStorage` (wrapped in try/catch). On `401` go to `/login`; on `403` show "You don't have access to this page".

### 3.2 Async job pattern (all analysis)

```
POST /analyze/{image|document|claim}  → 202 { job_id }
GET  /jobs/{job_id}   every 1000 ms while status is queued|running
       → { status, steps:[{name,status,duration_ms}], result_id, error }
when status = done   → GET /results/{result_id}
when status = failed → show error.message + "Try again"
```

TanStack Query: `refetchInterval: d => (d?.status === 'done' || d?.status === 'failed') ? false : 1000`.

Step names are prefixed per input in claim mode (`img_1:ai_detector`, `doc:ocr`). Group them by prefix in the progress list.

### 3.3 Mock mode

`VITE_USE_MOCKS=1` uses the frontend mock layer; backend `MOCK_ANALYSIS=1` returns canned LOW / MEDIUM / HIGH results with every field. Build every screen against mocks first.

### 3.4 Error codes → UI behaviour

| Code | HTTP | UI behaviour |
|---|---|---|
| `UNSUPPORTED_FILE_TYPE` | 415 | Inline under the dropzone: "Only JPG, PNG, WebP and PDF are supported." |
| `FILE_TOO_LARGE` | 413 | Inline: "This file is over 15 MB." |
| `TOO_MANY_PAGES` | 422 | Inline: "Only the first 10 pages will be analysed." (warning, not a blocker if the backend accepted it) |
| `TOO_MANY_FILES` | 422 | Inline: "Up to 6 photos per claim." |
| `CORRUPT_FILE` | 422 | Inline: "This file could not be opened." |
| `NO_INPUT` | 422 | Disable Submit until a file is added |
| `JOB_NOT_FOUND` / `RESULT_NOT_FOUND` | 404 | Full-page "Not found" with link back to Queue/History |
| `JOB_TIMEOUT` | — (job failed) | "Analysis took too long. Try again." + retry |
| `RATE_LIMITED` | 429 | Toast: "Too many requests, wait a moment." |
| `NOT_AUTHENTICATED` | 401 | Redirect to `/login` |
| `FORBIDDEN_ROLE` | 403 | "You don't have access to this page." |
| `INTERNAL_ERROR` | 500 | "Something went wrong." + retry; never show technical detail |

---

## 4. Route map

| Route | Screen | Portal | Backend status |
|---|---|---|---|
| `/` | Landing | Public | Static |
| `/login` | Demo login | Public | Prompt 6 |
| `/claim/new` | 5-step claim wizard | Claimant | Prompts 6–8 |
| `/claim/:id` | Claim status + "Your evidence" | Claimant | Prompts 6–7 |
| `/app` | Dashboard | Investigator | Prompt 9 |
| `/app/queue` | Triage queue | Investigator | Prompt 6 (use `/history` until then) |
| `/app/analyze` | Analyze (Image / Document / Full claim) | Investigator | **Available now** |
| `/app/results/:id` | Result / case page | Investigator | **Available now** (identity, voice, story, timeline tabs later) |
| `/app/history` | History (temporary until Queue) | Investigator | **Available now** |
| `/app/network` | Fraud network | Investigator | Prompt 7 |
| `/app/analytics` | Trend analytics | Investigator | Prompt 9 |

"Available now" = backend Prompts 1–5 done. Build later screens against mock data until their endpoints exist.

---

## 5. Investigator screens

### 5.1 Analyze page (`/app/analyze`), F16. Required for demo steps 1 and 2.

**Purpose:** upload files directly and run an analysis.

**Layout:** three tabs: **Image**, **Document**, **Full claim**. Each tab is a separate upload with its own endpoint. Below the tabs, a "Try a sample" row with one-click demo files.

| Tab | Inputs | Endpoint |
|---|---|---|
| Image | 1 image (JPG/PNG/WebP, ≤ 15 MB) | `POST /analyze/image` field `file` |
| Document | 1 PDF or bill image (≤ 15 MB, ≤ 10 pages) | `POST /analyze/document` field `file` |
| Full claim | 0–6 images, 0–1 document, optional ID photo, optional selfie, optional metadata form | `POST /analyze/claim` fields `image[]`, `document`, `id_photo`, `selfie`, `metadata` (JSON string) |

**Metadata form (Full claim, all optional):** claim date, incident date, claimed amount (₹), claimant name, claim type (motor / health / property).

**Flow:** choose files → client-side type/size check → Analyze → **progress list** (each step with spinner, ✓, ✗ or "skipped" and duration, grouped by input) → on done, navigate to `/app/results/:result_id`.

**States:** empty dropzone with hint text; file preview thumbnail (image) or file name + page count (PDF); inline validation errors (§3.4); job failed panel with retry; Analyze disabled until valid.

### 5.2 Result / case page (`/app/results/:id`), F17–F23

**Data:** `GET /results/{id}`.

**Top section (always first):**

1. **Overall card (largest):** band badge (word + icon + colour), risk as a percentage, confidence pill, the `summary` paragraph, `recommended_action`.
2. **Score row:** Image authenticity, Document authenticity (gauges showing authenticity % = 1 − risk, plus the band word). If a pipeline did not run, show "Not analysed", not 0.
3. **Smaller cards:** Identity, Voice (show "Not analysed" until those pipelines exist).
4. **Quality warnings banner** if `quality_warnings` is non-empty.
5. **Duplicate banner** if `IMG-DUP-01` is present (both thumbnails, similarity, link to the earlier claim). Prompt 7.

**Tabs:**

| Tab | Content | Fields used |
|---|---|---|
| Image | Viewer with **Original / Heatmap / Side-by-side**, opacity slider, numbered evidence-yellow markers at each `bbox`; label which map is shown ("regions with unusual compression/noise" vs "regions the AI detector relied on"). Multiple images: thumbnail strip to switch (`image_results[]`) | `artifacts`, `evidence[].bbox`, `image_results` |
| Document | Page viewer (backend page images or react-pdf) with page navigation; boxes drawn over flagged fields; **flagged-fields table** (field, value, reason, severity). Hover a row ↔ highlight its box and vice versa | `artifacts.pages`, `evidence[].bbox`, `evidence[].field`, `evidence[].page` |
| All evidence | Evidence cards sorted by contribution; filter by pipeline and severity | `evidence[]` |
| Why this score | Per pipeline: table of evidence id, title, w, p, push (w·p), contribution %; the formula string with real numbers; overrides applied; quality gates applied | `why_this_score` |
| Checks run | Every detector with ok / skipped / failed, duration, reason | `checks_run` |
| Identity | Liveness checklist, ID vs selfie match, Aadhaar QR printed-vs-QR table (mismatches highlighted). Prompt 6 | `identity`, `liveness`, `aadhaar_qr` |
| Voice | Audio player, original transcript, English translation, synthetic-voice gauge. Prompt 8 | `voice` |
| Story | Contradictions and consistent points, each linked to its evidence; label "For investigator review, not part of the score". Prompt 9 | `story` |
| Evidence timeline | Vertical timeline, red contradiction connectors with rule id, "Undated" group. Prompt 7 | `GET /results/{id}/timeline` |
| Location | Map with claimed pin and photo GPS pins, distance. Prompt 7 | metadata + evidence |

**Evidence card:** rank number (matches the marker on the image/page), title, plain-English reason, severity word, calibrated score bar, weight, contribution %, source, "Show on image/page" link.

**Actions bar:**
- **Download JSON** → `GET /results/{id}/report.json`
- **Download PDF report** → `GET /results/{id}/report.pdf`
- **Delete analysis** → confirm dialog → `DELETE /results/{id}` → back to History
- **Decision bar** (Approve / Reject / Request evidence / Escalate), Prompt 6: reject and request-evidence open a dialog pre-filled by `POST /results/{id}/decision/draft`; nothing is sent until "Send to claimant" (`POST /results/{id}/decision`). Show "What the claimant will see" preview.

**States:** skeleton while loading; `RESULT_NOT_FOUND` page; if confidence is low, the caveat line under the band.

### 5.3 History (`/app/history`), temporary until Queue

`GET /history?limit=&offset=&band=&mode=`. Table: date, mode, file names, band badge, overall risk, link. Filters: band, mode. Pagination. Empty state: "No analyses yet. Go to Analyze."

### 5.4 Triage queue (`/app/queue`), F15

`GET /queue?band=&type=&status=`. Risk-sorted table: claim id, claimant (masked), type, submitted, band, top reason, status. Filters. **Fast-track** button on LOW rows (one-click approve, `fast_track: true`).

### 5.5 Dashboard (`/app`), F14

`GET /analytics/summary`. KPI cards: claims today, fast-tracked, flagged, top flag reasons, 7-day sparkline. Link to Analytics.

### 5.6 Analytics (`/app/analytics`), F26

`GET /analytics/trends?range=7d|30d|90d&type=`. KPI row with change vs previous period; stacked LOW/MEDIUM/HIGH bars per day; flagged-rate and average-risk lines (7-day rolling dashed); top signals bar; by claim type; by modality; recycled evidence and rings per week; decisions per week; spike banner. Every chart has a text summary and a table toggle. Clicking a bar opens the Queue filtered.

### 5.7 Fraud network (`/app/network`), F25

`GET /network`. Force graph: claim nodes coloured by band (band word in tooltip), entity nodes as small grey dots, edges labelled with the shared item (phone / email / bank / image match). Click a claim node → result page.

---

## 6. Claimant screens

### 6.1 Landing (`/`) and Login (`/login`), F01–F02

Landing: one-line pitch, buttons "File a claim" and "Open investigator demo". Login: two cards ("I'm filing a claim" / "I work at an insurer"), demo users prefilled (password `demo`), role-based redirect.

### 6.2 Claim wizard (`/claim/new`), F03–F11

Progress indicator, Back/Next, state kept across steps.

| Step | Content | Endpoint |
|---|---|---|
| 1. Policy | Policy picker (`GET /policies/mine`), claim type, peril | — |
| 2. Your story | Language dropdown, mic button (≤ 90 s), live transcript + English translation, auto-filled date / time / amount / damaged items (all editable), map pin, typed description alternative | `POST /voice/transcribe` |
| 3. Verify it's you | Liveness: camera, oval guide, 3 random prompts (blink, turn, read a code), then ID card capture; Aadhaar QR read automatically | `POST /identity/liveness/session`, `POST /identity/liveness/verify`, `POST /identity/aadhaar-qr` |
| 4. Evidence | Guided capture slots by claim type (motor: full vehicle, damage close-up, number plate, repair estimate; health: bill, discharge summary, prescription; property: wide shot, close-up, invoice). Each slot: "Use camera" (verified capture) or "Upload" (unverified source) | held client-side |
| 5. Review | Summary, consent checkbox (mentions voice sent for transcription), Submit → toast "Claim submitted" → status page | `POST /claims` |

Fallback messages: "Camera blocked: allow camera access or upload a selfie instead"; voice failure → typed description.

### 6.3 Claim status (`/claim/:id`), F12–F13

`GET /claims/{id}/status`, `GET /claims/{id}/evidence-timeline`.
- Status timeline: Submitted → Under review → Decision.
- Decision notice: Approved / Rejected / More evidence needed, with the **claimant message** and next steps.
- "Your evidence" list: each item Received → Checked → Needs replacing.
- "Submit new evidence" panel when the reason allows resubmission → `POST /claims/{id}/resubmit`.
- **Never** show scores, bands, evidence ids, heatmaps or detector names.

---

## 7. Shared components

| Component | Responsibility |
|---|---|
| `RiskBadge` | Band word + icon + colour |
| `ConfidencePill` | high / medium / low |
| `ScoreGauge` | Semicircle gauge with % and band word; respects reduced motion |
| `FileDropzone` | Drag-and-drop + real file input, type/size validation, preview |
| `PipelineProgress` | Step checklist grouped by input prefix, spinners, durations |
| `EvidenceCard` / `EvidenceList` | Card per evidence; sort and filter |
| `ImageViewer` | Original / heatmap / side-by-side, opacity slider, markers |
| `PageViewer` | Document page with navigation |
| `BoxOverlay` | Draws normalised boxes; hover sync with cards and table rows; `ResizeObserver` |
| `FlaggedFieldTable` | Field, value, reason, severity; row ↔ box highlight |
| `WhyThisScore` | Push table + formula string + overrides + gates |
| `ChecksRunTable` | Detector status table |
| `QualityWarnings` | Banner |
| `ExportButtons` | JSON + PDF download |
| `ErrorState` / `EmptyState` / `LoadingSkeleton` | Standard states |
| `LanguageSwitch` | EN / हिंदी (claimant) |

---

## 8. Demo checklist for the UI

1. Analyze → Image → AI sample → HIGH with heatmap and reasons; genuine sample → LOW.
2. Analyze → Document → tampered invoice → boxes on the total and line items, flagged-fields table, hover sync.
3. Full claim → image + document → overall HIGH, "Why this score" shows the numbers.
4. Download the PDF report.
5. Every screen tested with the network unplugged (backend local) and with mocks.
6. Every error code in §3.4 shows the right message.
