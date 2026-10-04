# Lucen AI: Project Folder Structure (file 2 of 3)

**AI-Powered Synthetic Identity and Deepfake Claim Detection System**

This file is the complete repository layout for Lucen AI. Every folder and file the build needs is listed with its purpose and the spec section that defines its behaviour. Create files exactly at these paths; if a new file is needed, put it in the folder whose rule it fits (section 3) and add it here.

Companion files:
- `LUCEN_AI_ARCHITECTURE.md` (file 1): how everything works. Section numbers below (§) refer to it.
- `LUCEN_AI_FEATURES.md` (file 3): what each feature does for the user, with acceptance criteria. Feature ids (F01…) refer to it.

---

## 1. Top level

```
lucen-ai/
├── README.md                     # quick start, screenshots, architecture diagram, demo steps
├── docker-compose.yml            # frontend (nginx) + backend (uvicorn) services, shared ./data volume
├── Makefile                      # make dev | test | lint | data | train | seed | demo | openapi
├── .env.example                  # every environment variable, no values for secrets (§21.3)
├── .gitignore                    # models/*.keras, data/runtime/, data/synthetic/, .env, node_modules
├── .editorconfig
├── docs/
├── frontend/
├── backend/
├── training/
├── models/
├── data/
└── scripts/
```

---

## 2. Full tree

### 2.1 `docs/`

```
docs/
├── LUCEN_AI_ARCHITECTURE.md      # file 1
├── LUCEN_AI_FOLDER_STRUCTURE.md  # file 2 (this file)
├── LUCEN_AI_FEATURES.md          # file 3
├── API.md                        # endpoint notes; the OpenAPI schema is the reference
├── MODEL_CARDS.md                # one card per model: purpose, data, measured metrics, limits
├── EVALUATION.md                 # measured numbers and how they were produced (§17.8)
├── DEMO_SCRIPT.md                # timed 10-minute walkthrough (§23)
└── diagrams/                     # architecture and sitemap PNG/SVG used in slides
```

### 2.2 `frontend/`

