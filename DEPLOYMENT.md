# Lucen AI: Deployment Plan

Put this file at `docs/DEPLOYMENT.md`. It follows the three spec files (architecture §21, features F38/F39, folder structure §2). Anything marked **(verify)** must be checked on the day; anything marked **(estimate)** must be replaced with a measured number.

> **Free Render tier?** Read **§13 (Free-tier mode)** first. The full ML backend does not fit on Render Free, so §2, §5.3 and §5.8 describe the paid setup and §13 overrides them.

---

## 1. Decision (read this first)

| Part | Where it runs | Why |
|---|---|---|
| **Judged live demo** | **Your laptop, Docker Compose, network unplugged** | F39 and the final checklist require the full 10-minute demo to work offline. No cloud host can promise that. This is the primary deployment. |
| **Frontend (hosted backup / shareable link)** | **Vercel** | It is a static Vite SPA. Vercel gives free HTTPS, instant deploys, global CDN. |
| **Backend (hosted backup / shareable link)** | **Render** (Docker web service, paid instance + persistent disk) | The backend is a long-running Python process with SQLite, a FAISS index, uploaded files and heavy ML models. It needs a real disk and several GB of RAM. |

**Vercel for the frontend, Render for the backend.** Vercel alone cannot work, and Render alone is possible but gives you less for the frontend.

### Why not Vercel for the backend

Vercel runs serverless functions. Lucen AI's backend does not fit that model:

- Models (PyTorch, TensorFlow, PaddleOCR, InsightFace, CLIP) are far above serverless size limits.
- Analysis jobs run in an in-process background thread and are polled for 10 to 60 seconds. Serverless functions freeze or die after the response.
- SQLite, `faiss.index` and uploads need a **persistent disk** (`data/runtime/`). Serverless has none.
- Models load once at startup (`lifespan`). Serverless would reload them on every cold start.

### Why not the Render free tier for the backend

As of mid-2026 **(verify at render.com/pricing)**: the Free web service has 512 MB RAM and 0.1 CPU, sleeps after 15 minutes idle (about one minute to wake), has an ephemeral filesystem and **cannot attach a disk**. The full model set will not fit in 512 MB. Use Free only for the static frontend if you ever choose Render for it.

### Why the offline laptop stays primary

Judges may have poor Wi-Fi, free/cheap cloud hosts have cold starts, and F39 explicitly says the demo must run with the network unplugged. The hosted version is a **backup and a shareable link**, not the main plan.

---

## 2. Render instance sizing for the backend

Render instance tiers **(verify current prices)**: Starter 512 MB / 0.5 CPU (~$7), Standard 2 GB / 1 CPU (~$25), Pro 4 GB / 2 CPU (~$85), Pro Plus 8 GB / 4 CPU. Persistent disk is about $0.25 per GB per month.

Rough memory need **(estimate; measure with `/health` and `docker stats`)**:

| Component | Approx. RAM |
|---|---|
| FastAPI + SQLite + FAISS | ~0.3 GB |
| SigLIP image detector (PyTorch) | ~1 GB |
| CLIP (duplicates) | ~0.6 GB |
| PaddleOCR | ~1 GB |
| InsightFace `buffalo_l` | ~0.5 GB |
| Tamper CNN (TensorFlow / ONNX) | ~0.5 GB |
| Voice spoof classifier (wav2vec2-style) | ~1.2 GB |
| Headroom for a running job | ~1 GB |

| Goal | Instance | Notes |
|---|---|---|
| Full feature set hosted | **Pro Plus (8 GB)** | Safest. Turn it on only for the demo window, then suspend. |
| Cheaper hosted backup | **Pro (4 GB)** | Set `LAZY_LOAD_BONUS_MODELS=true` (see §6) and skip the voice classifier. Image + document + scoring (the Must features) fit. |
| Not recommended | Starter / Standard | Likely out-of-memory when models load. |

Render bills per second, so create the service the day before the event and **suspend it afterwards**.

---

## 3. Architecture of the hosted setup

