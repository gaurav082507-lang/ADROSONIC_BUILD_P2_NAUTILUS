# Lucen AI: Frontend Build Prompts

How to use this:
1. Attach the three spec files to your coding AI (Cursor, Claude Code, Windsurf, etc.): `LUCEN_AI_ARCHITECTURE.md`, `LUCEN_AI_FOLDER_STRUCTURE.md`, `LUCEN_AI_FEATURES.md`.
2. Paste the **Master prompt** once at the start.
3. Then paste **Phase 1**, check its "Done when" list, and move on one phase at a time. Don't paste all phases together: smaller steps give working code.
4. The frontend runs entirely on mock data until the backend is ready (`VITE_MOCK=1`).

---

## Master prompt (paste first)

```
You are building the frontend of Lucen AI, an insurance-claim fraud detection
product for the ADROSONIC Build hackathon. Three spec files are attached:

- LUCEN_AI_ARCHITECTURE.md  → data contracts (§6, §6.8), API (§7, §7.5–§7.8),
                              frontend architecture (§8), analytics (§8.13)
- LUCEN_AI_FOLDER_STRUCTURE.md → exact file paths (section 2.2 frontend/)
- LUCEN_AI_FEATURES.md      → every screen, flow, state and acceptance criterion
                              (F01–F43). This file wins on anything the user sees.

Follow them exactly. Do not invent endpoints, fields or features that are not in
the specs. If something is ambiguous, pick the simplest option consistent with
the specs and leave a // DECISION: comment.

STACK (do not substitute):
React 18 + TypeScript (strict) + Vite, Tailwind CSS, shadcn/ui, TanStack Query,
react-router-dom v6, react-dropzone, react-pdf, Recharts, react-leaflet,
react-force-graph-2d, @mediapipe/tasks-vision, lucide-react, Vitest +
Testing Library. Fonts self-hosted with @fontsource (the demo must work offline).

NON-NEGOTIABLE RULES (from LUCEN_AI_FEATURES.md section 0):
1. The system recommends, a human decides. Nothing auto-approves or auto-rejects.
2. Claimant screens NEVER show scores, percentages, bands, evidence ids,
   detector names, heatmaps, metadata dates or internal notes.
3. On result pages, Image authenticity, Document authenticity and Overall fraud
   likelihood are shown first and largest. Identity and Voice are smaller cards.
4. A risk band is always word + icon + colour, never colour alone.
5. Every screen has loading, empty, error and success states. Errors say what
   happened and how to fix it. Empty states offer a next action.
6. Claimant portal: mobile-first (360 px), English/Hindi switch on every page.
   Investigator portal: desktop-first (1366 px and up), English.
7. Keyboard navigable, visible focus rings, prefers-reduced-motion respected,
   contrast at least 4.5:1, every chart has a table view.

DESIGN DIRECTION: "forensic evidence lab", calm and precise, not flashy SaaS.
- Palette (Tailwind tokens):
  paper   #F3F5F7  page background (cool light slate)
  surface #FFFFFF  panels
  ink     #14213D  primary text and primary buttons (deep ink blue)
  muted   #5B6578  secondary text
  rule    #D5DBE3  borders and dividers
  marker  #F2C230  evidence-yellow: numbered evidence markers and focus accents
  Bands:  LOW #2F7D5B (shield-check icon), MEDIUM #B7791F (alert-triangle icon),
          HIGH #B4232C (octagon-alert icon). Each with a 10% tint background.
- Type: IBM Plex Sans for everything; IBM Plex Mono only for real codes
  (claim ids like LC-1042, evidence ids like IMG-AI-01). Sentence case
  everywhere. No all-caps labels, no eyebrow text above headings.
- Signature element (spend boldness here only): numbered evidence-yellow
  circular markers drawn on images and PDF pages. Marker 1 on the image
  corresponds to evidence card 1; hovering either highlights both.
- Radius: 6 px on inputs/buttons, 10 px on panels. One subtle border, no
  heavy shadows, no gradients, no decorative animation. Motion only in
  response to user actions (dialog open, tab change, gauge fill once on load).
- Copy: plain verbs, active voice, buttons say exactly what happens
  ("Send to claimant", "Analyze photo"), toasts reuse the same verb.

ARCHITECTURE RULES:
- All API calls go through src/api/client.ts (base URL /api, Bearer token from
  AuthProvider, maps error JSON from §7.2 to typed errors; 401 → logout +
  redirect to /login).
- One typed function per endpoint in src/api/endpoints.ts.
- Until the backend exports OpenAPI, hand-write src/api/types.ts matching §6
  and §6.8 exactly; later it is replaced by the generated schema.d.ts.
- Mock layer: when import.meta.env.VITE_MOCK === "1", endpoints.ts returns
  fixtures from src/mocks/ with a 300–800 ms delay. Mock jobs progress through
  steps over ~4 seconds. Include LOW, MEDIUM and HIGH results matching demo
  scenarios A–D in LUCEN_AI_FEATURES.md F42.
- Server state in TanStack Query; wizard draft in a React context + reducer;
  no Redux. No localStorage except the auth token in sessionStorage.

Work phase by phase. After each phase: list files created, run type-check
and tests, and report anything not finished. Reply "Ready for Phase 1" now.
```