```
frontend/
├── package.json                  # name: "lucen-ai"
├── jsconfig.json                 # editor autocomplete and the @/ import alias
├── components.json               # shadcn/ui config ("tsx": false, so components are generated as .jsx)
├── vite.config.js                # dev proxy /api → http://localhost:8000
├── tailwind.config.js            # design tokens (§8.8)
├── postcss.config.js
├── index.html                    # <title>Lucen AI</title>
├── Dockerfile                    # build → nginx static serve
├── nginx.conf                    # SPA fallback, /api proxy to backend
├── public/
│   ├── favicon.svg
│   └── samples/                  # thumbnails for "Try a sample" buttons
└── src/
    ├── main.jsx                  # bootstrap: QueryClientProvider, AuthProvider, I18nProvider, Router
    ├── App.jsx                   # route table, layouts, route guards
    │
    ├── routes/
    │   ├── LandingPage.jsx                   # F01
    │   ├── LoginPage.jsx                     # F02
    │   ├── NotFoundPage.jsx
    │   ├── ForbiddenPage.jsx                 # wrong role
    │   ├── claimant/
    │   │   ├── ClaimWizardPage.jsx           # /claim/new (F03–F11)
    │   │   ├── MyClaimsPage.jsx              # /claims (list of own claims)
    │   │   └── ClaimStatusPage.jsx           # /claim/:id (F12, F13)
    │   └── app/
    │       ├── DashboardPage.jsx             # /app (F14)
    │       ├── QueuePage.jsx                 # /app/queue (F15)
    │       ├── AnalyzePage.jsx               # /app/analyze (F16)
    │       ├── ResultPage.jsx                # /app/results/:id (F17–F24, F27)
    │       ├── NetworkPage.jsx               # /app/network (F25)
    │       └── AnalyticsPage.jsx             # /app/analytics (F26)
    │
    ├── layouts/
    │   ├── PublicLayout.jsx                  # landing, login
    │   ├── ClaimantLayout.jsx                # no sidebar, language switch, mobile-first
    │   └── InvestigatorLayout.jsx            # left sidebar + top bar with claim search
    │
    ├── features/
    │   ├── auth/
    │   │   ├── AuthProvider.jsx              # token + user in context, sessionStorage persistence
    │   │   ├── useAuth.js
    │   │   ├── RequireRole.jsx               # route guard → /login or /forbidden
    │   │   └── DemoUserCards.jsx             # one-click demo logins
    │   ├── claimant/
    │   │   ├── WizardShell.jsx               # stepper, back/next, step validation, draft state
    │   │   ├── wizardStore.js                # wizard draft state (React context + reducer)
    │   │   ├── StepPolicy.jsx                # F04
    │   │   ├── StepStory.jsx                 # F05, F07
    │   │   ├── StepVerify.jsx                # F08, F09
    │   │   ├── StepEvidence.jsx              # F10
    │   │   ├── StepReview.jsx                # F11
    │   │   ├── StatusTimeline.jsx            # F12 stages
    │   │   ├── DecisionNotice.jsx            # F12 reason + next steps
    │   │   ├── ResubmitPanel.jsx             # F12 new evidence upload
    │   │   └── MyEvidenceTimeline.jsx        # F13
    │   ├── voice/
    │   │   ├── VoiceRecorder.jsx             # MediaRecorder, 90 s cap, level meter
    │   │   ├── TranscriptPanel.jsx           # original + English, editable fields
    │   │   ├── useTranscribe.js              # POST /voice/transcribe
    │   │   └── webSpeechFallback.js          # browser speech API fallback
    │   ├── liveness/
    │   │   ├── LivenessCapture.jsx           # camera, oval guide, prompts, progress ring
    │   │   ├── useFaceLandmarker.js          # MediaPipe Face Landmarker (guidance only)
    │   │   ├── frameSampler.js               # timestamped JPEG frames per challenge
    │   │   └── useLivenessSession.js         # session + verify calls
    │   ├── idcard/
    │   │   ├── IdCapture.jsx                 # camera or upload of the ID card
    │   │   └── AadhaarQrPanel.jsx            # investigator view: signature + printed-vs-QR table
    │   ├── evidence/
    │   │   ├── CaptureSlotList.jsx           # guided slots per claim type (F10)
    │   │   ├── CaptureSlot.jsx               # "Use camera" / "Upload", source badge
    │   │   └── slotConfig.js                 # motor / health / property slot definitions
    │   ├── map/
    │   │   └── LocationPicker.jsx            # react-leaflet pin (F07)
    │   ├── upload/                           # investigator Analyze page (F16)
    │   │   ├── UploadTabs.jsx
    │   │   ├── FileDropzone.jsx
    │   │   ├── ClaimMetadataForm.jsx
    │   │   ├── SampleButtons.jsx
    │   │   └── useSubmitAnalysis.js
    │   ├── progress/
    │   │   ├── PipelineProgress.jsx
    │   │   └── useJobPolling.js              # poll /jobs/{id} every 1 s
    │   ├── dashboard/
    │   │   ├── KpiCards.jsx                  # F14
    │   │   ├── TopReasons.jsx
    │   │   └── TrendSparkline.jsx
    │   ├── queue/
    │   │   ├── QueueTable.jsx                # F15
    │   │   ├── QueueFilters.jsx
    │   │   └── FastTrackButton.jsx
    │   ├── results/                          # F17
    │   │   ├── ScoreSummary.jsx              # image, document, overall first and largest
    │   │   ├── ScoreGauge.jsx
    │   │   ├── SecondaryScoreCard.jsx        # identity, voice
    │   │   ├── RiskBadge.jsx
    │   │   ├── ExplanationPanel.jsx
    │   │   ├── WhyThisScore.jsx              # contributions
    │   │   ├── EvidenceList.jsx
    │   │   ├── EvidenceCard.jsx
    │   │   ├── QualityWarnings.jsx
    │   │   ├── DetectorStatusTable.jsx       # "Checks run"
    │   │   ├── DuplicateBanner.jsx           # F21
    │   │   ├── IdentityTab.jsx               # F18
    │   │   ├── VoiceTab.jsx                  # F19
    │   │   ├── StoryTab.jsx                  # F20
    │   │   └── LocationPanel.jsx             # F23
    │   ├── viewers/
    │   │   ├── ImageViewer.jsx
    │   │   ├── HeatmapControls.jsx
    │   │   ├── PdfViewer.jsx
    │   │   ├── BoxOverlay.jsx
    │   │   └── FieldTable.jsx
    │   ├── timeline/
    │   │   ├── EvidenceTimeline.jsx          # F22 investigator vertical timeline
    │   │   ├── TimelineEvent.jsx
    │   │   └── ContradictionConnector.jsx
    │   ├── decision/
    │   │   ├── DecisionBar.jsx               # F24
    │   │   ├── DecisionDialog.jsx            # AI draft, reason dropdown, chips, preview
    │   │   ├── ClaimantPreview.jsx           # "what the claimant will see"
    │   │   ├── useDecisionDraft.js           # POST /results/{id}/decision/draft
    │   │   └── AuditList.jsx
    │   ├── network/
    │   │   ├── NetworkGraph.jsx              # F25 react-force-graph-2d
    │   │   └── NodeSidePanel.jsx
    │   ├── analytics/
    │   │   ├── AnalyticsFilters.jsx          # F26 range + claim type
    │   │   ├── KpiRow.jsx
    │   │   ├── BandsOverTimeChart.jsx
    │   │   ├── FlaggedRateChart.jsx
    │   │   ├── TopSignalsChart.jsx
    │   │   ├── ByClaimTypeChart.jsx
    │   │   ├── ByModalityChart.jsx
    │   │   ├── RingsChart.jsx
    │   │   ├── DecisionsChart.jsx
    │   │   ├── SpikeBanner.jsx
    │   │   └── ChartTableToggle.jsx          # accessible table view of any chart
    │   └── report/
    │       └── ExportButtons.jsx             # F27
    │
    ├── api/
    │   ├── client.js                         # fetch wrapper, Bearer token, error mapping
    │   ├── endpoints.js                      # one function per endpoint, with JSDoc for request and response shapes
    │   └── types.js                          # JSDoc @typedef shapes (Evidence, AnalysisResult, ...) mirroring docs/openapi.json
    ├── mocks/
    │   ├── handlers.js                       # mock API used when VITE_MOCK=1
    │   └── fixtures/                         # LOW / MEDIUM / HIGH results, sync endpoint responses
    ├── i18n/
    │   ├── en.json                           # claimant portal strings
    │   └── hi.json
    ├── components/ui/                        # shadcn/ui primitives
    ├── hooks/                                # useToast, useDebounce, useMediaPermission
    ├── lib/
    │   ├── format.js                         # score → %, band → word, colour, icon
    │   ├── bbox.js                           # normalised box → pixel rect
    │   └── dates.js
    ├── styles/globals.css
    └── test/                                 # Vitest + Testing Library
        ├── ScoreGauge.test.jsx
        ├── BoxOverlay.test.jsx
        ├── EvidenceCard.test.jsx
        ├── useJobPolling.test.js
        ├── WizardShell.test.jsx
        ├── DecisionDialog.test.jsx
        ├── RequireRole.test.jsx
        └── EvidenceTimeline.test.jsx
```