```
Browser (HTTPS)
   │
   ├── https://lucen-ai.vercel.app          → Vercel (static SPA, React build)
   │        │  VITE_API_BASE_URL
   │        ▼
   └── https://lucen-api.onrender.com/api/v1 → Render web service (Docker, FastAPI)
                │
                ├── persistent disk /app/data/runtime   (lucen.db, faiss.index, uploads, artifacts)
                ├── persistent disk /app/models         (downloaded weights, calibration.json, demo_qr_public.pem)
                └── image-baked data/demo_samples, data/demo_cache
```

Camera and microphone (liveness, voice statement, in-app capture) **only work on HTTPS or localhost**. Both Vercel and Render provide HTTPS automatically, so a phone can open the claimant portal from the hosted link. On the laptop, `localhost` is fine. Do not demo the claimant wizard on a phone over a plain `http://192.168.x.x` address.

---

## 4. Frontend on Vercel

### 4.1 Settings

| Setting | Value |
|---|---|
| Framework preset | Vite |
| Root directory | `frontend` |
| Build command | `npm run build` |
| Output directory | `dist` |
| Node version | 20 LTS |

### 4.2 Environment variables (Vercel dashboard)

| Name | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://lucen-api.onrender.com/api/v1` |
| `VITE_MOCK` | `0` (set to `1` for a fully backend-free preview using `mocks/handlers.js`) |

`frontend/src/api/client.js` must read `import.meta.env.VITE_API_BASE_URL` and fall back to `/api/v1` for local dev (where `vite.config.js` proxies `/api` to `localhost:8000` and nginx proxies it in Docker).

### 4.3 `frontend/vercel.json`

The only thing needed is the SPA fallback, so deep links such as `/app/results/abc` and `/claim/LC-1057` do not 404 on refresh:

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

This mirrors the SPA fallback already in `nginx.conf`.

### 4.4 Call the backend directly (do not proxy through Vercel)

Two ways to reach the API from the SPA:

1. **Direct (recommended):** the browser calls the Render URL, and the backend allows the Vercel origin through `CORS_ORIGINS`. Uploads of up to 15 MB go straight to Render with no intermediary size limits.
2. **Vercel rewrite** of `/api/*` to Render. Avoids CORS but puts Vercel in the upload path **(verify body-size and timeout behaviour before relying on it)**. Not recommended for 15 MB uploads.

### 4.5 CORS

On Render set (no wildcard, matching spec §20.1):

```
CORS_ORIGINS=https://lucen-ai.vercel.app,https://<your-preview>.vercel.app
```

If you use a custom domain, add it. Vercel preview URLs change per deploy, so for the final demo use the production URL only.

### 4.6 Session storage note

`AuthProvider` keeps the token in `sessionStorage`. This works across the Vercel to Render split because the token is sent as `Authorization: Bearer`, not as a cookie, so there are no third-party-cookie problems.

---

## 5. Backend on Render

### 5.1 Service type

**Web Service → Docker**, region closest to the venue, single instance. Do not scale to more than 1 instance: SQLite and a local FAISS file are single-writer, and Render persistent disks only attach to one instance.

### 5.2 `backend/Dockerfile` requirements

- Base: `python:3.11-slim`.
- System packages: `libgl1`, `libglib2.0-0`, `libzbar0` (for `pyzbar`), `tesseract-ocr`, `poppler-utils` if used, `curl` (healthcheck), fonts for WeasyPrint.
- Install CPU-only PyTorch: `pip install torch --index-url https://download.pytorch.org/whl/cpu`. This saves about 2 GB over the default CUDA build.
- Install `requirements.txt` pinned (spec §3.3).
- If TensorFlow plus PyTorch plus PaddlePaddle conflict or bloat the image, **export the tamper CNN to ONNX and use `onnxruntime`** (spec §27.1). Decide this in the first two hours.
- Start command (Render injects `$PORT`):

