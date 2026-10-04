# 🛡️ Lucen AI — Backend Architecture & Integration Guide

**System:** AI-Powered Synthetic Identity & Deepfake Claim Detection Engine  
**Framework:** FastAPI + Python 3.11+ / Uvicorn  
**Database:** SQLite + Repository Pattern (`backend/app/db/`)  
**OpenAPI Specification:** [docs/openapi.json](file:///c:/Users/gaura/Desktop/LUCENAI/docs/openapi.json) (41 endpoints)

---

## 1. Quick Start

### 1.1 Virtual Environment & Dependencies
```bash
# From workspace root
python -m venv backend/.venv
backend\.venv\Scripts\activate      # Windows
# or: source backend/.venv/bin/activate  # Linux/macOS

pip install -r backend/requirements.txt
```

### 1.2 Running the Development Server
```bash
# Start backend server on http://localhost:8000
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### 1.3 Running Tests
```bash
python -m pytest backend/tests -x --timeout=120 -q
# Target: 109 passed, 1 skipped, 43 warnings
```

---

## 2. Directory & Component Structure

```
backend/app/
├── main.py                     # FastAPI application factory & router mounting
├── api/v1/                     # REST API route handlers
│   ├── analytics.py            # Dashboard aggregate statistics
│   ├── analyze.py              # File upload & async analysis triggers
│   ├── artifacts.py            # Signed artifact download & preview
│   ├── auth.py                 # JWT login & user profile (`/auth/login`, `/auth/me`)
│   ├── claims.py               # Claims CRUD, evidence submission & status
│   ├── decisions.py            # Investigator decision workflow (draft/final)
│   ├── health.py               # Liveness & readiness probes
│   ├── identity.py             # Active liveness session & verification
│   ├── jobs.py                 # Background analysis job status polling
│   ├── mock_data.py            # Seed data helper endpoints
│   ├── network.py              # Fraud ring network graph & community queries
│   ├── policies.py             # Claimant policy verification
│   ├── queue.py                # Investigator claim review queue
│   ├── results.py              # Analysis results & "Why this score" retrieval
│   └── voice.py                # Bhashini ASR, translation & voice spoofing
├── core/
│   ├── auth.py                 # JWT encoding/decoding, role dependencies
│   ├── config.py               # Pydantic Settings (secrets as SecretStr)
│   ├── errors.py               # Standardized error codes & AppException
│   ├── rate_limit.py           # In-memory sliding window rate limiter
│   └── security.py             # File MIME/magic validation & path safety
├── db/
│   ├── database.py             # SQLite connection & WAL mode config
│   ├── migrations.py           # Schema initialization & table migrations
│   ├── models.py               # SQLite entity definitions
│   └── repository.py           # Query layer (Claims, Results, Decisions, etc.)
├── detectors/                  # Forensic & ML detector modules
│   ├── base.py                 # `run_safely()` detector harness with timeout
│   ├── document/               # OCR, font anomaly, regex, Tamper CNN, ELA
│   ├── identity/               # Face match, Aadhaar Secure QR, active liveness
│   ├── image/                  # SigLIP deepfake, ELA, noise, EXIF, pHash/CLIP
│   ├── story_reviewer.py       # LLM narrative-vs-evidence contradiction detector
│   └── voice/                  # Audio features & synthetic speech detection
├── pipelines/                  # Domain orchestration pipelines
│   ├── claim_pipeline.py       # Cross-modal claim & GPS location validation
│   ├── document_pipeline.py    # Document forensics & tamper extraction
│   ├── identity_pipeline.py    # ID card vs selfie vs Aadhaar QR verification
│   ├── image_pipeline.py       # Full-image AI & tamper localization
│   └── voice_pipeline.py       # Bhashini transcription + audio spoof check
├── schemas/                    # Pydantic schemas (OpenAPI models)
│   ├── claims.py, result.py, evidence.py, decision.py, network.py, ...
├── scoring/                    # Mathematical risk fusion & confidence engine
│   ├── bands.py                # LOW/MEDIUM/HIGH band & confidence thresholds
│   ├── fusion.py               # Noisy-OR mathematical fusion: 1 - Π(1 - wᵢpᵢ)
│   ├── overrides.py            # Deterministic override rules (O1 to O7)
│   ├── quality.py              # Image/document quality gating multipliers
│   └── weights.py              # Master Evidence ID catalog & default weights
└── services/
    ├── bhashini.py             # Two-phase official Bhashini ULCA client
    ├── network.py              # NetworkX fraud ring graph & Louvain clustering
    ├── orchestrator.py         # End-to-end async job runner & artifact signer
    └── job_manager.py          # In-memory background task tracker
```

---

## 3. Environment Variables & Secrets

All secrets are declared in `backend/.env` (and documented with blank values in `.env.example`). Loaded via `pydantic-settings` as `SecretStr`. Never logged or returned in API responses.

| Variable | Description | Example / Default |
|---|---|---|
| `ENVIRONMENT` | Runtime mode (`development`, `production`, `test`) | `development` |
| `API_V1_STR` | Prefix for API routes | `/api/v1` |
| `JWT_SECRET_KEY` | Secret for HMAC-SHA256 token signing | `minimum-32-chars-long-secure-key` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Session token validity duration | `1440` (24 hours) |
| `SQLITE_DB_PATH` | Path to SQLite database file | `backend/data/lucen_ai.db` |
| `STORAGE_LOCAL_DIR` | Upload storage directory | `backend/data/uploads` |
| `ARTIFACT_LOCAL_DIR` | Forensic artifacts storage | `backend/data/artifacts` |
| `BHASHINI_CONFIG_URL` | Bhashini ULCA Config endpoint | Official MeitY ULCA URL |
| `BHASHINI_USER_ID` | Bhashini APP_ID / User ID | `****` |
| `BHASHINI_UDYAT_KEY` | Bhashini Udyat API Key | `****` |
| `BHASHINI_INFERENCE_KEY` | Bhashini Inference API Key | `****` |
| `BHASHINI_PIPELINE_ID` | Bhashini Pipeline ID | `****` |

---

## 4. Authentication & Role-Based Access Control

The backend implements JWT Bearer Authentication. 

### 4.1 Login Endpoint
`POST /api/v1/auth/login`
- **Request:**
  ```json
  {
    "email": "investigator@lucen.ai",
    "password": "Password123!"
  }
  ```
- **Response:**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "role": "investigator",
    "user_id": "usr-inv-01",
    "name": "Senior Investigator"
  }
  ```

### 4.2 Roles & Protected Endpoints
- **`investigator`**: Access to `/api/v1/queue`, `/api/v1/results/*`, `/api/v1/network/*`, `/api/v1/analytics/*`, `/api/v1/decisions/*`, `/api/v1/analyze/*`.
- **`claimant`**: Access to `/api/v1/claims` (submit claim), `/api/v1/claims/mine`, `/api/v1/claims/{id}/status`, `/api/v1/policies/mine`, `/api/v1/identity/liveness/*`.

---

## 5. Scoring & Explainability Engine

### 5.1 Noisy-OR Probability Fusion
The system combines evidence probabilities using the bounded Noisy-OR formula:
$$\text{Risk Score} = 1 - \prod_{i=1}^{n} (1 - w_i \cdot p_i)$$
Where:
- $w_i \in [0.0, 1.0]$: Pre-calibrated evidence weight from [scoring/weights.py](file:///c:/Users/gaura/Desktop/LUCENAI/backend/app/scoring/weights.py)
- $p_i \in [0.0, 1.0]$: Detector probability (calibrated via temperature scaling)

### 5.2 Risk Bands
- **`LOW`**: Score `0.00` – `0.29` (Auto-approval eligible)
- **`MEDIUM`**: Score `0.30` – `0.69` (Standard human review)
- **`HIGH`**: Score `0.70` – `1.00` (Fast-track fraud investigation)

### 5.3 Confidence & Quality Gating
- High quality inputs $\to$ `high` confidence.
- Single detector failure or unverified Aadhaar QR $\to$ step down to `medium`.
- Low resolution image ($\le 800\text{px}$) or compression artifacts $\to$ applies low-res multiplier to weights; drops confidence to `medium` or `low`.
- Complete pipeline failure $\to$ returns confidence `low` and attaches `CHECKS_FAILED` quality warning.

### 5.4 Override Rules (O1 to O7)
Deterministic rules can override mathematical fusion:
- **O1 (Verified Digital Document)**: Valid digital signature + zero tamper markers $\to$ caps score at `0.05` (`LOW`).
- **O2 (Duplicate Image)**: Exact perceptual hash match in unrelated claim $\to$ forces score $\ge 0.85$ (`HIGH`).
- **O3 (Aadhaar QR Biometric Mismatch)**: QR photo differs from submitted ID photo $\to$ forces score $\ge 0.80$ (`HIGH`).
- **O4 (Face Mismatch)**: Claimant selfie does not match ID card portrait $\to$ forces score $\ge 0.75$ (`HIGH`).
- **O5 (Liveness Failed)**: Active challenge or blink test failed $\to$ forces score $\ge 0.70$ (`HIGH`).
- **O6 (All Detectors Failed)**: Pipeline execution error $\to$ score `0.50`, confidence `low`.
- **O7 (Voice Spoof)**: High synthetic voice probability $\to$ forces voice risk $\ge 0.75$.

---

## 6. Key API Endpoints Overview

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Public | Authenticate user & issue JWT |
| `GET` | `/api/v1/auth/me` | Authenticated | Retrieve current user profile |
| `POST` | `/api/v1/analyze/image` | Investigator | Submit single image for immediate forensic analysis |
| `POST` | `/api/v1/analyze/document` | Investigator | Submit invoice/document for tamper analysis |
| `POST` | `/api/v1/analyze/claim` | Investigator | Submit multi-file claim package |
| `GET` | `/api/v1/jobs/{job_id}` | Investigator | Poll async analysis job progress |
| `GET` | `/api/v1/results/{result_id}` | Investigator | Fetch complete forensic report with "Why this score" |
| `GET` | `/api/v1/artifacts/{id}/{name}` | Authenticated | Fetch preview image, ELA heatmap, or PDF page |
| `GET` | `/api/v1/queue` | Investigator | Filterable list of claims sorted by risk / urgency |
| `POST` | `/api/v1/results/{id}/decision`| Investigator | Record Approve / Reject / Refer decision with reasons |
| `GET` | `/api/v1/network/graph` | Investigator | Fraud ring graph (nodes, typed edges, weights) |
| `GET` | `/api/v1/network/rings` | Investigator | Detected fraud ring clusters with shared identifiers |
| `PATCH`| `/api/v1/network/rings/{id}` | Investigator | Update ring status (`open`, `confirmed`, `dismissed`) |
| `GET` | `/api/v1/analytics/overview` | Investigator | Fraud rate trends, band distribution, savings |
| `POST` | `/api/v1/claims` | Claimant | Submit new claim with photos, PDF, voice, GPS |
| `GET` | `/api/v1/claims/mine` | Claimant | List claimant's submitted claims |
| `GET` | `/api/v1/claims/{id}/status` | Claimant | Real-time claim status & tracker |
| `POST` | `/api/v1/identity/liveness/session` | Claimant | Generate randomized active liveness challenge |
| `POST` | `/api/v1/identity/liveness/verify` | Claimant | Verify selfie frames against active challenge |
| `POST` | `/api/v1/voice/transcribe` | Claimant/Inv | Bhashini ASR & Indic translation |

---

## 7. Seeding & Demo Data Scripts

The repository includes pre-configured demo scenarios:
```bash
# 1. Seed Scenarios A through E (Real vs Deepfake images, tampered invoices)
python scripts/seed_demo_claims.py

# 2. Seed Network Demo (Cross-claim fraud rings with shared bank accounts & vehicles)
python scripts/seed_network_demo.py

# 3. Full rebuild of the fraud ring graph (tests scaling up to 5,000 claims)
python scripts/rebuild_network.py
```

### Demo Scenarios Pre-seeded:
- **Scenario A**: Clean authentic claim $\to$ Band `LOW` (Score ~0.08)
- **Scenario B**: AI-generated car damage photo $\to$ Band `HIGH` (Score ~0.94)
- **Scenario C**: Tampered medical invoice (altered totals & font anomaly) $\to$ Band `HIGH` (Score ~0.88)
- **Scenario D**: Synthetic identity (Aadhaar QR mismatch + face swap) $\to$ Band `HIGH` (Score ~0.96)
- **Scenario E**: Multi-claim fraud ring (reused photos, shared bank account) $\to$ Band `HIGH` (Score ~0.92)
