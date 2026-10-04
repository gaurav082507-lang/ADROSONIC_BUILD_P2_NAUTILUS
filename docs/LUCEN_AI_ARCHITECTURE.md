# Lucen AI: Final Project Architecture (file 1 of 3)

**AI-Powered Synthetic Identity and Deepfake Claim Detection System**
ADROSONIC Build, 24-hour hackathon · Fraud Detection and AI track

> **The three build files (give all three to the implementing AI together):**
> 1. `LUCEN_AI_ARCHITECTURE.md` (this file): system design, contracts, API, pipelines, scoring, database, deployment, plan. **Wins on any conflict about how something works.**
> 2. `LUCEN_AI_FOLDER_STRUCTURE.md`: the complete repository tree, every file's purpose, folder rules and build order.
> 3. `LUCEN_AI_FEATURES.md`: every feature in depth: user flow, screens, states, edge cases and acceptance criteria. **Wins on any conflict about what the user sees.**
>
> **About "v2":** sections and rows marked v2 were added in round 2. They are all part of the final build, not a later version. Build priority is set by §1.5, §22.3 and §22.5.

This document is the single source of truth for the team. **v2** merges the Round-2 additions into the original build spec: a claimant portal next to the investigator dashboard, a multilingual voice statement with synthetic-voice detection, a live liveness challenge, Aadhaar Secure QR verification, a story-vs-evidence review panel, and a fraud-network view. Everything is checked against the Adrosonic problem statement in section 1.5. It covers the product scope, the final technology choices, the full repository structure, every component in detail (frontend, backend, pipelines, scoring, explanations, training), the data contracts, testing, deployment, the 24-hour plan, and the demo script. Anything marked **(estimate)** is a planning figure to be replaced with a measured number; anything marked **(verify)** is a fact to confirm on the day (a library version, a license, a model label).

> **Rule for the proposal and the demo:** report accuracy only as a *measured* number on your own test set, and call everything else a *target*. Never present a target as a result.

---

## Table of contents