### 2.3 `backend/`

```
backend/
├── Dockerfile
├── requirements.txt              # pinned after first install (§27.1)
├── pyproject.toml                # ruff, mypy, pytest config
└── app/
    ├── main.py                   # FastAPI(title="Lucen AI"), routers, CORS, lifespan (load models once)
    │
    ├── api/
    │   ├── deps.py               # current_user(), require_role(), get_db()
    │   └── v1/
    │       ├── health.py         # GET /health
    │       ├── auth.py           # POST /auth/login, GET /auth/me, POST /auth/logout (§7.8)
    │       ├── policies.py       # GET /policies/mine
    │       ├── analyze.py        # POST /analyze/{image,document,claim}
    │       ├── jobs.py           # GET /jobs/{id}
    │       ├── results.py        # GET /results/{id}, report exports, GET /results/{id}/timeline
    │       ├── artifacts.py      # GET /artifacts/{id}/{name}
    │       ├── claims.py         # POST /claims, GET /claims/mine, GET /claims/{id}/status,
    │       │                     # GET /claims/{id}/evidence-timeline, POST /claims/{id}/resubmit
    │       ├── voice.py          # POST /voice/transcribe
    │       ├── identity.py       # POST /identity/liveness/session|verify, POST /identity/aadhaar-qr
    │       ├── queue.py          # GET /queue
    │       ├── decisions.py      # POST /results/{id}/decision/draft, POST /results/{id}/decision
    │       ├── network.py        # GET /network
    │       └── analytics.py      # GET /analytics/trends, GET /analytics/summary (dashboard)
    │
    ├── core/
    │   ├── config.py             # Settings (pydantic-settings), thresholds, feature flags
    │   ├── logging.py            # structured logs, request ids
    │   ├── security.py           # file validation (magic bytes), size and page limits
    │   ├── auth.py               # bcrypt hashing, itsdangerous token sign/verify
    │   ├── errors.py             # error types → HTTP problem responses (§7.2)
    │   └── decision_reasons.py   # reason codes, default messages, evidence→reason map (§7.6, §7.7)
    │
    ├── schemas/
    │   ├── evidence.py           # Evidence, BBox, EvidenceKind
    │   ├── result.py             # AnalysisResult, PipelineScore (+ voice, liveness, aadhaar_qr, story, links, decision)
    │   ├── job.py                # JobStatus, StepProgress
    │   ├── requests.py           # ClaimMetadata
    │   ├── auth.py               # LoginRequest, TokenResponse, User
    │   ├── claims.py             # ClaimCreate, ClaimStatus (claimant-safe)
    │   ├── decisions.py          # DecisionRequest, DecisionDraft
    │   ├── timeline.py           # TimelineEvent, Contradiction, ClaimantTimelineItem
    │   ├── analytics.py          # TrendsResponse
    │   └── network.py            # Node, Edge
    │
    ├── services/
    │   ├── orchestrator.py       # runs pipelines, collects evidence, calls scoring + explain
    │   ├── job_manager.py        # job lifecycle, progress events, concurrency limit
    │   ├── storage.py            # file save/load, retention cleanup
    │   ├── report.py             # PDF / JSON report builder
    │   ├── claims_service.py     # wizard submission → claim row → analysis job; resubmission
    │   ├── decision_service.py   # draft generation, validation, template fallback, audit write
    │   ├── analytics_service.py  # SQL aggregations, spike rule, 60 s cache (§8.13)
    │   └── demo_cache.py         # cached Bhashini / LLM responses for offline demo
    │
    ├── pipelines/
    │   ├── image_pipeline.py     # §10
    │   ├── document_pipeline.py  # §11
    │   ├── identity_pipeline.py  # §12 (face match + liveness + Aadhaar QR)
    │   ├── voice_pipeline.py     # §14.1
    │   ├── claim_pipeline.py     # §14 combines all + cross-checks + entity links + story
    │   └── timeline.py           # §14.5 builds timeline_events
    │
    ├── detectors/
    │   ├── base.py               # Detector protocol, run_safely(), timeout wrapper (§9.3)
    │   ├── image/
    │   │   ├── preprocess.py     # validate, orient, RGB, quality metrics
    │   │   ├── metadata.py       # EXIF + C2PA
    │   │   ├── ai_detector.py    # SigLIP AI-vs-human detector wrapper
    │   │   ├── ela.py
    │   │   ├── noise.py
    │   │   ├── localization.py   # forensic heatmap, occlusion map
    │   │   └── duplicates.py     # SHA-256 → pHash → CLIP + FAISS (§13)
    │   ├── document/
    │   │   ├── kind.py           # digital PDF vs scan vs image
    │   │   ├── pdf_parser.py     # PyMuPDF text, fonts, metadata, embedded images
    │   │   ├── ocr.py            # PaddleOCR / Tesseract adapter
    │   │   ├── fields.py         # regex + LLM field extraction
    │   │   ├── rules.py          # DOC-LOGIC-01…07
    │   │   ├── fonts.py          # DOC-FONT-01/02, DOC-OVERLAY-01
    │   │   ├── tamper_cnn.py     # patch CNN on ELA + heatmap
    │   │   └── anomaly.py        # Isolation Forest per-word outliers
    │   ├── identity/
    │   │   ├── face_match.py     # InsightFace detect + ArcFace compare
    │   │   ├── liveness.py       # session store, server-side landmark checks, spoken code
    │   │   └── aadhaar_qr.py     # QR decode, signature check, printed-vs-QR compare
    │   ├── voice/
    │   │   ├── preprocess.py     # decode, 16 kHz mono, duration, loudness, SNR
    │   │   ├── bhashini.py       # ASR + NMT client, timeouts, demo cache
    │   │   ├── spoof.py          # synthetic-speech classifier
    │   │   └── fields.py         # transcript → ClaimMetadata (LLM + regex, substring-validated)
    │   └── claim/
    │       ├── cross_checks.py   # CLM-X-01…08
    │       ├── story.py          # story-vs-evidence review (LLM, validated)
    │       └── entity_links.py   # phone / email / bank hash / image match links, CLM-NET-*
    │
    ├── scoring/
    │   ├── calibration.py
    │   ├── weights.py            # evidence catalog with default weights
    │   ├── fusion.py             # noisy-OR, caps, cross-pipeline blend
    │   ├── overrides.py          # O1–O7
    │   ├── bands.py
    │   └── quality.py
    │
    ├── explain/
    │   ├── templates.py          # evidence id → sentence template
    │   ├── explainer.py          # rank + compose summary and "why this score"
    │   ├── llm.py                # LLM client, guardrails, timeout, fallback
    │   └── claimant_message.py   # §7.7 prompt, blocked-word validation, translation check
    │
    ├── db/
    │   ├── database.py           # SQLite connection, WAL mode
    │   ├── models.py             # all tables (§9.7, §9.11, §7.8)
    │   ├── migrations.py         # create-if-missing + simple ALTERs on startup
    │   └── repository.py         # CRUD helpers per table
    │
    └── utils/
        ├── images.py
        ├── pdf.py
        ├── audio.py
        ├── hashing.py            # salted hashes for phone / email / bank
        └── timing.py

backend/tests/
├── conftest.py                   # temp SQLite, seeded users, mock models
├── test_auth.py                  # login, role guard 401/403, claimant can't read others' claims
├── test_scoring.py               # fusion, overrides O1–O7, bands, info evidence never scores
├── test_rules.py                 # DOC-LOGIC-*
├── test_image_pipeline.py
├── test_document_pipeline.py
├── test_identity.py              # face zones, liveness verify, Aadhaar QR valid / tampered / missing
├── test_voice.py                 # fallbacks, field substring validation
├── test_duplicates.py            # cross-person match, same-claim re-upload not flagged
├── test_cross_checks.py          # CLM-X-01…08
├── test_timeline.py              # sorting, undated group, claimant view hides metadata
├── test_decisions.py             # draft validation, template fallback, audit row, nothing sent before /decision
├── test_analytics.py             # empty DB zeros, sums, spike thresholds
├── test_claimant_safety.py       # claimant endpoints never return scores, evidence ids, internal notes
├── test_api.py                   # contract test against schema
└── golden/                       # expected outputs for demo samples
```

