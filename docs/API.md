# Lucen AI: API Reference

Base URL: `/api/v1`  
All requests except file uploads accept and return `application/json`. File uploads use `multipart/form-data`.

---

## 0. Authentication (P2-15)

All endpoints (except `GET /api/v1/health`) require a Bearer JWT token:

```
Authorization: Bearer <access_token>
```

Obtain a token via `POST /api/v1/auth/login`. Tokens are signed with HS256, expire after `AUTH_TOKEN_HOURS` (default 24h), and explicitly reject `alg=none`.

### Roles

| Role | Description |
|---|---|
| `investigator` | Full access to analysis, results, decisions, queue |
| `claimant` | Can submit claims, see own jobs/results, request liveness |
| `admin` | User management (future) |

### Endpoint Auth Matrix

| Method | Path | Required Role |
|---|---|---|
| GET | `/health` | **None (public)** |
| POST | `/auth/login` | **None (public)** |
| POST | `/auth/register` | **None (public)** |
| POST | `/analyze/image` | `investigator` |
| POST | `/analyze/document` | `investigator` |
| POST | `/analyze/claim` | `investigator` or `claimant` |
| GET | `/jobs/{id}` | Any authenticated; claimants see only own jobs |
| GET | `/results/{id}` | `investigator` |
| DELETE | `/results/{id}` | `investigator` |
| GET | `/results/{id}/report.json` | `investigator` |
| GET | `/results/{id}/report.pdf` | `investigator` |
| GET | `/results/history` | `investigator` |
| GET | `/artifacts/{result_id}/{name}/url` | Any authenticated |
| GET | `/artifacts/{result_id}/{name}?sig=&exp=` | **None (signed URL)** |
| POST | `/identity/liveness/session` | `claimant` or `investigator` |
| POST | `/identity/liveness/verify` | `claimant` or `investigator` |
| GET/POST/PUT/DELETE | `/claims/*` | `investigator` or `claimant` |
| GET/POST | `/policies/*` | `investigator` |
| GET/POST | `/queue/*` | `investigator` |
| POST | `/decisions/*` | `investigator` |
| GET | `/voice/languages` | `claimant` or `investigator` |
| POST | `/voice/transcribe` | `claimant` or `investigator` |

---

## 1. Async Job Pattern

Analysis is asynchronous:
1. `POST /api/v1/analyze/{image|document|claim}` returns `202 Accepted` with `{"job_id": "<uuid>"}`.
2. Poll `GET /api/v1/jobs/{job_id}` every 1000 ms while `status` is `queued` or `running`.
3. When `status` is `done`, fetch the final payload from `GET /api/v1/results/{result_id}`.
4. When `status` is `failed`, inspect `error`.

---

## 2. Standard Error Format (§7.2)