1. [Product overview and goals](#1-product-overview-and-goals)
2. [Scope and feature matrix](#2-scope-and-feature-matrix)
3. [Final technology stack](#3-final-technology-stack)
4. [High-level architecture](#4-high-level-architecture)
5. [Repository structure](#5-repository-structure)
6. [Data contracts](#6-data-contracts)
7. [API specification](#7-api-specification)
8. [Frontend architecture](#8-frontend-architecture)
9. [Backend architecture](#9-backend-architecture)
10. [Image pipeline](#10-image-pipeline)
11. [Document pipeline](#11-document-pipeline)
12. [Identity pipeline (bonus)](#12-identity-pipeline-bonus)
13. [Duplicate detection (bonus)](#13-duplicate-detection-bonus)
14. [Claim mode and cross-checks](#14-claim-mode-and-cross-checks)
15. [Risk scoring engine](#15-risk-scoring-engine)
16. [Explanation engine](#16-explanation-engine)
17. [ML training and data generation](#17-ml-training-and-data-generation)
18. [Robustness to poor-quality input](#18-robustness-to-poor-quality-input)
19. [Testing and evaluation](#19-testing-and-evaluation)
20. [Security, privacy and ethics](#20-security-privacy-and-ethics)
21. [Deployment and operations](#21-deployment-and-operations)
22. [Team roles and the 24-hour plan](#22-team-roles-and-the-24-hour-plan)
23. [Demo script (10 minutes)](#23-demo-script-10-minutes)
24. [Evaluation-criteria mapping](#24-evaluation-criteria-mapping)
25. [Risks and mitigations](#25-risks-and-mitigations)
26. [Limitations](#26-limitations)
27. [Appendices](#27-appendices)

---

## 1. Product overview and goals

### 1.1 The problem

Insurers process thousands of digital claims a day: accident photos, vehicle damage images, medical reports and identity documents. Generative tools such as Midjourney, Adobe Firefly and open-source deepfake models let fraudsters fabricate convincing evidence at scale. Traditional fraud checks were not designed for AI-generated or AI-edited content.

### 1.2 What Lucen AI does

A claims handler opens a web app and chooses what to verify:

- **Image**: a claim photo (vehicle damage, property, injury).
- **PDF / document**: an invoice, medical report, repair estimate or ID document (PDF or scanned image).
- **Full claim** (recommended for the demo): an image plus a document, optionally an ID photo and a selfie.

Two independent pipelines analyze the inputs. Each detector emits a piece of **evidence** (a score, a weight, a human-readable reason, and where relevant a region). A **risk engine** fuses the evidence into three numbers: an *image authenticity score*, a *document authenticity score* and an *overall fraud likelihood* mapped to **Low / Medium / High**. An **explainer** turns the strongest evidence into plain-English reasons an investigator can act on.

### 1.3 Design principles

| Principle | What it means in practice |
|---|---|
| **Integration over model sophistication** | The brief says a well-integrated pipeline beats a sophisticated model that is poorly integrated. Pre-trained models where they exist; small trained models only where none exists. |
| **Explainable by construction** | Every score is a function of evidence objects. No score exists without a list of reasons behind it. The LLM describes; it never decides. |
| **Independent pipelines, shared contract** | Image and document pipelines share nothing except the evidence schema and the scoring engine. Either can be developed, tested and demoed alone. |
| **Contract first** | The API schema is fixed in hour 0–2 so the frontend can be built against a mock while the ML is still training. |
| **Graceful degradation** | Every detector can fail or time out without breaking the run; the result records which checks did not run and lowers confidence accordingly. |
| **Honest about uncertainty** | Scores are calibrated; low-quality inputs reduce the weight of the affected detectors and trigger a visible quality warning. |

### 1.4 Success criteria

1. Upload an image and see a calibrated AI-generated probability, a risk band, a heatmap and reasons within an acceptable demo latency (target under 15 s on the demo machine **(estimate)**).
2. Upload a PDF or scan and see flagged fields with reasons and boxes drawn on the page.
3. See the composite Low / Medium / High score with an explanation.
4. Show the architecture and key decisions.
5. Show identity mismatch detection (bonus).

### 1.5 Problem-statement compliance (read before changing anything)

Every v2 addition is **on top of** the mandatory scope, never instead of it. If time runs short, v2 features are cut before any must-have.

| Problem statement requirement | Where it is met | Status |
|---|---|---|
| A. Classify images as authentic vs AI-generated / manipulated | §10 Image pipeline (`IMG-AI-01` + forensics) | Must, never cut |
| A. Confidence score per prediction | Calibrated `p_ai`, confidence level (§15.2, §15.7) | Must |
| A. Flag images above a defined risk threshold, show confidence | Bands + thresholds in `core/config.py` (§6.5.1) | Must |
| A. Optionally highlight suspicious regions | ELA / noise heatmap, occlusion map (§10 Step 6) | Should |
| B. Analyze PDF / image documents: fonts, altered values, metadata | §11 Document pipeline | Must, never cut |
| B. OCR then rule-based **or ML** checks | PaddleOCR / Tesseract + rules + tamper CNN + Isolation Forest | Must |
| B. Flag suspicious fields with a reason | Evidence with field, bbox and reason (§6.2, §11.3) | Must |
| C. Image authenticity score, document authenticity score, overall fraud likelihood | `PipelineScore` image + document, `overall` (§6.4, §6.5) | Must |
| C. Explainable: show why a score was assigned | Contributions, "why this score", templates (§15.4, §16) | Must |
| D. Web UI to upload files and see results | Investigator **Analyze** page keeps direct image / document upload (§8.12) | Must, never removed |
| D. Show fraud score, flagged indicators, plain-English explanation | Result dashboard (§8.4) | Must |
| E. (Bonus) Face comparison ID vs selfie, mismatch or morphing | §12 Identity, strengthened by liveness and Aadhaar QR (§12.4, §12.5) | Bonus |
| "Purely rule-based approaches are discouraged" | ML is the core of detection (SigLIP detector, tamper CNN, Isolation Forest, ArcFace, CLIP, audio spoof model). Rules and the Aadhaar QR check are **extra** evidence, never the only signal | Respected |
| Generalize to unseen fraud patterns | Held-out generator / recipe tests (§17.8) | Respected |
| Synthetic data, robustness to low-res, noise, compression, incomplete inputs | §17, §18 | Respected |
| Team of 2–4, 24 hours, pre-trained models allowed | Roles for 3–4 people (§22, §22.5) | Respected |
| Demo order: image → document → composite → architecture → identity | §23 follows this exact order | Respected |

**Rules for v2 features:**
1. The three required scores (image, document, overall) always appear first and largest on the result page. Identity and voice scores are shown as additional cards.
2. The single-file Analyze page (image only / document only) stays, because demo steps 1 and 2 require uploading an image and a document directly.
3. No v2 feature may block a must-have: every new detector follows the `run_safely` protocol (§9.3) and can fail without failing the job.

---

## 2. Scope and feature matrix

Priorities follow the problem statement: **Must** items are scored directly; **Bonus** items feed the 15% innovation criterion.

| ID | Feature | Priority | Pipeline | Owner |
|---|---|---|---|---|
| A | Image manipulation detection with confidence score and threshold flag | Must | Image | ML expert |
| A+ | Suspicious-region highlighting | Should | Image | ML expert |
| B | Document tampering detection (fonts, values, metadata) with OCR | Must | Document | ML assistant |
| B+ | Flagged fields with a reason and a bounding box | Must | Document | ML assistant |
| C | Image score, document score, overall fraud likelihood, explainable | Must | Scoring | ML expert |
| D | Web UI: upload, results, scores, indicators, explanation | Must | Frontend | Web owner |
| E | Face comparison: ID document vs selfie, morph suspicion | Bonus | Identity | ML assistant |
| F | Duplicate-image detection across claims | Bonus | Image | ML expert |
| G | Embedded-photo extraction from PDFs into the image pipeline | Bonus | Document→Image | ML assistant |
| H | Cross-checks between image, document and claim data | Bonus | Claim | ML expert |
| I | Downloadable investigator report (PDF / JSON) | Should | Report | Web owner |
| J | Claimant portal: 5-step claim wizard + status tracker | Should | Frontend | Web owner |
| K | Voice statement in Indian languages (Bhashini ASR + translation) with form auto-fill | Should | Voice | Integration owner |
| L | Synthetic / cloned voice detection on the statement | Bonus | Voice | ML lead |
| M | Liveness challenge (blink, head turn, spoken code) before face match | Should | Identity | Web owner (client) + ML support (server verify) |
| N | Aadhaar Secure QR verification (signature + printed-vs-QR comparison) | Bonus | Identity | Integration owner |
| O | Story-vs-evidence review panel (LLM, information only by default) | Bonus | Claim | Integration owner |
| P | Fraud network view (shared phone / email / bank / duplicate image) | Bonus | Claim | Web owner |
| Q | Case actions (approve / reject / request evidence / escalate) + audit log | Should | Backend + Frontend | Web owner |
| R | Investigator triage queue sorted by risk (replaces History) | Should | Frontend | Web owner |
| S | Fraud-risk trend analytics page (bands over time, flagged rate, top reasons, spike alert) | Should | Backend + Frontend | Web owner |
| T | Digital evidence timeline per claim (investigator view with date contradictions; simplified claimant view) | Should | Backend + Frontend | Integration owner |

**Explicitly out of scope** (state this in the proposal): video deepfake classification, continuous real-time video streaming, live-call voice analysis, integration with a real claims system or with UIDAI online services, model training on real fraud data (none is available), and legal or forensic certification of results. A short recorded voice statement (≤ 90 s) and a short liveness capture **are in scope** in v2.

---

## 3. Final technology stack

### 3.1 Summary table

| Layer | Choice | Why this and not something else |
|---|---|---|
| **Frontend framework** | React 18 + TypeScript, built with Vite | Team already knows HTML/CSS/JS; TypeScript catches contract errors; Vite starts instantly. |
| **Styling / UI kit** | Tailwind CSS + shadcn/ui components | Fast to build a polished dashboard without a designer. |
| **Charts** | Recharts (score gauges, evidence bars) | Simple React API. |
| **Uploads** | react-dropzone | Drag-and-drop with type and size validation. |
| **PDF viewing** | pdf.js via `react-pdf` | Render a page, overlay boxes with absolute positioning. |
| **Server state** | TanStack Query | Job polling, caching and retries with little code. |
| **API client types** | `openapi-typescript` generated from FastAPI's OpenAPI | Frontend types can never drift from the backend. |
| **Backend framework** | FastAPI + Uvicorn + Pydantic v2 | Python (the ML stack) with typed schemas, auto-generated docs and OpenAPI. |
| **Job handling** | FastAPI `BackgroundTasks` + in-process job manager (SQLite-backed) | No Redis or Celery to set up; enough for a single-machine demo. |
| **Database** | SQLite | Zero setup; holds jobs, results, evidence, image hashes. |
| **File storage** | Local filesystem (UUID-named) | Simple; cleaned on a timer. |
| **Image AI detector (final)** | Hugging Face `Ateeqq/ai-vs-human-image-detector` (SigLIP vision transformer) | **Decision made.** Apache 2.0 licensed; reports about 99% test accuracy but users have reported overfitting, so it is calibrated and combined with other evidence. |
| **Deep-learning frameworks** | PyTorch (via Hugging Face `transformers`) for the detector; TensorFlow / Keras for the tamper CNN | Detector ships as a PyTorch model; the team prefers Keras for the model it trains. (If the team prefers a single framework, use `timm` + PyTorch for the CNN.) |
| **Image forensics** | OpenCV, Pillow, NumPy, scikit-image | ELA, noise residuals and heatmaps. |
| **Metadata** | `exifread` or `piexif` for EXIF; `c2pa-python` for content credentials **(verify install)** | Provenance signals. |
| **PDF parsing** | PyMuPDF (`fitz`), pdfplumber as a fallback | Text, fonts, sizes, coordinates, metadata and embedded images. |
| **OCR** | PaddleOCR (primary), Tesseract via `pytesseract` (fallback) | Word boxes and confidence; runs locally, so the demo does not depend on the internet. |
| **Field extraction** | Regex first; LLM API (Claude, Gemini or GPT, whichever key you have) for structured JSON extraction | LLM handles layout variety; regex handles the well-formed cases and is the fallback. |
| **Document ML** | Keras EfficientNetB0 (patch-level tamper CNN on ELA input); scikit-learn Isolation Forest (word-level anomaly) | No suitable pre-trained document-tamper model exists, so the team trains one on synthetic tampering. |
| **Identity (bonus)** | InsightFace (ArcFace embeddings, `buffalo_l`) | Strong face embeddings. **Check the pre-trained model license (verify): InsightFace's released models have historically been restricted to non-commercial research use.** |
| **Duplicate search (bonus)** | `imagehash` (pHash) + CLIP embeddings + FAISS | Cheap and effective for reused claim photos. |
| **Region highlighting** | ELA heatmap (always) + occlusion-sensitivity map or Grad-CAM for the detector | Occlusion is model-agnostic and always works; Grad-CAM for a ViT needs a reshape transform (stretch goal). |
| **Scoring** | Custom Python (noisy-OR fusion, temperature-scaled calibration) | Fully explainable and tunable. |
| **Explanations** | Template-based reasons (always) + optional LLM rewrite | Deterministic base, fluent extra. |
| **Reports** | ReportLab or WeasyPrint | Investigator PDF. |
| **Synthetic data** | `faker`, Jinja2 + WeasyPrint / ReportLab, Pillow, OpenCV, `diffusers` (Stable Diffusion inpainting) | Generate authentic and tampered documents and images. |
| **Testing** | pytest + httpx (backend), Vitest (frontend), optional Playwright smoke test | Enough for the code-quality criterion. |
| **Packaging** | Docker Compose (frontend + backend), Makefile for shortcuts | One command to run the demo. |
| **Compute for training** | Google Colab or Kaggle GPU | Training the tamper CNN takes well under an hour **(estimate)**. |
| **Voice: ASR + translation (v2)** | Bhashini pipeline API (ASR + NMT); browser Web Speech API as fallback | Indian-language coverage; team has used it before **(verify: key and pipeline ids before the event)**. |
| **Voice: synthetic-speech detector (v2)** | Pretrained wav2vec2 / AASIST-style audio deepfake classifier from Hugging Face | Chosen by a bake-off in hours 0–3, like the image detector **(verify model id and licence)**. |
| **Audio handling (v2)** | `MediaRecorder` in browser; `soundfile`, `librosa` or `torchaudio` on server | Decode, resample to 16 kHz mono, duration and loudness checks. |
| **Liveness (v2)** | MediaPipe Face Landmarker (browser, for live feedback) + MediaPipe Python (server, for verification) | Blink and head-turn from landmarks; server re-checks so the browser cannot fake a pass. |
| **Aadhaar Secure QR (v2)** | `pyzbar` / OpenCV QR decoder + `pyaadhaar` (or own decoder) + `cryptography` for RSA signature check | Decodes the UIDAI-signed QR and verifies it offline **(verify library behaviour and the UIDAI public certificate)**. |
| **Map pin (v2)** | Leaflet + OpenStreetMap tiles (`react-leaflet`) | Incident location field only; no fraud check depends on it. |
| **Network graph (v2)** | `react-force-graph-2d` | Interactive fraud-ring view. |

### 3.2 Model decisions in one place

| Task | Model | Status |
|---|---|---|
| AI-generated / manipulated **image** classification | `Ateeqq/ai-vs-human-image-detector` | **Final.** Calibrate on your own validation set. |
| **Document** tampering | Tamper CNN (EfficientNetB0 on ELA patches) + Isolation Forest + rules | Trained by the team on synthetic data. No off-the-shelf model was found that is suitable. |
| **OCR** | PaddleOCR (local) | Pre-trained, used as-is. |
| **Field extraction** | Regex + LLM API | Pre-trained, used as-is. |
| **Face matching** | InsightFace ArcFace | Pre-trained, used as-is (bonus). |
| **Synthetic voice detection (v2)** | Audio deepfake classifier (HF) | Pre-trained, calibrated on team-made real vs cloned clips. |
| **ASR + translation (v2)** | Bhashini | External service, used as-is; never produces a score. |
| **Image embeddings for duplicates** | CLIP (e.g. via `open_clip`) | Pre-trained, used as-is (bonus). |

The LLM is used for exactly four jobs: field extraction (documents and the voice transcript), rewriting explanations, the story-vs-evidence review panel (§14.2), and drafting the claimant-facing decision message for the investigator to edit (§7.7). It never produces a score by default and never sends anything to a claimant without an investigator clicking Send.

### 3.3 Dependency notes

- Pin every version in `requirements.txt` and `package-lock.json` after the first successful install; do not chase upgrades during the 24 hours.
- Pre-download all model weights before the event (`scripts/download_models.py`) so the demo never depends on the venue network.
- CPU is sufficient for inference on the demo machine; a GPU speeds up training only.


---

## 4. High-level architecture

### 4.1 Layered view

```
┌──────────────────────────────────────────────────────────────────────────┐
│ FRONTEND  (React + TypeScript + Vite)                                    │
│  Upload page · Results dashboard · Evidence viewer · Report export       │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  HTTPS / JSON (REST), multipart uploads
┌───────────────────────────────▼──────────────────────────────────────────┐
│ API  (FastAPI)                                                           │
│  /analyze/image · /analyze/document · /analyze/claim · /jobs · /results  │
│  validation · CORS · job manager · artifact serving · report export      │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  in-process calls
┌───────────────────────────────▼──────────────────────────────────────────┐
│ ORCHESTRATOR                                                             │
│  routes files by type, runs pipelines, reports progress, handles errors  │
├──────────────────────┬──────────────────────┬────────────────────────────┤
│ IMAGE PIPELINE       │ DOCUMENT PIPELINE    │ IDENTITY PIPELINE (bonus)  │
│ metadata · SigLIP ·  │ parse · OCR · fields │ face detect · ArcFace ·    │
│ ELA · noise · map ·  │ · rules · tamper CNN │ similarity · selfie check  │
│ duplicates           │ · anomaly · embedded │                            │
│                      │   images → image     │                            │
└──────────────────────┴──────────┬───────────┴────────────────────────────┘
                                  │  list[Evidence]
┌─────────────────────────────────▼────────────────────────────────────────┐
│ SCORING ENGINE   calibrate → quality-gate → fuse → cross-check → band    │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │  AnalysisResult
┌─────────────────────────────────▼────────────────────────────────────────┐
│ EXPLAINER   evidence → templated reasons → optional LLM rewrite          │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────────┐
│ STORAGE  SQLite (jobs, results, evidence, hashes) · files · FAISS index  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Request lifecycle (one full claim)

1. **Upload.** The frontend sends a multipart request to `POST /api/v1/analyze/claim` with the image, the document, and optional ID photo, selfie and claim metadata.
2. **Validation.** The API checks size, extension and magic bytes, generates UUID file names, stores the files, creates a `job` row with status `queued`, and returns `202 {job_id}`.
3. **Background execution.** A background task starts the orchestrator. It sets the job to `running` and records progress steps as they complete (`metadata`, `ai_detector`, `forensics`, `ocr`, and so on).
4. **Pipelines run.** The image and document pipelines run independently (the document pipeline may hand embedded photos to the image pipeline). Each detector returns `Evidence` objects; a detector that fails returns a `DetectorStatus` with the error instead.
5. **Scoring.** The scoring engine calibrates and quality-gates the evidence, fuses it into pipeline risks, applies cross-checks and override rules, and produces the three scores and the band.
6. **Explanation.** The explainer ranks evidence by contribution and writes reasons (template first; optional LLM rewrite with a strict fallback).
7. **Persist.** Result, evidence and artifacts (heatmaps, page renders with boxes) are saved; the job becomes `done`.
8. **Poll and render.** The frontend polls `GET /api/v1/jobs/{job_id}` every second, showing per-step progress, then fetches the result and renders the dashboard.

### 4.3 Key architectural decisions

| Decision | Choice | Reason |
|---|---|---|
| One shared evidence schema | Every detector returns `Evidence` | Uniform scoring, uniform UI, uniform explanations, uniform tests. |
| Scoring separated from detection | `scoring/` never imports a model | Weights and thresholds can be tuned without touching ML code. |
| Async job with polling | 202 + poll, not one long request | The UI shows progress; timeouts are avoided; the demo looks alive. |
| Local OCR and local models | No network needed except the optional LLM | Demo reliability at the venue. |
| LLM only describes | Score computed by deterministic code | Auditable, reproducible, defensible to investigators. |
| Trained parts only where necessary | Document tamper CNN and anomaly model | Judges discourage purely rule-based document checks; no pre-trained model exists. |
| Mock mode | `MOCK_ANALYSIS=1` returns canned results | Frontend work never blocks on the ML. |

### 4.4 v2 architecture additions

```
┌──────────────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                                 │
│  Claimant portal: wizard (policy → voice story → verify identity →       │
│                   evidence → review) · status tracker                    │
│  Investigator portal: dashboard · triage queue · analyze (single file) · │
│                   result/case page · fraud network                       │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ REST (+ sync calls for transcription and liveness)
┌───────────────────────────────▼──────────────────────────────────────────┐
│ API (FastAPI)  existing endpoints + /claims /voice /identity/liveness    │
│                /identity/aadhaar-qr /queue /decision /network            │
└───────────────────────────────┬──────────────────────────────────────────┘
┌───────────────────────────────▼──────────────────────────────────────────┐
│ ORCHESTRATOR                                                             │
├────────────┬──────────────┬─────────────────────────┬────────────────────┤
│ IMAGE      │ DOCUMENT     │ IDENTITY                │ VOICE (v2)         │
│ (§10)      │ (§11)        │ face match (§12)        │ quality · synthetic│
│            │              │ + liveness (§12.4)      │ speech detector    │
│            │              │ + Aadhaar QR (§12.5)    │ (§14.1)            │
├────────────┴──────────────┴─────────────────────────┴────────────────────┤
│ CLAIM CROSS-CHECKS (§14): CLM-X-* · story review (§14.2) · links (§14.3) │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ list[Evidence]
                 SCORING (§15, unchanged engine) → EXPLAINER (§16) → STORAGE
```

Two kinds of calls exist in v2:

| Call type | Used for | Why |
|---|---|---|
| **Synchronous** (user waits, < 10 s) | Voice transcription + auto-fill, liveness verification, Aadhaar QR read during the wizard | The claimant needs immediate feedback to continue the form |
| **Asynchronous job** (202 + poll, unchanged) | Full claim analysis after submit | Heavy models; progress list on screen |

The scoring engine, evidence contract, detector protocol, mock mode and folder rules are unchanged. New detectors are added as new `Detector` implementations that return `Evidence`.

---

## 5. Repository structure

The complete tree, with the purpose of every file, is in **`LUCEN_AI_FOLDER_STRUCTURE.md`**. Summary of the top level:

```
lucen-ai/
├── frontend/    React 18 + TypeScript + Vite (claimant portal + investigator portal)
├── backend/     FastAPI app: api → services → pipelines → detectors → scoring → explain → db
├── training/    offline data generation, training, calibration (never imported by the app)
├── models/      weights and calibration.json loaded by the app
├── data/        real, synthetic, eval, demo samples, runtime (uploads, artifacts, SQLite)
├── scripts/     model download, demo seeding, demo-key and demo-card generation, eval
└── docs/        these three files, API notes, model cards, evaluation
```

### 5.1 Folder rules (summary; full list in the folder-structure file)

- `backend/app/scoring/` and `backend/app/explain/` **never import** anything from `detectors/`. They see only `Evidence`.
- `detectors/` **never import** `scoring/`. They return evidence with a raw score and a proposed weight; the scoring engine decides.
- `training/` is offline. The app loads only files from `models/`.
- `data/runtime/` is the only folder the running app writes to.
- No secrets in the repo. `.env.example` lists variable names only.

---

## 6. Data contracts

All contracts are Pydantic models on the backend and generated TypeScript types on the frontend. They are the first thing the team agrees on.

### 6.1 `BBox`

Boxes are **normalised** so the same box works at any render size.

```json
{ "page": 0, "x": 0.412, "y": 0.633, "w": 0.087, "h": 0.024 }
```

`x, y` are the top-left corner as fractions of page (or image) width and height; `page` is 0 for single images.

### 6.2 `Evidence`

```json
{
  "id": "DOC-LOGIC-01",
  "pipeline": "document",
  "source": "consistency_rules",
  "kind": "risk",
  "raw_score": 1.0,
  "calibrated_score": 1.0,
  "weight": 0.80,
  "effective_weight": 0.80,
  "severity": "high",
  "title": "Line items do not add up to the total",
  "reason": "The line items sum to 1,000.00 but the stated total is 1,200.00.",
  "field": "total_amount",
  "bbox": { "page": 0, "x": 0.71, "y": 0.82, "w": 0.12, "h": 0.03 },
  "details": { "expected": 1000.0, "found": 1200.0 },
  "artifact": null
}
```

| Field | Meaning |
|---|---|
| `id` | Catalog id (see the evidence catalogs in sections 10–14). Stable, used to pick the explanation template. |
| `kind` | `risk` (raises risk), `info` (shown, no effect on score), or `warning` (quality issue, affects weights). |
| `raw_score` | Detector output in [0, 1] before calibration. |
| `calibrated_score` | Probability-like risk after calibration; equals `raw_score` for rule-based evidence. |
| `weight` | Catalog default in [0, 1]: how much this evidence type can move the score. |
| `effective_weight` | `weight` × quality gating factor. |
| `severity` | `low`, `medium`, `high`, derived from `calibrated_score × effective_weight`. |
| `artifact` | Optional name of a generated file (e.g. `heatmap.png`). |

### 6.3 `DetectorStatus`

```json
{ "detector": "ai_detector", "status": "ok", "duration_ms": 1840, "error": null }
```

`status` is `ok`, `skipped` (not applicable, e.g. no EXIF in a PNG) or `failed` (with an error string). Failed detectors are shown in the UI; they never crash the run.

### 6.4 `PipelineScore`

```json
{
  "pipeline": "image",
  "risk": 0.748,
  "authenticity": 0.252,
  "band": "HIGH",
  "confidence": "medium",
  "evidence_ids": ["IMG-AI-01", "IMG-ELA-01", "IMG-EXIF-01"]
}
```

`authenticity = 1 − risk`. `confidence` is `high`, `medium` or `low` and is lowered when detectors failed or the input quality was poor.

### 6.5 `AnalysisResult`

```json
{
  "id": "6f1c…",
  "mode": "claim",
  "created_at": "2026-09-30T09:14:22Z",
  "image": { "…PipelineScore…" },
  "document": { "…PipelineScore…" },
  "identity": null,
  "overall": {
    "risk": 0.882,
    "band": "HIGH",
    "confidence": "medium",
    "summary": "High fraud likelihood. The claim photo is very likely AI-generated (97%), …"
  },
  "evidence": [ "…list of Evidence…" ],
  "detector_status": [ "…list of DetectorStatus…" ],
  "quality_warnings": [
    { "code": "LOW_RESOLUTION", "message": "The image is 320×240; AI-detection confidence is reduced." }
  ],
  "artifacts": {
    "image_heatmap": "/api/v1/artifacts/6f1c/image_heatmap.png",
    "document_pages": ["/api/v1/artifacts/6f1c/page_0_boxes.png"]
  },
  "versions": { "detector": "Ateeqq/ai-vs-human-image-detector@<hash>", "calibration": "2026-09-29" }
}
```

### 6.5.1 Bands

| Band | Default risk range | Meaning shown to the user |
|---|---|---|
| LOW | risk < 0.35 | No significant signs of manipulation found. |
| MEDIUM | 0.35 ≤ risk < 0.65 | Some signals; route to manual review. |
| HIGH | risk ≥ 0.65 | Strong signals; prioritise investigation. |

Thresholds live in `core/config.py` and are re-tuned on the validation set (sections 15.7 and 15.9).

### 6.6 `JobStatus`

```json
{
  "job_id": "b7a2…",
  "status": "running",
  "mode": "claim",
  "steps": [
    { "name": "validate",     "status": "done",    "duration_ms": 40 },
    { "name": "image_metadata","status": "done",   "duration_ms": 25 },
    { "name": "ai_detector",  "status": "running", "duration_ms": null },
    { "name": "ocr",          "status": "pending", "duration_ms": null }
  ],
  "result_id": null,
  "error": null
}
```

`status`: `queued | running | done | failed`. Step statuses: `pending | running | done | skipped | failed`.

### 6.7 `ClaimMetadata` (optional form fields in claim mode)

```json
{
  "claim_date": "2026-09-12",
  "incident_date": "2026-09-10",
  "claimed_amount": 1200.00,
  "currency": "INR",
  "claimant_name": "A. Kumar"
}
```

These enable the cross-checks in section 14. Every field is optional.

### 6.8 v2 contract changes

**`ClaimMetadata` (all optional, extends §6.7):**

```json
{
  "claim_date": "2026-09-12",
  "incident_date": "2026-09-10",
  "incident_time": "19:30",
  "claimed_amount": 180000.0,
  "currency": "INR",
  "claimant_name": "A. Kumar",
  "claimant_phone": "+91XXXXXXXXXX",
  "claimant_email": "a.kumar@example.com",
  "bank_account_ref": "salted-hash-only",
  "claim_type": "motor",
  "peril": "collision",
  "incident_lat": 23.35,
  "incident_lng": 85.33,
  "incident_location_text": "Ring Road, Ranchi",
  "statement_language": "hi",
  "statement_original": "…",
  "statement_en": "…",
  "liveness_session_id": "…",
  "aadhaar_qr_session_id": "…"
}
```

`claim_type`: `motor | health | property`. `peril`: free enum per type (collision, theft, fire, hospitalisation, water damage…). `incident_lat/lng` only feed `CLM-X-06` (§14) and the map shown to the investigator; no other check depends on them.

**`AnalysisResult` additions (extends §6.5):**

```json
{
  "voice": { "…PipelineScore…" },
  "liveness": {
    "performed": true, "passed": true, "code_match": true,
    "challenges": [{ "name": "blink_twice", "ok": true, "ms": 2100 }]
  },
  "aadhaar_qr": {
    "found": true, "signature_valid": true, "mode": "uidai|demo_key|unsigned",
    "comparisons": [{ "field": "dob", "printed": "12/04/1998", "qr": "12/04/1998", "match": true }],
    "photo_similarity": 0.71
  },
  "story": { "contradictions": [], "consistent_points": [], "source": "llm|unavailable" },
  "links": [{ "result_id": "…", "reason": "same bank account" }],
  "decision": {
    "status": "open|approved|rejected|evidence_requested|escalated", "by": "…", "at": "…",
    "reason_code": "PHOTO_NOT_VERIFIED", "claimant_message": "…", "internal_note": "…"
  }
}
```

`identity` (already in §6.5) now aggregates face match, liveness and Aadhaar QR evidence. Regenerate `schema.d.ts` after these changes; the contract test (§19.3) fails until you do.

---

## 7. API specification

Base path: `/api/v1`. JSON responses; uploads are `multipart/form-data`. OpenAPI is served at `/openapi.json` and interactive docs at `/docs`.

| Method | Path | Purpose | Success |
|---|---|---|---|
| `POST` | `/analyze/image` | Analyze one image | `202` `{job_id}` |
| `POST` | `/analyze/document` | Analyze one PDF or document image | `202` `{job_id}` |
| `POST` | `/analyze/claim` | Analyze image(s) + document (+ ID and selfie) | `202` `{job_id}` |
| `GET` | `/jobs/{job_id}` | Job status and step progress | `200` `JobStatus` |
| `GET` | `/results/{result_id}` | Full result | `200` `AnalysisResult` |
| `GET` | `/results/{result_id}/report.json` | Download JSON report | `200` file |
| `GET` | `/results/{result_id}/report.pdf` | Download investigator PDF | `200` file |
| `GET` | `/artifacts/{result_id}/{name}` | Heatmaps, annotated pages | `200` image |
| `GET` | `/history` | Recent analyses (id, mode, band, time) | `200` list |
| `GET` | `/health` | Liveness + which models loaded | `200` |

### 7.1 Upload fields

| Endpoint | Fields |
|---|---|
| `/analyze/image` | `file` (JPG, PNG, WebP; max 15 MB) |
| `/analyze/document` | `file` (PDF, JPG, PNG; max 15 MB; PDFs max 10 pages) |
| `/analyze/claim` | `image` (0..n), `document` (0..1), `id_photo` (0..1), `selfie` (0..1), `metadata` (JSON string, optional). At least one file is required. |

### 7.2 Error format

A single shape for every error, so the frontend has one handler.

```json
{
  "error": {
    "code": "UNSUPPORTED_FILE_TYPE",
    "message": "Only JPG, PNG, WebP and PDF files are supported.",
    "details": { "received": "application/zip" }
  }
}
```

| Code | HTTP | When |
|---|---|---|
| `UNSUPPORTED_FILE_TYPE` | 415 | Magic-byte check fails or type not allowed |
| `FILE_TOO_LARGE` | 413 | Over the size limit |
| `TOO_MANY_PAGES` | 422 | PDF exceeds the page limit |
| `CORRUPT_FILE` | 422 | File cannot be opened |
| `NO_INPUT` | 422 | Claim request has no files |
| `JOB_NOT_FOUND` | 404 | Unknown job id |
| `RESULT_NOT_FOUND` | 404 | Unknown result id |
| `INTERNAL_ERROR` | 500 | Unexpected failure (details only in logs) |

### 7.3 Polling contract

The client polls `GET /jobs/{id}` every 1000 ms while `status` is `queued` or `running`, then calls `GET /results/{result_id}`. Polling stops on `done` or `failed`. TanStack Query handles this with `refetchInterval` that returns `false` when finished.

### 7.4 Mock mode

With `MOCK_ANALYSIS=1` the analyze endpoints ignore the files, wait 3 seconds while emitting fake step progress, and return one of three canned results (LOW, MEDIUM, HIGH) chosen by file name. The frontend team builds every screen against this.

### 7.5 v2 endpoints

| Method | Path | Purpose | Success |
|---|---|---|---|
| `POST` | `/claims` | Claimant submits the wizard; creates a claim row and starts the `/analyze/claim` job internally | `202` `{claim_id, job_id}` |
| `GET` | `/claims/mine` | Claimant's own claims: id, type, submitted date, current stage (claimant-safe) | `200` |
| `POST` | `/claims/{id}/resubmit` | Claimant uploads replacement evidence after an evidence request or resubmittable rejection; starts a new analysis, claim returns to Under review | `202` |
| `GET` | `/claims/{id}/status` | Claimant-facing timeline, the decision, the **claimant-facing reason** for a rejection or evidence request, and next steps. **Never returns scores, bands, evidence or internal notes** | `200` |
| `POST` | `/voice/transcribe` | Audio → original transcript, English translation, extracted fields (sync) | `200` |
| `POST` | `/identity/liveness/session` | Issue random challenges, spoken code and nonce (expires in 120 s) | `200` |
| `POST` | `/identity/liveness/verify` | Sampled frames + code audio → liveness result (sync) | `200` |
| `POST` | `/identity/aadhaar-qr` | ID image → QR decode, signature check, printed-vs-QR comparison (sync) | `200` |
| `GET` | `/queue?band=&type=&status=` | Investigator queue sorted by overall risk | `200` |
| `POST` | `/results/{id}/decision/draft` | AI-drafted reason code, claimant message and internal note from the detected evidence, for the investigator to edit (§7.7) | `200` |
| `POST` | `/results/{id}/decision` | Approve / reject / request evidence / escalate; reason code + claimant message required for reject and request evidence; writes audit log (§7.6) | `200` |
| `GET` | `/network` | Nodes and edges for the fraud-network view | `200` |
| `GET` | `/analytics/summary` | Dashboard numbers: claims today, fast-tracked, flagged, top flag reasons, 7-day sparkline | `200` |
| `GET` | `/analytics/trends?range=7d\|30d\|90d&type=` | Fraud-risk trend data for the analytics page (§8.13) | `200` |
| `GET` | `/results/{id}/timeline` | Investigator evidence timeline: every dated event with source and any contradiction (§14.5) | `200` |
| `GET` | `/claims/{id}/evidence-timeline` | Claimant evidence timeline: what they submitted and when, received / checked / needs replacing. **No scores, dates from metadata or detector names** (§14.5) | `200` |

`/analyze/claim` gains the upload field `audio` (0..1) and accepts `liveness_session_id` / `aadhaar_qr_session_id` inside `metadata`.

New error codes: `UNSUPPORTED_AUDIO` (415), `AUDIO_TOO_LONG` (413), `LIVENESS_SESSION_EXPIRED` (422), `QR_NOT_FOUND` (422, returned only by the sync endpoint; in the job it becomes a warning, not a failure).

Mock mode (§7.4) must return canned `voice`, `liveness`, `aadhaar_qr`, `story` and `links` blocks for the three canned results, and canned responses for every sync endpoint.

### 7.6 Decisions and the reason shown to the claimant

When the investigator **rejects** a claim or **requests more evidence**, the claimant must see why. Each decision therefore has two separate texts:

| Field | Seen by | Required | Content |
|---|---|---|---|
| `reason_code` | Claimant (as a sentence) + investigator | Yes for reject and request evidence | One of the codes below |
| `claimant_message` | Claimant | Prefilled from the code, editable, max 500 characters | Plain, polite explanation and what to do next |
| `internal_note` | Investigator team only | Optional | Fraud details, scores, evidence ids |

**Request body:**

```jsonc
{
  "action": "reject",
  "reason_code": "PHOTO_NOT_VERIFIED",
  "claimant_message": "The damage photos you submitted could not be verified as original photos of your vehicle. You can upload new photos taken with the in-app camera, or contact support to appeal.",
  "internal_note": "IMG-AI-01 0.97 and IMG-DUP-01 match with LC-1042.",
  "also_mention": [],
  "replace_items": ["img_2"],          // request evidence: items marked "needs replacing" (feeds the claimant timeline)
  "claimant_message_translated": {"lang": "hi", "text": "…"},
  "message_source": "llm_draft",
  "draft_edited": true,
  "fast_track": false                  // true only for one-click approval of LOW claims from the queue
}
```

**Reason codes and default claimant messages** (stored in `core/decision_reasons.py`, editable without code changes):

| Code | Default claimant message | Typical evidence behind it (internal only) |
|---|---|---|
| `PHOTO_NOT_VERIFIED` | The photos submitted could not be verified as original, unedited photos of the incident. | `IMG-AI-01`, `IMG-ELA-01`, `IMG-EXIF-02*` |
| `PHOTO_PREVIOUSLY_USED` | One or more photos have already been submitted with another claim. | `IMG-DUP-01` |
| `DOCUMENT_NOT_VERIFIED` | Details in the submitted document could not be verified or appear to have been changed. | `DOC-LOGIC-*`, `DOC-FONT-*`, `DOC-CNN-01`, `DOC-META-*` |
| `AMOUNT_MISMATCH` | The amount in your documents does not match the amount claimed. | `CLM-X-02` |
| `IDENTITY_NOT_VERIFIED` | We could not confirm your identity from the ID and live photo provided. | `ID-FACE-*`, `ID-LIVE-*`, `ID-QR-*`, `ID-DEEP-01` |
| `DETAILS_INCONSISTENT` | Some details in your claim do not match each other (for example dates or names). | `CLM-X-01/03/05` |
| `INCOMPLETE_SUBMISSION` | Required documents or photos are missing or unreadable. | quality warnings, skipped checks |
| `POLICY_NOT_COVERED` | This incident is not covered under your policy terms. | none (business reason) |
| `OTHER` | Free text written by the investigator. | any |

**Rules:**
1. Reject and Request evidence are disabled until a reason code is chosen; the UI pre-fills `claimant_message` from the code and the investigator can edit it.
2. The claimant sees the reason category and message, **not** the scores, evidence ids, heatmaps, percentages or which detector fired. Telling a fraudster exactly which check caught them teaches them how to avoid it next time; a clear category still tells an honest claimant what to fix.
3. Every rejection message ends with next steps: upload new evidence (if the reason allows resubmission) or appeal / contact support.
4. A rejected claim with a resubmittable reason (`PHOTO_NOT_VERIFIED`, `DOCUMENT_NOT_VERIFIED`, `INCOMPLETE_SUBMISSION`, `IDENTITY_NOT_VERIFIED`) shows a "Submit new evidence" button; new uploads run a fresh analysis and return the claim to "Under review".
5. Approvals show "Approved" with an optional message; no reason code is needed.
6. Every decision, reason code, claimant message and internal note is written to the `actions` audit log.

### 7.7 AI-drafted decision message (investigator edits, investigator sends)

Typing a careful message for every rejection is slow. When the investigator clicks **Reject** or **Request evidence**, the dialog opens already filled with an AI draft based on the anomalies found. The investigator reads it, edits anything, and clicks **Send to claimant**. Nothing reaches the claimant without that click.

**Flow**

1. Dialog opens → frontend calls `POST /results/{id}/decision/draft` with `{action: "reject" | "request_evidence"}`.
2. **Reason code suggestion is deterministic, not AI:** the backend picks the reason code from the top contributing risk evidence using a fixed map (`core/decision_reasons.py`), e.g. `IMG-DUP-01` → `PHOTO_PREVIOUSLY_USED`, `IMG-AI-01` / `IMG-ELA-01` → `PHOTO_NOT_VERIFIED`, `DOC-*` → `DOCUMENT_NOT_VERIFIED`, `CLM-X-02` → `AMOUNT_MISMATCH`, `ID-*` → `IDENTITY_NOT_VERIFIED`. If several apply, the top one is selected and the others are offered as ticked "also mention" chips.
3. **The LLM drafts the wording** of the claimant message (and an internal-note summary) from a **claimant-safe input**, not from raw evidence (see "What the LLM receives").
4. The draft is validated (see "Validation"); if it fails or the LLM is unavailable, the default template message for that reason code (§7.6 table) is used instead, so the dialog is never empty.
5. The dialog shows: reason code dropdown (preselected), "also mention" chips, claimant message box (AI draft, editable), "Regenerate" button, language toggle (English / claimant's language), a **"What the claimant will see" preview**, and the internal note box (AI summary, editable).
6. Investigator edits and clicks **Send to claimant** → `POST /results/{id}/decision`.

**Response of `/decision/draft`:**

```json
{
  "suggested_reason_code": "PHOTO_PREVIOUSLY_USED",
  "also_mention": ["DOCUMENT_NOT_VERIFIED"],
  "claimant_message": "We were unable to approve your claim because one of the photos you submitted has already been used with another claim, and some details in your repair invoice could not be verified. You can upload new photos of the damage using the in-app camera and a fresh copy of the invoice, or contact support if you would like to appeal this decision.",
  "claimant_message_translated": { "lang": "hi", "text": "…" },
  "internal_note_draft": "Top signals: IMG-DUP-01 (match with LC-1042, 0.96), IMG-AI-01 (0.94), DOC-LOGIC-01 (line items 1,000.00 vs total 1,200.00).",
  "source": "llm|template",
  "resubmittable": true
}
```

**What the LLM receives (claimant-safe input only)**

- The action, the selected reason code(s) and their default messages from §7.6
- Claim type and the names of the items involved in plain words ("damage photo 2", "repair invoice"), never detector ids, scores or technical terms
- Whether resubmission is allowed and what the claimant can upload
- The claimant's name and preferred language

The internal-note draft is built separately from the full evidence list (ids, scores, details) and never goes to the claimant.

**System prompt (claimant message):**

```
You write a short, polite message to an insurance claimant explaining a decision
an investigator has already made. Use only the reasons provided. Do not accuse the
claimant of fraud or lying. Do not mention scores, percentages, AI, models,
detectors, metadata, heatmaps or any technical checks. Say clearly what was wrong
in plain words and what the claimant can do next. 2–4 sentences, under 500
characters. Return only the message text.
```

**Validation (any failure → template message, `source = "template"`):**

- Length ≤ 500 characters, 2–4 sentences.
- No digits except dates and claim ids that appear in the input.
- Blocked words and phrases (case-insensitive): fraud, fake, forged, lie, lying, AI, artificial intelligence, model, detector, algorithm, score, probability, percent, %, metadata, EXIF, ELA, heatmap, pixel, signature check, deepfake, synthetic.
- Must mention every selected reason code's subject (photo / document / identity / amount / missing items) and must contain a next step (upload, resubmit, appeal or contact support).
- Translation to the claimant's language (LLM, or Bhashini NMT if preferred) is validated the same way after back-translation to English; if that fails, only English is offered.

**Audit:** the `actions` row records `message_source` (`llm_draft`, `template` or `manual`), whether the investigator edited the draft, and the final text sent. This shows judges and auditors that a human approved every message.

**Settings:** `DECISION_DRAFT_ENABLED=true`, `DECISION_DRAFT_TIMEOUT_S=6`. Mock mode returns a canned draft for each reason code.

**Tests:** draft validation rejects each blocked word; template fallback on timeout; reason-code map picks `PHOTO_PREVIOUSLY_USED` when `IMG-DUP-01` is the top contributor; nothing is written to `actions` or shown to the claimant until `/decision` is called.

### 7.8 Demo login, roles and access rules

The prototype has a **demo login**, not production authentication (stated in limitation 9). It exists so the two portals behave like a real product: a claimant sees only their own claims and never reaches investigator pages.

**Roles**

| Role | Can do | Cannot do |
|---|---|---|
| `claimant` | File claims, see own claim status, decision reason, own evidence timeline, resubmit evidence | See scores, evidence, other claims, any `/app` page or investigator endpoint |
| `investigator` (the policy maker) | Everything under `/app`: analyze, queue, case page, decisions, network, analytics | Act as a claimant |

**Seeded demo users** (`scripts/seed_demo.py`; password `demo` for all, shown on the login page):

| Name | Email | Role |
|---|---|---|
| Ravi Kumar | `ravi@demo.lucen` | claimant (scenario A, genuine) |
| Anil Verma | `anil@demo.lucen` | claimant (scenarios B, D) |
| Priya Sharma | `priya@demo.lucen` | investigator |

**Endpoints**

| Method | Path | Purpose | Success |
|---|---|---|---|
| `POST` | `/auth/login` | `{email, password}` → `{token, user: {id, name, role}}` | `200` |
| `GET` | `/auth/me` | Current user from the token | `200` |
| `POST` | `/auth/logout` | Client discards the token; server records the event | `204` |
| `GET` | `/policies/mine` | Claimant's demo policies for wizard step 1 | `200` |

**Mechanics:** passwords stored as bcrypt hashes (`passlib`); token is an `itsdangerous` signed, time-limited string containing `user_id` and `role` (`AUTH_SECRET`, `AUTH_TOKEN_HOURS=8`), sent as `Authorization: Bearer`. FastAPI dependencies `current_user()` and `require_role("investigator")` guard every router: claimant routers (`/claims/*`, `/voice/*`, `/identity/*`, `/policies/mine`) require any logged-in user and check ownership of the claim; everything else requires `investigator`. Wrong role → `403 FORBIDDEN_ROLE`; missing or expired token → `401 NOT_AUTHENTICATED`. In `MOCK_ANALYSIS=1` the login still works against the seeded users.

**Tables** (add to §9.11):

```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE,
  role TEXT,                         -- claimant | investigator
  password_hash TEXT, preferred_language TEXT DEFAULT 'en', created_at TEXT
);
CREATE TABLE policies (              -- seeded demo policies; used by wizard step 1 and CLM-X-07
  policy_number TEXT PRIMARY KEY, holder_user_id TEXT, claim_type TEXT,
  start_date TEXT, end_date TEXT, vehicle_or_asset TEXT
);
-- claims gains: claimant_user_id TEXT, policy_number TEXT
```

**Not built:** registration, password reset, OTP, multi-tenant separation, real identity provider. Say so if judges ask.

---

## 8. Frontend architecture

### 8.1 Goals

The interface is scored at 20% and is the first thing judges see. It must let a non-technical claims handler upload files, understand the verdict in seconds, and drill into the evidence. Every design choice below serves those three things.

### 8.2 Screens and routes

| Route | Screen | Purpose |
|---|---|---|
| `/` | Home | One question: "What do you want to verify?" with three large cards (Image, Document, Full claim) and a "Try a sample" row. |
| `/analyze` | Analyze | Tabbed upload: **Image**, **Document**, **Full claim**. |
| `/results/:id` | Result | The dashboard for one analysis. |
| `/history` | History | Table of past analyses with band, time, and a link. |

> **v2:** these four screens become part of the investigator portal. The full v2 route map, the claimant portal and the new result-page tabs are in §8.12.

### 8.3 User flows

**Flow A: image only.** Home → choose Image → drop file → *Analyze* → progress list → result dashboard with image authenticity gauge, heatmap, evidence cards.

**Flow B: document only.** Home → choose Document → drop PDF or scan → *Analyze* → progress → dashboard with the page render, boxes over flagged fields, and a table of flagged fields with reasons.

**Flow C: full claim.** Choose Full claim → drop image, document, optionally ID photo and selfie, fill the optional metadata form → *Analyze* → dashboard with all three gauges, the overall band, and cross-check findings.

**Flow D: samples.** "Try a sample" buttons upload the curated files from `data/demo_samples/` so the live demo never depends on file dialogs.

### 8.4 The result dashboard (layout)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Overall fraud likelihood        [ HIGH ▲ ]     0.88   confidence: medium│
│ "The claim photo is very likely AI-generated (97%) and the invoice      │
│  total does not match its line items."                                  │
├───────────────────────┬───────────────────────┬────────────────────────┤
│ Image authenticity    │ Document authenticity │ Identity match (bonus) │
│ gauge 25%  HIGH RISK  │ gauge 10%  HIGH RISK  │ 0.31  MISMATCH         │
├───────────────────────┴───────────────────────┴────────────────────────┤
│ [Image] [Document] [Identity] [All evidence] [Checks run]              │
│ ┌──────────────────────────────┐  ┌─────────────────────────────────┐  │
│ │ Viewer: original | heatmap   │  │ Evidence cards (sorted by       │  │
│ │ opacity slider               │  │ contribution)                   │  │
│ │ or PDF page with boxes       │  │  ● DOC-LOGIC-01  HIGH           │  │
│ │                              │  │    Line items ≠ total           │  │
│ └──────────────────────────────┘  └─────────────────────────────────┘  │
│ Quality warnings · Download JSON · Download PDF report                  │
└────────────────────────────────────────────────────────────────────────┘
```

### 8.5 Component responsibilities

| Component | Responsibility | Key props |
|---|---|---|
| `UploadTabs` | Switches between the three modes; owns which dropzones appear. | `mode`, `onSubmit` |
| `FileDropzone` | Drag and drop, type and size validation, preview thumbnail. | `accept`, `maxSizeMb`, `onFile` |
| `ClaimMetadataForm` | Optional claim date, incident date, amount, name. | `value`, `onChange` |
| `PipelineProgress` | Renders `JobStatus.steps` as a checklist with spinners and durations. | `steps` |
| `ScoreGauge` | Semicircle gauge; shows percent **and** the band word so colour is never the only cue. | `value`, `band`, `label` |
| `RiskBadge` | LOW / MEDIUM / HIGH with an icon. | `band` |
| `EvidenceCard` | Title, plain-English reason, calibrated score bar, weight, source, "show on image" link. | `evidence` |
| `EvidenceList` | Sort by contribution or severity; filter by pipeline. | `items`, `filter` |
| `ExplanationPanel` | The summary paragraph and the top three reasons. | `summary`, `top` |
| `QualityWarnings` | Banner listing low-resolution, skipped or failed checks. | `warnings`, `status` |
| `ImageViewer` | Original, heatmap, or side by side; opacity slider. | `src`, `heatmapSrc`, `mode` |
| `PdfViewer` | Renders one page via pdf.js; page navigation. | `fileUrl`, `page` |
| `BoxOverlay` | Draws normalised boxes over an image or PDF canvas; hover highlights the matching evidence card. | `boxes`, `size`, `activeId` |
| `FieldTable` | Flagged fields with value, reason and severity; row hover ↔ box highlight. | `fields` |
| `ExportButtons` | JSON and PDF downloads. | `resultId` |

### 8.6 State management

- **Server state:** TanStack Query. `useSubmitAnalysis` is a mutation returning `job_id`; `useJobPolling(jobId)` is a query with `refetchInterval: (data) => data?.status === 'done' || data?.status === 'failed' ? false : 1000`; `useResult(resultId)` is a query enabled once the job is done.
- **UI state:** local component state and URL params (active tab, selected evidence id). No global store is needed.
- **Persistence:** none in the browser except optional `localStorage` for "last used tab" wrapped in try/catch.

### 8.7 Overlay maths (boxes on images and PDF pages)

Boxes arrive normalised (section 6.1). `lib/bbox.ts`:

```ts
export function toPixelRect(b: BBox, renderedWidth: number, renderedHeight: number) {
  return {
    left:   b.x * renderedWidth,
    top:    b.y * renderedHeight,
    width:  b.w * renderedWidth,
    height: b.h * renderedHeight,
  };
}
```

The overlay is an absolutely-positioned `<div>` layer the same size as the rendered image or canvas. Recompute on resize with a `ResizeObserver`. This is why the backend never returns pixel coordinates.

### 8.8 Design system

| Element | Choice |
|---|---|
| Band colours | LOW green, MEDIUM amber, HIGH red, each with a distinct icon and a text label |
| Typography | System font stack; large numbers for scores |
| Layout | 12-column grid, dashboard cards, max width about 1200 px |
| Motion | Gauge fill animation only; respects `prefers-reduced-motion` |
| Dark mode | Optional; Tailwind `dark:` classes if time allows |

### 8.9 Accessibility and usability

- Colour is never the only signal (band word + icon).
- All controls keyboard-reachable; focus rings visible.
- Dropzone has a real `<input type="file">` fallback.
- Contrast at least 4.5:1 for text.
- Errors use the single error shape and are shown inline with a retry button.
- Empty, loading and failure states are designed for every screen.

### 8.10 Frontend build and tooling

| Concern | Tool |
|---|---|
| Dev server | `vite` on port 5173, proxy `/api` to the backend on 8000 |
| Types | `npm run gen:api` runs `openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts` |
| Lint / format | ESLint + Prettier |
| Tests | Vitest + React Testing Library for `ScoreGauge`, `BoxOverlay`, `EvidenceCard`, polling hook |
| Production | `vite build` → static files served by nginx in the frontend container |

### 8.11 Building the frontend when nobody is a frontend specialist

1. Generate the project skeleton and routes with an AI coding assistant, giving it sections 6, 7 and 8 of this document.
2. Build every screen against `MOCK_ANALYSIS=1` first.
3. Add the real backend only when the mock UI is complete.
4. Reserve the last 30 minutes of the UI window for empty, error and loading states, which are what judges hit first.

### 8.12 v2 frontend: two portals

**Route map**

| Route | Screen | Portal |
|---|---|---|
| `/` | Landing: one-line pitch, "Open investigator demo", "File a claim" | Public |
| `/login` | Two cards: "I'm filing a claim" / "I work at an insurer"; demo users prefilled; role-based redirect (§7.8) | Public |
| `/claim/new` | 5-step wizard | Claimant |
| `/claim/:id` | Status timeline; **"Your evidence" timeline** (§14.5); decision with the claimant-facing reason and next steps; evidence-request / resubmission upload | Claimant |
| `/app` | Dashboard: claims today, fast-tracked, flagged, top flag reasons, 7-day trend | Investigator |
| `/app/queue` | Triage queue (replaces History): risk-sorted table, filters, "fast-track" for LOW | Investigator |
| `/app/analyze` | Original Analyze page: Image / Document / Full claim tabs. **Required for demo steps 1–2** | Investigator |
| `/app/results/:id` | Original result dashboard (§8.4), extended below | Investigator |
| `/app/network` | Fraud-network graph | Investigator |
| `/app/analytics` | Fraud-risk trend analytics (§8.13) | Investigator |

Investigator pages share a left sidebar (Dashboard, Queue, Analyze, Analytics, Network) and a top bar with claim search. Claimant pages have no sidebar, a language switch (English / हिंदी) and one main action per screen; they are built mobile-first.

**Claimant wizard**

| Step | Screen content | Calls |
|---|---|---|
| 1. Policy | Policy number (format check), claim type (motor / health / property), peril | none |
| 2. Your story | Language dropdown, mic button, live transcript + English translation, auto-filled date / time / amount / damaged items (editable), map pin for location, typed description as an alternative | `POST /voice/transcribe` |
| 3. Verify it's you | Liveness challenge (camera, oval guide, 3 random prompts), then ID card capture; Aadhaar QR read automatically if present | `/identity/liveness/*`, `POST /identity/aadhaar-qr` |
| 4. Evidence | Guided capture list by claim type (motor: full vehicle, damage close-up, number plate, repair estimate; health: bill, discharge summary, prescription; property: wide shot, close-up, invoice). Each slot: "Use camera" (marked verified capture) or "Upload" (marked unverified source) | uploads held client-side |
| 5. Review | Summary, consent checkbox, "Submit claim" → toast "Claim submitted" | `POST /claims` |

The claimant never sees fraud scores, but **does** see the decision and its reason (§7.6): for example "Rejected: the photos submitted could not be verified as original, unedited photos. You can upload new photos with the in-app camera or contact support to appeal." Errors explain what to do next ("Camera blocked: allow camera access or upload a selfie instead").

**Result dashboard additions** (layout of §8.4 unchanged; the three required scores stay at the top):

| Tab / panel | Content |
|---|---|
| Score row | Image, Document, Overall (required, largest) + Identity and Voice as smaller cards |
| Duplicate banner | When `IMG-DUP-01` fires: both thumbnails, similarity, link to the earlier claim |
| Identity tab | Liveness checklist → ID vs live selfie (match %) → Aadhaar QR panel (signature status, printed vs QR table with mismatches in red, QR photo next to printed photo) |
| Voice tab | Audio player, original transcript, English translation, synthetic-voice gauge |
| Story tab | Contradictions and confirmations, each linked to the evidence card or box it refers to; label "For investigator review, not part of the score" |
| Evidence timeline tab | Vertical timeline of every dated event (policy start, incident, photo capture, document issue, PDF created, submitted, uploads, checks, decision); contradictions shown as red connectors with the rule id; click an event to open its evidence (§14.5) |
| Location panel | Map with the claimed pin and any photo GPS pins; distance if both exist (`CLM-X-06`) |
| Decision bar | Approve / Reject / Request evidence / Escalate. Reject and Request evidence open a dialog pre-filled by AI (§7.7): suggested reason code, "also mention" chips, AI-drafted claimant message (editable, Regenerate, English / claimant-language toggle, "what the claimant will see" preview), AI-drafted internal note. Nothing is sent until the investigator clicks "Send to claimant". Audit list under "Checks run" |

**Design direction:** investigator portal on a light slate background with ink-blue text, one bold accent (evidence yellow) used for numbered evidence markers pinned on images and documents, red / amber / green reserved for bands, always paired with the band word and an icon (§8.9).


### 8.13 Fraud-risk trend analytics (v2)

Route `/app/analytics`, data from `GET /analytics/trends`. The dashboard (`/app`) keeps its small 7-day sparkline and links here. Charts use Recharts. Every chart has a text summary and a table view toggle, and bands use word + colour.

| Panel | Chart | Computed from |
|---|---|---|
| KPI row | Total claims, % flagged (MEDIUM + HIGH), % HIGH, average overall risk, median time to decision, each with change vs previous period | `results`, `claims`, `actions` |
| Risk bands over time | Stacked bar per day: LOW / MEDIUM / HIGH | `results.band` by `created_at` day |
| Flagged rate and average risk | Two lines per day, with a dashed 7-day rolling average | same |
| Top fraud signals | Horizontal bar: how often each evidence id was a top-3 contributor (e.g. `IMG-AI-01`, `IMG-DUP-01`, `DOC-LOGIC-01`), with its plain-English title | evidence of each result |
| By claim type | Grouped bar: motor / health / property × band | `claims.type` |
| By modality | Share of flags driven by image / document / identity / voice | top contributor's module |
| Recycled evidence and rings | Count of duplicate matches and of network clusters with ≥ 3 claims, per week | `entities`, §13.1, §14.3 |
| Decisions | Approved / rejected / evidence requested / escalated per week; % of HIGH claims later approved (a rough check on false positives) | `actions` |
| Spike alert | Banner when today's flagged rate is ≥ 2× the 7-day average and ≥ 5 claims: "Flagged claims are up today, mostly from reused photos (IMG-DUP-01)" | same query |

Filters: range (7 / 30 / 90 days), claim type. Clicking a bar opens the queue filtered to that day / band / signal.

**Response shape (abridged):**

```json
{
  "range": "30d",
  "kpis": {"total": 312, "flagged_pct": 0.21, "high_pct": 0.07, "avg_risk": 0.29,
           "median_hours_to_decision": 5.5, "prev": {"flagged_pct": 0.17}},
  "daily": [{"date": "2026-10-01", "low": 8, "medium": 2, "high": 1, "avg_risk": 0.31}],
  "top_signals": [{"id": "IMG-DUP-01", "title": "Photo used in another claim", "count": 19}],
  "by_type": [{"type": "motor", "low": 140, "medium": 25, "high": 12}],
  "by_modality": {"image": 0.52, "document": 0.31, "identity": 0.12, "voice": 0.05},
  "rings_weekly": [{"week": "2026-W39", "duplicates": 6, "clusters": 1}],
  "decisions_weekly": [{"week": "2026-W39", "approved": 50, "rejected": 7, "evidence": 4, "escalated": 2}],
  "spike": null
}
```

Implementation: `app/api/v1/analytics.py` + `app/services/analytics_service.py`, plain SQL `GROUP BY` over SQLite (fast enough at demo scale; no extra store). Cache each response for 60 s.

**Demo data:** `seed_demo.py --history 30` generates ~300 synthetic past claims over 30 days with realistic band mix (≈75 % LOW / 18 % MEDIUM / 7 % HIGH), a weekend dip, and a 2-day spike of reused photos linked to one bank-account ring, so the charts, spike alert and network page tell one story. Seeded rows are marked `is_seed=1` and can be hidden with a toggle.

**Tests:** empty database returns zeros, not errors; band counts sum to totals; spike rule triggers only above both thresholds.

---

## 9. Backend architecture

### 9.1 Application structure

`app/main.py` creates the FastAPI app with a lifespan handler that (a) loads settings, (b) opens SQLite and creates tables, (c) **loads every model once** (SigLIP detector, tamper CNN, anomaly model, PaddleOCR, InsightFace, CLIP) into a singleton `ModelRegistry`, and (d) starts a cleanup task. Loading at startup means the first request is not slow, and `/health` can report which models are ready.

Routers are thin: validate input, create a job, hand off to the orchestrator. All logic lives in `services/`, `pipelines/`, `detectors/`, `scoring/` and `explain/`.

### 9.2 Layer contracts

| Layer | Input | Output | May import |
|---|---|---|---|
| `api/` | HTTP | HTTP | `services`, `schemas`, `core` |
| `services/orchestrator` | file paths, metadata | `AnalysisResult` | `pipelines`, `scoring`, `explain`, `db` |
| `pipelines/` | file path(s) | `PipelineOutput(evidence, status, artifacts, extras)` | `detectors`, `schemas` |
| `detectors/` | arrays / paths | `list[Evidence]` (+ status) | `schemas`, `utils`, model registry |
| `scoring/` | `list[Evidence]` | `PipelineScore`, overall | `schemas` only |
| `explain/` | `AnalysisResult` | summary text | `schemas`, `llm` |

### 9.3 The `Detector` protocol

Every detector implements the same interface so the orchestrator can time-box and catch failures uniformly.

```python
class Detector(Protocol):
    name: str
    timeout_s: float
    def run(self, ctx: AnalysisContext) -> DetectorOutput: ...

@dataclass
class DetectorOutput:
    evidence: list[Evidence]
    artifacts: dict[str, Path]      # e.g. {"heatmap": Path(...)}
    extras: dict[str, Any]          # values other detectors may need
```

`base.py` provides `run_safely(detector, ctx)`: it runs the detector with a timeout, catches every exception, records a `DetectorStatus` (`ok`, `skipped`, `failed`, duration, error) and returns an empty output on failure. **A detector failure never fails the job.**

### 9.4 `AnalysisContext`

A small object passed through a pipeline: `job_id`, file paths, decoded image(s), parsed PDF, OCR result, extracted fields, quality metrics, `ClaimMetadata`, and a scratch dictionary for cross-detector data. Detectors read from it and write `extras` back into it (for example, the OCR detector stores word boxes for the font and anomaly detectors).

### 9.5 Job manager

- Creates the job row, returns the id, and runs the orchestrator in a `BackgroundTasks` worker thread (heavy work is CPU-bound, so it runs in a thread pool, not on the event loop).
- Exposes `start_step(name)`, `finish_step(name, status)` so the orchestrator can record progress.
- Persists job state in SQLite so a restart does not lose the history.
- Concurrency: a semaphore limits concurrent analyses to 1 or 2 on a laptop, to avoid memory pressure. Extra jobs wait in `queued`.

### 9.6 Storage and cleanup

- Uploads are saved as `data/runtime/uploads/{job_id}/{uuid}.{ext}` (the original file name is stored only as metadata, never used as a path).
- Artifacts (heatmaps, annotated pages) go to `data/runtime/artifacts/{result_id}/`.
- A cleanup task deletes uploads older than 24 hours by default (`RETENTION_HOURS`). Results and evidence rows stay unless deleted.

### 9.7 Database schema (SQLite)

```sql
CREATE TABLE jobs (
  id TEXT PRIMARY KEY, mode TEXT, status TEXT,
  steps_json TEXT, result_id TEXT, error TEXT,
  created_at TEXT, updated_at TEXT
);
CREATE TABLE results (
  id TEXT PRIMARY KEY, job_id TEXT, mode TEXT,
  overall_risk REAL, overall_band TEXT,
  image_risk REAL, document_risk REAL, identity_risk REAL,
  summary TEXT, json TEXT,            -- full AnalysisResult
  created_at TEXT
);
CREATE TABLE evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT, result_id TEXT,
  evidence_id TEXT, pipeline TEXT, source TEXT, kind TEXT,
  raw_score REAL, calibrated_score REAL, weight REAL, effective_weight REAL,
  severity TEXT, title TEXT, reason TEXT, field TEXT,
  bbox_json TEXT, details_json TEXT, artifact TEXT
);
CREATE TABLE image_hashes (           -- for duplicate detection
  id INTEGER PRIMARY KEY AUTOINCREMENT, result_id TEXT,
  phash TEXT, faiss_index INTEGER, created_at TEXT
);
CREATE INDEX idx_evidence_result ON evidence(result_id);
```

### 9.8 Configuration (`core/config.py`)

All tunables are settings, loaded from environment variables with defaults, so nothing is hard-coded inside detectors.

| Setting | Default | Meaning |
|---|---|---|
| `MAX_UPLOAD_MB` | 15 | Per-file limit |
| `MAX_PDF_PAGES` | 10 | Page limit |
| `RETENTION_HOURS` | 24 | Upload cleanup |
| `MAX_CONCURRENT_JOBS` | 1 | Analyses running at once |
| `DETECTOR_TIMEOUT_S` | 30 | Per-detector time box |
| `BAND_LOW_MAX` / `BAND_MED_MAX` | 0.35 / 0.65 | Band thresholds |
| `IMAGE_MODEL_ID` | `Ateeqq/ai-vs-human-image-detector` | Detector |
| `MODELS_DIR` | `models/` | Weights |
| `OCR_ENGINE` | `paddle` | `paddle` or `tesseract` |
| `LLM_PROVIDER` / `LLM_API_KEY` | unset | Field extraction and explanation rewriting |
| `LLM_ENABLED` | `true` | Falls back to regex and templates when `false` |
| `MOCK_ANALYSIS` | `0` | Return canned results |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed origins |

### 9.9 Logging and observability

- Structured JSON logs with a request id and job id on every line.
- One log line per detector: name, status, duration, evidence count.
- `/health` returns `{"status":"ok","models":{"ai_detector":true,"tamper_cnn":true,…}}`.
- Timing per step is stored in `steps_json`, which makes the "where did the time go" question answerable during the demo.

### 9.10 Latency budget (estimates for a CPU-only laptop)

| Step | Estimate |
|---|---|
| Validation, preprocess, metadata | under 0.5 s |
| SigLIP detector (one image) | 1–3 s |
| ELA + noise + heatmap | under 1 s |
| Occlusion localization (if enabled) | 5–15 s; optional, so run only on request or on flagged images |
| PDF parse + page render | under 1 s per page |
| PaddleOCR | 2–6 s per page |
| LLM field extraction | 2–6 s |
| Tamper CNN sliding window | 2–8 s per page |
| Scoring + explanation | under 0.5 s (template) + 2–5 s (LLM rewrite) |

Replace these with measured numbers on the demo machine; if the total is too high, the first levers are: skip occlusion by default, cap the pages analyzed, and cache demo-sample results with `seed_demo.py`.

### 9.11 v2 database additions

```sql
CREATE TABLE claims (
  id TEXT PRIMARY KEY, result_id TEXT, claimant_name TEXT,
  claimant_user_id TEXT, policy_number TEXT,          -- §7.8
  claim_type TEXT, peril TEXT, status TEXT,
  metadata_json TEXT, created_at TEXT, updated_at TEXT
);
CREATE TABLE entities (
  id INTEGER PRIMARY KEY AUTOINCREMENT, result_id TEXT,
  kind TEXT,                         -- phone | email | bank | image_match
  value_hash TEXT, display TEXT,     -- display is masked, e.g. ••••4417
  created_at TEXT
);
CREATE TABLE actions (               -- audit log of case decisions
  id INTEGER PRIMARY KEY AUTOINCREMENT, result_id TEXT,
  actor TEXT, action TEXT, reason_code TEXT,
  claimant_message TEXT, internal_note TEXT,
  message_source TEXT,               -- llm_draft | template | manual
  draft_edited INTEGER, created_at TEXT
);
CREATE TABLE liveness_sessions (
  id TEXT PRIMARY KEY, nonce TEXT, challenges_json TEXT, spoken_code TEXT,
  used INTEGER DEFAULT 0, expires_at TEXT
);
CREATE TABLE id_checks (             -- Aadhaar QR results; no full Aadhaar number, no QR payload stored
  id TEXT PRIMARY KEY, mode TEXT, signature_valid INTEGER,
  comparisons_json TEXT, created_at TEXT
);
CREATE TABLE timeline_events (       -- §14.5; one row per dated event
  id INTEGER PRIMARY KEY, claim_id TEXT, result_id TEXT,
  at TEXT, at_precision TEXT,          -- exact | day | approximate
  kind TEXT,                           -- policy_start | incident | photo_captured | doc_issued |
                                       -- pdf_created | pdf_modified | submitted | uploaded |
                                       -- checks_complete | decision | resubmitted
  source TEXT,                         -- claimant | exif | pdf_metadata | ocr | system | investigator
  artifact_id TEXT, label TEXT, claimant_visible INTEGER
);
ALTER TABLE results ADD COLUMN is_seed INTEGER DEFAULT 0;
CREATE INDEX idx_entities_hash ON entities(kind, value_hash);
CREATE INDEX idx_timeline_claim ON timeline_events(claim_id, at);
```

New settings (§9.8): `BHASHINI_API_KEY`, `BHASHINI_USER_ID`, `VOICE_MODEL_ID`, `MAX_AUDIO_SECONDS=90`, `LIVENESS_YAW_DEG=20`, `LIVENESS_SESSION_S=120`, `AADHAAR_QR_MODE=uidai|demo_key`, `UIDAI_CERT_PATH`, `DEMO_QR_PUBKEY_PATH`, `STORY_ENABLED=true`, `STORY_SCORING=false`, `DECISION_DRAFT_ENABLED=true`, `DECISION_DRAFT_TIMEOUT_S=6`, `ENTITY_HASH_SALT`, `AUTH_SECRET`, `AUTH_TOKEN_HOURS=8`. The `users` and `policies` tables are defined in §7.8.

---

## 10. Image pipeline

**Entry point:** `analyze_image(path, ctx) -> PipelineOutput`
**Purpose:** decide whether a photo is authentic or AI-generated / manipulated, say how sure we are, and show where.

### 10.1 Step-by-step

```
upload → validate/decode → quality metrics → metadata (EXIF, C2PA)
       → AI detector (SigLIP) → ELA → noise residual → localization
       → duplicate lookup (bonus) → Evidence list
```

#### Step 1: Validate and decode (`preprocess.py`)

- Verify magic bytes match JPG, PNG or WebP; reject anything else.
- Decode with Pillow, apply EXIF orientation, convert to RGB, strip alpha.
- Keep the **original bytes** on disk untouched. ELA and metadata analysis must run on the original file, not a re-encoded copy.
- Compute **quality metrics** and store them in the context: width, height, megapixels, JPEG quality estimate (from quantization tables), Laplacian-variance sharpness, and whether the image looks like a screenshot (exact screen aspect ratios, UI-like flat regions).
- Emit a `warning`-kind evidence (`IMG-QUAL-01`) if the image is below 512 px on the short side, heavily compressed (estimated JPEG quality below 50) or extremely blurry. This reduces the effective weights of the AI and forensic detectors (section 15.3) and appears in `quality_warnings`.

#### Step 2: Metadata (`metadata.py`)

- **EXIF:** read Make, Model, Software, DateTimeOriginal, DateTime, GPS, lens. Missing EXIF is weak evidence on its own because messaging apps strip it.
- **C2PA / content credentials:** try to read a manifest with `c2pa-python` **(verify install and API)**. If a manifest declares generative-AI involvement, that is decisive. If a valid signed manifest from a camera exists, report it as `info` (provenance verified) without lowering risk, because signatures prove origin, not that the scene is honest.
- **Software strings:** match against two lists: *generators* (Midjourney, DALL·E, Stable Diffusion, Firefly, etc.) and *editors* (Photoshop, GIMP, Lightroom, Snapseed, etc.).
- **Date logic:** capture time later than modify time, or a capture date outside the claim window (only when claim metadata exists).

#### Step 3: AI-generated image detector (`ai_detector.py`)

- Model: `Ateeqq/ai-vs-human-image-detector`, loaded once via the `transformers` image-classification pipeline (or `AutoModelForImageClassification` + `AutoImageProcessor` for access to raw logits, which calibration needs).
- **Do not hard-code label names.** Read `model.config.id2label` at startup and map the "AI-generated" class programmatically **(verify the label strings on the day)**.
- Output: logits → softmax → `p_ai` (probability of AI-generated).
- **Calibration:** apply temperature scaling fitted on your validation set (`models/calibration.json`, section 15.2). The uncalibrated model is likely over-confident, and the model card's own users report overfitting.
- **Test-time augmentation (optional, cheap):** average `p_ai` over the original and one or two mild variants (a re-encode at JPEG quality 85, a slight resize). A large disagreement between variants lowers confidence and is reported as a detail.
- **Large images:** the processor resizes internally; for high-resolution photos also evaluate a centre crop and a tile grid and take the maximum, noting that a resize can wash out generator artifacts.
- Evidence: `IMG-AI-01` with `raw_score = p_ai`, calibrated score after temperature scaling.

#### Step 4: Error Level Analysis (`ela.py`)

```python
def ela_map(img: Image.Image, quality: int = 90, scale: float = 15.0) -> np.ndarray:
    buf = io.BytesIO(); img.convert("RGB").save(buf, "JPEG", quality=quality)
    recompressed = Image.open(buf)
    diff = ImageChops.difference(img.convert("RGB"), recompressed)
    return np.clip(np.asarray(diff).astype("float32") * scale, 0, 255).astype("uint8")
```

- Regions that were pasted or edited after the last JPEG save recompress differently from the rest of the image.
- Convert to a single-channel map, blur lightly, then compute: (a) the fraction of pixels above a robust threshold (median + k·MAD), and (b) the largest connected high-error region and its bounding box.
- Map to a risk score with a logistic function whose parameters come from calibration on your data.
- **Known limitation:** ELA is meaningless on images that were saved once as a single JPEG with uniform quality, on PNGs, and on images resized after editing. When the file is not a JPEG, mark the detector `skipped` rather than emit a misleading score.
- Artifact: `ela_heatmap.png` (colour-mapped, saved for the viewer). Evidence: `IMG-ELA-01` with the box of the largest region.

#### Step 5: Noise residual consistency (`noise.py`)

- Compute a high-pass residual (image minus a denoised copy, e.g. median or wavelet).
- Split into blocks (e.g. 64×64) and compute residual variance per block.
- A composite or generated image often has inconsistent noise statistics across blocks; measure the dispersion of block variances after excluding flat regions (sky, walls) with low texture.
- Weak, supporting evidence: `IMG-NOISE-01` with a low default weight. Also compute a simple FFT peak metric (periodic upsampling artifacts) and fold it into the same evidence's `details`.

#### Step 6: Localization (`localization.py`)

The brief marks region highlighting as optional; it is high-value for the demo.

1. **Default: forensic heatmap.** Combine the ELA map and the noise-block map into one normalised heatmap and overlay it (fast, always available).
2. **Model-based (stretch): occlusion sensitivity.** Slide a grey patch over the image on a coarse grid (for example 7×7), measure the drop in `p_ai`, and build a map of the regions the detector relies on. Model-agnostic and needs no gradients; costs about 49 forward passes, so run it only for images with `p_ai` above the medium threshold, or on demand.
3. **Model-based (stretch): Grad-CAM for the ViT** via `pytorch-grad-cam` with a `reshape_transform` for patch tokens. More elegant but fiddlier; only attempt with spare time.

Be clear in the UI what the heatmap shows: "regions with unusual compression or noise" versus "regions the AI detector relied on". The two are different things.

#### Step 7: Duplicate lookup (bonus) — see section 13.

#### Step 8: Evidence assembly

The pipeline returns all evidence objects plus artifacts (`ela_heatmap.png`, `overlay.png`), statuses for each detector, and `extras` (`p_ai`, quality metrics, EXIF summary) for the claim pipeline.

### 10.2 Image evidence catalog

| ID | Title | Default weight | Score mapping | Notes |
|---|---|---|---|---|
| `IMG-C2PA-01` | Content credentials declare AI generation | 0.95 | 1.0 | Also triggers override rule O1 |
| `IMG-C2PA-02` | Valid camera-signed provenance | 0 (`info`) | n/a | Shown as positive information only |
| `IMG-AI-01` | AI-generated image probability | 0.65 | calibrated `p_ai` | Weight is set from the bake-off result |
| `IMG-ELA-01` | Localized compression inconsistency | 0.25 | logistic(anomaly) | JPEG only |
| `IMG-NOISE-01` | Inconsistent noise pattern | 0.20 | logistic(dispersion) | Weak signal |
| `IMG-EXIF-01` | No camera EXIF present | 0.10 | 0.5 | Common after messaging apps; low weight |
| `IMG-EXIF-02a` | Software tag names an AI generator | 0.80 | 0.95 | Strong |
| `IMG-EXIF-02b` | Software tag names an image editor | 0.35 | 0.8 | Editors are not proof of fraud |
| `IMG-EXIF-03` | Timestamps inconsistent | 0.30 | 0.7 | Capture after modify, or outside claim window |
| `IMG-DUP-01` | Near-duplicate of an earlier submission | 0.70 | 0.9 | pHash distance ≤ 6 or CLIP cosine ≥ 0.95 |
| `IMG-QUAL-01` | Low-quality input | n/a (`warning`) | n/a | Lowers effective weights of AI and forensic evidence |

Weights are starting values. The bake-off and validation set (section 17) decide the final numbers, and the values in use are recorded in `models/calibration.json`.

### 10.3 Failure handling

| Failure | Behaviour |
|---|---|
| File cannot be decoded | `CORRUPT_FILE` error; job fails cleanly |
| Detector model not loaded | Detector `failed`; pipeline continues with forensics; confidence set to `low` |
| ELA on a non-JPEG | Detector `skipped` with reason |
| C2PA library missing | Detector `skipped`; noted in `Checks run` |
| Timeout | Detector `failed` with `timeout`; partial evidence discarded |

---

## 11. Document pipeline

**Entry point:** `analyze_document(path, ctx) -> PipelineOutput`
**Purpose:** decide whether a PDF or document image has been tampered with, flag the suspicious fields, and say why.

No single pre-trained model does this well, so the pipeline is **layered**: cheap deterministic checks, OCR-based checks, and two small models trained on synthetic tampering. Layers 1–3 provide precise, explainable reasons; layers 4–5 provide the machine-learning component the challenge asks for.

### 11.1 Step-by-step

```
upload → validate → detect kind (digital PDF / scanned PDF / image)
  ├─ digital PDF: PyMuPDF text + fonts + metadata + embedded images
  └─ scan / image: render → OCR words + boxes + confidence
→ field extraction (regex → LLM) → consistency rules → font/layout checks
→ tamper CNN (ELA patches) → anomaly model (word features)
→ embedded images → image pipeline → Evidence list
```

#### Step 1: Validate and detect kind (`kind.py`)

- Magic-byte check; reject encrypted PDFs that cannot be opened; enforce page limit.
- For PDFs, extract text per page with PyMuPDF. **Digital** if pages have a meaningful text layer (for example more than 50 characters per page); **scanned** if pages are mostly one big image with little or no text; **hybrid** if both. Record per page.
- For PNG/JPG documents: kind is `image`.

#### Step 2: Render pages

Render each page (up to the limit) to an RGB image at **150 dpi** with PyMuPDF (`page.get_pixmap(dpi=150)`). Rendered pages feed OCR, ELA and the tamper CNN, and are the base for the annotated pages shown in the UI. Store the page size in points so normalised boxes map back correctly.

#### Step 3: Metadata and structure (`pdf_parser.py`, PDFs only)

| Check | How | Evidence |
|---|---|---|
| Producer / Creator is an online editor or consumer tool | Read `doc.metadata`; match against a list (online PDF editors, image editors, converters) | `DOC-META-01` |
| Modified date after created date by more than a minute | Compare `creationDate` and `modDate` | `DOC-META-02` |
| Incremental updates (revisions appended after first save) | Count `%%EOF` markers in the raw bytes (heuristic) and inspect the xref structure | `DOC-META-03` |
| Creation date after the date stated in the document, or after the claim date | Compare to extracted fields and claim metadata | `DOC-META-04` |
| Embedded XMP edit history | Parse XMP if present | `info` |

Legitimate documents often have odd metadata, so these carry modest weights; they matter mostly in combination with other evidence.

#### Step 4: Text, fonts and layout (digital PDFs)

PyMuPDF `page.get_text("dict")` returns spans with text, font name, size, flags, colour and bounding box.

- Group spans into **lines** and into **field groups** (label + value pairs, table cells in one column).
- **Font inconsistency (`DOC-FONT-01`):** within a group that should share a style (all amounts in a column, all digits of one number), flag a span whose font name or subset differs. Edited numbers are commonly retyped in a different font.
- **Size and baseline inconsistency (`DOC-FONT-02`):** flag a span whose size or baseline offset deviates from its neighbours by more than a tolerance.
- **Text/visual mismatch:** compare the text layer with OCR of the rendered page; a difference at a specific field (the visible digits differ from the hidden text) is strong evidence of overlay editing. Emit as `DOC-OVERLAY-01`.
- Each finding carries the span's bounding box, normalised by page size.

#### Step 5: OCR (`ocr.py`) — scans and images, and as a cross-check for digital PDFs

- PaddleOCR returns per-line polygons, text and confidence; convert to **word-level** boxes (split lines by character positions or use Tesseract's word output if PaddleOCR is line-level only **(verify)**).
- Keep: text, box, confidence, estimated character height, baseline angle.
- Preprocess for poor scans: deskew, denoise, adaptive threshold only if confidence is low; keep the original for ELA.
- **Scan-specific style checks:** per-word character height, stroke width (from the distance transform of the binarised word), inter-character spacing, and ink colour. Words that deviate from their neighbours in the same field group produce `DOC-FONT-02`-type evidence (`source = ocr_style`).
- **OCR confidence outliers (`DOC-OCR-01`):** low-confidence words inside numeric fields are a weak tamper cue, and also a warning that the extraction might be unreliable.

#### Step 6: Field extraction (`fields.py`)

Goal: a dictionary of typed fields with the box of each value.

1. **Regex pass** for well-formed items: dates (multiple formats), amounts with currency, percentages, policy / claim / invoice numbers, ID numbers, phone numbers, emails.
2. **LLM pass (if enabled)** for layout variety: send the OCR / text-layer text (optionally page image) and request strict JSON with a fixed schema, for example `{"document_type","issuer","recipient","invoice_number","date","due_date","line_items":[{"description","qty","unit_price","amount"}],"subtotal","tax","total","currency"}`. Validate with Pydantic; reject any field not present in the source text (a substring check) to prevent invented values.
3. **Map values back to boxes** by matching extracted strings against OCR word sequences, so every field can be highlighted.
4. If the LLM is disabled, unavailable or returns invalid JSON, use the regex output only and record `fields.llm = skipped`.

#### Step 7: Consistency rules (`rules.py`)

Deterministic, explainable, and the source of the most readable reasons.

| ID | Rule | Default weight |
|---|---|---|
| `DOC-LOGIC-01` | Sum of line items ≠ subtotal / total (tolerance 0.01) | 0.80 |
| `DOC-LOGIC-02` | Tax or discount percentage does not reproduce the stated amount | 0.50 |
| `DOC-LOGIC-03` | Date logic invalid: due date before invoice date, service date in the future, invoice after claim date, implausible date of birth | 0.50 |
| `DOC-LOGIC-04` | ID / policy number fails its format or checksum (for example Luhn where applicable) | 0.50 |
| `DOC-LOGIC-05` | Same field disagrees across pages (name, total, policy number) | 0.60 |
| `DOC-LOGIC-06` | Numbers formatted inconsistently within the document (thousand separators, decimal marks) | 0.25 |
| `DOC-LOGIC-07` | Amount in words differs from amount in digits | 0.70 |

Each rule returns an `Evidence` with the concrete numbers in `details` and in the reason text, plus the boxes of the involved fields.

#### Step 8: Tamper CNN (`tamper_cnn.py`) — trained by the team

- **Input:** ELA of each rendered page (JPEG quality 90, scale 15), cut into **128×128 patches with stride 64**. Skip near-blank patches (low variance) to save time.
- **Model:** Keras EfficientNetB0 (ImageNet weights) with a small head (global average pool, dropout, one sigmoid unit): probability that the patch contains tampering.
- **Inference:** run all patches in batches, assemble a probability heatmap the size of the page, smooth it, threshold, extract connected components as boxes, and score the page as the mean of the top-k patch probabilities (k = 5) to be robust to a single spike.
- **Evidence:** `DOC-CNN-01` (page-level score, with the heatmap artifact and up to three boxes for the strongest regions).
- **Why patches and ELA:** edits to a single field are tiny relative to a page, so a whole-page classifier misses them, and ELA exposes compression differences that survive better than raw pixels. Training details are in section 17.

#### Step 9: Word-level anomaly model (`anomaly.py`) — trained by the team

- **Features per word:** height, width, aspect ratio, baseline offset from line median, character spacing, stroke width, ink intensity, OCR confidence, font size and font id (for digital PDFs).
- **Model:** scikit-learn Isolation Forest fitted on **authentic** documents only, so it learns what normal looks like. Standardise features per document (z-score against that page's own words) so it detects *within-page* outliers, which is what an edited number is.
- **Evidence:** `DOC-ANOM-01` listing the top outlier words with boxes and which feature deviated most ("stroke width 2.1σ above the line's median").

#### Step 10: Embedded images (`pdf_parser.py` → image pipeline)

Extract images embedded in the PDF (skip tiny logos and decorations below a size threshold), save them, and run each through the **image pipeline**. Any image evidence is re-labelled `pipeline="document"`, `source="embedded_image"`, and its id gets the prefix `DOC-IMG-`. A fake damage photo pasted into a report is caught here, and this is the bridge that makes the two pipelines feel like one product.

#### Step 11: Visual ELA on scans (`DOC-VIS-01`)

For scanned or image documents, run the ELA map on the page and report large anomalous regions that also overlap text boxes. This feeds the same heatmap the CNN uses, providing a non-learned second opinion.

### 11.2 Document evidence catalog

| ID | Title | Default weight |
|---|---|---|
| `DOC-META-01` | Producer/Creator is a consumer or online editing tool | 0.15 |
| `DOC-META-02` | Modified long after creation | 0.20 |
| `DOC-META-03` | File contains appended revisions | 0.20 |
| `DOC-META-04` | Creation date inconsistent with document or claim date | 0.35 |
| `DOC-FONT-01` | Font differs within a field group | 0.40 |
| `DOC-FONT-02` | Size, baseline or stroke inconsistent within a line | 0.30 |
| `DOC-OVERLAY-01` | Visible text differs from hidden text layer | 0.70 |
| `DOC-OCR-01` | Low-confidence words inside numeric fields | 0.15 |
| `DOC-LOGIC-01…07` | Consistency rules (table above) | 0.25–0.80 |
| `DOC-CNN-01` | Tamper CNN detects edited regions | 0.50 |
| `DOC-ANOM-01` | Word-level style anomalies | 0.30 |
| `DOC-VIS-01` | Compression anomaly over text region (scans) | 0.25 |
| `DOC-IMG-*` | Embedded image flagged by the image pipeline | inherits from the image evidence |
| `DOC-QUAL-01` | Low scan quality | `warning`; lowers CNN and anomaly weights |

### 11.3 Annotated page artifact

For each analyzed page the backend writes `page_{n}_boxes.png`: the rendered page with flagged boxes drawn in the severity colour and the evidence id printed beside each box. The frontend also draws its own interactive overlay from the normalised boxes; the PNG is used in the PDF report.

### 11.4 Failure handling

| Failure | Behaviour |
|---|---|
| Encrypted / corrupt PDF | `CORRUPT_FILE`, job fails cleanly |
| OCR fails | Digital-PDF checks still run; scan checks `failed`; confidence lowered |
| LLM unavailable or returns invalid JSON | Regex extraction only; noted in `Checks run` |
| No fields found | Rules skipped, not "passed"; the result says "no extractable fields" |
| Tamper CNN missing | Detector `failed`; layers 1–3 and 9 still produce a result |
| More pages than the limit | Only the first pages are analyzed, with a visible notice |

---

## 12. Identity pipeline (bonus)

**Entry point:** `analyze_identity(id_photo, selfie) -> PipelineOutput`

### 12.1 Steps

1. **Detect faces** in both images with InsightFace. Require exactly one dominant face in the selfie; for the ID document choose the largest face and note if several exist. No face → `warning` evidence `ID-QUAL-01` and the pipeline is skipped.
2. **Quality check:** face size, blur, pose angle (from landmarks) and brightness. Poor quality lowers the weight of the similarity evidence.
3. **Embed and compare:** ArcFace 512-dimensional embeddings; cosine similarity.
4. **Decision zones:**

| Cosine similarity | Interpretation | Evidence |
|---|---|---|
| ≥ upper threshold (e.g. 0.45 **(tune)**) | Same person | none (or `info`) |
| between lower and upper | Ambiguous; possible morph or poor quality | `ID-FACE-02`, medium risk |
| < lower threshold (e.g. 0.30 **(tune)**) | Different person | `ID-FACE-01`, high risk |

   Thresholds depend on the model and image quality; **set them on your own matched and mismatched pairs**, not from a blog post.
5. **Selfie deepfake check:** run the selfie through the same AI detector as the image pipeline (`ID-DEEP-01`), because a synthetic selfie is a common identity-fraud route.
6. **Morphing hint:** a morphed ID photo often yields mid-range similarity to both source identities. With only two images you cannot prove a morph, so the wording is "the similarity is unusually low or ambiguous for a genuine match" and the evidence is labelled a *suspicion*.

### 12.2 Identity evidence catalog

| ID | Title | Default weight |
|---|---|---|
| `ID-FACE-01` | Faces do not match | 0.85 |
| `ID-FACE-02` | Ambiguous match; possible morph or low quality | 0.45 |
| `ID-DEEP-01` | Selfie appears AI-generated | 0.70 |
| `ID-QUAL-01` | No usable face / multiple faces | `warning` |

### 12.3 Privacy note

Face images are personal data. Process in memory where possible, do not store embeddings, delete uploads on the retention timer, and state this on the slide about ethics.

### 12.4 Liveness challenge (v2)

**Why:** a static photo or a pre-recorded deepfake video cannot follow random instructions issued at that moment. This strengthens bonus item E (identity mismatch and morphing).

**Flow**

1. Wizard calls `POST /identity/liveness/session` → `{session_id, nonce, challenges, spoken_code}`. Challenges are a random order of `blink_twice` and `turn_left` or `turn_right`; `spoken_code` is 4 random digits. Expires in 120 s.
2. Browser runs MediaPipe Face Landmarker for live guidance (oval, prompt, progress ring).
3. For each challenge the browser samples 4–6 timestamped JPEG frames; for the code it records about 3 s of audio.
4. Browser posts frames, audio and `session_id` to `POST /identity/liveness/verify`.
5. **The server decides**, never the browser:
   - Blink: eye aspect ratio from server-side landmarks drops below threshold in at least 2 frames separated by an open-eye frame.
   - Head turn: yaw from landmarks exceeds `LIVENESS_YAW_DEG` in the requested direction.
   - Spoken code: ASR (Bhashini, or Web Speech fallback text sent with the audio and re-checked) contains the 4 digits in order.
   - Timestamps inside the session window; nonce matches; session not reused.
6. The best frontal frame becomes the **selfie** for ArcFace matching (§12.1) and the selfie deepfake check (`ID-DEEP-01`).
7. If the camera is unavailable the claimant can upload a selfie; the result records `ID-LIVE-03`.

**Evidence (append to §12.2)**

| ID | Title | Default weight |
|---|---|---|
| `ID-LIVE-01` | Liveness challenge failed (blink or head turn not observed) | 0.75 |
| `ID-LIVE-02` | Spoken code did not match | 0.50 |
| `ID-LIVE-03` | Liveness not performed (uploaded selfie instead) | 0.15 |
| `ID-LIVE-00` | Liveness passed (challenges, timings) | 0 (`info`) |

**Honest limit:** a random challenge defeats replayed videos and photos. It does not fully defeat a real-time face-swap filter operated by a live person; `ID-DEEP-01` is the second line of defence. Neither is a certified liveness system.

### 12.5 Aadhaar Secure QR verification (v2)

**Why:** synthetic identities usually come with an edited or fabricated ID card. Every recent Aadhaar card and e-Aadhaar PDF carries a **Secure QR** signed by UIDAI that contains the holder's name, date of birth, gender, address, the last 4 digits of the Aadhaar number and a small photo. If someone edits the printed card, the printed details no longer match the signed QR; if someone fabricates the QR, the signature fails.

**Flow (`detectors/identity/aadhaar_qr.py`)**

1. Locate and decode the QR on the ID image (or the e-Aadhaar PDF page) with `pyzbar`, falling back to OpenCV's QR detector after upscaling and sharpening.
2. Classify the QR:
   - **Secure QR** (large numeric string) → decode to bytes, decompress, split fields, separate the signature and the embedded photo **(verify the exact format against `pyaadhaar` and UIDAI documentation)**.
   - **Old XML QR** (unsigned, older cards) → read fields, mark `mode = "unsigned"`; no signature claim is made.
3. **Signature check:** verify the RSA signature with the UIDAI public certificate (`UIDAI_CERT_PATH`) when `AADHAAR_QR_MODE=uidai`. In `demo_key` mode, verify against the team's demo public key (see "Demo data" below).
4. **Printed vs QR comparison:** use the document pipeline's OCR on the same card image to read printed name, DOB / year of birth, gender and the last 4 digits of the printed number. Compare with the QR values using normalised strings and `rapidfuzz` for names. Also run the Verhoeff checksum on the printed 12-digit number (`DOC-LOGIC-04`).
5. **Photo check:** ArcFace similarity between the QR photo and (a) the printed photo on the card and (b) the live selfie. The QR photo is small, so this is supporting evidence with a modest weight.
6. Return evidence; never store the QR payload or the full Aadhaar number (§20.2).

**Evidence**

| ID | Title | Default weight | Notes |
|---|---|---|---|
| `ID-QR-01` | QR signature is invalid | 0.85 | Triggers override O7 |
| `ID-QR-02` | Printed details do not match the signed QR (name, DOB, gender or last 4 digits) | 0.75 | Reason lists each mismatched field with both values |
| `ID-QR-03` | QR photo does not match the printed photo or the selfie | 0.45 | Small photo; low weight |
| `ID-QR-04` | QR missing, unreadable or unsigned | `warning` | Skips the other QR checks; never scored as fraud |
| `ID-QR-00` | QR verified and printed details match | 0 (`info`) | |

**Demo data (privacy-safe):** the team cannot obtain UIDAI-signed QRs for fictional people and must not use real people's Aadhaar data without consent. For the demo, generate Aadhaar-style sample cards whose QR uses the same structure but is signed with a **team demo key**, run the verifier in `demo_key` mode, and label it on screen as "demo signing key". Keep the `uidai` mode path implemented and tested on a consenting team member's own e-Aadhaar only if the team chooses to, with the number masked and nothing stored.

**Not done:** no call to UIDAI online authentication services, no storage of Aadhaar numbers, no Aadhaar-based decision on its own (it is one evidence item among many).

---

## 13. Duplicate detection (bonus)

**Goal:** flag a photo that was already submitted in another claim (a very common insurance-fraud pattern that needs no AI at all).

1. For each analyzed image compute a **pHash** (`imagehash`) and a **CLIP embedding** (`open_clip`, image encoder, L2-normalised).
2. Query the **FAISS** index (inner-product on normalised vectors) for the nearest neighbours; also compare pHash Hamming distance against the `image_hashes` table.
3. Flag if pHash distance ≤ 6 **or** cosine similarity ≥ 0.95 **(tune)**. The CLIP route catches crops, colour changes and mild edits that defeat pHash.
4. Report which earlier analysis it matches (`IMG-DUP-01`, with the earlier result id and similarity) and show both thumbnails.
5. Add the image to the index **after** analysis, and never match an analysis against itself.
6. Seed the index with the demo samples (`seed_demo.py`) so the demo can show a "reused photo" case.

Index storage: FAISS `IndexFlatIP` in memory, persisted to `data/runtime/faiss.index`, with a parallel `image_hashes` table mapping index position → result id.

### 13.1 v2: duplicate matches in the case view and the network

- When `IMG-DUP-01` fires, the result page shows a banner with both thumbnails, the similarity and a link to the earlier claim.
- Every duplicate match also becomes an `image_match` row in the `entities` table, so it appears as an edge in the fraud-network view (§14.3).
- **Cross-person reuse is the main case:** if claimant B uploads a photo already submitted by claimant A (same file, resized, cropped, recoloured or screenshotted), `IMG-DUP-01` fires on B's claim with A's claim id, the similarity and both thumbnails. The banner says "Matches a photo in claim LC-1042 filed by a different claimant" (claimant name masked unless the investigator opens that claim).
- Check order, cheapest first: exact SHA-256 of the file → pHash Hamming distance → CLIP cosine. An exact hash match is reported as "identical file".
- **What is not flagged:** a photo matched only against earlier evidence of the **same claim** (for example the claimant re-uploads it after an evidence request). A match against the **same claimant's other claim** is still flagged, labelled "same claimant, different claim".
- The claimant never sees which claim matched; if rejected, they see reason `PHOTO_PREVIOUSLY_USED` (§7.6).
- Test: seed one photo under claimant A; submit a cropped, JPEG-recompressed copy as claimant B → `IMG-DUP-01` fires; re-upload the same photo to B's own claim → no new match.

---

## 14. Claim mode and cross-checks

`claim_pipeline.py` runs the image, document and identity pipelines on the supplied files (in parallel where CPU allows) and then adds **cross-modal checks** that neither pipeline can do alone.

| ID | Check | Needs | Weight |
|---|---|---|---|
| `CLM-X-01` | Photo capture time falls outside the incident window | EXIF date + `incident_date` | 0.40 |
| `CLM-X-02` | Amount in the document differs from the declared claim amount | extracted total + `claimed_amount` | 0.50 |
| `CLM-X-03` | Name on the ID differs from the name in the document or claim | OCR / extracted names + `claimant_name` | 0.45 |
| `CLM-X-04` | Same image reused across claims | duplicate index | inherits `IMG-DUP-01` |
| `CLM-X-05` | Document creation date is later than the claim filing date | PDF metadata + `claim_date` | 0.40 |
| `CLM-X-06` | Photo GPS far from the stated incident location | EXIF GPS + optional location | 0.35 (only if provided) |
| `CLM-X-07` | Evidence dated before the policy start (photo capture or document issue date) | EXIF / OCR date + `policy_start_date` (from the seeded demo policy table) | 0.45 (v2) |
| `CLM-X-08` | Repair invoice / bill dated before the incident | OCR document date + `incident_date` | 0.45 (v2) |

Name comparison uses normalised strings (case, punctuation, initials) with a fuzzy ratio (for example `rapidfuzz`) and reports the two strings it compared. Every cross-check is skipped, not failed, when its inputs are missing, and the "Checks run" table says so.

Overall scoring for a claim is described in section 15.5.

### 14.1 Voice statement and synthetic-voice detection (v2)

**Entry point:** `analyze_voice(audio_path, ctx) -> PipelineOutput`.

The audio is used twice, on two different paths:

| Use | When | Path |
|---|---|---|
| Transcription + translation + form auto-fill | During the wizard, before submit (sync) | `POST /voice/transcribe` |
| Synthetic-voice detection | During analysis, after submit (job) | Voice pipeline in `/analyze/claim` |

Transcription never sits on the analysis path, so Bhashini latency never delays the risk result.

**Steps**

```
audio (webm/wav, ≤ 90 s) → validate + resample 16 kHz mono → quality metrics
  → Bhashini ASR (source language) → Bhashini NMT (→ English)        [wizard]
  → LLM field extraction (strict JSON, substring-validated)            [wizard]
  → synthetic-speech classifier → calibrate → Evidence                 [analysis]
```

- **Field extraction** reuses §11 Step 6 exactly: fixed schema `{incident_type, peril, incident_date, incident_time, location_text, damaged_items[], amount_claimed}`, Pydantic validation, every value must appear in the English transcript, regex fallback. The claimant can edit every auto-filled field.
- **Synthetic-speech classifier:** read labels from `id2label`; calibrate with temperature scaling on team-recorded real clips vs clips generated with open-source TTS / voice-cloning tools (§17.11).
- **Fallbacks:** Bhashini fails → browser Web Speech API (English / Hindi) → typed description. Classifier fails → detector `failed`, job continues.

| ID | Title | Default weight |
|---|---|---|
| `VOI-SPOOF-01` | Statement voice appears synthetic or cloned | 0.55 **(estimate; set by bake-off)** |
| `VOI-QUAL-01` | Audio too short, silent or noisy | `warning` (gates `VOI-SPOOF-01` to 0.5) |
| `VOI-TXT-00` | Transcript and translation | 0 (`info`) |

### 14.2 Story-vs-evidence review panel (v2)

**Principle kept:** the LLM describes; it never decides. By default (`STORY_SCORING=false`) the story check is `info` evidence shown in its own tab and does not change any score.

**Inputs:** the English statement, structured claim fields, and the **structured outputs of other detectors** (extracted document fields and dates, EXIF dates, duplicate matches, detected damage labels if available). Prefer facts over raw images; send claim photos to a vision LLM only if structured facts are too thin.

**System prompt:**

```
You compare a claimant's statement with evidence facts for a claims investigator.
Return ONLY JSON: {"contradictions":[{"statement_quote","evidence_ref","evidence_fact","severity"}],
"consistent_points":[{"statement_quote","evidence_ref"}]}.
statement_quote must be copied exactly from the statement. evidence_ref must be one of
the provided ids. Do not infer intent. Do not give a risk level.
```

**Validation (drop the item, not the whole answer):** `statement_quote` must be a substring of the statement; `evidence_ref` must exist; every number or date in `evidence_fact` must appear in that evidence's `details`. Invalid JSON or timeout → tab shows "Story check not available", detector `failed`.

| ID | Title | Default weight |
|---|---|---|
| `CLM-STORY-00` | Story review result | 0 (`info`) |
| `CLM-STORY-01` | Statement contradicts evidence (only if `STORY_SCORING=true`) | 0.25, source cap 0.25 |

If a team ever sets `STORY_SCORING=true`, say so on the architecture slide; the default for the demo is `false`.

### 14.3 Entity links and the fraud network (v2)

- After each analysis, write `phone`, `email`, `bank` (salted hash) and `image_match` rows to `entities`.
- Link the result to earlier results sharing any entity.

| ID | Title | Default weight |
|---|---|---|
| `CLM-NET-01` | Shares a phone, email or bank account with another claimant's claim | 0.40 |
| `CLM-NET-02` | Part of a cluster of 3 or more linked claims | 0.55 |

`GET /network` returns `{nodes:[{id,type,label,band}], edges:[{source,target,reason}]}`. The network page colours claim nodes by band (with the band word in the tooltip) and draws entity nodes as small grey dots.

### 14.4 Location

The wizard's map pin fills `incident_lat/lng`. The only check that uses it is the existing `CLM-X-06` (photo GPS far from the stated location), which is **skipped** whenever photo GPS is missing, as is common after messaging apps. No weather or other external location data is used.


### 14.5 Digital evidence timeline (v2)

Puts every dated fact about a claim on one line, so an investigator can see at a glance that, for example, the "accident photo" was taken three weeks before the accident, or the repair bill was issued before the car was damaged. Built by `app/pipelines/timeline.py` at the end of the claim pipeline and stored in `timeline_events`.

**Event sources**

| Event | Source | Precision |
|---|---|---|
| Policy start | seeded demo policy table | day |
| Incident date / time | claimant (form or voice) | exact or day |
| Photo captured | EXIF `DateTimeOriginal`; marked "no date" if stripped | exact |
| Document issue date | OCR / LLM field extraction | day |
| PDF created / modified | PDF metadata | exact |
| Liveness and ID capture | system | exact |
| Submitted, each upload, checks complete, decision, resubmission | system / `actions` | exact |

**Investigator view** (Evidence timeline tab on the case page): vertical timeline, oldest at top, each event with icon, time, source badge (claimant / photo metadata / document text / system / investigator) and a thumbnail. Order contradictions are drawn as red connectors between the two events with the rule id and template text: `CLM-X-01` photo outside the incident window, `CLM-X-05` PDF created after filing, `CLM-X-07` evidence before policy start, `CLM-X-08` bill before incident. Events with no reliable date (stripped EXIF) are listed in an "Undated" group rather than guessed. The timeline **adds no score of its own**: it only displays dates and the cross-check evidence already in the score.

**Claimant view** ("Your evidence" on `/claim/:id`): what they submitted and when, from system events only, each item marked Received → Checked → Needs replacing (the last only if an evidence request names it). It never shows metadata dates, contradictions, scores or detector names; the reason for any replacement comes from the §7.6 / §7.7 claimant message.

**Response of `/results/{id}/timeline` (abridged):**

```json
{
  "events": [
    {"at": "2026-08-30", "kind": "policy_start", "source": "system", "label": "Policy started"},
    {"at": "2026-09-02T10:14:00", "kind": "photo_captured", "source": "exif", "artifact_id": "img_2", "label": "Damage photo 2 taken"},
    {"at": "2026-09-21", "kind": "incident", "source": "claimant", "label": "Incident (stated)"},
    {"at": "2026-09-22T09:03:00", "kind": "submitted", "source": "system", "label": "Claim submitted"}
  ],
  "contradictions": [
    {"rule": "CLM-X-01", "from": 1, "to": 2, "text": "The photo was taken 19 days before the stated incident."}
  ],
  "undated": [{"artifact_id": "img_3", "label": "Damage photo 3 (no capture date)"}]
}
```

**Tests:** events sort correctly across precisions; stripped EXIF goes to "Undated"; claimant endpoint never returns `exif`, `pdf_metadata` or `ocr` sourced events.

---

## 15. Risk scoring engine

**Location:** `backend/app/scoring/`. **Input:** `list[Evidence]` + quality flags + claim metadata. **Output:** `PipelineScore` for each pipeline and the overall score.
This is the heart of the "risk scoring logic and explainability" criterion (25%), so it is fully deterministic and documented.

### 15.1 Processing order

```
raw evidence → calibrate → quality-gate weights → per-pipeline fusion
             → cross-pipeline blend → override rules → band → confidence
```

### 15.2 Calibration (`calibration.py`)

Detector outputs are not probabilities until calibrated.

- **AI detector:** temperature scaling. Fit a single scalar `T` on the validation set so that `softmax(logits / T)` minimises log-loss. Store `T` in `models/calibration.json`. Report Expected Calibration Error (ECE) before and after.
- **Tamper CNN:** the same, on a held-out validation set of patches, then again at page level.
- **Forensic scores (ELA, noise):** fit a logistic mapping from the raw anomaly statistic to a probability using labelled authentic and tampered examples (Platt scaling).
- **Rules:** deterministic evidence keeps `calibrated_score = raw_score` (1.0 for a violated arithmetic rule, or a graded value where the rule has degrees, such as how far a total is off).
- The calibration file records the data used, date and library versions, so a run can be reproduced.

### 15.3 Quality gating (`quality.py`)

Poor input should reduce the influence of detectors that are unreliable on it, not add risk.

```
effective_weight = weight × gate
```

| Condition | Detectors affected | Gate |
|---|---|---|
| Short side below 512 px | `IMG-AI-01`, `IMG-ELA-01`, `IMG-NOISE-01` | 0.7 |
| Estimated JPEG quality below 50 | `IMG-ELA-01`, `IMG-NOISE-01` | 0.5 |
| Screenshot or non-JPEG | `IMG-ELA-01` | 0 (skipped) |
| Scan resolution below 100 dpi equivalent | `DOC-CNN-01`, `DOC-ANOM-01`, `DOC-VIS-01` | 0.6 |
| High OCR failure rate | field-based rules | 0.5 |

The gate values are starting points to tune on the degraded validation set. Every gated weight is visible in the evidence card so investigators can see that the system discounted the evidence and why.

### 15.4 Per-pipeline fusion (`fusion.py`)

Only `kind = risk` evidence participates. Let each evidence item have calibrated score `pᵢ ∈ [0,1]` and effective weight `wᵢ ∈ [0,1]`. Use a **noisy-OR**:

```
risk = 1 − Π (1 − wᵢ · pᵢ)          # over risk-kind evidence
authenticity = 1 − risk
```

Why noisy-OR: independent signals reinforce each other, no single weak signal can produce a high score, a single strong signal (weight near 1, score near 1) can, and each term is directly attributable to one piece of evidence.

**Guard against many weak signals.** Noisy-OR can inflate when many low-value signals accumulate. Only evidence with `pᵢ ≥ 0.2` **and** `wᵢ·pᵢ ≥ 0.02` participates; the rest appear in the list as context but are not multiplied in. Cap the combined contribution of any single *source* (for example all metadata checks together) at 0.4 so metadata cannot dominate.

**Contribution** of each evidence item, used for ranking and explanation:

```
contribution_i = wᵢ · pᵢ · Π_{j≠i} (1 − wⱼ · pⱼ)      # marginal share of the fused risk
```

(For display, normalise contributions so they sum to the fused risk.)

### 15.5 Cross-pipeline blend (overall score)

For a claim with several pipelines, let `R_k` be each active pipeline's risk. A pure noisy-OR across pipelines saturates near 1 too easily, so use a blend of the strongest signal and the average:

```
overall = 0.7 · max(R_k) + 0.3 · mean(R_k)
```

Cross-check evidence (`CLM-X-*`) is fused into its own pseudo-pipeline `R_claim` using the same noisy-OR and then included in the blend. If only one pipeline ran, `overall = R` of that pipeline.

The band and the confidence come from `overall` after overrides.

### 15.6 Override rules (`overrides.py`)

Hard rules for cases where the evidence is decisive on its own.

| Rule | Condition | Effect |
|---|---|---|
| O1 | `IMG-C2PA-01` present | overall and image risk ≥ 0.95 |
| O2 | `DOC-LOGIC-01` violated **and** `DOC-CNN-01` above medium threshold on the total's region | document risk ≥ 0.85 |
| O3 | `ID-FACE-01` present | overall risk ≥ 0.80 |
| O4 | `IMG-DUP-01` present and matched claim is closed as fraudulent (only if such data exists) | overall ≥ 0.90 |
| O5 | `DOC-OVERLAY-01` present | document risk ≥ 0.80 |
| O6 | `ID-LIVE-01` **and** `ID-FACE-01` present | overall risk ≥ 0.85 |
| O7 | `ID-QR-01` present (signature invalid in `uidai` or `demo_key` mode) | identity risk ≥ 0.85 |

Each triggered override is itself listed as an evidence-style entry ("Rule O1 applied: content credentials state the image is AI-generated") so nothing is hidden.

### 15.7 Bands and confidence

**Bands** from `overall`:

| Band | Range (defaults) |
|---|---|
| LOW | < 0.35 |
| MEDIUM | 0.35 to < 0.65 |
| HIGH | ≥ 0.65 |

Tune the two thresholds on the validation set so that the false-negative rate on known fakes is acceptable and the LOW band is not full of fakes; record the chosen values and the operating point in `docs/EVALUATION.md`.

**Confidence** (`high | medium | low`) is separate from the score. Start at `high` and step down one level for each of: a detector `failed`, a quality warning that gated weights by more than 30%, fewer than two independent evidence sources, disagreement between the AI detector and forensic evidence (for example `p_ai` above 0.8 while ELA is quiet), or an out-of-distribution input (extreme aspect ratio, blank pages).

### 15.8 Worked example (numbers verified)

**Image (claim photo).** Evidence: `IMG-AI-01` (p 0.97, w 0.70), `IMG-ELA-01` (p 0.70, w 0.25), `IMG-EXIF-01` (p 0.50, w 0.10).

```
terms:  0.97·0.70 = 0.679 ;  0.70·0.25 = 0.175 ;  0.50·0.10 = 0.050
risk_img = 1 − (1−0.679)(1−0.175)(1−0.050) = 1 − 0.321·0.825·0.95 ≈ 0.748   → HIGH
```

**Document (invoice).** Evidence: `DOC-LOGIC-01` (p 1.00, w 0.80), `DOC-CNN-01` (p 0.75, w 0.50), `DOC-FONT-01` (p 0.60, w 0.30), `DOC-META-02` (p 0.50, w 0.15).

```
terms:  0.80 ; 0.375 ; 0.18 ; 0.075
risk_doc = 1 − 0.20·0.625·0.82·0.925 ≈ 0.905   → HIGH
```

**Overall.**

```
overall = 0.7·max(0.748, 0.905) + 0.3·mean(0.748, 0.905) = 0.7·0.905 + 0.3·0.8265 ≈ 0.882   → HIGH
```

**A genuine image for contrast.** `IMG-AI-01` (p 0.05, w 0.65) is below the 0.2 participation threshold and is not multiplied in; `IMG-ELA-01` (p 0.10) likewise; `IMG-EXIF-01` (p 0.5, w 0.10) contributes 0.05, so `risk_img ≈ 0.05`, well inside LOW (the guard prevents small residual scores from accumulating into a false alarm). Numbers shown if all three were multiplied in: ≈ 0.104.

### 15.9 Tuning procedure

1. Freeze the evidence catalog and default weights.
2. Run all validation samples (synthetic and the hand-made real-edit set) through detectors and save the evidence (no scoring yet).
3. Grid-search or hand-tune weights and band thresholds *offline* on that saved evidence (`training/calibrate.py`), because scoring is cheap.
4. Choose an operating point (for example recall on fakes at least 0.9 with LOW-band precision at least 0.9) and write it into `calibration.json`.
5. Report the result on the untouched test set only once.

### 15.10 v2 scoring changes

- **Cross-pipeline blend (§15.5):** add `R_voice` to the set of pipeline risks when the voice pipeline ran. Liveness and Aadhaar QR evidence fuse inside the identity pipeline (`R_identity`). `CLM-NET-*` fuse inside `R_claim`.
- **Required scores stay primary:** the image score, document score and overall score are always computed and shown first; identity and voice are additional `PipelineScore` cards.
- **Per-source caps (§15.4):** `aadhaar_qr` 0.85, `liveness` 0.75, `voice` 0.55, `llm_story` 0.25 (only relevant if `STORY_SCORING=true`).
- **Confidence (§15.7):** step down one level if liveness was not performed on a claim that included an ID document, or if the Aadhaar QR was unreadable on an Aadhaar card.
- **Tests:** add cases to `test_scoring.py` for O6 and O7, for `ID-QR-04` never raising risk, and for `CLM-STORY-00` never changing any score.

---

## 16. Explanation engine

**Location:** `backend/app/explain/`. Explanations are 25% of the score and the reason an investigator would trust the tool.

### 16.1 Layered approach

1. **Templates (always).** Every evidence id has a sentence template in `templates.py` filled from `details`. Deterministic, auditable, and available offline.
2. **Ranking.** Sort risk evidence by contribution (section 15.4) and take the top three to five.
3. **Summary paragraph.** Compose from the band, the top reasons and the confidence statement, using a fixed grammar: *"[Band] fraud likelihood ([score]). [Top reason 1]. [Top reason 2]. [Caveat if confidence is not high]. Recommended action: [action]."*
4. **LLM rewrite (optional).** If enabled, send the *structured evidence* (not the raw documents) and ask for a 2–3 sentence plain-English summary.

### 16.2 Template examples

| Evidence id | Template |
|---|---|
| `IMG-AI-01` | "The image shows patterns typical of AI-generated pictures ({p:.0%} likelihood after calibration)." |
| `IMG-ELA-01` | "One region of the photo was compressed differently from the rest, which often means it was edited after capture." |
| `IMG-EXIF-02a` | "The file's metadata names an AI image generator ({software})." |
| `IMG-DUP-01` | "This photo closely matches one submitted earlier in claim {other_id} ({sim:.0%} similar)." |
| `DOC-LOGIC-01` | "The line items add up to {expected:,.2f} but the stated total is {found:,.2f}." |
| `DOC-FONT-01` | "The value '{text}' uses a different font ({font_a}) from the other amounts in the same column ({font_b})." |
| `DOC-META-02` | "The PDF was modified {delta} after it was created, using {producer}." |
| `DOC-CNN-01` | "The tamper detector found an area around '{field}' whose compression pattern differs from the rest of the page." |
| `ID-FACE-01` | "The face on the ID does not match the selfie (similarity {sim:.2f}, below the match threshold)." |
| `CLM-X-02` | "The document total ({doc:,.2f}) differs from the amount claimed ({claimed:,.2f})." |
| `VOI-SPOOF-01` | "The recorded statement shows patterns of a synthetic or cloned voice ({p:.0%} likelihood after calibration)." |
| `ID-LIVE-01` | "The person did not complete the live check ({failed_challenge} not detected)." |
| `ID-LIVE-02` | "The spoken code did not match the code shown on screen." |
| `ID-QR-01` | "The QR code on the ID card failed its digital signature check, so its contents cannot be trusted." |
| `ID-QR-02` | "The printed {field} on the ID card ('{printed}') does not match the value stored in its signed QR code ('{qr}')." |
| `ID-QR-03` | "The photo inside the ID card's QR code does not match the printed photo (similarity {sim:.2f})." |
| `CLM-X-06` | "The photo was taken {distance_km:.0f} km from the location given for the incident." |
| `CLM-X-07` | "The {item} is dated {item_date}, before the policy started on {policy_start}." |
| `CLM-X-08` | "The {doc_kind} is dated {doc_date}, before the incident on {incident_date}." |
| `CLM-NET-01` | "This claimant shares a {entity_kind} with claim {other_id}." |
| `CLM-NET-02` | "This claim is linked to {n} other claims through shared details." |

### 16.3 Recommended actions by band

| Band | Action text |
|---|---|
| LOW | "No significant indicators. Proceed with the normal process." |
| MEDIUM | "Route to manual review. Check the highlighted items." |
| HIGH | "Escalate to the fraud investigation team before any payout." |

The tool recommends; it does not decide claims. This wording is deliberate.

### 16.4 LLM guardrails (`llm.py`)

- The prompt contains only the structured evidence list (id, title, score, details) and the band. No raw personal data beyond what appears in the details.
- Instruction: *"Write 2–3 sentences. Use only the facts provided. Do not add facts, numbers or causes. Do not change the risk level. If confidence is not high, say so."*
- **Validation after generation:** every number in the output must appear in the input; if any number or entity is not found in the input, discard the LLM text and use the template summary.
- Timeout of a few seconds; on error or timeout use the template summary and set `summary_source = "template"`.
- The score, band and evidence are **never** produced or altered by the LLM.

### 16.5 What the UI shows

- The summary paragraph.
- The top reasons as evidence cards with the score bar and a link to the region on the image or page.
- "Why this score" panel: the fusion terms in plain form ("Strongest contributor: AI-generated image probability, 61% of the total").
- "Checks run" table with `ok / skipped / failed` for every detector, so nothing is hidden.

---

## 17. ML training and data generation

Only two models are trained by the team: the **document tamper CNN** and the **word-level anomaly model**. The image detector is pre-trained (final choice), with calibration fitted on your own data. Optionally a small logistic "stacker" can be trained on the image evidence, but the default is transparent noisy-OR fusion.

### 17.1 Data plan

| Set | Content | Approx. size **(estimate)** | Used for |
|---|---|---|---|
| Authentic documents | Rendered invoices, medical bills, claim forms, repair estimates | 600–1000 pages | Train + validate CNN; fit anomaly model |
| Tampered documents | Same pages after automatic edits (with masks) | 600–1000 pages | Train + validate CNN |
| Authentic images | Real photos: vehicles, damage, property (public datasets, your own photos) | 300–1000 | Calibration and thresholds |
| Fake images | Fully generated + inpainted + spliced | 300–1000 | Calibration and thresholds |
| **Real-edit test set** | 20–30 documents and 20–30 images tampered **by hand** in real editors | small | **Test only, never trained on** |
| Demo samples | 6–8 curated files | small | Live demo; also in the golden tests |

Check the license of every dataset you download, and prefer generating your own data over redistributing someone else's.

### 17.2 Clean document generator (`make_clean_documents.py`)

- Jinja2 HTML templates (invoice, hospital bill, repair estimate, claim form, ID-style card) rendered to PDF with WeasyPrint or ReportLab.
- Randomise: company names, addresses, dates, item lists, amounts, tax rates, fonts (a small pool), font sizes, table layouts, logos, colours, and paper size, using `faker` and a seeded RNG (seed stored per sample for reproducibility).
- Guarantee **internal consistency** (totals add up, dates in order) so the rules pass on authentic samples.
- Render to PNG at 150 dpi, then push through the shared degradation pipeline (17.4).

### 17.3 Tamper generator (`make_tampered_documents.py`)

Each recipe edits one or more regions and writes a **mask** PNG of the edited pixels plus a JSON record (recipe, region, before/after text).

| Recipe | How | Notes |
|---|---|---|
| Digit replacement | Whiten region, redraw a changed number with a slightly different font or size | The most realistic edit; include variants with matching font too |
| Overlay text | Paste a new text box over the original | |
| Inpaint and retype | `cv2.inpaint` the region, then type new text | |
| Copy-move | Copy a region elsewhere on the page | For example duplicate a stamp or signature |
| Splice | Paste a region from another document | |
| Style change | Change weight, colour or size of one field | |
| Logic edit | Change a value so that a rule breaks (a total, a date) | Also creates rule-violation labels for testing the rules |

Also generate "**hard negatives**": authentic pages with harmless variation (mixed fonts by design, stamps, handwriting-like fonts) so the models do not learn "any variation = tamper".

### 17.4 Shared degradation pipeline (`degrade.py`) — critical

Apply the **same random processing to authentic and tampered pages**: JPEG quality between 50 and 95, resize down and up, Gaussian noise, slight blur, small rotation and perspective. If only the tampered pages were re-saved, the model would learn "re-compressed = fake" and fail on everything real. This is the most common mistake in this kind of project.

Also generate a set of **scan-like** samples (paper texture, skew, shadows, moiré) so the pipeline meets low-quality input during training, not for the first time in the demo.

### 17.5 Fake image generator (`make_fake_images.py`)

- **Fully generated:** Stable Diffusion (via `diffusers`) with prompts such as "car with front bumper damage on a road, photo".
- **Inpainted edits:** take a real photo, mask a region, inpaint with a damage prompt (dent, scratch, cracked windshield).
- **Classical edits:** copy-move and splice.
- Apply the same degradation to real and fake images.
- Record the generator, prompt and seed; keep at least one generator **held out** for the generalization test.

### 17.6 Tamper CNN training recipe (`train_doc_cnn.py`)

| Item | Choice |
|---|---|
| Input | 128×128 ELA patches (quality 90, scale 15), 3 channels |
| Label | 1 if the patch overlaps the tamper mask by at least 10% of its area, else 0 |
| Sampling | All positive patches + 3–5× as many random negative patches per page (plus hard negatives) |
| Backbone | `EfficientNetB0`, ImageNet weights |
| Head | GlobalAveragePooling → Dropout(0.3) → Dense(1, sigmoid) |
| Phase 1 | Freeze backbone; Adam lr 1e-3; up to 5–10 epochs |
| Phase 2 | Unfreeze the last blocks (keep BatchNorm frozen); Adam lr 1e-5; up to 10–20 epochs |
| Loss / metrics | Binary cross-entropy; AUC, precision, recall |
| Class balance | Class weights or the sampling ratio above |
| Callbacks | Early stopping on validation AUC (patience 3–5), ModelCheckpoint, ReduceLROnPlateau |
| Augmentation | Horizontal shifts and minor scale; **no** JPEG-changing augmentation on the ELA input (it would destroy the signal) |
| Compute | Colab or Kaggle GPU **(estimate under an hour)** |

**Split by document, never by patch.** All patches from a page (and all pages from a template family, if possible) belong to exactly one of train / validation / test (for example 70 / 15 / 15). Patch-level splitting leaks and produces fake 99% accuracy.

### 17.7 Anomaly model (`train_anomaly.py`)

Fit `IsolationForest(n_estimators=200, contamination="auto")` on per-word features from **authentic** pages, with features standardised within each page. Evaluate by injecting tampered words (from the tamper generator's JSON records) and checking their anomaly rank. Save with `joblib` together with the feature order.

### 17.8 Evaluation protocol (`evaluate.py`)

Report **measured** numbers; nothing else goes on a slide as a result.

| Level | Metrics |
|---|---|
| Patch | AUC, precision, recall, F1 on the held-out documents |
| Page | ROC-AUC, precision/recall at the chosen threshold, confusion matrix |
| Per tamper type | Recall for each recipe (the table that shows where it is weak) |
| **Generalization** | Train with one recipe (or one generator) held out; report performance on it |
| **Real edits** | Same metrics on the hand-made set, reported separately and honestly |
| Robustness | Metrics after extra JPEG compression, blur, noise and downscaling |
| Calibration | ECE and reliability curve before and after calibration |
| End-to-end | Band confusion matrix across the whole pipeline on the full test set |
| Image detector | AUC and accuracy of the Ateeqq detector on **your** real/fake images, before and after calibration; per-generator recall |

### 17.9 Detector sanity check on your own data (`01_detector_bakeoff.ipynb`)

Even though the Ateeqq model is final, run it in the first hours on your real and fake images. It tells you (a) whether it generalizes to insurance-style photos, (b) the right weight for `IMG-AI-01`, and (c) the temperature for calibration. If it underperforms on inpainted edits (likely: it classifies whole images), lean on ELA, noise and the localization heatmap for those, and say so in the limitations.

### 17.10 Reproducibility

Fix random seeds; store the recipe JSON per sample; write `models/README.md` with the command that produced each weight file; store the metric tables in `docs/EVALUATION.md` with the date and git commit.

### 17.11 v2 data for the new detectors

| Set | How to make it | Used for |
|---|---|---|
| Real voice clips | 20–40 short statements recorded by the team in 2–3 languages, varied phones and rooms | Calibrating `VOI-SPOOF-01` |
| Synthetic voice clips | Same sentences generated with open-source TTS and voice-cloning tools; at least one tool held out | Calibration + held-out generalization test |
| Liveness attempts | Scripted runs: live person, printed photo, phone replaying a video, AI-generated face video | Pass/fail table for the honesty slide |
| Aadhaar-style demo cards | Synthetic people (`faker`), demo-key-signed QR, versions with edited printed DOB / name / photo | `ID-QR-01/02/03` tests and demo scenario D |

Apply the shared degradation idea (§17.4) to audio as well: re-encode at low bitrates, add room noise and phone-speaker playback to **both** real and synthetic clips, so the classifier does not learn "compressed = fake".

---

## 18. Robustness to poor-quality input

The problem statement requires handling low resolution, noise, compression artifacts and incomplete inputs. The system addresses each explicitly.

| Challenge | Handling |
|---|---|
| Low resolution | Quality metrics at intake; effective weights reduced (15.3); explicit warning; the AI detector's processor resizes anyway, but confidence is stated as lower |
| Heavy JPEG compression | ELA and noise weights reduced; document CNN trained with compression in the shared degradation pipeline |
| Noise and blur | Trained with noise/blur; OCR preprocessing (denoise, deskew) when confidence is low |
| Scans and photos of documents | Scan path uses OCR and visual checks; skew correction before OCR |
| Incomplete inputs | Missing EXIF, missing fields, missing metadata: checks are `skipped`, never scored as "clean" |
| Multi-page PDFs | Page limit with a notice; per-page evidence with page numbers |
| Password-protected or corrupt files | Clean error message, no crash |
| Unusual formats (HEIC, TIFF, WebP) | Convert with Pillow plugins where possible; otherwise a clear "unsupported" message |
| Screenshots | Detected; ELA disabled; an `info` note explains why |
| Everything fails | The result says what could not be checked and sets confidence to `low` |

---

## 19. Testing and evaluation

### 19.1 Backend tests (`pytest`)

| Test file | What it covers |
|---|---|
| `test_scoring.py` | Fusion maths against hand-computed values (the worked example in 15.8 is a test), participation threshold, per-source cap, band boundaries, override rules, confidence downgrades |
| `test_rules.py` | Each consistency rule with a passing and failing case, including tolerance and formatting edge cases |
| `test_image_pipeline.py` | Runs on known real and fake sample images with a stubbed model (fast) and with the real model (marked `slow`); checks evidence ids and no crash on a corrupt file |
| `test_document_pipeline.py` | Runs on a clean PDF, a tampered PDF and a scan; checks flagged fields and boxes |
| `test_api.py` | Uploads with `httpx`: success, wrong type, too large, poll to completion, result shape, mock mode |
| `tests/golden/` | Stored expected evidence ids and bands for each demo sample; a change fails the test so the demo cannot silently break |

### 19.2 Frontend tests

- Vitest + React Testing Library for `ScoreGauge` (renders band word), `BoxOverlay` (correct pixel rectangles), `EvidenceCard`, `useJobPolling` (stops when done).
- One Playwright smoke test (optional): upload a demo sample in mock mode and assert the band badge appears.

### 19.3 Contract test

A test that regenerates the OpenAPI schema and fails if `frontend/src/api/schema.d.ts` is out of date.

### 19.4 Performance check

`scripts/run_eval.py` also records per-step timings for every demo sample, so the latency table (9.10) is measured, not guessed.

### 19.5 Definition of done for each pipeline

A pipeline is done when: (1) it returns valid `Evidence` for all demo samples, (2) no input crashes it, (3) failures degrade gracefully, (4) its tests pass, (5) its measured metrics are in `docs/EVALUATION.md`, and (6) the UI renders its output in the results dashboard.

---

## 20. Security, privacy and ethics

Claim files contain personal data, so the prototype should behave like a system that could be trusted with it.

### 20.1 Upload safety

| Risk | Control |
|---|---|
| Malicious file disguised by extension | Validate **magic bytes**, not the extension or the client MIME type |
| Path traversal / overwriting | Store under server-generated UUID names; never use the client file name in a path |
| Oversized files or decompression bombs | Enforce `MAX_UPLOAD_MB`; set Pillow's `MAX_IMAGE_PIXELS`; cap PDF pages and render size |
| Malicious PDF content | Parse and render only; never execute embedded JavaScript or launch actions; run PyMuPDF with default safe settings; per-detector timeouts |
| Resource exhaustion | Concurrency limit on jobs; timeouts; rate limiting on the analyze endpoints if exposed beyond localhost |
| Cross-origin abuse | Explicit `CORS_ORIGINS` allow-list, no wildcard |
| Secrets | API keys only in environment variables; never logged; `.env` gitignored |
| Error leakage | Internal errors return `INTERNAL_ERROR`; stack traces only in server logs |

### 20.2 Privacy

- **Retention:** uploads deleted after `RETENTION_HOURS`; a "delete this analysis" action removes the row and artifacts.
- **Minimisation:** face embeddings are computed in memory and not stored; the FAISS index stores image embeddings (not faces) and hashes.
- **LLM use:** when the LLM is enabled, extracted document text is sent to an external provider. Say so in the README and on the ethics slide, make it switchable (`LLM_ENABLED=false`), and prefer sending extracted fields rather than full page images. For a real deployment, a self-hosted model would replace it.
- **Demo data:** use only synthetic or consented sample files; never real people's IDs.
- **Aadhaar (v2):** never store the full Aadhaar number, the QR payload or the QR photo; store only the comparison outcome and masked last 4 digits. Do not log OCR text from ID cards. The demo uses synthetic Aadhaar-style cards signed with a team demo key.
- **Voice (v2):** audio follows the same retention timer as uploads; transcripts are stored with the claim; audio is sent to Bhashini only when the claimant presses the mic button, and the consent line in wizard step 5 says so.
- **Liveness frames (v2):** kept only for the session, then deleted; only the chosen selfie frame follows the normal upload retention.
- **Claimant view (v2):** `/claims/{id}/status` shows the decision, the reason category and the claimant message (§7.6), but never scores, evidence, detector names or internal notes.

### 20.3 Responsible-AI statement (for the proposal and the demo)

- The system **assists** investigators; it does not approve or deny claims.
- Scores are probabilistic. False positives (flagging genuine claims) and false negatives (missing fakes) both exist, and the report shows confidence and which checks did not run.
- Every flag is explained and traceable to evidence, so a human can overrule it.
- Face comparison and deepfake detection can perform unevenly across skin tones, lighting and camera quality; test on varied samples and state the limits.
- Not suitable as sole evidence for legal or forensic conclusions.

---

## 21. Deployment and operations

### 21.1 Local run (development)

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt --break-system-packages   # omit the flag in a venv
python ../scripts/download_models.py                       # cache all weights before the event
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend && npm install && npm run gen:api && npm run dev   # http://localhost:5173
```

### 21.2 Docker Compose (demo)

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - ./models:/app/models:ro
      - ./data/runtime:/app/data/runtime
      - ./data/demo_samples:/app/data/demo_samples:ro
    healthcheck: { test: ["CMD","curl","-f","http://localhost:8000/api/v1/health"], interval: 10s, retries: 10 }
  frontend:
    build: ./frontend
    ports: ["8080:80"]
    depends_on: [backend]
```

Model weights are mounted, not baked into the image, so rebuilds stay fast and the same weights are used everywhere.

### 21.3 Environment variables

See section 9.8. `.env.example`:

```
MAX_UPLOAD_MB=15
MAX_PDF_PAGES=10
RETENTION_HOURS=24
MAX_CONCURRENT_JOBS=1
DETECTOR_TIMEOUT_S=30
IMAGE_MODEL_ID=Ateeqq/ai-vs-human-image-detector
OCR_ENGINE=paddle
LLM_ENABLED=true
LLM_PROVIDER=          # e.g. anthropic | gemini | openai
LLM_API_KEY=           # never commit
MOCK_ANALYSIS=0
DEMO_MODE=1           # use data/demo_cache responses first for external calls
AUTH_SECRET=          # random string, never commit
AUTH_TOKEN_HOURS=8
AADHAAR_QR_MODE=demo_key
DEMO_QR_PUBKEY_PATH=models/demo_qr_public.pem
BHASHINI_API_KEY=
BHASHINI_USER_ID=
ENTITY_HASH_SALT=
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```

### 21.4 Hardware

| Task | Requirement |
|---|---|
| Demo inference | A laptop CPU with 8 GB or more RAM is workable **(estimate; measure it)**; a GPU is optional |
| Training | A free Colab or Kaggle GPU |
| Disk | A few GB for model weights and generated data |

### 21.5 Demo-day reliability checklist

- [ ] All models downloaded and loading offline (`/health` shows every model `true`).
- [ ] `LLM_ENABLED` decision made; template fallback verified by unplugging the network once.
- [ ] `seed_demo.py` run: demo samples analyzed once, results cached, FAISS index seeded.
- [ ] Frontend production build served; no dev-server dependency.
- [ ] Browser zoom, full-screen and a backup laptop tested.
- [ ] A recorded screen capture of the full demo as a fallback.
- [ ] Sample files open from a known folder; no file-dialog hunting.

### 21.6 Makefile targets

| Target | Action |
|---|---|
| `make dev` | Start backend and frontend in dev mode |
| `make test` | Backend pytest + frontend Vitest |
| `make data` | Generate synthetic documents and images |
| `make train` | Train tamper CNN and anomaly model, then calibrate |
| `make eval` | Run `scripts/run_eval.py` and write `docs/EVALUATION.md` tables |
| `make demo` | Seed demo data and run Docker Compose |

---

## 22. Team roles and the 24-hour plan

### 22.1 Roles

The team is small (two to four people). The suggested split follows the strengths described so far: two machine-learning people and no dedicated web developer.

| Role | Owns |
|---|---|
| **ML lead** | Image pipeline, scoring engine, calibration, evaluation, model sanity checks |
| **ML support** | Document pipeline, synthetic data generators, tamper CNN and anomaly model, OCR and rules |
| **Web owner** (a named person, using an AI coding assistant heavily; if the team is only two, the ML lead and ML support share this and keep the UI simple) | Frontend, API glue, report export, Docker, demo polish |
| **Everyone** | Writing tests for their own code; rehearsing the demo |

Assign the web owner **at hour 0**; an unowned UI is the most common way a strong ML project loses points.

### 22.2 Hour-by-hour plan

| Hours | ML lead | ML support | Web owner |
|---|---|---|---|
| **0–2** | Repo, `schemas/`, evidence catalog draft, scoring skeleton with fake evidence | Start clean-document generator; collect real and fake image samples | Vite + React + Tailwind shell; generate `schema.d.ts`; mock mode returns canned results |
| **2–5** | Image detector wrapper, metadata, ELA, calibration notebook (sanity check on your data) | Tamper generator (digit replace, overlay, copy-move), shared degradation; PDF parser and OCR wired | Upload page, progress list, results dashboard on mock data |
| **5–9** | Noise, localization heatmap, duplicate index; scoring fusion and overrides with tests | Field extraction (regex + LLM), consistency rules, font checks, start CNN training on Colab | Image viewer with heatmap, PDF viewer with box overlay, evidence cards |
| **9–13** | Explainer (templates first), claim pipeline and cross-checks | CNN evaluation, anomaly model, embedded-image handoff; fix rule false positives | Connect real API, error and empty states, history page |
| **13–17** | Threshold and weight tuning on saved evidence; identity pipeline | Real-edit test set (hand-made), robustness runs, per-tamper-type table | Report export (JSON/PDF), quality warnings, checks-run table |
| **17–20** | End-to-end evaluation, `EVALUATION.md`, latency measurements | Retrain if needed; document model cards | Visual polish, accessibility pass, Docker Compose |
| **20–22** | Golden tests on demo samples; fix regressions | Bug bash with degraded inputs | Demo samples buttons, production build, offline check |
| **22–24** | Freeze code at hour 22; rehearse; record backup video; README; slide with measured results | ← | ← |

**Hard rules:** a feature not working by hour 18 is cut or hidden; freeze at hour 22; never change models or weights after the freeze.

### 22.3 Cut list (drop in this order if time runs short)

1. Occlusion-based localization (keep the ELA heatmap)
2. PDF report (keep JSON)
3. Identity pipeline
4. Duplicate detection
5. LLM rewrite of explanations (keep templates)
6. History page

**Never cut:** image detection with confidence, document flags with reasons, composite score with explanation, working upload UI.

### 22.4 Milestones (checkpoint questions)

| Hour | Question to ask |
|---|---|
| 3 | Can the UI show a full mock result end to end? |
| 9 | Does each pipeline return real evidence for at least one sample? |
| 13 | Does a real upload produce a real dashboard? |
| 17 | Do we have measured metrics we are willing to show? |
| 20 | Can a stranger run the demo from the README? |
| 22 | Is the code frozen and the backup video recorded? |

### 22.5 v2 roles, plan and cut list

The original plan already fills 24 hours. v2 is only realistic with these two changes:

1. **Pre-event preparation (verify the rules):** if allowed, generate synthetic data, train the tamper CNN and anomaly model, run both bake-offs (image, voice) and create the Aadhaar-style demo cards **before** the 24 hours. Otherwise the v2 bonus features move to the bottom of the cut list.
2. **A fourth person, the Integration owner** (the problem statement allows up to 4): Bhashini, Aadhaar QR, story review, entity links, the new endpoints and the demo caches. With three people, the ML lead takes entity links and Aadhaar QR, and the web owner takes the Bhashini client.

| Hours | Integration owner (new) | Changes for existing roles |
|---|---|---|
| 0–2 | Bhashini key and pipelines tested; v2 contracts in `schemas/`; mock responses for sync endpoints | Web owner: all new routes as shells on mock data |
| 2–6 | `/voice/transcribe` end to end with field extraction | ML lead: voice bake-off next to the image bake-off |
| 6–10 | Aadhaar QR decoder, demo-key signing script, printed-vs-QR comparison | Web owner: wizard steps 1, 2, 4 |
| 10–14 | Story review with validation; entity links + `/network` | ML support: server-side liveness verify; web owner: liveness UI and ID capture |
| 14–18 | Decisions + audit; seed demo scenarios A–D; cache Bhashini and LLM responses | Web owner: result-page tabs, decision bar, queue, network page |
| 18–22 | Bug bash on new paths; offline test with the network unplugged | As original plan |

**Cut list v2** (cut from the top; this list runs **before** the original §22.3 list):

1. Fraud-network page (keep `CLM-NET-01` evidence on the case page)
2. Story review tab
3. Claimant status page (keep the wizard)
4. Synthetic-voice detection (keep transcription and auto-fill)
5. Dashboard and analytics charts (keep the queue; keep the KPI row)
6. Claimant evidence timeline (keep the investigator timeline)
7. Aadhaar QR photo comparison (keep signature and field comparison)

**Never cut:** everything on the original never-cut list (image detection with confidence, document flags with reasons, composite score with explanation, working upload UI) plus the investigator Analyze page used in demo steps 1–2.

---

## 23. Demo script (10 minutes)

Follows the **exact order required** by the problem statement (image → document → composite → architecture → identity). v2 features appear inside the step they belong to.

| Time | Step | What to show | What to say |
|---|---|---|---|
| 0:00–0:40 | Framing | Landing page; one sentence on the problem | "AI can fabricate claim evidence at scale. Lucen AI flags it and explains why." |
| 0:40–2:15 | **1. Image** | Investigator → Analyze → Image tab: upload an AI-generated damage photo; progress list; image authenticity score, confidence, band, heatmap. Then a genuine photo for contrast | "97% likely AI-generated after calibration; the heatmap shows where; the genuine photo scores low." |
| 2:15–3:45 | **2. Document** | Analyze → Document tab: tampered invoice; flagged fields with boxes and reasons; hover a row to highlight its box | "The total doesn't match the line items, and the amount uses a different font." |
| 3:45–5:45 | **3. Composite** | Claimant wizard for scenario B, prefilled except the voice step: speak 15 s in Hindi, fields fill, submit. Switch to the queue: it appears at the top as HIGH. Open it: image, document and overall scores, "why this score", duplicate banner, story tab | "Overall is HIGH because of independent strong signals; here is each one's contribution. The story tab is for the investigator and does not change the score." |
| 5:45–7:15 | **4. Architecture** | §4.1 and §4.4 diagrams; pre-trained vs trained; evidence contract; deterministic scoring; LLM only describes | "Pre-trained where it exists, trained on synthetic tampering where it doesn't, and every score traces back to evidence." |
| 7:15–8:45 | **5. Identity (bonus)** | Live liveness challenge in front of the judges (scenario A, passes). Then scenario D: liveness failed, ID vs selfie mismatch, Aadhaar QR shows printed DOB ≠ signed QR DOB, network shows 4 claims sharing one bank account | "A fake video can't follow random instructions, and an edited ID card can't match its own signed QR." |
| 8:45–9:30 | Honesty slide | Measured metrics (image, document, voice, liveness attempts); known limits | "On our hand-made test sets: [measured numbers]. Here is where it is weak." |
| 9:30–10:00 | Close | Impact: fewer manual reviews, faster honest claims, explanations investigators can act on | One-line summary |

**Demo scenarios (seed with `scripts/seed_demo.py`; cache every external response):**

| ID | Scenario | Expected |
|---|---|---|
| A | Genuine motor claim, Hindi voice statement, liveness passed, Aadhaar-style card verified, camera photos | LOW, fast-track |
| B | AI-generated damage photo, reused from an earlier claim, repair invoice consistent | HIGH (`IMG-AI-01`, `IMG-DUP-01`) |
| C | Health claim with a tampered hospital bill: total ≠ line items, amount in a different font, PDF modified after creation | HIGH (`DOC-LOGIC-01`, `DOC-FONT-01`, `DOC-META-02`) |
| D | Synthetic identity: liveness failed, ID vs selfie mismatch, printed DOB edited (QR mismatch), bank account shared with 3 other claims | HIGH via O6, visible cluster in the network |

**Rehearsal rules:** time it twice; keep every demo file in one folder; one person drives, one narrates; run the whole demo once with the network unplugged; know the answers to "what happens on a low-quality image?" (§15.3), "why not train a bigger model?" (the brief's own emphasis) and "is the Aadhaar check real?" (real format and signature logic; demo cards use a demo key for privacy).

---

## 24. Evaluation-criteria mapping

| Criterion (weight) | What Lucen AI offers | Evidence to show |
|---|---|---|
| **Detection accuracy on sample data (25%)** | Pre-trained SigLIP detector calibrated on your data; ELA and noise for edits; tamper CNN and rule checks for documents; robustness through degradation; v2: synthetic-voice detector calibrated on team clips | Measured metrics table; ROC; per-tamper-type recall; real-edit test set; held-out-generator result; voice and liveness attempt tables |
| **Risk scoring and explainability (25%)** | Evidence objects, calibrated scores, noisy-OR fusion, contributions, overrides, template reasons, checks-run table; v2 adds field-by-field Aadhaar QR comparisons and a validated story review | "Why this score" panel; the worked example; evidence cards with reasons |
| **UI / demo quality (20%)** | Two portals: claimant wizard (voice in Indian languages, live identity check, guided capture) and investigator dashboard (queue, analyze, case page with heatmaps and overlays, network) | Live demo in the required order; accessibility and empty states |
| **Code quality and architecture (15%)** | Layered monorepo, typed contracts, detector protocol, deterministic scoring, tests, Docker, docs; every v2 feature follows the same contracts and mock mode | Repo tree; tests passing; README and this document |
| **Innovation and bonus features (15%)** | Identity comparison (required bonus) plus liveness challenge, Aadhaar Secure QR verification, multilingual voice intake with synthetic-voice detection, embedded-image bridge, cross-claim duplicate detection and fraud network | Demo steps 3 and 5; architecture slide |

---

## 25. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The image detector over-trusts itself on insurance-style photos | High | High | Calibrate on your data; combine with ELA, noise, metadata; report per-generator results; state the limit |
| The detector misses small local edits (it classifies whole images) | High | Medium | Lean on ELA, noise map and localization for edited regions; show the heatmap; say so in the limitations |
| Tamper CNN overfits the synthetic generator | High | High | Shared degradation; hard negatives; hold out a recipe; **real-edit test set**; treat the CNN as one signal among several |
| No usable frontend skills on the team | Medium | High | Assign the web owner at hour 0; generate from the contracts with an AI assistant; build against mock mode first |
| Model files or network unavailable at the venue | Medium | High | Pre-download everything; local OCR; template fallback; backup video |
| LLM extraction invents values | Medium | Medium | Strict JSON schema; substring validation; regex fallback; the LLM never scores |
| OCR quality on bad scans | Medium | Medium | Preprocessing; confidence gating; skip rather than guess |
| Too slow for a live demo | Medium | Medium | Cache demo results; make occlusion optional; cap pages; measure latency early |
| False positives on authentic but unusual documents | Medium | Medium | Hard-negative training; modest metadata weights; participation threshold; MEDIUM band means "review" |
| Data leakage inflates reported accuracy | Medium | High | Split by document and template; report on the untouched test set once |
| Scope creep | High | Medium | Cut list (22.3); freeze at hour 22 |
| Licence problems (InsightFace models, LayoutLM if used, datasets) | Low | Medium | Note licences in `MODEL_CARDS.md`; hackathon use is non-commercial; state it |
| Bhashini key, quota or latency issue at the venue (v2) | Medium | Medium | Test in hour 0; Web Speech fallback; typed description; cached demo responses |
| Webcam blocked on the demo laptop (v2) | Medium | High | Test browser permissions early; upload-selfie path; backup video of the liveness step |
| Aadhaar QR unreadable on low-quality photos (v2) | Medium | Low | Upscale and sharpen before decoding; `ID-QR-04` is a warning, never fraud |
| Using real Aadhaar data (v2) | Low | High | Synthetic demo cards with a demo key; masking; nothing stored |
| v2 scope pushes must-haves late (v2) | High | High | v2 cut list (§22.5) applies first; milestone at hour 13 must show real image + document results |

---

## 26. Limitations

State these plainly in the proposal and the demo; judges reward candour.

1. **Synthetic-trained document models** may not generalize to real forgeries; the real-edit test set exists to measure exactly this.
2. **The image detector is a whole-image classifier.** It is strong on fully generated images and weaker on small local edits.
3. **New generators appear constantly.** Pre-trained detectors degrade as generators change; the calibration and evidence-fusion design reduces, but does not remove, this risk.
4. **ELA and noise analysis** depend on compression history and do not work on every file type.
5. **OCR errors** propagate into field extraction and rule checks; low-confidence text is flagged, not trusted.
6. **Metadata can be legitimately odd or deliberately cleaned**; it is weak evidence and weighted accordingly.
7. **Face matching** depends on image quality and can perform unevenly across demographics and lighting; thresholds must be set on representative pairs.
8. **Scores are decision support**, not proof; the system does not establish intent or legal fraud.
9. **Prototype scope:** single machine, SQLite, demo login only (no real authentication or multi-tenant separation), basic audit log of case decisions only.
10. **Liveness** defeats replays and photos, not every real-time face-swap; it is not a certified liveness system.
11. **Aadhaar QR** checks only cards that carry a Secure QR; older unsigned QRs cannot be verified, and the demo uses a demo signing key instead of real UIDAI-signed cards.
12. **Synthetic-voice detection** is calibrated on a small team-made set and may not generalize to new voice-cloning tools; it is one signal among many.
13. **Story review** depends on an LLM and is shown for review only; it does not affect scores by default.

### 26.1 Future work (one slide)

Video deepfakes, active learning from investigator feedback, a fine-tuned document-tamper model on real data, model ensembles updated as generators evolve, role-based access and audit logging, self-hosted LLM, integration with claims-management systems.

---

## 27. Appendices

### 27.1 Suggested `requirements.txt` groups (versions pinned after first install)

```
# API
fastapi  uvicorn[standard]  pydantic  pydantic-settings  python-multipart  httpx
# Images / forensics
pillow  opencv-python-headless  numpy  scipy  scikit-image  imagehash  exifread  piexif
c2pa-python        # verify availability on your platform
# ML
torch  transformers  tensorflow  scikit-learn  joblib  faiss-cpu  open_clip_torch
# Documents
pymupdf  pdfplumber  paddleocr  paddlepaddle  pytesseract  rapidfuzz
# Identity (bonus)
insightface  onnxruntime
# v2: voice, liveness, Aadhaar QR
soundfile  librosa  mediapipe  pyzbar  pyaadhaar  cryptography  requests
# Reports / misc
reportlab  weasyprint  jinja2  faker
# Tests
pytest  pytest-asyncio
```

Installing TensorFlow, PyTorch and PaddlePaddle together is heavy and can conflict on some machines. If it does, run the training code (TensorFlow) only in Colab and keep the app on a smaller set: load the trained CNN through `tf.keras` only if TensorFlow installs cleanly; otherwise export the model to ONNX and use `onnxruntime` in the app. Decide this in the first two hours, not the last two.

### 27.2 Frontend dependencies

```
react  react-dom  react-router-dom  @tanstack/react-query
tailwindcss  postcss  autoprefixer  class-variance-authority  lucide-react
recharts  react-dropzone  react-pdf  openapi-typescript
@mediapipe/tasks-vision  react-leaflet  leaflet  react-force-graph-2d   # v2
vitest  @testing-library/react  eslint  prettier  typescript  vite
```

### 27.3 Sample `Evidence` factory (backend)

```python
def make_evidence(*, id, pipeline, source, raw, weight, title, reason,
                  kind="risk", field=None, bbox=None, details=None, artifact=None):
    return Evidence(
        id=id, pipeline=pipeline, source=source, kind=kind,
        raw_score=float(raw), calibrated_score=float(raw),   # overwritten by calibration
        weight=weight, effective_weight=weight,               # overwritten by quality gating
        severity="low", title=title, reason=reason,
        field=field, bbox=bbox, details=details or {}, artifact=artifact,
    )
```

### 27.4 Sample fusion function

```python
def fuse(evidence: list[Evidence]) -> float:
    terms = []
    for e in evidence:
        if e.kind != "risk":
            continue
        t = e.effective_weight * e.calibrated_score
        if e.calibrated_score >= 0.2 and t >= 0.02:
            terms.append(t)
    risk = 1.0
    for t in terms:
        risk *= (1.0 - t)
    return 1.0 - risk
```

(The per-source cap in 15.4 is applied to the terms before multiplication.)

### 27.5 Sample LLM prompts

**Field extraction (system):**
```
You extract structured data from OCR text of an insurance-related document.
Return ONLY valid JSON matching the schema. Use null for anything not present.
Copy values exactly as they appear; never infer, correct, or invent values.
```

**Explanation rewrite (system):**
```
You write a short plain-English summary for a claims investigator.
Use only the facts in the provided evidence list. Do not add any facts, numbers
or causes. Do not change the stated risk level. 2-3 sentences. If confidence
is not "high", mention that some checks were limited.
```

### 27.6 Prompt for generating the frontend with an AI assistant

```
Build a React 18 + TypeScript + Vite + Tailwind + shadcn/ui frontend called
Lucen AI for an insurance-claim fraud-detection API. Use TanStack Query,
react-router-dom, react-dropzone, react-pdf, Recharts, react-leaflet,
react-force-graph-2d and @mediapipe/tasks-vision. Follow the data contracts
and API in the attached specification exactly (sections 6, 6.8, 7, 7.5).

Two portals:
1) Claimant (mobile-first, no sidebar, English/Hindi switch): /claim/new is
   a 5-step wizard (Policy → Your story [mic button, POST /voice/transcribe,
   editable auto-filled fields, map pin] → Verify it's you [liveness
   challenge with MediaPipe Face Landmarker guidance, frames posted to
   /identity/liveness/verify; then ID card capture posted to
   /identity/aadhaar-qr] → Evidence [guided capture slots by claim type,
   camera vs upload marked] → Review [consent, POST /claims]).
   /claim/:id shows a status timeline and a "Your evidence" list
   (received / checked / needs replacing), never scores.
2) Investigator (left sidebar, light slate background, ink-blue text,
   evidence-yellow numbered markers): /app dashboard, /app/queue risk-sorted
   table, /app/analyze (tabs Image | Document | Full claim; upload → 202 job
   id → poll /jobs every second → /results/{id}), /app/results/:id dashboard
   (image, document and overall scores first and largest; identity and voice
   as smaller cards; explanation panel; evidence cards sorted by
   contribution; image viewer with heatmap opacity slider; PDF viewer with
   box overlays linked to a flagged-field table; tabs Identity [liveness
   checklist, ID vs selfie, Aadhaar QR printed-vs-QR table], Voice, Story
   [labelled "for review, not part of the score"]; duplicate banner;
   Evidence timeline tab [vertical timeline, red contradiction connectors,
   Undated group]; decision bar; quality warnings; checks-run table; JSON/PDF export),
   /app/network force graph, /app/analytics trend page (KPI row, stacked
   band bars per day, flagged-rate and average-risk lines, top signals,
   by claim type, spike banner; range and type filters; table toggle).

Provide a mock API layer with canned LOW, MEDIUM and HIGH results including
voice, liveness, aadhaar_qr, story and links blocks, and canned responses for
every sync endpoint. Accessible: never rely on colour alone, keyboard
navigable, visible focus. Include empty, loading and error states. Add Vitest
tests for ScoreGauge, BoxOverlay, EvidenceCard, the polling hook and the
wizard step validation.
```

### 27.7 Glossary

| Term | Meaning |
|---|---|
| **ELA** | Error Level Analysis: recompress an image at a known JPEG quality and amplify the difference; edited regions often show different error levels |
| **C2PA** | A standard for signed "content credentials" describing how a file was created or edited |
| **SigLIP** | A vision-language transformer family; the chosen detector is fine-tuned from it for real-vs-AI classification |
| **Temperature scaling** | Post-hoc calibration that divides logits by a fitted scalar so probabilities match observed frequencies |
| **ECE** | Expected Calibration Error: gap between confidence and accuracy across bins |
| **Noisy-OR** | Way to combine independent risk signals: `1 − Π(1 − wᵢpᵢ)` |
| **Isolation Forest** | Anomaly-detection model that isolates outliers with random splits |
| **ArcFace** | Face-embedding model; similarity between embeddings measures identity match |
| **pHash / CLIP / FAISS** | Perceptual hash, image-embedding model, and vector search library used for duplicate detection |
| **Hard negative** | An authentic sample that looks unusual, used to stop a model equating "different" with "fake" |
| **Bounding box (normalised)** | A rectangle stored as fractions of the page or image size |
| **Aadhaar Secure QR** | The QR code on Aadhaar cards and e-Aadhaar, containing the holder's details and photo, digitally signed by UIDAI |
| **Liveness challenge** | Random on-screen instructions (blink, turn, read digits) that a recording or photo cannot follow |
| **Bhashini** | Government of India language platform providing speech recognition and translation for Indian languages |
| **Verhoeff checksum** | The check-digit algorithm used by 12-digit Aadhaar numbers |

### 27.8 Reference links

- Image detector: <https://huggingface.co/Ateeqq/ai-vs-human-image-detector>
- Research reference on text manipulation detection: <https://huggingface.co/papers/2312.06934>
- Problem statement: ADROSONIC Build, "AI-Powered Synthetic Identity & Deepfake Claim Detection System"

---

*End of document.*