### 2.4 `training/` (offline; never imported by the app)

```
training/
├── configs/
│   ├── doc_cnn.yaml
│   └── tamper_recipes.yaml
├── data_gen/
│   ├── make_clean_documents.py       # Jinja2 templates → authentic invoices, bills, estimates
│   ├── make_tampered_documents.py    # edits + *_mask.png ground truth
│   ├── make_fake_images.py           # inpainting, splice, copy-move
│   ├── make_synthetic_voices.py      # TTS / cloning clips from team sentences (§17.11)
│   ├── degrade.py                    # shared JPEG / blur / noise / resize (images + audio)
│   └── templates/
├── train_doc_cnn.py
├── train_anomaly.py
├── calibrate.py                      # temperatures, weights, band thresholds
├── calibrate_voice.py
├── evaluate.py                       # metrics, ROC, per-tamper-type table → docs/EVALUATION.md
└── notebooks/
    ├── 01_detector_bakeoff.ipynb
    ├── 02_threshold_tuning.ipynb
    └── 03_voice_bakeoff.ipynb
```

### 2.5 `models/`

```
models/
├── README.md                     # source, licence and version of every file
├── doc_cnn.keras                 # gitignored if large
├── anomaly.joblib
├── calibration.json              # temperatures, weights, thresholds, model versions
├── demo_qr_public.pem            # demo Aadhaar-style QR verification key (public only)
└── uidai_cert.pem                # optional, only if uidai mode is tested
```

