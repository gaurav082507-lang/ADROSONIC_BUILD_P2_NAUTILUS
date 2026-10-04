# Deployment Readiness

The Lucen AI prototype is now ready for pre-deployment staging.

## Environment Variables
- `LOG_CLAIM_INTAKE`: Set to "1" to enable verbose debugging in orchestrator, disabled in prod.
- `SQLITE_DB_PATH`: Absolute path to `lucen.db`.
- `VITE_API_URL`: Backend URL for frontend to connect (e.g., https://api.lucen.ai).
- `VITE_USE_MOCKS`: Must be "0" or omitted to disable MSW service workers.

## AI Models & Artifacts
- **HuggingFace Cache**: Set `HF_HOME` to a fast SSD location.
- **Artifacts**: Located in `data/runtime/artifacts/`. Ensure this is backed by persistent volume storage (S3/EBS).

## Infrastructure Limits
- **RAM**: Minimum 8GB per uvicorn worker due to in-memory PyTorch models (Florence-2, InsightFace). 16GB recommended.
- **Disk Space**: At least 50GB for FAISS index and local artifacts.
- **Ports**: 
  - `8000` (Backend - FastAPI)
  - `5173` (Frontend - Vite, or `80` if served statically via NGINX)

## Recent Hosting Changes
- FastAPI now parses `multipart/form-data` natively across all upload endpoints (`/claims`, `/liveness/verify`, `/voice/transcribe`, `/analyze/*`).
- Artifact URLs are strictly relative and secured with short-lived HMAC signatures (`?exp=&sig=`).
- The frontend Service Worker is explicitly unregistered if `VITE_USE_MOCKS !== '1'` to prevent cache poisoning or network interception in production.
- Analytics endpoints now pull raw business metrics directly from SQLite.
- Background tasks via `BackgroundTasks` now properly link `result_id` to database `claims` upon completion for seamless frontend polling.