Every error response uses a uniform top-level envelope:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable description",
    "details": {}
  }
}
```

### Error Code Catalog

| HTTP Status | Error Code | Description / UI Action |
|---|---|---|
| 401 | `UNAUTHORIZED` | Missing or invalid Bearer JWT token. |
| 403 | `FORBIDDEN` | Insufficient role permissions or invalid/expired artifact signature. |
| 404 | `JOB_NOT_FOUND` | Specified job ID not found. |
| 404 | `RESULT_NOT_FOUND` | Specified analysis result ID or artifact not found. |
| 404 | `CLAIM_NOT_FOUND` | Specified claim ID does not exist. |
| 404 | `RING_NOT_FOUND` | Specified fraud ring ID does not exist. |
| 413 | `FILE_TOO_LARGE` | File exceeds maximum upload size (15 MB for image/doc, 10 MB for voice). |
| 415 | `UNSUPPORTED_FILE_TYPE` | Only JPG, PNG, WebP, and PDF (plus supported audio formats) are accepted. |
| 422 | `NO_INPUT` | Empty file or no files submitted in analysis/claim request. |
| 422 | `TOO_MANY_FILES` | Claim upload exceeds limit of 6 images. |
| 422 | `TOO_MANY_PAGES` | PDF exceeds maximum allowed page count (10 pages). |
| 422 | `CORRUPT_FILE` | Decompression bomb, corrupt, or unreadable file. |
| 422 | `VALIDATION_ERROR` | Schema, parameters, or JSON validation failed. |
| 422 | `CONSENT_REQUIRED` | Claimant mandatory consent not accepted. |
| 422 | `VOICE_CONSENT_REQUIRED` | Explicit consent (`consent_voice_processing=True`) missing for voice statement. |
| 422 | `POLICY_INVALID` | Policy does not exist, does not belong to claimant, or incident date is out of range. |
| 422 | `FAST_TRACK_NOT_ALLOWED` | Claim is not in LOW risk band or confidence is low. |
| 422 | `RESUBMISSION_NOT_ALLOWED` | Claim is not in `needs_evidence` state. |
| 422 | `INVALID_AUDIO_FORMAT` | Audio format or header magic bytes invalid. |
| 422 | `AUDIO_TOO_LARGE` | Voice audio exceeds 10 MB limit. |
| 422 | `AUDIO_TOO_LONG` | Voice audio exceeds 90-second duration limit. |
| 429 | `RATE_LIMITED` | Exceeded rate limit (20 req/min per IP). |
| 500 | `INTERNAL_ERROR` | Unexpected internal server error. |
| 503 | `BHASHINI_UNAVAILABLE` | External Bhashini pipeline unreachable or API keys rejected. |

---

## 3. Endpoints

### 3.1 Health Check
- **`GET /api/v1/health`**
  - **Response 200:**
    ```json
    {
      "status": "ok",
      "models": {
        "ai_image_detector": true
      }
    }
    ```

### 3.2 Analysis Endpoints
- **`POST /api/v1/analyze/image`**
  - **Content-Type:** `multipart/form-data`
  - **Form Fields:** `file` (UploadFile, accepts aliases `file`, `image`, `files`, `images`)
  - **Response 202:** `{"job_id": "<uuid>"}`

- **`POST /api/v1/analyze/document`**
  - **Content-Type:** `multipart/form-data`
  - **Form Fields:** `file` (UploadFile, accepts aliases `file`, `document`, `files`)
  - **Response 202:** `{"job_id": "<uuid>"}`

- **`POST /api/v1/analyze/claim`**
  - **Content-Type:** `multipart/form-data`
  - **Form Fields:**
    - `image`: 0 to 6 image files. Accepts aliases: `image`, `images`, `files`, `evidence_slot[]`, `evidence_slot`
    - `document`: 0 to 1 PDF or scan document (`document`, `doc`)
    - `id_photo`: 0 to 1 ID document photo (`id_photo`, `id_card`)
    - `selfie`: 0 to 1 claimant live selfie
    - `metadata`: Optional JSON string conforming to `ClaimMetadata`. Can include `incident_location` as either a JSON object `{"lat": 19.076, "lng": 72.877}` or a string `"19.076,72.877"`.
  - **Response 202:** `{"job_id": "<uuid>"}`

### 3.3 Job Status
- **`GET /api/v1/jobs/{job_id}`**
  - **Response 200:**
    ```json
    {
      "job_id": "<uuid>",
      "status": "running | done | failed",
      "mode": "image | document | claim",
      "steps": [
        {"name": "img_1:ai_detector", "status": "done", "duration_ms": 180},
        {"name": "doc:ocr", "status": "running", "duration_ms": 0}
      ],
      "result_id": "<uuid>",
      "error": null
    }
    ```

### 3.4 Results & Explanations
- **`GET /api/v1/results/{result_id}`**
  - **Response 200:** Full `AnalysisResult` object:
    - `overall`: `{risk, band, confidence, summary}`
    - `image`: `{risk, authenticity, band, confidence, evidence_ids}`
    - `document`: `{risk, authenticity, band, confidence, evidence_ids}`
    - `image_results`: List of `PipelineScore` for each analyzed image
    - `evidence`: List of `Evidence` sorted by `contribution` descending
    - `why_this_score`: Grouped object `{image, document, identity, voice, claim, overall, items}`
      - `why_this_score.items`: Flat list of all contribution items sorted by `contribution_pct` descending
    - `why_this_score_items`: Top-level flat list alias of `WhyThisScoreItem[]`
    - `checks_run`: List of all detectors with status (`ok`, `skipped`, `failed`) and duration
    - `top_reasons`: 3–5 bullet explanations
    - `recommended_action`: Plain-English operational guidance
    - `artifacts`: URLs for heatmaps, overlays, and page bounding boxes (auto-signed with `?exp=&sig=` or direct accessible paths)
    - `versions`: Detector model IDs, calibration date, engine version, git commit

- **`GET /api/v1/results/{result_id}/evidence`**
  - **Query Params:**
    - `pipeline`: Filter by pipeline (e.g. `image`, `document`, `img_1`, `doc`)
    - `severity`: Filter by severity (`low`, `medium`, `high`)
    - `kind`: Filter by kind (`risk`, `authenticity`, `info`)
  - **Response 200:** Filtered `List[Evidence]`

### 3.5 History & Deletion
- **`GET /api/v1/history`**
  - **Query Params:**
    - `page`: int (default 1)
    - `page_size`: int (default 20, max 100)
    - `mode`: optional mode filter (`image`, `document`, `claim`)
    - `band`: optional risk band filter (`LOW`, `MEDIUM`, `HIGH`)
  - **Response 200:**
    ```json
    {
      "items": [
        {
          "id": "<uuid>",
          "created_at": "2026-10-03T10:00:00Z",
          "mode": "claim",
          "overall_risk": 0.88,
          "overall_band": "HIGH",
          "thumbnail_url": "/api/v1/artifacts/<uuid>/preview_img_1.jpg",
          "evidence_count": 4,
          "top_reason": "AI-Generated Image detected."
        }
      ],
      "total": 1,
      "page": 1,
      "page_size": 20
    }
    ```

- **`DELETE /api/v1/results/{result_id}`**
  - Permanently purges the result, associated job, artifacts directory, and uploaded files.
  - **Response 204 No Content**

### 3.6 Reports & Audits
- **`GET /api/v1/results/{result_id}/report.json`**
  - Full analysis payload supplemented with an audit cryptographic block:
    ```json
    {
      "...": "AnalysisResult fields",
      "audit": {
        "investigator": "System Auditor",
        "exported_at": "2026-10-03T10:15:00Z",
        "sha256": "4a5c...64hex",
        "format_version": "1.0.0"
      }
    }
    ```

- **`GET /api/v1/results/{result_id}/report.pdf`**
  - Generates a formal 10-section A4 audit report with executive summary, score breakdown, forensic heatmaps, evidence tables, methodology formulas, and NumberedCanvas disclaimer footers.
  - **Content-Type:** `application/pdf`
  - **Content-Disposition:** `attachment; filename="lucen_report_<result_id>.pdf"`

### 3.7 Artifacts
- **`GET /api/v1/artifacts/{result_id}/{name}`**
  - Serves generated artifacts (heatmaps, page boxes, previews) with directory traversal protection and `Cache-Control: public, max-age=86400`.

### 3.8 Timeline & Cross-Check Events
- **`GET /api/v1/results/{result_id}/timeline`**
  - **Response 200:** Chronological timeline object:
    ```json
    {
      "events": [
        {
          "event_id": "evt_incident",
          "label": "Reported Incident Time",
          "timestamp_iso": "2026-10-01T14:30:00+05:30",
          "display_date": "01 Oct 2026, 02:30 PM IST",
          "source": "claim_metadata",
          "badge": "Metadata"
        }
      ],
      "undated_events": [],
      "contradictions": [
        {
          "from_event_id": "evt_exif_0",
          "to_event_id": "evt_incident",
          "evidence_id": "CLM-X-01",
          "severity": "high",
          "rule_name": "Photo Taken Before Incident",
          "detail": "Photo timestamp (2026-09-30 18:45) is 19.8 hours before reported incident."
        }
      ]
    }
    ```

### 3.9 Entity Store & Identity Privacy
- **`GET /api/v1/claims/{id}/entities`**
  - **Response 200:** Masked entities extracted for fraud cross-referencing:
    ```json
    {
      "claim_id": "<uuid>",
      "entities": [
        {
          "id": "<uuid>",
          "entity_type": "vehicle_plate | phone | invoice_num | tax_id | bank_acc",
          "entity_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "masked_value": "MH-12-****-3456",
          "source": "claim_field | ocr_text",
          "created_at": "2026-10-03T10:00:00Z"
        }
      ]
    }
    ```

---

## 7. Voice Endpoints (§13)

### 7.1 List Supported Languages
- **`GET /api/v1/voice/languages`**
  - **Required Role:** `claimant` or `investigator`
  - **Response 200:**
    ```json
    [
      {"code": "hi", "name": "Hindi", "native": "हिन्दी"},
      {"code": "en", "name": "English", "native": "English"},
      {"code": "ta", "name": "Tamil", "native": "தமிழ்"},
      {"code": "te", "name": "Telugu", "native": "తెలుగు"},
      {"code": "mr", "name": "Marathi", "native": "मराठी"},
      {"code": "bn", "name": "Bengali", "native": "বাংলা"},
      {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી"},
      {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ"},
      {"code": "ml", "name": "Malayalam", "native": "മലയാളം"},
      {"code": "pa", "name": "Punjabi", "native": "ਪੰਜਾਬੀ"},
      {"code": "or", "name": "Odia", "native": "ଓଡ଼ିଆ"},
      {"code": "as", "name": "Assamese", "native": "অসমীয়া"},
      {"code": "ur", "name": "Urdu", "native": "اردو"}
    ]
    ```

### 7.2 Synchronous Voice Transcription & Wizard Auto-Fill
- **`POST /api/v1/voice/transcribe`**
  - **Required Role:** `claimant` or `investigator`
  - **Content-Type:** `multipart/form-data`
  - **Form Parameters:**
    - `file`: Audio file (`.webm`, `.ogg`, `.mp3`, `.m4a`, `.wav`). Max 10 MB, max 90s. Optional if `text` is provided.
    - `language`: Bhashini language code (`hi`, `en`, `ta`, etc.). Default: `"hi"`.
    - `text`: Optional raw transcript (when using Web Speech API fallback in claimant wizard).
  - **Response 200:**
    ```json
    {
      "language": "hi",
      "duration_s": 6.2,
      "transcript": "मेरी कार का एक्सीडेंट 12 सितंबर को हुआ था और मरम्मत में 45000 का खर्च आया।",
      "translation_en": "My car had an accident on September 12 and the repair cost 45000.",
      "extracted": {
        "claimed_amount": 45000.0,
        "incident_date": "2026-09-12",
        "incident_time": null,
        "vehicle_number": null,
        "place": null
      },
      "source": "bhashini"
    }
    ```
  - **Errors:**
    - `422 INVALID_AUDIO_FORMAT`: Unsupported audio format or invalid magic bytes.
    - `422 AUDIO_TOO_LARGE`: Audio exceeds 10 MB limit.
    - `422 AUDIO_TOO_LONG`: Audio duration exceeds 90s.
    - `503 BHASHINI_UNAVAILABLE`: Bhashini service unreachable or credentials invalid.

---

## 8. Network Intelligence & Fraud Rings API

### 8.1 Network Graph Exploration
- **`GET /api/v1/network/graph`**
  - **Required Role:** `investigator`
  - **Query Parameters:**
    - `focus_type`: Optional focus node type (`claim`, `claimant`, `ring`).
    - `focus_id`: Optional node ID to center neighborhood.
    - `hops`: Graph expansion distance (1 to 4, default: 2).
    - `min_strength`: Minimum edge weight (0.0 to 1.0, default: 0.3).
    - `limit`: Maximum nodes returned (default: 300).
  - **Response 200:**
    ```json
    {
      "nodes": [
        {"id": "CLM-RING-01", "type": "claim", "label": "CLM-RING-01", "band": "MEDIUM"},
        {"id": "user_vikram", "type": "claimant", "label": "Vikram Malhotra"},
        {"id": "bank_hash_9876", "type": "bank", "label": "Bank ****4417"}
      ],
      "edges": [
        {"source": "CLM-RING-01", "target": "bank_hash_9876", "strength": 1.0, "kind": "bank"}
      ]
    }
    ```

### 8.2 Fraud Rings Listing & Detail
- **`GET /api/v1/network/rings`**
  - **Required Role:** `investigator`
  - **Query Parameters:** `status` (`open`, `under_review`, `confirmed`, `dismissed`), `min_score` (float).
  - **Response 200:**
    ```json
    {
      "total": 1,
      "items": [
        {
          "id": "ring_f96ab48037",
          "claims_count": 3,
          "claimants_count": 3,
          "total_amount": 485000.0,
          "ring_score": 0.6,
          "band": "MEDIUM",
          "status": "open",
          "reasons": ["3 claimants share bank account ****4417"]
        }
      ]
    }
    ```

- **`GET /api/v1/network/rings/{ring_id}`**
  - **Required Role:** `investigator`
  - Returns complete member dossier, shared entities, and audit history.

- **`POST /api/v1/network/rings/{ring_id}/status`**
  - **Required Role:** `investigator`
  - **Body:** `{"status": "confirmed"|"dismissed"|"under_review"|"open", "note": "Mandatory audit rationale"}`
  - Note is mandatory when changing status to `confirmed` or `dismissed` (Principle P2).

- **`GET /api/v1/network/rings/{ring_id}/report.json`** & **`GET /api/v1/network/rings/{ring_id}/report.pdf`**
  - Downloadable fraud ring audit investigation report in JSON or PDF format.

---

## 9. Analytics & Longitudinal Intelligence API

### 9.1 Summary KPIs
- **`GET /api/v1/analytics/summary`**
  - **Required Role:** `investigator`
  - **Response 200:**
    ```json
    {
      "claims_today": 8,
      "fast_tracked": 12,
      "total": 315,
      "flagged": 72,
      "flagged_rate": 0.229,
      "top_reasons": [{"id": "IMG-AI-01", "title": "AI-Generated Image", "count": 28}],
      "sparkline_7d": [5, 7, 6, 8, 9, 7, 8],
      "open_rings": 1
    }
    ```

### 9.2 Longitudinal Trends & Bursts
- **`GET /api/v1/analytics/trends`**
  - **Required Role:** `investigator`
  - **Query Parameters:** `range` (`7d`, `30d`, `90d`), `type` (`motor`, `health`, `property`).
  - **Response 200:**
    ```json
    {
      "range": "30d",
      "type": null,
      "daily": [{"date": "2026-05-10", "low": 5, "medium": 2, "high": 1, "flagged_rate": 0.375}],
      "top_signals": [{"id": "IMG-AI-01", "title": "AI Image", "count": 28}],
      "by_type": [{"type": "motor", "total": 165, "flagged": 42}],
      "recycled_evidence_weekly": [{"week": "2026-W18", "count": 4}],
      "spike": {"detected": false, "message": null}
    }
    ```