The demo **private** key lives outside the repo (for example `~/.lucen/demo_qr_private.pem`) and is used only by `scripts/make_demo_aadhaar_cards.py`.

### 2.6 `data/`

```
data/
├── real/                         # authentic photos and documents (team's own or licensed)
├── synthetic/
│   ├── documents_clean/
│   ├── documents_tampered/       # with *_mask.png
│   ├── images_fake/
│   ├── voices_real/
│   ├── voices_fake/
│   └── id_cards/                 # demo-key-signed Aadhaar-style cards (valid + tampered)
├── eval_real_edits/              # hand-made tampering, test only, never trained on
├── demo_samples/                 # curated files for scenarios A–D and the Analyze page samples
│   ├── scenario_a/ … scenario_d/
│   └── analyze/                  # ai_photo.jpg, genuine_photo.jpg, tampered_invoice.pdf, clean_invoice.pdf
├── demo_cache/                   # cached Bhashini + LLM responses keyed by input hash
└── runtime/                      # gitignored: uploads/, artifacts/, lucen.db, faiss.index
```

### 2.7 `scripts/`

```
scripts/
├── download_models.py            # HF, PaddleOCR, InsightFace, CLIP, audio model weights
├── make_demo_keys.py             # creates the demo RSA key pair for Aadhaar-style QR signing
├── make_demo_aadhaar_cards.py    # synthetic people, signed QR, tampered variants
├── seed_demo.py                  # users, policies, scenarios A–D, --history 30 analytics data, FAISS index
├── warm_demo_cache.py            # runs every external call once and stores responses in data/demo_cache
├── run_eval.py
└── export_openapi.py             # dumps the FastAPI schema → docs/openapi.json (reference for frontend/src/api/types.js)
```