---

## Phase 1: Foundation (setup, design system, auth, layouts, mocks)

```
PHASE 1: foundation. Build only this:

1. Vite + React + TS project per LUCEN_AI_FOLDER_STRUCTURE.md 2.2: package.json
   name "lucen-ai", index.html title "Lucen AI", vite.config.ts with /api proxy
   to http://localhost:8000, Tailwind config with the Master-prompt tokens,
   shadcn/ui installed (button, card, tabs, dialog, select, checkbox, input,
   textarea, badge, tooltip, toast, table, skeleton, sheet, progress).
2. src/lib/format.ts: score→"%", band→{word, icon, colour classes}, INR
   formatting (₹1,80,000), Indian dates (22 Sep 2026).
3. Shared components: RiskBadge, ScoreGauge (semicircle, % + band word),
   EvidenceMarker (numbered yellow circle), EmptyState, ErrorState,
   PageSkeleton.
4. src/api/client.ts, endpoints.ts, types.ts and src/mocks/ fixtures for every
   endpoint in ARCHITECTURE §7, §7.5 and §7.8.
5. Auth (F02): AuthProvider, useAuth, RequireRole, LoginPage with the two
   cards and three one-click demo users (Ravi Kumar, Anil Verma = claimant;
   Priya Sharma = investigator; password "demo"), ?role= highlighting,
   role-based redirect, Log out, /forbidden page.
6. Layouts: PublicLayout, ClaimantLayout (top bar, language switch, no
   sidebar), InvestigatorLayout (sidebar: Dashboard, Queue, Analyze,
   Analytics, Network; top bar with claim-id search, user name, Log out).
7. i18n: tiny provider + en.json / hi.json for claimant strings.
8. LandingPage (F01) exactly as specified.
9. App.tsx with every route from ARCHITECTURE §8.12 + /app/analytics +
   /claims, each non-built page as a titled placeholder inside its layout.
10. Tests: RequireRole (claimant blocked from /app), ScoreGauge renders word
    and percent, format.ts.

Done when: `npm run dev` with VITE_MOCK=1 lets me land, log in as each demo
user, land in the right portal, and get /forbidden as a claimant on /app/queue.
```

---

## Phase 2: Must-haves (Analyze page + Result page)

