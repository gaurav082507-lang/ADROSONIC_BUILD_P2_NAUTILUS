# 💻 Lucen AI — Frontend Integration & Architecture Guide

**Application:** Dual-Portal Deepfake & Synthetic Identity Fraud Detection Interface  
**Framework:** React 19 + Vite 8 + Tailwind CSS v4 + React Router v7  
**Icons & Maps:** Lucide React + Leaflet / React-Leaflet  
**OpenAPI Specification:** [docs/openapi.json](file:///c:/Users/gaura/Desktop/LUCENAI/docs/openapi.json)

---

## 1. Quick Start

### 1.1 Installation
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

### 1.2 Development Server
```bash
# Run local Vite dev server
npm run dev
```
- Local URL: `http://localhost:5173`
- The Vite dev server automatically proxies all `/api/*` calls to the backend running at `http://localhost:8000` (configured in `vite.config.js`).

### 1.3 Production Build & Linting
```bash
# Lint with oxlint (fast Rust-based linter)
npm run lint

# Production build to frontend/dist
npm run build

# Preview production build locally
npm run preview
```

---

## 2. Environment Configuration

The frontend configuration resides in `frontend/.env`:

```env
# Set to 0 to use live backend at http://localhost:8000 via Vite proxy
# Set to 1 to use offline mock handlers (frontend/src/mocks/handlers.js)
VITE_USE_MOCKS=0
```

### Vite Reverse Proxy (`vite.config.js`):
```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

---

## 3. Directory Structure

```
frontend/src/
├── api/                        # Backend API communication layer
│   ├── auth.js                 # Auth endpoints, claims, decisions, queue, liveness
│   ├── client.js               # Central `fetchClient` wrapper with token & error handling
│   └── types.js                # JSDoc type definitions mirroring docs/openapi.json
├── assets/                     # Logos, branding icons, hero images
├── components/                 # Reusable UI components
│   ├── BoxOverlay.jsx          # Forensic bounding box & tamper heatmap canvas
│   ├── DecisionBar.jsx         # Sticky investigator decision bar (Approve/Reject/Refer)
│   ├── DuplicateBanner.jsx     # Alert banner when pHash duplicate photo is detected
│   ├── ErrorBanner.jsx         # Standard error callout for API errors
│   ├── FlaggedFieldTable.jsx   # Document tampering field-by-field comparison
│   ├── LocationTab.jsx         # Interactive Leaflet map with claim vs EXIF GPS markers
│   ├── Logo.jsx                # Lucen AI branding component
│   ├── RiskBadge.jsx           # Accessible LOW / MEDIUM / HIGH risk badge with icons
│   └── TimelineTab.jsx         # Claim lifecycle & evidence submission audit trail
├── contexts/
│   └── AuthContext.jsx         # React Context managing session, user state, and logout
├── i18n/                       # Internationalization support
│   ├── I18nContext.jsx         # Language toggle context (English / Hindi)
│   └── strings.js              # Localization dictionary for bilingual claimant flow
├── layouts/                    # Portal shell layouts
│   ├── ClaimantLayout.jsx      # Mobile-first claimant header, language toggle, bottom nav
│   └── InvestigatorLayout.jsx  # Desktop sidebar, search bar, triage metrics, profile menu
├── mocks/
│   └── handlers.js             # Standalone offline mock responses for demo resilience
├── routes/                     # Screen / view components
│   ├── LandingPage.jsx         # Public landing page with role picker
│   ├── LoginPage.jsx           # Email / password login form
│   ├── app/                    # 🕵️ Investigator Portal Routes
│   │   ├── AnalyticsPage.jsx   # Fraud metrics, risk band distribution, financial savings
│   │   ├── AnalyzePage.jsx     # Instant drag-and-drop file upload & live analysis trigger
│   │   ├── DashboardPage.jsx   # Overview statistics, recent alerts, triage queue summary
│   │   ├── HistoryPage.jsx     # Audit log of past decisions and investigator notes
│   │   ├── NetworkPage.jsx     # Interactive fraud ring graph (entities, shared identifiers)
│   │   ├── QueuePage.jsx       # Prioritized investigator triage queue
│   │   └── ResultPage.jsx      # Comprehensive forensic analysis report
│   └── claimant/               # 📱 Claimant Portal Routes
│       ├── ClaimStatusPage.jsx # Real-time claim review progress tracker
│       ├── ClaimWizardPage.jsx # Multi-step claim submission (Voice, ID, Selfie, Photos)
│       └── MyClaimsPage.jsx    # Claimant claim history list
├── App.jsx                     # Router declaration & route role guards
└── main.jsx                    # React 19 root mount & provider setup
```

---

## 4. API Client & Communication (`src/api/client.js`)

All communication with the backend goes through `fetchClient(endpoint, options)`.

### 4.1 Token Storage & Injection
- The access token is stored in `sessionStorage.getItem('lucen_token')`.
- `fetchClient` automatically injects the Bearer token into outgoing requests:
  ```javascript
  headers['Authorization'] = `Bearer ${token}`;
  ```
- If an endpoint returns `401 Unauthorized`, `fetchClient` clears `sessionStorage` and immediately redirects to `/login`.

### 4.2 Standardized Error Envelope
Backend errors return the standard contract:
```json
{
  "status": 400,
  "error": {
    "code": "TOO_MANY_FILES",
    "message": "Maximum 6 images allowed per claim.",
    "details": { "count": 7, "max": 6 }
  }
}
```
`fetchClient` parses this and throws an instance of `ApiError`:
```javascript
export class ApiError extends Error {
  constructor(status, error_code, details = {}, message = "") {
    super(message || error_code);
    this.status = status;
    this.error_code = error_code;
    this.details = details;
  }
}
```

---

## 5. Dual-Portal Routing & Role Guarding

The router in `src/App.jsx` enforces role-based layout mounting:

```
/ (Landing Page)
├── /login ── Authenticates user, stores token in sessionStorage
│
├── /app/* (Investigator Portal — Requires role === 'investigator')
│   ├── /app/dashboard   → High-level metrics & triage cards
│   ├── /app/queue       → Prioritized claims queue
│   ├── /app/analyze     → Direct image/document analysis dropzone
│   ├── /app/results/:id → Deep forensic breakdown & decision bar
│   ├── /app/network     → Fraud ring graph visualizer
│   ├── /app/analytics   → Aggregate charts & statistics
│   └── /app/history     → Historical audit log
│
└── /claimant/* (Claimant Portal — Requires role === 'claimant')
    ├── /claimant/claims     → List of submitted claims
    ├── /claimant/wizard     → Step-by-step claim filing with voice & liveness
    └── /claimant/claims/:id → Real-time status tracker
```

---

## 6. Key UI Modules & Forensic Views

### 6.1 Result Detail View (`routes/app/ResultPage.jsx`)
The investigator report displays:
1. **Overall Risk Score & Band**: Visualized with `<RiskBadge band={overall.band} score={overall.risk} />`.
2. **Confidence Level**: `high`, `medium`, or `low` with explanatory quality warning tooltips.
3. **"Why This Score" Panel**: Ranked list of evidence contributions ($1 - \prod(1 - w_i p_i)$) showing exactly how each detector contributed to the score.
4. **Forensic Image Canvas (`BoxOverlay.jsx`)**: Renders detected faces, ELA heatmaps, and bounding boxes over submitted photos.
5. **Document Forensics (`FlaggedFieldTable.jsx`)**: Side-by-side comparison of printed text vs. tamper anomaly bounding boxes.
6. **Story vs. Evidence Review**: Highlights contradictions between the claimant's statement and EXIF/metadata evidence.
7. **Decision Bar (`DecisionBar.jsx`)**: Sticky bottom bar allowing the investigator to select reasons and commit `APPROVE`, `REJECT`, or `REFER_TO_SIU`.

### 6.2 Claimant Wizard Flow (`routes/claimant/ClaimWizardPage.jsx`)
1. **Policy Selection**: Autocomplete policy number from active policies.
2. **Voice Description**: Integrated audio recorder submitting to `/api/v1/voice/transcribe` (Bhashini Indic ASR).
3. **Incident Location**: Automatically captures HTML5 Geolocation coordinates (`lat, lng`).
4. **Identity & Aadhaar Verification**: Uploads Aadhaar card photo to parse Secure QR.
5. **Active Liveness Challenge**: Requests dynamic challenge (`look_left`, `blink`, `turn_right`) and captures selfie video frames.
6. **Damage Evidence Upload**: Accepts up to 6 vehicle/property damage photographs.

### 6.3 Fraud Ring Network Graph (`routes/app/NetworkPage.jsx`)
Visualizes connected entities across claims:
- **Nodes**: Claims, Claimants, Bank Accounts, Phone Numbers, Email Addresses, Vehicles, Repair Garages.
- **Edges**: Strong (1.0 - Bank/Phone), Medium (0.6 - Address/Email), Weak (0.3 - Garage).
- **Cluster Highlighting**: Louvain community groups showing active fraud rings.

---

## 7. Connecting Frontend with Backend

1. **Start the backend:**
   ```bash
   cd c:\Users\gaura\Desktop\LUCENAI
   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Verify demo accounts are seeded:**
   ```bash
   python scripts/seed_demo_claims.py
   python scripts/seed_network_demo.py
   ```

3. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

4. **Log in:**
   - **Investigator Portal**: `investigator@lucen.ai` / `Password123!`
   - **Claimant Portal**: `claimant@example.com` / `Password123!`

5. **Generate TypeScript / OpenAPI Types (Optional):**
   The OpenAPI contract is at `docs/openapi.json`. You can inspect or generate client types using:
   ```bash
   npx openapi-typescript ../docs/openapi.json -o src/api/schema.d.ts
   ```