---

## 3. Folder rules

1. `scoring/` and `explain/` never import from `detectors/`; they see only `Evidence`.
2. `detectors/` never import `scoring/`; they return evidence with a raw score and proposed weight.
3. `api/v1/*` files contain only request parsing, auth dependencies and calls to `services/`. No ML or SQL in route files.
4. `services/` coordinate; `pipelines/` run detectors in order; `detectors/` do one check each.
5. Every detector goes through `run_safely()`: a failure or timeout marks it `failed` and the job continues.
6. `training/` is offline; the app loads only from `models/`.
7. `data/runtime/` is the only folder the running app writes to (plus `data/demo_cache/` when `scripts/warm_demo_cache.py` runs).
8. Claimant-facing schemas (`schemas/claims.py`, claimant timeline) must not contain score, band, evidence or internal-note fields. `test_claimant_safety.py` enforces this.
9. `docs/openapi.json` is generated and is the contract; update `frontend/src/api/types.js` (JSDoc typedefs) whenever it changes (`make openapi`).
10. No secrets in the repo. `.env.example` lists names only.

## 4. Naming conventions

- Python: `snake_case.py`, one detector class per file, class name `XxxDetector`.
- Evidence ids: `MODULE-KIND-NN` (`IMG-AI-01`, `DOC-LOGIC-03`, `ID-QR-02`, `CLM-X-07`). Defined once in `scoring/weights.py`; templates in `explain/templates.py` use the same key.
- React (JavaScript): `PascalCase.jsx` components, `useXxx.js` hooks, one component per file.
- API paths: lowercase, plural nouns, no trailing slash.