```
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

- Run **one** worker (`--workers 1`). The job manager and model registry are in-process singletons.

### 5.3 Persistent disk

Attach one disk (for example 10 GB) and mount it at `/app/data/runtime`:

| What lives there | Why it must persist |
|---|---|
| `lucen.db` | Users, claims, results, audit log, entities |
| `faiss.index` | Duplicate detection index with the seeded "earlier claim" photo |
| `uploads/`, `artifacts/` | Heatmaps and annotated pages shown on result pages |

For the weights, either:

- **Option A (simpler): bake into the image.** Run `scripts/download_models.py` during the Docker build. Image gets large, build takes longer, but nothing to manage at runtime.
- **Option B: second path on the disk.** On first start, if `/app/models/doc_cnn.keras` is missing, run `download_models.py`. First boot is slow (minutes), later boots are fast.

Trained artefacts (`doc_cnn.keras`, `anomaly.joblib`, `calibration.json`) are gitignored if large. Commit them with **Git LFS**, or upload them to a release / bucket and have `download_models.py` fetch them. Do not leave this to the last hour.

### 5.4 Files the image must contain

| Path | Notes |
|---|---|
| `data/demo_samples/` | Scenario A to D files and the Analyze-page samples |
| `data/demo_cache/` | Cached Bhashini + LLM responses (run `scripts/warm_demo_cache.py` locally first and commit the output) |
| `models/demo_qr_public.pem` | Public demo key only |

Never ship the demo **private** key (`~/.lucen/demo_qr_private.pem`). Cards are generated locally by `make_demo_aadhaar_cards.py` and the signed card images are committed as demo data.

### 5.5 Health check

Set the Render health check path to `/api/v1/health`. It reports which models are loaded. Models load in `lifespan`, so give the first deploy several minutes before Render marks it unhealthy **(verify the health-check grace behaviour)**.

### 5.6 Environment variables (Render dashboard)

Secrets are set in the dashboard, never in the repo.

| Name | Value | Secret |
|---|---|---|
| `CORS_ORIGINS` | Vercel production URL | no |
| `AUTH_SECRET` | long random string | **yes** |
| `AUTH_TOKEN_HOURS` | `8` | no |
| `ENTITY_HASH_SALT` | long random string | **yes** |
| `DEMO_MODE` | `1` | no |
| `MOCK_ANALYSIS` | `0` | no |
| `LLM_ENABLED` | `true` or `false` | no |
| `LLM_PROVIDER` / `LLM_API_KEY` | only if the LLM is on | **yes** |
| `BHASHINI_API_KEY` / `BHASHINI_USER_ID` | optional; cache covers the demo | **yes** |
| `AADHAAR_QR_MODE` | `demo_key` | no |
| `DEMO_QR_PUBKEY_PATH` | `models/demo_qr_public.pem` | no |
| `MAX_CONCURRENT_JOBS` | `1` | no |
| `DETECTOR_TIMEOUT_S` | `30` (raise to `45` on a slower instance) | no |
| `MAX_UPLOAD_MB` / `MAX_PDF_PAGES` | `15` / `10` | no |
| `RETENTION_HOURS` | `24` | no |
| `IMAGE_MODEL_ID` | `Ateeqq/ai-vs-human-image-detector` | no |
| `OCR_ENGINE` | `paddle` | no |

Set `LLM_ENABLED=false` for a fully deterministic hosted run: every result still has a template summary and template decision messages (F37, F24).

### 5.7 Seeding the hosted database

`seed_demo.py` must run **after** the disk is mounted and the models exist, because it builds the FAISS index and analyses scenarios A to D.

Options, best first:

1. **Seed on first boot, guarded:** add a setting `SEED_ON_START=1`. In `lifespan`, if the `users` table is empty, run the seed with `--history 30`, then ignore it on later boots. (This setting is not in the spec yet; add it to `core/config.py` and `.env.example`.)
2. **Render Shell** (paid services): `python scripts/seed_demo.py --history 30` once.
3. Seed locally and upload `lucen.db` + `faiss.index` to the disk. Fragile; avoid.

Acceptance check: `make seed` equivalent produces scenarios A=LOW, B=HIGH, C=HIGH, D=HIGH every time (F42).

### 5.8 `render.yaml` (Blueprint, optional)

```yaml
services:
  - type: web
    name: lucen-api
    runtime: docker
    dockerfilePath: ./backend/Dockerfile
    dockerContext: .
    plan: pro plus          # or "pro" for the reduced-model setup (verify plan names)
    healthCheckPath: /api/v1/health
    disk:
      name: lucen-data
      mountPath: /app/data/runtime
      sizeGB: 10
    envVars:
      - key: CORS_ORIGINS
        sync: false
      - key: AUTH_SECRET
        generateValue: true
      - key: ENTITY_HASH_SALT
        generateValue: true
      - key: DEMO_MODE
        value: "1"
      - key: MOCK_ANALYSIS
        value: "0"
      - key: AADHAAR_QR_MODE
        value: demo_key
      - key: MAX_CONCURRENT_JOBS
        value: "1"
      - key: LLM_ENABLED
        value: "false"
      - key: SEED_ON_START
        value: "1"
