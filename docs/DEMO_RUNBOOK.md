# Lucen AI Demo Runbook

**Version:** Final Prototype (2026-10-04)

## Prerequisites
- Node.js installed (v18+)
- Python 3.11+ installed
- Playwright browsers installed (`playwright install`)

## 1. Environment Setup

1. **Start the Backend:**
   ```bash
   cd backend
   $env:LOG_CLAIM_INTAKE="1"
   .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Start the Frontend:**
   ```bash
   cd web
   npm run dev -- --host
   ```

3. **Reset Database to Demo State:**
   ```bash
   python scripts/reset_demo.py
   ```
   *Note: This strictly calls `POST /api/v1/admin/reset-demo` to re-seed the live environment with 6 canonical claims for the investigator queue without needing a backend restart.*

## 2. Live Demo Flow

### Step A: The Claimant Journey
1. Navigate to `http://localhost:5173/login`.
2. Click **CLAIMANT PORTAL** and **Sign in**.
3. Choose **Motor** claim, and fill out details (Date: Today, Amount: 5000).
4. **Identity Step:** Upload ID Card and Selfie. The WebAssembly Mediapipe pipeline will instantly run facial mapping.
5. **Evidence Step:** Upload images (e.g. `genuine_car.jpg`, `ai_car.jpg`) and a repair document (e.g. `tampered_invoice.pdf`).
6. Submit the claim. The frontend routes to `Under Review` while the orchestrator works.

### Step B: The Investigator Triage
1. Open a new context to `http://localhost:5173/login`.
2. Click **INVESTIGATOR CONSOLE** and **Sign in**.
3. Navigate to **Queue**. You will see the new claim cleanly listed at the top as `under_review`.
4. Click **Open**. The app navigates to `/app/results/{result_id}`.

### Step C: Deep Forensics
1. **Overview Tab:** Review the high-level risk score (expect ~90% risk due to tampering).
2. **Image Tab:** View the localization heatmap overlay on the `ai_car.jpg`.
3. **Document Tab:** Observe the bounding boxes around the tampered fonts on the invoice.
4. **Claim Checks:** Scroll through the executed forensic pipelines confirming successful execution.

## 3. Analytics
Navigate to `http://localhost:5173/app/dashboard` to view real-time management roll-ups isolated cleanly from test noise.