## 5. Where each feature lives

| Feature (file 3) | Frontend | Backend |
|---|---|---|
| F01 Landing, F02 Login | `routes/LandingPage`, `routes/LoginPage`, `features/auth/` | `api/v1/auth.py`, `core/auth.py` |
| F03–F11 Claim wizard | `routes/claimant/ClaimWizardPage`, `features/claimant/`, `voice/`, `liveness/`, `idcard/`, `evidence/`, `map/` | `api/v1/claims.py`, `voice.py`, `identity.py`, `policies.py`, `services/claims_service.py` |
| F12–F13 Claim status + evidence timeline | `routes/claimant/ClaimStatusPage`, `StatusTimeline`, `DecisionNotice`, `ResubmitPanel`, `MyEvidenceTimeline` | `api/v1/claims.py`, `pipelines/timeline.py` |
| F14 Dashboard | `routes/app/DashboardPage`, `features/dashboard/` | `api/v1/analytics.py` (summary) |
| F15 Queue | `features/queue/` | `api/v1/queue.py` |
| F16 Analyze | `routes/app/AnalyzePage`, `features/upload/`, `progress/` | `api/v1/analyze.py`, `jobs.py` |
| F17–F23 Case page | `routes/app/ResultPage`, `features/results/`, `viewers/`, `timeline/` | `api/v1/results.py`, `artifacts.py` |
| F24 Decisions + AI draft | `features/decision/` | `api/v1/decisions.py`, `services/decision_service.py`, `explain/claimant_message.py`, `core/decision_reasons.py` |
| F25 Network | `features/network/` | `api/v1/network.py`, `detectors/claim/entity_links.py` |
| F26 Analytics | `features/analytics/` | `api/v1/analytics.py`, `services/analytics_service.py` |
| F27 Export | `features/report/` | `services/report.py` |
| F28–F37 Detection + scoring | n/a | `pipelines/`, `detectors/`, `scoring/`, `explain/` |
| F38–F43 Platform | `mocks/`, `i18n/` | `services/job_manager.py`, `demo_cache.py`, `core/security.py`, `scripts/seed_demo.py` |

## 6. Build order (create in this order)

1. **Hour 0–2, skeleton:** top-level files; `backend/app/main.py`, `core/config.py`, `schemas/*`, `api/v1/health.py`, `db/models.py`; `export_openapi.py`; frontend `App.jsx`, layouts, `api/client.js`, `mocks/`; every route as a shell on mock data.
2. **Must-haves:** `detectors/image/*`, `pipelines/image_pipeline.py`, `detectors/document/*`, `pipelines/document_pipeline.py`, `scoring/*`, `explain/templates.py`, `explainer.py`, `analyze.py`, `jobs.py`, `results.py`; frontend `upload/`, `progress/`, `results/`, `viewers/`.
3. **Portals:** `auth`, `policies`, `claims`, wizard features, `queue`, `decisions`, `decision/`.
4. **Bonus, in cut-list order reversed:** identity (face match → liveness → Aadhaar QR), duplicates, cross-checks + timeline, voice, entity links + network, analytics, story.
5. **Demo:** `make_demo_keys.py`, `make_demo_aadhaar_cards.py`, `seed_demo.py`, `warm_demo_cache.py`; offline run.