```

If the Dockerfile copies `models/` and `data/`, `dockerContext` must be the repo root (as above), not `./backend`. Adjust the `COPY` paths in the Dockerfile to match.

---

## 6. Ways to shrink the backend if memory is tight

In order of how little they hurt the demo:

1. Set `LLM_ENABLED=false` (no memory cost, but removes network dependency).
2. **Lazy-load the bonus models** (voice spoof classifier, InsightFace, CLIP) on first use instead of in `lifespan`. Add `LAZY_LOAD_BONUS_MODELS=true`. The first liveness or voice call is slow; the Must pipeline stays fast.
3. Export the tamper CNN to ONNX (`onnxruntime`) and drop TensorFlow from the image.
4. Use the Tesseract OCR fallback (`OCR_ENGINE=tesseract`) if PaddleOCR is too heavy.
5. Last resort: follow the cut list in the feature spec §7 (voice spoof detection first, then identity, then duplicate detection). **Never cut** F16, F17, F28, F30, F36, F37, F38.

---

## 7. Alternatives (if Render does not work out)

| Option | Fits when | Watch out for |
|---|---|---|
| **Hugging Face Spaces (Docker SDK)** | You want free or cheap RAM for ML and your models are already on Hugging Face | Persistent storage is a paid add-on; the filesystem is otherwise reset on restart. Re-seed on boot. **(verify current free hardware and storage terms)** |
| **One cloud VM (AWS EC2, GCP, DigitalOcean) running your own `docker-compose.yml`** | You want the exact local setup, plus a public IP | You manage HTTPS (Caddy or nginx + Let's Encrypt) because the camera needs HTTPS. Frontend and backend both on the VM, so no CORS split. ~8 GB RAM class. |
| **Railway / Fly.io** | Comparable to Render | Check volume support and RAM limits for the same reasons. |
| **Frontend on Render Static Site instead of Vercel** | You want everything in one dashboard | Free static hosting is fine. Needs the same SPA rewrite (`/*` to `/index.html`) in Render's redirect/rewrite rules. |

If you use a single VM, the existing `docker-compose.yml` plus `frontend/nginx.conf` (SPA fallback and `/api` proxy) already works, and `VITE_API_BASE_URL` can stay unset.

---

## 8. Local offline deployment (primary demo)

This is what the judges see. It follows spec §21.2.

```bash
cp .env.example .env            # fill AUTH_SECRET, ENTITY_HASH_SALT; leave LLM/Bhashini empty if offline
python scripts/download_models.py
python scripts/make_demo_keys.py
python scripts/make_demo_aadhaar_cards.py
python scripts/warm_demo_cache.py    # needs internet once
make seed                            # runs seed_demo.py --history 30
docker compose up --build            # frontend http://localhost:8080, backend :8000
```

Offline settings: `DEMO_MODE=1`, `MOCK_ANALYSIS=0`, `LLM_ENABLED=false` (or true with cached responses), `AADHAAR_QR_MODE=demo_key`.

Map tiles are the only thing that needs the internet; the location picker already has a plain lat/lng fallback (F07).

Two more checks:

- Unplug the network and run the **entire** 10-minute script once.
- Keep a second laptop with the same build, and a screen recording of the full demo.

---

## 9. Step-by-step rollout

### Day before the event

1. Freeze models and weights; commit trained artefacts via Git LFS or a release asset.
2. Make `client.js` read `VITE_API_BASE_URL`; add `frontend/vercel.json`; add `SEED_ON_START` (and `LAZY_LOAD_BONUS_MODELS` if needed).
3. Build the backend image locally and confirm `/api/v1/health` shows every model `true`.
4. Create the Render service (Pro Plus or Pro), attach the disk, set env vars, deploy.
5. Wait for the first boot to finish downloading models and seeding. Open `/api/v1/health` and `/docs`.
6. Deploy the frontend to Vercel with `VITE_API_BASE_URL`. Put the final Vercel URL into Render's `CORS_ORIGINS` and redeploy the backend.
7. Run the smoke test in §10 against the hosted URLs.

### Event day

1. Primary: laptop with Docker Compose, network unplugged.
2. Backup: the Vercel link, only if Wi-Fi is solid. Open it once beforehand so the Render instance is warm.
3. After the event: suspend or delete the Render service so it stops billing.

---

## 10. Smoke test (hosted and local)

| # | Check | Pass looks like |
|---|---|---|
| 1 | `GET /api/v1/health` | `status: ok`, models `true` |
| 2 | Open the Vercel URL, refresh on `/app/queue` | page loads, no 404 |
| 3 | Log in as Priya (investigator, password `demo`) | lands on `/app` with non-zero KPIs |
| 4 | Log in as Ravi, open `/app` | `/forbidden` page; `GET /queue` returns 403 |
| 5 | Analyze: upload the AI sample image | progress list runs, result shows HIGH with heatmap |
| 6 | Analyze: upload the tampered invoice | boxes over the total and font, `DOC-LOGIC-01` listed |
| 7 | Queue shows scenarios B, C, D above A | B, C, D HIGH; A LOW with Fast-track |
| 8 | Claimant wizard on a phone over HTTPS | camera and mic permission prompts appear |
| 9 | Reject scenario B | message pre-filled, no blocked words, claimant sees it after Send |
| 10 | Restart the Render service | data (users, queue, FAISS match) is still there, proving the disk works |
| 11 | Browser dev tools, Network tab | no CORS errors; API calls go to the Render URL |

---

## 11. Risks specific to deployment

| Risk | Mitigation |
|---|---|
| Backend out of memory on first request | Size the instance with measured RAM; lazy-load bonus models; watch Render metrics |
| Cold start or long first boot | Keep the service paid and always on during the event; hit `/health` 10 minutes before demo time |
| Lost data on redeploy | Everything runtime-written lives on the persistent disk; re-seed script is idempotent |
| CORS errors after a Vercel URL change | Update `CORS_ORIGINS` and redeploy the backend |
| Camera blocked on a hosted page | Both hosts serve HTTPS; test permissions on the demo browser early; upload-selfie fallback exists (F08) |
| Venue network fails | Local Docker Compose offline demo is primary; recorded backup video |
| Secrets leak | Dashboard-only env vars; `.env` gitignored; demo private key never in the repo or image |
| Hosted build too large or slow | CPU-only torch, ONNX for the CNN, bake only needed weights |
| Real or personal data in the demo | Only synthetic users, cards and claims (spec §20.2); `RETENTION_HOURS` cleanup stays on |

---

## 12. Rough cost for the event window **(verify rates)**

| Item | Estimate |
|---|---|
| Vercel (Hobby) | $0 |
| Render Pro Plus web service, 1 to 2 days | billed per second; a couple of dollars to low tens of dollars |
| Render persistent disk, 10 GB | ~$2.50 per month, prorated |
| LLM / Bhashini | $0 if disabled or served from `data/demo_cache` |

Render's per-second billing means a short event-window deploy is cheap, as long as you remember to suspend it afterwards.


---

## 13. Free-tier mode (Render Free)

Render Free limits **(verify at render.com/pricing)**: 512 MB RAM, 0.1 CPU, sleeps after 15 minutes without traffic (about one minute to wake), ephemeral filesystem, no persistent disk, 750 free instance hours per month per workspace, limited build minutes.

The full backend (SigLIP, CLIP, PaddleOCR, InsightFace, voice model, TensorFlow) needs several GB of RAM, so it **cannot run on Free**. Pick one of these modes. The laptop stays the real demo in every case.

| Mode | What runs on Render Free | What the hosted link shows | Effort |
|---|---|---|---|
| **A. Preview (recommended)** | Tiny backend with `MOCK_ANALYSIS=1` | Real login, roles, wizard, queue, case pages, decisions, analytics and network, all on canned LOW / MEDIUM / HIGH results and seeded data | Low |
| **B. Lite real** | Backend without torch / TF / Paddle: metadata, ELA, noise, PyMuPDF fonts and metadata, regex fields, consistency rules, Tesseract OCR, scoring, template explanations | Real **document** checks and forensic image checks. `IMG-AI-01`, duplicates, identity, voice show as `skipped` in "Checks run" | Medium |
| **C. Split** | Render Free as API, plus a free Hugging Face Space (Docker) running the SigLIP detector as a small HTTP service | Real AI-image score too | High; needs a new `AI_DETECTOR_URL` remote detector |

Say on screen that the hosted link is a preview. Never present mock results as measured detection.

### 13.1 Mode A: do this

1. **Skip model loading in mock mode.** In `main.py` `lifespan`, when `MOCK_ANALYSIS=1`, do not build the `ModelRegistry`. Import torch, tensorflow, paddleocr, insightface and open_clip lazily inside the detectors, never at module top level, or the process will run out of memory just importing them.
2. **Split requirements.** Add `backend/requirements-render.txt` with only: fastapi, uvicorn, pydantic, pydantic-settings, python-multipart, httpx, passlib[bcrypt], itsdangerous, pillow, numpy, reportlab (if PDF export is wanted). Use it in a separate `backend/Dockerfile.render` (python:3.11-slim, no torch). `/health` should report models as `"mocked"`.
3. **Ship seeded state in the image.** The filesystem resets on every spin-down and deploy, so run `seed_demo.py --history 30` locally, commit the resulting `lucen.db` as `data/seed_snapshot/lucen.db`, and on boot copy it to `data/runtime/` if no database exists. Users, policies, scenarios A to D and the 300 history claims then exist on every wake-up. (Add a `SEED_SNAPSHOT_PATH` setting.)
4. **Heatmaps and pages.** Mock results point at artifacts; commit the matching small PNGs under `data/demo_samples/` and serve them from there.
5. **Frontend:** deploy to Vercel as in §4. Set `VITE_API_BASE_URL` to the Render URL. (If you want zero backend, set `VITE_MOCK=1` and skip Render entirely; login, queue and analytics then come from `mocks/handlers.js`.)

### 13.2 Free-tier `render.yaml`

No `disk` block, no paid plan:

```yaml
services:
  - type: web
    name: lucen-api
    runtime: docker
    dockerfilePath: ./backend/Dockerfile.render
    dockerContext: .
    plan: free
    healthCheckPath: /api/v1/health
    envVars:
      - key: MOCK_ANALYSIS
        value: "1"
      - key: DEMO_MODE
        value: "1"
      - key: LLM_ENABLED
        value: "false"
      - key: AADHAAR_QR_MODE
        value: demo_key
      - key: MAX_CONCURRENT_JOBS
        value: "1"
      - key: CORS_ORIGINS
        sync: false
      - key: AUTH_SECRET
        generateValue: true
      - key: ENTITY_HASH_SALT
        generateValue: true
```

### 13.3 Cold starts and sleeping

- A sleeping service takes about a minute to wake, which looks like a broken app. Open `/api/v1/health` **10 minutes before** you show the link.
- To stay awake during the event, point a free uptime monitor (for example UptimeRobot) at `/api/v1/health` every 5 to 10 minutes. One always-on free web service is about 744 hours a month, inside the 750-hour allowance **(verify)**. Stop the monitor after the event.
- The frontend on Vercel should show a friendly "Waking up the server, about a minute" state when the first API call is slow. Add this to `api/client.js` (retry with a visible banner).

### 13.4 What changes elsewhere in this plan

| Section | Free-tier change |
|---|---|
| §2 sizing | Not applicable on Free; Pro Plus or Pro is the minimum for real models |
| §5.3 persistent disk | Not available; use the committed seed snapshot (§13.1 step 3). Anything written at runtime is lost on restart |
| §5.7 seeding | Replace first-boot seeding with the snapshot copy |
| §5.8 `render.yaml` | Use §13.2 |
| §10 smoke test | Skip #10 (restart persistence of new data). Items 1 to 4, 7, 9 and 11 still apply; 5 and 6 return canned results |
| §11 risks | Add: judges mistaking mock results for real detection (label the preview), and Free-tier cold start |

### 13.5 If you need real AI-image scoring online for free

Use Mode C, or host the **whole** backend on a free Hugging Face Space (Docker SDK) instead of Render, since a Space offers far more RAM than Render Free **(verify current free hardware)**. Its storage is also ephemeral on the free tier, so the committed seed snapshot approach still applies. Then Render is not needed at all; keep the frontend on Vercel.