```
PHASE 2: the scored core. Build F16, F17, F38 and the viewers. This is the
most important phase; polish it.

1. AnalyzePage (F16): tabs Image | Document | Full claim; FileDropzone with
   type/size validation and previews; SampleButtons (load files from
   public/samples in mock mode); ClaimMetadataForm on Full claim.
2. Job flow (F38): useSubmitAnalysis → job id → useJobPolling (1 s) →
   PipelineProgress checklist (spinner, tick + duration, skipped, failed) →
   navigate to /app/results/:id on completion.
3. ResultPage (F17), top to bottom exactly as in F17:
   header with Decision bar placeholder; DuplicateBanner slot; Overall
   fraud likelihood (largest: band, %, confidence, recommended action);
   ExplanationPanel (summary + top 3 reason chips); ScoreSummary (Image and
   Document gauges large, SecondaryScoreCard for Identity/Voice when present);
   WhyThisScore expandable (contributions, overrides, blend);
   tabs: Image | Document | All evidence | Checks run (other tabs come later
   as disabled placeholders); QualityWarnings banner; ExportButtons.
4. Viewers: ImageViewer (Original / Heatmap / Side by side, opacity slider,
   caption explaining what the heatmap means), PdfViewer (react-pdf, page
   nav), BoxOverlay (normalised bbox → pixels, ARCHITECTURE §8.7, numbered
   EvidenceMarker on each box), FieldTable. Hovering a box, marker, card or
   table row highlights all linked items.
5. EvidenceList + EvidenceCard (title, plain reason, calibrated score bar,
   weight, gated weight if reduced, source, "Show on image/page").
6. DetectorStatusTable (ok/skipped/failed, duration, note).
7. Tests: BoxOverlay maths, EvidenceCard, useJobPolling.

Done when: in mock mode, the "AI-generated damage photo" sample shows a HIGH
result with heatmap and markers; the "Tampered invoice" sample shows boxes on
the PDF linked to the field table; the three required scores are above the
fold at 1366×768.
```

---

## Phase 3: Claimant portal (wizard, status, evidence timeline)

```
PHASE 3: claimant portal. Build F03–F13. Mobile-first, bilingual.

1. WizardShell + wizardStore (F03): 5-dot stepper, sticky Back/Next, per-step
   validation message, unsaved-changes warning, completed steps clickable.
2. StepPolicy (F04): policies from /policies/mine, peril options by type.
3. StepStory (F05): language dropdown, VoiceRecorder (MediaRecorder, 90 s cap,
   level meter, timer), POST /voice/transcribe, TranscriptPanel (original +
   English read-only, auto-filled editable fields incl. damaged-item chips),
   Record again, Type instead, Web Speech fallback, all error cases in F05.
   LocationPicker (F07) with text-field fallback when tiles fail.
4. StepVerify: LivenessCapture (F08) — camera, oval guide, one prompt at a
   time from the session, MediaPipe Face Landmarker for guidance text only,
   frameSampler, verify call, pass/fail screens, 2 retries, upload-selfie
   fallback. Then IdCapture (F09) — camera with card frame or upload, tips,
   "couldn't read QR" message with continue option. Never show the claimant
   signature or match results.
5. StepEvidence (F10): CaptureSlotList from slotConfig (motor/health/property
   exactly as the F10 table), camera vs upload badges, HEIC message, no
   client-side compression.
6. StepReview (F11): summaries with Edit links, consent checkbox, POST /claims,
   confirmation screen with claim id.
7. MyClaimsPage and ClaimStatusPage (F12): stage tracker, DecisionNotice
   (approved / rejected with reason + message + next steps / evidence needed),
   ResubmitPanel, Contact support, poll every 10 s until decided.
8. MyEvidenceTimeline (F13): system events only, Received / Checked / Needs
   replacing chips.
9. Tests: WizardShell validation, claimant pages render no score/band/evidence
   fields even if the mock accidentally includes them.

Done when: as Ravi on a 360 px viewport, I can complete the wizard in Hindi
with mocks and see the claim at "Submitted"; as Anil, a mocked rejection shows
"Photo already used in another claim" with Submit new evidence.
```

---

## Phase 4: Investigator workflow (dashboard, queue, case tabs, decisions)

```
PHASE 4: investigator workflow. Build F14, F15, F18–F24.

1. DashboardPage (F14): KPI cards linking to filtered queue, top reasons,
   7-day sparkline, spike banner, recently decided.
2. QueuePage (F15): table with all columns in F15, default sort, filters in
   the URL, search, tags, Fast-track confirm dialog on LOW rows only.
3. Result page tabs:
   - IdentityTab (F18): liveness checklist, ID vs selfie with zone label,
     AadhaarQrPanel (signature status + mode label, printed-vs-QR table with
     red "Mismatch", QR photo vs printed photo, masked numbers).
   - VoiceTab (F19): player, transcripts, edited-field notes, spoof gauge.
   - StoryTab (F20): "For investigator review. Not part of the score."
     contradictions with quotes and evidence links; unavailable state.
   - DuplicateBanner (F21) with Compare side-by-side and Open claim.
   - EvidenceTimeline tab (F22): vertical timeline, source badges,
     red ContradictionConnector with rule id + sentence, Undated group,
     click event → evidence card.
   - LocationPanel (F23): stated pin vs photo GPS pins, skipped message.
4. Decisions (F24): DecisionBar; Approve and Escalate dialogs; Reject /
   Request evidence DecisionDialog that calls /decision/draft on open and
   shows: reason dropdown (preselected), Also-mention chips, editable message
   with 500-char counter, Regenerate, English / claimant-language toggle,
   items-to-replace checklist (Request evidence only), ClaimantPreview
   rendered exactly like ClaimStatusPage, internal note, "Template message"
   label when the draft fell back, Send to claimant / Cancel. Nothing is
   sent until Send. AuditList on the case page with message source and
   "edited" flag.
5. Tests: DecisionDialog (preselected reason, Cancel sends nothing, editing
   sets draft_edited), EvidenceTimeline ordering and Undated group.

Done when: scenario B in mocks shows the duplicate banner and a red timeline
contradiction, and rejecting it opens a pre-filled message with
PHOTO_PREVIOUSLY_USED; scenario D shows liveness failed, face mismatch and a
DOB mismatch in red.
```

---

## Phase 5: Network, analytics, export, polish

```
PHASE 5: finish. Build F25, F26, F27 and a polish pass.

1. NetworkPage (F25): react-force-graph-2d, claim nodes coloured by band
   with band word in tooltip, grey entity dots, labelled edges, filters
   (band, entity type, clusters ≥ 3), NodeSidePanel, 300-node cap;
   "Linked to N claims" chip on the case page opens the network centred.
2. AnalyticsPage (F26): filters (range, type, hide seeded data), KpiRow with
   change vs previous period, BandsOverTimeChart (stacked), FlaggedRateChart
   (two lines + dashed 7-day average), TopSignalsChart, ByClaimTypeChart,
   ByModalityChart, RingsChart, DecisionsChart, SpikeBanner; every chart has
   a one-line text summary and a Table toggle; clicking a bar opens the
   filtered queue. Mock data: 30 days with a 2-day reused-photo spike.
3. ExportButtons (F27): JSON download and PDF report link.
4. Polish pass across the whole app:
   - every page: loading skeleton, empty state with action, error with retry
   - keyboard-only walkthrough of wizard, queue, case page, decision dialog
   - 360 px check of every claimant page, 1366 px check of investigator pages
   - remove any copy that mentions "AI", "fraud", scores or detectors on
     claimant pages
   - Lighthouse accessibility ≥ 90 on the case page (target)
5. Final: run all tests, type-check, build; list any acceptance criterion
   from LUCEN_AI_FEATURES.md F01–F27 that is not met.

Done when: the full demo order in ARCHITECTURE §23 can be clicked through on
mock data with the network unplugged.
```

---

## Switching from mocks to the real backend

```
The backend is running at http://localhost:8000. Run
`python scripts/export_openapi.py` output into src/api/schema.d.ts, replace
src/api/types.ts imports with the generated types, fix every type error
without changing the UI behaviour, and run the app with VITE_MOCK=0. List any
endpoint whose real response differs from the mock fixtures.
```
