# Lucen AI: Complete Feature Specification (file 3 of 3)

**AI-Powered Synthetic Identity and Deepfake Claim Detection System**
ADROSONIC Build, 24-hour hackathon

This file describes **every feature of Lucen AI in depth**: why it exists, who uses it, the exact user flow, what each screen shows in every state, what the backend does, which endpoints and data it uses, the edge cases, and the acceptance criteria that define "done".

Companion files:
- `LUCEN_AI_ARCHITECTURE.md` (file 1): how things work internally. References like **§10** point there.
- `LUCEN_AI_FOLDER_STRUCTURE.md` (file 2): where each file goes.

If this file and file 1 disagree about **what the user sees**, this file wins. If they disagree about **how it works internally** (scores, weights, contracts), file 1 wins.

---

## 0. Ground rules that apply to every feature

These rules are not repeated in each feature. Every feature must respect them.

1. **The system recommends; a human decides.** No claim is approved or rejected automatically. Lucen AI produces scores, a band (LOW / MEDIUM / HIGH), reasons and a recommended action. Only an investigator (the insurer's policy maker) clicks Approve, Reject, Request evidence or Escalate.
2. **The claimant never sees fraud internals.** Claimant screens and claimant endpoints never show or return scores, percentages, bands, evidence ids, detector names, heatmaps, metadata dates or internal notes. They do see their stage, the decision, the reason in plain words, and what to do next.
3. **The three required scores come first.** On every result view, the image authenticity score, document authenticity score and overall fraud likelihood are shown first and largest. Identity and voice are smaller secondary cards.
4. **Every score traces back to evidence.** Every number on screen can be explained by a list of evidence items with plain-English reasons. The LLM may reword text; it never creates, changes or removes a score, band or evidence item.
5. **Nothing fails the whole job.** Any single check can fail or time out. The result still appears, the failed check is listed in "Checks run" as `failed`, and confidence is lowered.
6. **The demo runs offline.** Every external call (Bhashini, LLM) has a cached response for the seeded demo scenarios and a fallback for anything else.
7. **Colour is never the only signal.** Every band appears as a word plus an icon plus a colour. Every chart has a table view.
8. **Claimant portal is mobile-first and bilingual** (English / हिंदी switch on every claimant page). The investigator portal is desktop-first, English.
9. **Every screen has four states:** loading (skeleton or spinner), empty (helpful message plus a next action), error (what went wrong plus how to fix it), and success.
10. **Privacy by default:** no full Aadhaar number, QR payload, face embedding or raw bank account number is stored. Bank accounts, phones and emails are stored as salted hashes with a masked display value (`••••4417`). Uploads are deleted after `RETENTION_HOURS`.

**Priorities:** **Must** = scored directly by the problem statement, never cut. **Should** = expected in a polished product. **Bonus** = innovation marks; cut first if time runs short (order in section 6).

**Roles:** **Claimant** (person filing a claim). **Investigator** (insurer staff / policy maker who reviews and decides).

---

## 1. Feature index

| ID | Feature | Portal | Priority | File 1 ref |
|---|---|---|---|---|
| F01 | Landing page | Public | Should | §8.12 |
| F02 | Demo login and roles | Public | Should | §7.8 |
| F03 | Claim wizard shell | Claimant | Should | §8.12 |
| F04 | Step 1: Policy selection | Claimant | Should | §7.8, §8.12 |
| F05 | Step 2: Voice statement with auto-filled form | Claimant | Should | §14.1 |
| F06 | Synthetic / cloned voice detection | Backend | Bonus | §14.1 |
| F07 | Incident location picker | Claimant | Should | §14.4 |
| F08 | Step 3a: Liveness challenge | Claimant | Should | §12.4 |
| F09 | Step 3b: ID card capture and Aadhaar Secure QR verification | Claimant + Backend | Bonus | §12.5 |
| F10 | Step 4: Guided evidence capture | Claimant | Should | §8.12 |
| F11 | Step 5: Review and submit | Claimant | Should | §7.5 |
| F12 | Claim status tracker, decision reason, resubmission | Claimant | Should | §7.6 |
| F13 | Claimant "Your evidence" timeline | Claimant | Should | §14.5 |
| F14 | Investigator dashboard | Investigator | Should | §8.12 |
| F15 | Triage queue | Investigator | Should | §7.5 |
| F16 | Analyze page (direct upload) | Investigator | **Must** | §8.2–8.3 |
| F17 | Result / case page core | Investigator | **Must** | §8.4, §16 |
| F18 | Identity tab | Investigator | Bonus | §12 |
| F19 | Voice tab | Investigator | Bonus | §14.1 |
| F20 | Story-vs-evidence review tab | Investigator | Bonus | §14.2 |
| F21 | Recycled-evidence (duplicate) banner | Investigator | Bonus | §13.1 |
| F22 | Investigator evidence timeline tab | Investigator | Should | §14.5 |
| F23 | Location panel | Investigator | Should | §14.4 |
| F24 | Decision bar, reason codes, AI-drafted claimant message, audit log | Investigator | Should | §7.6, §7.7 |
| F25 | Fraud network page | Investigator | Bonus | §14.3 |
| F26 | Fraud-risk trend analytics page | Investigator | Should | §8.13 |
| F27 | Report export (PDF / JSON) | Investigator | Should | §8.5 |
| F28 | Image manipulation / AI-generation detection | Engine | **Must** | §10 |
| F29 | Suspicious-region highlighting | Engine | Should | §10 Step 6 |
| F30 | Document tampering detection | Engine | **Must** | §11 |
| F31 | Embedded-image bridge (PDF photos → image checks) | Engine | Bonus | §11 Step 10 |
| F32 | Face match: ID vs selfie, morph suspicion | Engine | Bonus | §12.1 |
| F33 | Duplicate-image detection across claims | Engine | Bonus | §13 |
| F34 | Cross-checks between image, document and claim | Engine | Bonus | §14 |
| F35 | Entity links (shared phone / email / bank / photo) | Engine | Bonus | §14.3 |
| F36 | Risk scoring engine | Engine | **Must** | §15 |
| F37 | Explanation engine | Engine | **Must** | §16 |
| F38 | Async jobs and live progress | Platform | **Must** | §7.3, §9.5 |
| F39 | Mock mode and offline demo cache | Platform | Should | §7.4 |
| F40 | Quality gating and robustness | Platform | **Must** | §15.3, §18 |
| F41 | Security and privacy | Platform | **Must** | §20 |
| F42 | Seed data and demo scenarios A–D | Platform | Should | §23 |
| F43 | Accessibility and bilingual UI | Platform | Should | §8.9 |

---

## 2. Public pages

### F01. Landing page

**Purpose:** explain Lucen AI in five seconds and route the visitor to the right portal.
**Route:** `/` · **Users:** anyone · **Priority:** Should

**Screen content (top to bottom):**
1. Header: Lucen AI logo and wordmark, "Log in" button on the right.
2. Hero: headline "Catch AI-faked claims before they're paid." Sub-line: "Lucen AI checks claim photos, documents, identity and voice for AI generation and tampering, and explains every flag in plain English." Two buttons: **File a claim** (→ `/login?role=claimant`) and **Open investigator demo** (→ `/login?role=investigator`).
3. "What it checks" row: four cards with icon and one sentence each: Photos (AI-generated or edited), Documents (altered amounts, fonts, metadata), Identity (liveness, face match, Aadhaar QR), Voice (statement in Indian languages, cloned-voice check).
4. "How it works" strip: Upload → Checks run → Scores + reasons → A human decides.
5. Footer: "Prototype for ADROSONIC Build. Demo data only. Decisions are always made by a person."

**States:** static page; no loading state.

**Acceptance criteria:**
- Both buttons reach the login page with the matching card highlighted.
- Page renders correctly at 360 px width and at 1440 px.
- No claim data or API call is needed to render it.

---

### F02. Demo login and roles

**Purpose:** make the two portals behave like a real product: a claimant sees only their own claims; only an investigator reaches `/app`. This is a demo login, not production security.
**Route:** `/login` · **Priority:** Should · **Backend:** §7.8

**Screen content:**
- Two large cards side by side (stacked on mobile):
  - **"I'm filing a claim"**: buttons "Continue as Ravi Kumar (genuine claim)" and "Continue as Anil Verma (suspicious claims)".
  - **"I work at an insurer"**: button "Continue as Priya Sharma (investigator)".
- Below: an email + password form, prefilled with the highlighted card's user, and a note "Demo password for all users: demo".
- `?role=claimant` or `?role=investigator` in the URL highlights the matching card.

**Flow:**
1. User clicks a demo button or submits the form → `POST /auth/login`.
2. On success the token and user are kept in `AuthProvider` (sessionStorage, cleared on tab close).
3. Redirect: claimant → `/claims` (or `/claim/new` if they have no claims); investigator → `/app`.
4. Header shows the user's name and a **Log out** button on every page after login. Log out clears the token and returns to `/`.

**Route guards (`RequireRole`):**
- No token → redirect to `/login?next=<path>`; after login return to `next` if the role allows it.
- Claimant opening any `/app/*` route → `/forbidden` page: "This page is for insurer staff. Go to your claims."
- Investigator opening `/claim/new` → allowed only in "preview as claimant" mode is **not** built; show `/forbidden` with a link back to `/app`.
- Expired token on any API call (`401`) → toast "Your session expired, please log in again" and redirect to `/login`.

**Backend rules:** every claimant endpoint checks that the claim belongs to the logged-in user (`403` otherwise). Every investigator endpoint requires role `investigator`.

**Edge cases:** wrong password → inline error "Email or password is incorrect" (never say which). Backend down → "Can't reach the server. Is the backend running?" with a retry button.

**Acceptance criteria:**
- One click logs in as each demo user.
- A claimant cannot load `/app/queue` (UI) or `GET /queue` (API, returns 403).
- Claimant A cannot read claimant B's claim status (API returns 403).
- Refreshing the page keeps the session; closing the tab ends it.

---

## 3. Claimant portal

### F03. Claim wizard shell

**Purpose:** let an ordinary person file a complete, checkable claim in about three minutes on a phone, with one main action per screen.
**Route:** `/claim/new` · **Priority:** Should

**Layout:** `ClaimantLayout` (no sidebar). At the top: "File a claim", a five-dot stepper with labels (Policy · Your story · Verify it's you · Evidence · Review), and the language switch. At the bottom: a sticky bar with **Back** and **Next** (Next becomes **Submit claim** on step 5).

**Behaviour:**
- Wizard state lives in `wizardStore` (React context + reducer) and survives moving back and forth between steps. It is **not** saved to the server until Submit. If the user reloads, show a warning before leaving ("Your claim isn't submitted yet. Leave anyway?").
- **Next** is disabled until the step's required fields are valid; a short line under the button says what is missing ("Choose a policy to continue").
- Steps can be revisited by tapping a completed dot; future dots are disabled.
- Camera and microphone permissions are requested only on the step that needs them, with a one-line reason shown first ("We use your camera to check it's really you").

**Acceptance criteria:**
- All five steps can be completed with keyboard only on desktop and with touch on a 360 px phone.
- Going back to step 2 from step 4 keeps the uploaded evidence.
- Validation messages appear in the selected language.

---

### F04. Step 1: Policy selection

**Purpose:** tie the claim to a real (seeded) policy, which fixes the claim type and gives the policy start date used by later checks.

**Screen content:**
- "Which policy is this claim for?" with a list of the claimant's policies from `GET /policies/mine`: each card shows policy number, type icon (motor / health / property), the insured vehicle or asset, and validity dates.
- After selecting: "What happened?" with peril options for that type: motor (collision, theft, fire, natural calamity), health (hospitalisation, day-care procedure), property (fire, water damage, theft, storm).

**Rules:**
- `claim_type` is taken from the selected policy and cannot be changed.
- If the claimant has no policies: empty state "No policies found on your account" with a "Contact support" link (demo users always have at least one).

**Data produced:** `policy_number`, `claim_type`, `peril`.

**Acceptance criteria:** selecting a motor policy shows only motor perils; Next stays disabled until a peril is chosen.

---

### F05. Step 2: Voice statement with auto-filled form

**Purpose:** many claimants are more comfortable speaking than typing, especially in their own language. They say what happened; the form fills itself; they correct anything wrong. The recorded audio is later checked for voice cloning (F06).
**Priority:** Should · **Backend:** §14.1 · **Endpoint:** `POST /voice/transcribe` (sync)

**Screen content:**
1. Language dropdown (default from the user's preferred language): Hindi, English, Bengali, Marathi, Tamil, Telugu, Kannada, Gujarati, Odia, Punjabi, Malayalam **(verify the Bhashini pipeline list on the day; show only languages that work)**.
2. A large round **mic button** with the prompt "Tell us what happened: when, where, what was damaged and how much it costs." A live level meter and a timer show while recording. The maximum is 90 s; recording stops automatically at the limit with a notice.
3. After stopping: a spinner "Understanding your statement…" then two panels:
   - **What you said** (original-language transcript) and **In English** (translation), both read-only.
   - **Auto-filled details**, editable: incident date, incident time, location description, damaged items (chips that can be removed or added), amount claimed (₹), short description.
4. Actions: **Record again**, **Type instead** (shows a text area; the same fields can be filled manually).
5. The location picker (F07) sits under the details.

**Flow and backend:**
1. Browser records with `MediaRecorder` (webm/opus) and sends the audio plus `language` to `POST /voice/transcribe`.
2. Backend: validate (≤ 90 s, ≤ 10 MB) → resample to 16 kHz mono → Bhashini ASR in the source language → Bhashini NMT to English → field extraction (LLM with strict JSON schema plus regex fallback).
3. **Every extracted value must literally appear in the English transcript** (substring check). Anything that fails is dropped rather than invented.
4. Response: `{transcript_original, transcript_en, language, fields: {incident_date, incident_time, location_text, damaged_items[], amount_claimed}, source: "bhashini|web_speech|cache"}`.
5. The audio file is kept with the wizard draft and uploaded on Submit so the voice pipeline (F06) can analyse it.

**Fallbacks (in order):** Bhashini fails or times out (8 s) → browser Web Speech API for English / Hindi → "We couldn't understand the recording. Please type what happened." with the text area open. The user is never stuck.

**Edge cases:**
- Silence or under 3 s → "We didn't hear anything. Hold the button closer and try again."
- Amount said in words ("pachaas hazaar") → extraction should produce 50000; if it can't, the field stays empty for the user to fill.
- Relative dates ("kal", "last Tuesday") → resolved against today's date and shown for confirmation.
- Microphone permission denied → explain how to allow it, and offer Type instead.

**Required to continue:** incident date, a description (spoken or typed), and amount claimed.

**Acceptance criteria:**
- A 15-second Hindi statement in demo scenario A fills date, location, damaged items and amount correctly (using the demo cache offline).
- Every auto-filled field can be edited.
- Unplugging the network still allows the typed path.

---

### F06. Synthetic / cloned voice detection

**Purpose:** a fraudster can file a claim using a cloned voice of the policyholder. Lucen AI checks whether the recorded statement sounds machine-generated. This extends deepfake detection beyond images.
**Priority:** Bonus · **Runs:** after Submit, inside the analysis job (never delays the wizard) · **Backend:** §14.1

**How it works:**
1. The voice pipeline loads the uploaded audio, computes duration, loudness and a noise estimate.
2. A pre-trained synthetic-speech classifier (Hugging Face, chosen by the voice bake-off; labels read from `id2label`, never hard-coded) returns a probability that the voice is synthetic.
3. Temperature scaling, fitted on team-recorded real clips versus TTS / voice-cloning clips, calibrates the probability.
4. Evidence: `VOI-SPOOF-01` (weight 0.55, source cap 0.55) when above threshold; `VOI-QUAL-01` warning if the audio is too short, silent or noisy (gates the spoof weight by half); `VOI-TXT-00` info carries the transcript for the investigator.

**What the investigator sees:** the Voice card on the result page and the Voice tab (F19).
**What the claimant sees:** nothing.

**Acceptance criteria:**
- A team-made cloned-voice clip scores above the threshold; a genuine team recording scores below it (measured, reported on the honesty slide).
- If the model fails to load, the job completes and "Checks run" lists the voice check as `failed`.

---

### F07. Incident location picker

**Purpose:** record where the incident happened so the investigator sees it on a map and the photo-GPS check (`CLM-X-06`) can run when photos carry GPS.
**Priority:** Should · **Backend:** §14.4

**Screen content:** a small react-leaflet map (OpenStreetMap tiles; offline fallback: a plain lat/lng text field) under the story details. A "Use my current location" button and drag-to-place pin. The location text from the voice statement is shown above the map; the pin is optional.

**Rules:** the pin fills `incident_lat`, `incident_lng`. It is used only by `CLM-X-06` and the investigator's Location panel (F23). No weather or other external data is used.

**Acceptance criteria:** skipping the pin never blocks the wizard; with no tiles available, the text-field fallback appears.

---

### F08. Step 3a: Liveness challenge

**Purpose:** prove a live person is present, so a printed photo, a replayed video or a pre-made deepfake clip can't pass identity checks. The best frame becomes the selfie for face matching (F32).
**Priority:** Should · **Backend:** §12.4 · **Endpoints:** `POST /identity/liveness/session`, `POST /identity/liveness/verify`

**Screen content:**
1. Intro: "Quick check that it's really you. It takes about 15 seconds." Button **Start camera**.
2. Camera view with an oval face guide. Above it one instruction at a time, from the random session list: "Blink twice", "Turn your head left" (or right), then "Read these numbers aloud: 4 7 1 9".
3. A progress ring per instruction. MediaPipe Face Landmarker runs in the browser **only for guidance** ("Move closer", "Face the camera", "Too dark"); it does not decide.
4. Result: "Thanks, you're verified" (pass) or "We couldn't confirm that. Try again" (fail, up to 2 retries with a new session).

**Flow:**
1. `POST /identity/liveness/session` → `{session_id, nonce, challenges: ["blink_twice","turn_left"], spoken_code: "4719", expires_in: 120}`.
2. For each challenge the browser samples 4–6 timestamped JPEG frames; for the code it records about 3 s of audio.
3. `POST /identity/liveness/verify` with frames, audio and session id.
4. **The server decides:** blink = eye aspect ratio drops below threshold in ≥ 2 frames separated by an open-eye frame; turn = yaw beyond `LIVENESS_YAW_DEG` (20°) in the requested direction; code = ASR contains the 4 digits in order; timestamps inside the session window; nonce matches; session not reused.
5. Response `{passed, challenges:[{name, ok}], code_match, best_frame_id}`. The best frontal frame is stored as the selfie.

**Fallback:** camera unavailable or blocked → "Upload a selfie instead". This is recorded as `ID-LIVE-03` (liveness not performed, low weight) and lowers confidence.

**Evidence produced:** `ID-LIVE-00` (passed, info), `ID-LIVE-01` (challenge failed, 0.75), `ID-LIVE-02` (code mismatch, 0.50), `ID-LIVE-03` (not performed, 0.15). Override O6: liveness failed **and** faces don't match → overall ≥ 0.85.

**Claimant never sees** the reason a liveness attempt failed beyond "We couldn't confirm that", so attackers can't tune their spoof.

**Edge cases:** session expired → silently start a new one; glasses or poor light → guidance text, not failure; two faces in frame → "Only one person should be in the frame."

**Acceptance criteria:**
- A live team member passes in under 20 s on a laptop webcam.
- Holding up a printed photo fails (blink and turn not observed).
- Reusing a session id returns `422 LIVENESS_SESSION_EXPIRED`.

---

### F09. Step 3b: ID card capture and Aadhaar Secure QR verification

**Purpose:** synthetic identities usually come with an edited or fabricated ID card. The Aadhaar Secure QR is digitally signed by UIDAI and holds the holder's name, date of birth, gender, last 4 digits and photo. If someone edits the printed card, it no longer matches its own signed QR; if someone fakes the QR, the signature fails. **No government API, licence or payment is needed;** verification is offline with a public certificate.
**Priority:** Bonus · **Backend:** §12.5 · **Endpoint:** `POST /identity/aadhaar-qr` (sync, during the wizard) and again inside the analysis job

**Claimant screen:**
- "Photo of your ID card (front)": **Use camera** with a card-shaped frame, or **Upload** (JPG / PNG / PDF e-Aadhaar).
- Tips: "Lay the card flat, avoid glare, make sure the QR code is sharp."
- After capture: "ID received" with a thumbnail. If the QR can't be read: "We couldn't read the QR code. Retake the photo closer to the QR, or continue without it." Continuing is allowed (it becomes a warning, never fraud).
- The claimant is never told whether the signature or details matched.

**Backend steps:**
1. Find and decode the QR with `pyzbar`; if that fails, upscale and sharpen and retry with OpenCV's QR detector.
2. Classify: **Secure QR** (large numeric string) → decode, decompress, split fields, separate signature and photo (`pyaadhaar` handles decoding; **verify the format on the day**). **Old XML QR** → read fields, mode `unsigned`, no signature claim.
3. **Signature check** with the RSA public key: UIDAI certificate in `uidai` mode, the team's demo public key in `demo_key` mode (default for the demo).
4. **Printed vs QR comparison:** OCR the printed name, DOB / year of birth, gender and last 4 digits of the number; compare with the QR values (normalised strings, `rapidfuzz` for names). Verhoeff checksum on the printed 12-digit number (`DOC-LOGIC-04`).
5. **Photo check:** ArcFace similarity between the QR photo and the printed card photo and the live selfie (supporting evidence only; the QR photo is small).
6. Store only `{mode, signature_valid, comparisons}`; never the QR payload or the full number.

**Evidence produced:** `ID-QR-00` verified (info); `ID-QR-01` signature invalid (0.85, override O7 → identity ≥ 0.85); `ID-QR-02` printed details don't match the QR (0.75, lists each mismatched field with both values); `ID-QR-03` photo mismatch (0.45); `ID-QR-04` QR missing / unreadable / unsigned (warning only).

**Demo data:** `scripts/make_demo_aadhaar_cards.py` creates synthetic people with demo-key-signed QRs: one valid card and tampered versions (edited printed DOB, edited name, swapped photo, corrupted signature). On screen the mode is labelled "demo signing key". Never use real people's Aadhaar data.

**Acceptance criteria:**
- The valid demo card produces `ID-QR-00`.
- The card with an edited printed DOB produces `ID-QR-02` showing printed vs QR DOB in red.
- A card with a corrupted signature produces `ID-QR-01` and identity risk ≥ 0.85.
- A blurry card produces `ID-QR-04` and does not raise the risk score.

---

### F10. Step 4: Guided evidence capture

**Purpose:** collect the right evidence for the claim type and record whether each photo was taken live in the app (harder to fake) or uploaded from the gallery.
**Priority:** Should

**Screen content:** a checklist of slots for the claim type:

| Claim type | Required slots | Optional slots |
|---|---|---|
| Motor | Full vehicle, damage close-up, number plate, repair estimate / invoice | Additional damage photos (up to 4), FIR / police report |
| Health | Hospital bill, discharge summary | Prescription, lab reports, additional bills |
| Property | Wide shot of the damage, close-up, invoice or estimate | Additional photos |

Each slot shows: an example silhouette, **Use camera** and **Upload** buttons, then a thumbnail with a badge: "Taken in app" (camera) or "Uploaded" (gallery), and a remove button.

**Rules:**
- Accepted: JPG, PNG, WebP for photos; PDF, JPG, PNG for documents. Max `MAX_UPLOAD_MB` (15 MB) per file, `MAX_PDF_PAGES` (10).
- Files stay in the browser until Submit.
- Capture source is sent as metadata (`capture_source: camera|upload`) and shown to the investigator; uploads are not penalised in the score, only labelled.
- Images are not compressed or resized by the browser (forensic checks need the original bytes).

**Required to continue:** all required slots filled.

**Edge cases:** wrong file type → "This slot needs a photo (JPG or PNG)"; HEIC from iPhone → "Please choose JPG, or use the in-app camera"; file too large → shows the limit.

**Acceptance criteria:** a motor claim cannot continue without a repair estimate; camera captures show the "Taken in app" badge on the investigator case page.

---

### F11. Step 5: Review and submit

**Purpose:** let the claimant check everything before submitting, and record consent.

**Screen content:** summary cards for each step with an **Edit** link: policy and peril; story (transcript snippet, date, amount, location); identity ("Verified" / "Selfie uploaded" and "ID card received"); evidence thumbnails. Consent checkbox: "I confirm these details are true. I agree that Lucen AI may process my photos, documents, ID, face and voice to check this claim." **Submit claim** is disabled until ticked.

**On submit:** `POST /claims` (multipart: all files + `ClaimMetadata` JSON) → `202 {claim_id, job_id}`. Show a confirmation screen: "Claim submitted. Your claim ID is LC-1057." Buttons: **Track my claim** (→ `/claim/LC-1057`) and **Back to my claims**. The analysis job starts in the background; the claimant does not wait for it.

**Edge cases:** network error during upload → keep the wizard state and show "Upload failed, try again"; double-click → the button disables on first click.

**Acceptance criteria:** submission creates a claim row, a job, and a "Submitted" timeline event; the new claim appears in the investigator queue once analysis completes.

---

### F12. Claim status tracker, decision reason, and resubmission

**Purpose:** a claimant should always know where their claim stands and, if it's rejected or more evidence is needed, **why** and **what to do next**, without being shown fraud internals.
**Routes:** `/claims` (list) and `/claim/:id` (detail) · **Priority:** Should · **Backend:** §7.6 · **Endpoints:** `GET /claims/mine`, `GET /claims/{id}/status`, `POST /claims/{id}/resubmit`

**My claims list (`/claims`):** cards with claim id, type icon, submitted date, current stage chip, and a **File a new claim** button.

**Claim detail (`/claim/:id`):**
1. **Stage tracker:** Submitted → Checks complete → Under review → Decision. Completed stages show date and time. The current stage is highlighted.
2. **Decision notice** (when a decision exists):
   - Approved: green-word "Approved" + optional message.
   - Rejected: "Rejected" + the reason category in plain words (from the reason code) + the investigator's claimant message + next steps.
   - More evidence needed: "We need more information" + what is needed + an upload area.
   - Escalated: shown to the claimant as "Under review" (escalation is internal).
3. **Your evidence** timeline (F13).
4. **Submit new evidence** panel when the reason is resubmittable (`PHOTO_NOT_VERIFIED`, `DOCUMENT_NOT_VERIFIED`, `INCOMPLETE_SUBMISSION`, `IDENTITY_NOT_VERIFIED`) or an evidence request is open: upload slots like F10; on submit, `POST /claims/{id}/resubmit` starts a new analysis and the stage returns to "Under review".
5. **Appeal / contact support** link on every rejection.

**Example rejection the claimant sees:**
> **Rejected:** Photo already used in another claim.
> We were unable to approve your claim because one of the photos you submitted has already been used with another claim. You can upload new photos of the damage using the in-app camera, or contact support if you'd like to appeal.
> [Submit new evidence] [Contact support]

**What the endpoint never returns:** scores, bands, evidence ids, detector names, heatmaps, metadata dates, internal notes, or which other claim matched. `test_claimant_safety.py` enforces this.

**Refresh:** the page polls `GET /claims/{id}/status` every 10 s while the stage is not Decision.

**Acceptance criteria:**
- After an investigator rejects with `PHOTO_PREVIOUSLY_USED`, the claimant sees the category, the edited message and the Submit new evidence button.
- After resubmission, the stage is "Under review" and the investigator queue shows the claim again with a "Resubmitted" tag.
- The JSON from `/claims/{id}/status` contains no field named score, band, evidence or internal_note.

---

### F13. Claimant "Your evidence" timeline

**Purpose:** show the claimant a clear record of what they submitted and its status. It builds trust and reduces "did you get my documents?" support calls.
**Priority:** Should · **Backend:** §14.5 · **Endpoint:** `GET /claims/{id}/evidence-timeline`

**Screen content:** a vertical list, newest at the bottom, of system events only:
- "Claim submitted · 22 Sep, 09:03"
- "Damage photo 1 received · 22 Sep, 09:03" → status chip **Received** → **Checked**
- "Repair invoice received · 22 Sep, 09:03" → **Checked** or **Needs replacing** (only if an evidence request names it)
- "New photo uploaded · 24 Sep, 18:20" (after resubmission)
- "Decision: Rejected · 23 Sep, 14:10"

**Rules:** no photo-metadata dates, document dates, contradictions, scores or detector names. "Needs replacing" appears only when the investigator's evidence request or resubmittable rejection names that item; the explanation comes from the investigator's message.

**Acceptance criteria:** the claimant timeline for scenario B never mentions the photo's capture date or the matched claim.

---

## 4. Investigator portal

All investigator pages use `InvestigatorLayout`: left sidebar (Dashboard, Queue, Analyze, Analytics, Network), top bar with a claim-id search box (Enter → `/app/results/:id` or "No claim found"), user name and Log out.

### F14. Investigator dashboard

**Purpose:** a one-glance start-of-day view: how much work there is and what kind of fraud is showing up.
**Route:** `/app` · **Priority:** Should · **Endpoint:** `GET /analytics/summary`

**Screen content:**
1. KPI cards: **Claims today**, **Fast-tracked (LOW)**, **Needs review (MEDIUM)**, **Flagged HIGH**, **Awaiting decision**. Each card links to the queue with that filter.
2. **Top flag reasons today**: up to five plain-English reasons with counts ("Photo used in another claim · 4").
3. **7-day risk trend** sparkline of flagged rate, with a link "Open analytics" (F26).
4. **Spike alert banner** (same rule as F26) when today's flagged rate is unusual.
5. **Recently decided**: last five decisions with action, reason code and who decided.

**Empty state:** "No claims yet today. Try the Analyze page or file a claim from the claimant portal."

**Acceptance criteria:** with seeded history, all KPI cards show non-zero numbers; clicking "Flagged HIGH" opens the queue filtered to HIGH.

---

### F15. Triage queue

**Purpose:** investigators work highest-risk first, and safe claims get fast-tracked so honest claimants are paid quickly.
**Route:** `/app/queue` · **Priority:** Should · **Endpoint:** `GET /queue?band=&type=&status=&q=`

**Table columns:** risk band badge (word + icon + colour) · overall score (%) · claim id · claimant name · claim type · top reason (plain English) · tags ("Resubmitted", "Duplicate photo", "Network link", "Liveness not done") · submitted time · status (Open, Evidence requested, Decided).

**Behaviour:**
- Default sort: open claims first, then overall risk descending, then oldest first.
- Filters: band, claim type, status, tag; free-text search on claim id or name. Filters are kept in the URL so they can be shared.
- **Fast-track** button on LOW rows: opens a confirm dialog "Approve LC-1051 without manual review?" → records an Approve action with `fast_track=true` in the audit log. Fast-track is never available on MEDIUM or HIGH.
- Row click → case page (F17).
- Analyses created on the Analyze page without a claim appear with type "Direct analysis" and no claimant name.

**Empty / loading / error:** skeleton rows while loading; "No claims match these filters" with "Clear filters"; error banner with retry.

**Acceptance criteria:** seeded scenario B and D appear above scenario A; fast-tracking a LOW claim writes an audit row and the claimant sees "Approved".

---

### F16. Analyze page (direct upload) — required for demo steps 1 and 2

**Purpose:** the problem statement requires a web UI where a reviewer can upload an image or a document and immediately see the result. This page does exactly that, without the claimant flow.
**Route:** `/app/analyze` · **Priority:** **Must** · **Endpoints:** `POST /analyze/image`, `POST /analyze/document`, `POST /analyze/claim`, `GET /jobs/{id}`

**Screen content:** three tabs:
- **Image:** one dropzone (JPG, PNG, WebP; ≤ 15 MB). Sample buttons: "AI-generated damage photo", "Genuine damage photo", "Edited photo".
- **Document:** one dropzone (PDF, JPG, PNG; ≤ 15 MB, ≤ 10 pages). Samples: "Tampered invoice", "Clean invoice", "Tampered hospital bill".
- **Full claim:** dropzones for claim image, document, optional ID photo, optional selfie, optional audio; the metadata form (claim date, incident date, amount, claimant name, claim type).

Each dropzone shows a thumbnail (or first PDF page) and file name after selection, with type and size validation messages.

**Flow:**
1. **Analyze** → `202 {job_id}`.
2. The **progress list** (F38) shows each check with a spinner, then a tick and its duration, or "skipped" / "failed".
3. On completion → redirect to `/app/results/:id`.

**Acceptance criteria:**
- Uploading the AI-generated sample shows the result page with the image score, band and heatmap in under 15 s on the demo laptop **(estimate; measure it)**.
- Uploading a `.exe` renamed to `.jpg` is rejected with "This file isn't a valid image" (magic-byte check).
- Sample buttons work offline.

---

### F17. Result / case page core

**Purpose:** the heart of the product. It shows the three required scores, why they are what they are, where the problem is on the image or page, and what to do next.
**Route:** `/app/results/:id` · **Priority:** **Must** · **Endpoint:** `GET /results/{id}`

**Layout (top to bottom):**
1. **Header:** claim id, claimant name (if a claim), claim type, submitted time, status chip, and the **Decision bar** (F24) on the right.
2. **Duplicate banner** (F21) if a photo was reused.
3. **Overall fraud likelihood:** the largest element. Band word + icon + colour, percentage, confidence (high / medium / low), and the recommended action:
   - LOW: "No significant indicators. Proceed with the normal process."
   - MEDIUM: "Route to manual review. Check the highlighted items."
   - HIGH: "Escalate to the fraud investigation team before any payout."
4. **Explanation panel:** a 2–3 sentence summary ("The claim photo is very likely AI-generated (97%) and the invoice total does not match its line items.") and the top three reasons as clickable chips.
5. **Score row:** **Image authenticity** gauge and **Document authenticity** gauge (large), then smaller cards for **Identity** and **Voice** when those ran. Each shows a percentage and band word.
6. **Why this score** (expandable): each pipeline's contributions in plain form ("AI-generated image probability: 61% of the image risk"), any override rules applied ("Rule O6 applied: liveness failed and faces did not match"), and the cross-pipeline blend.
7. **Tabs:**
   - **Image:** `ImageViewer` with Original / Heatmap / Side-by-side toggle and an opacity slider; boxes for flagged regions; a caption saying what the heatmap means ("regions with unusual compression or noise" vs "regions the AI detector relied on"); EXIF summary; capture source badge.
   - **Document:** `PdfViewer` (page navigation) with boxes over flagged fields; `FieldTable` of flagged fields (field, value, reason, severity). Hovering a row highlights its box and vice versa.
   - **Identity** (F18), **Voice** (F19), **Story** (F20), **Evidence timeline** (F22), **Location** (F23).
   - **All evidence:** every evidence card, sortable by contribution or severity, filterable by pipeline. Each card: id, title, plain-English reason, calibrated score bar, weight, source, "Show on image / page" link.
   - **Checks run:** every detector with `ok / skipped / failed`, duration and a one-line note ("ELA skipped: PNG file").
8. **Quality warnings** banner when inputs were low resolution, heavily compressed, blurry, or a check failed ("Image is 480 px wide; AI-detection weight reduced").
9. **Export** buttons (F27).
10. **Audit list** of decisions on this case (F24).

**States:** if the job is still running, show the progress list in place of the page; if the id is unknown, "Result not found" with a link to the queue.

**Acceptance criteria:**
- Scenario B shows HIGH overall with `IMG-AI-01` and `IMG-DUP-01` as the top two reasons, heatmap visible, duplicate banner visible.
- Scenario C shows boxes over the edited total and the different-font amount, with the field table linked to them.
- Every percentage on the page can be traced to an evidence card or the Why this score panel.
- Image, document and overall scores are above the fold on a 1366×768 screen.

---

### F18. Identity tab

**Purpose:** show the investigator every identity check in one place: was a live person present, does the face match the ID, is the ID card genuine.
**Priority:** Bonus

**Content, in order:**
1. **Liveness checklist:** each challenge with tick or cross and time taken ("Blink twice ✓ 2.1 s", "Turn left ✓", "Spoken code ✓"), or "Not performed: selfie uploaded instead".
2. **Face match:** ID photo crop and live selfie side by side, similarity percentage and zone: Same person / Ambiguous (possible morph or poor quality) / Different person. Selfie AI-detection result (`ID-DEEP-01`).
3. **Aadhaar QR panel:** signature status (Valid / Invalid / Unsigned / Not found) with mode label ("demo signing key"); a **printed vs QR** table (field, printed value, QR value, match ✓/✗), mismatches in red with the word "Mismatch"; QR photo next to the printed photo with similarity. Aadhaar numbers shown masked (`XXXX XXXX 4417`).

**Acceptance criteria:** scenario D shows liveness failed, faces "Different person", and DOB mismatch in red; scenario A shows all green with "Valid (demo signing key)".

---

### F19. Voice tab

**Purpose:** let the investigator hear the statement, read it in both languages and see the cloned-voice check.
**Priority:** Bonus

**Content:** audio player; language; original transcript and English translation side by side; extracted fields with a note of which ones the claimant edited after auto-fill; synthetic-voice gauge with band word and the calibrated probability; audio quality warning if any.

**Acceptance criteria:** the claimant's edits to auto-filled fields are visible ("Amount edited: 45,000 → 50,000"), because large edits can matter to an investigator.

---

### F20. Story-vs-evidence review tab

**Purpose:** an LLM compares what the claimant said with the facts the detectors found, and lists contradictions and confirmations for the investigator. It saves reading time; it does **not** change the score.
**Priority:** Bonus · **Backend:** §14.2 · **Setting:** `STORY_SCORING=false` (default)

**Content:**
- Label at the top: "For investigator review. Not part of the score."
- **Contradictions:** each with the exact quote from the statement, the evidence fact, a link to the evidence card, and severity. Example: "'The accident happened on 21 September' vs photo 2 taken on 2 September (photo metadata)".
- **Consistent points:** quotes the evidence supports.
- If unavailable: "Story check not available" (LLM off, timed out or invalid output).

**Validation:** each quote must exist verbatim in the statement, each evidence reference must exist, each number or date must match that evidence; failing items are dropped.

**Acceptance criteria:** turning the LLM off leaves the tab with the "not available" message and every score unchanged.

---

### F21. Recycled-evidence (duplicate) banner

**Purpose:** if a photo in this claim was already used in another claim, by another person or the same person, the investigator must see it immediately.
**Priority:** Bonus · **Backend:** §13, §13.1

**Content:** a prominent banner at the top of the case page:
> **Photo used in another claim.** Damage photo 2 matches a photo in claim **LC-1042** filed by a different claimant (94% similar). [Compare] [Open LC-1042]

**Compare** opens a side-by-side view of both images. Variants: "identical file" (exact hash match), "same claimant, different claim". Multiple matches are listed.

**Acceptance criteria:** see F33.

---

### F22. Investigator evidence timeline tab

**Purpose:** put every dated fact about a claim on one line so impossible orders stand out: the "accident photo" taken weeks before the accident, or the repair bill issued before the car was damaged.
**Priority:** Should · **Backend:** §14.5 · **Endpoint:** `GET /results/{id}/timeline`

**Content:** a vertical timeline, oldest at the top. Each event shows: icon, date/time, label, a **source badge** (Claimant said · Photo metadata · Document text · PDF metadata · System · Investigator), and a thumbnail where relevant. Events: policy start, incident (stated), each photo captured, each document's issue date, PDF created / modified, liveness and ID capture, submission, uploads, checks complete, decisions, resubmissions.

**Contradictions** are red connectors between two events with the rule id and sentence, for example "`CLM-X-01` The photo was taken 19 days before the stated incident." Rules shown: `CLM-X-01` (photo outside the incident window), `CLM-X-05` (PDF created after filing), `CLM-X-07` (evidence before policy start), `CLM-X-08` (bill before incident).

**Undated group:** photos without a capture date (stripped by messaging apps) are listed separately, never guessed.

**Rule:** the timeline adds no score of its own; it displays dates and evidence already in the score.

**Acceptance criteria:** scenario B's timeline shows the reused photo's capture date before the incident with a red connector; clicking an event opens its evidence card.

---

### F23. Location panel

**Purpose:** show where the claimant says the incident happened and, if photos carry GPS, where they were taken.
**Priority:** Should

**Content:** a map with the claimed pin (blue, "Stated location") and photo pins (orange, "Photo 1 GPS"), and the distance if both exist with `CLM-X-06` evidence if far. If no photo has GPS: "Photos have no location data (common after messaging apps). Location check skipped."

**Acceptance criteria:** with no GPS the check is `skipped`, not failed, and doesn't affect the score.

---

### F24. Decision bar, reason codes, AI-drafted claimant message and audit log

**Purpose:** the investigator makes the decision. When rejecting or requesting evidence, the claimant must be told why in plain words, but typing that every time is slow. Lucen AI drafts the message from the anomalies found; the investigator edits and sends it.
**Priority:** Should · **Backend:** §7.6, §7.7 · **Endpoints:** `POST /results/{id}/decision/draft`, `POST /results/{id}/decision`

**Decision bar:** four buttons: **Approve**, **Request evidence**, **Reject**, **Escalate**. Shows current status and who last acted.

**Approve dialog:** optional message to the claimant, optional internal note, **Confirm**.

**Escalate dialog:** internal note (required), escalate-to field (free text, e.g. "Fraud investigation team"). The claimant keeps seeing "Under review".

**Reject / Request evidence dialog (pre-filled by AI):**
1. On open, call `/decision/draft` with the action. A short loading state ("Drafting message…", max 6 s).
2. **Reason** dropdown, preselected **deterministically** from the top contributing evidence using a fixed map (not AI):

| Top evidence | Suggested reason code |
|---|---|
| `IMG-DUP-01` | `PHOTO_PREVIOUSLY_USED` |
| `IMG-AI-01`, `IMG-ELA-01`, `IMG-EXIF-02*`, `IMG-C2PA-01` | `PHOTO_NOT_VERIFIED` |
| `DOC-*` | `DOCUMENT_NOT_VERIFIED` |
| `CLM-X-02` | `AMOUNT_MISMATCH` |
| `ID-*` | `IDENTITY_NOT_VERIFIED` |
| `CLM-X-01/03/05/07/08` | `DETAILS_INCONSISTENT` |
| quality warnings / missing items | `INCOMPLETE_SUBMISSION` |

   Other applicable reasons appear as tick-box **"Also mention"** chips. `POLICY_NOT_COVERED` and `OTHER` are always selectable manually.
3. **Message to claimant** text box with the AI draft (2–4 sentences, plain words, next steps), a character counter (max 500), **Regenerate**, and a language toggle **English / claimant's language** (both versions are sent; the claimant sees their language with an English toggle).
4. For **Request evidence**: a checklist of the claim's items ("Damage photo 2", "Repair invoice") to mark as **needs replacing**; these feed the claimant's evidence timeline (F13).
5. **What the claimant will see** preview, rendered exactly as on `/claim/:id`.
6. **Internal note** box pre-filled with an AI summary of the technical signals ("Top signals: IMG-DUP-01 (match with LC-1042, 0.96), IMG-AI-01 (0.94)"). Never shown to the claimant.
7. **Send to claimant** (primary). Nothing is sent or saved until this is clicked. **Cancel** discards the draft.

**AI safety rules (backend validation; any failure → the default template message for the reason code is used and the dialog says "Template message"):**
- The LLM receives only claimant-safe input: the action, reason codes and their default messages, plain item names, whether resubmission is allowed, the claimant's name and language. Never scores, evidence ids or technical details.
- Output must be 2–4 sentences, ≤ 500 characters, mention every selected reason's subject and include a next step (upload, resubmit, appeal or contact support).
- Blocked words: fraud, fake, forged, lie, lying, AI, artificial intelligence, model, detector, algorithm, score, probability, percent, %, metadata, EXIF, ELA, heatmap, pixel, signature check, deepfake, synthetic.
- No digits except dates and the claim id.
- The translated version is back-translated to English and validated the same way; if it fails, only English is offered.

**Audit log:** each decision writes an `actions` row: actor, action, reason code(s), claimant message (final text), internal note, `message_source` (`llm_draft` / `template` / `manual`), `draft_edited` (true/false), items to replace, timestamp. The **Audit list** on the case page shows these in order ("Priya Sharma rejected · PHOTO_PREVIOUSLY_USED · AI draft, edited · 23 Sep 14:10").

**Rules:** Reject and Request evidence cannot be sent without a reason code; resubmittable reasons automatically enable the claimant's Submit new evidence panel; decisions can be changed later (new audit row, nothing overwritten).

**Acceptance criteria:**
- Opening Reject on scenario B preselects `PHOTO_PREVIOUSLY_USED` and fills a message containing none of the blocked words.
- With the LLM disabled, the template message fills in within 1 s.
- Clicking Cancel leaves no audit row and nothing on the claimant side.
- The audit row records `draft_edited=true` after the investigator changes one word.

---

### F25. Fraud network page

**Purpose:** organised fraud rings reuse the same phone, email, bank account or photos across many claims. A graph makes a ring visible instantly.
**Route:** `/app/network` · **Priority:** Bonus · **Backend:** §14.3 · **Endpoint:** `GET /network`

**Content:** a force-directed graph (`react-force-graph-2d`):
- **Claim nodes:** circles coloured by band, with the band word in the tooltip, labelled with the claim id.
- **Entity nodes:** small grey dots for a shared phone, email, bank account (masked `••••4417`) or a matched photo.
- **Edges:** claim → entity, labelled "same bank account", "same phone", "same photo".
- Filters: band, entity type, "only show clusters of 3 or more".
- Click a claim node → side panel with claim id, claimant, band, top reason, and **Open case**. Click an entity node → list of all claims sharing it.
- Case pages show a "Linked to 3 other claims" chip that opens the network centred on that claim.

**Evidence:** `CLM-NET-01` shares an entity with another claimant's claim (0.40); `CLM-NET-02` part of a cluster of 3+ (0.55).

**Performance:** cap the default view at 300 nodes; beyond that, show the largest clusters first.

**Acceptance criteria:** scenario D's four claims sharing one bank account appear as one visible cluster; raw bank numbers never appear anywhere in the UI or API.

---

### F26. Fraud-risk trend analytics page

**Purpose:** show the insurer how fraud risk changes over time, which fraud types are rising, and whether a spike is happening today.
**Route:** `/app/analytics` · **Priority:** Should · **Backend:** §8.13 · **Endpoint:** `GET /analytics/trends?range=7d|30d|90d&type=`

**Filters:** range (7 / 30 / 90 days, default 30), claim type (all / motor / health / property), "Hide seeded demo data" toggle.

**Panels:**
1. **KPI row:** total claims, % flagged (MEDIUM + HIGH), % HIGH, average overall risk, median time to decision; each with an arrow and change versus the previous period.
2. **Risk bands over time:** stacked bars per day (LOW / MEDIUM / HIGH).
3. **Flagged rate and average risk:** two lines per day with a dashed 7-day rolling average.
4. **Top fraud signals:** horizontal bars of how often each evidence id was a top-3 contributor, labelled in plain English ("Photo used in another claim").
5. **By claim type:** grouped bars, type × band.
6. **By modality:** share of flags driven by image / document / identity / voice.
7. **Recycled evidence and rings:** duplicates and clusters of 3+ per week.
8. **Decisions:** approved / rejected / evidence requested / escalated per week, and "% of HIGH claims later approved" (a rough false-positive check).
9. **Spike alert banner:** when today's flagged rate is at least twice the 7-day average and at least 5 claims are flagged: "Flagged claims are up today, mostly from reused photos."

**Interactions:** clicking any bar opens the queue filtered to that day / band / signal. Every chart has a one-line text summary and a **Table** toggle for accessibility.

**Demo data:** `seed_demo.py --history 30` creates about 300 synthetic past claims (≈75% LOW, 18% MEDIUM, 7% HIGH), a weekend dip, and a 2-day spike of reused photos tied to one bank-account ring, so analytics, the network and the queue tell one story.

**Acceptance criteria:** with an empty database every panel shows zeros or "No data yet", not an error; band counts per day add up to the day's total; the spike banner appears on the seeded spike day only.

---

### F27. Report export (PDF / JSON)

**Purpose:** let investigators attach the findings to an existing case file.
**Priority:** Should

**JSON:** the full `AnalysisResult` (scores, evidence, statuses, explanations) as downloaded from `GET /results/{id}`.
**PDF report (1–3 pages):** Lucen AI header, claim id, date, overall band and score with the recommended action, the three scores, the summary, top evidence with reasons, the image with heatmap thumbnail, the annotated document page, identity summary, checks run, decisions so far, and the footer "Generated by Lucen AI. Recommendations only; decisions are made by an investigator."

**Acceptance criteria:** the PDF opens in a normal viewer, contains no full Aadhaar number or bank number, and matches the on-screen scores.

---

## 5. Detection engine (backend features)

These features have no page of their own; they produce the evidence every screen shows. Each detector returns `Evidence` objects (id, title, plain-English reason, raw and calibrated score, weight, source, optional box and page, details) and a status (`ok / skipped / failed`).

### F28. Image manipulation and AI-generation detection

**Purpose:** problem-statement scope A: classify claim photos as authentic or AI-generated / manipulated, with a confidence score, and flag those above a threshold.
**Priority:** **Must** · **Backend:** §10

**Checks, in order:**
1. **Validate and decode:** magic bytes (JPG / PNG / WebP), EXIF orientation, RGB; keep the original bytes untouched for forensics. Quality metrics: size, megapixels, JPEG quality estimate, sharpness, screenshot detection → `IMG-QUAL-01` warning if poor.
2. **Metadata:** EXIF make, model, software, dates, GPS; C2PA content credentials. AI generator named in software (`IMG-EXIF-02a`, 0.80), editor named (`IMG-EXIF-02b`, 0.35), no camera EXIF (`IMG-EXIF-01`, 0.10, weak because messaging apps strip it), inconsistent timestamps (`IMG-EXIF-03`, 0.30), C2PA declares AI (`IMG-C2PA-01`, 0.95, override O1), valid camera provenance (`IMG-C2PA-02`, info).
3. **AI-generated detector:** pre-trained SigLIP AI-vs-human classifier; label read from `id2label`; temperature-scaled probability `p_ai`; optional test-time augmentation; tiles for large photos → `IMG-AI-01` (0.65, final weight from the bake-off).
4. **Error Level Analysis:** recompression difference map; skipped for non-JPEG and screenshots → `IMG-ELA-01` (0.25) with the box of the largest anomalous region.
5. **Noise residual consistency** and FFT periodicity → `IMG-NOISE-01` (0.20, weak).
6. **Localization** (F29).
7. **Duplicate lookup** (F33).

**Output:** image risk, authenticity = 1 − risk, band, confidence, evidence, heatmap artifact.

**Acceptance criteria:**
- On the team's held-out test set (including WhatsApp-compressed copies), report measured accuracy, precision and recall in `docs/EVALUATION.md`. Never present a target as a result.
- A PNG skips ELA with a note instead of a misleading score.
- A model loading failure leaves the other checks running and confidence lowered.

---

### F29. Suspicious-region highlighting

**Purpose:** show the investigator where on the photo the problem is (scope A, optional, high demo value).
**Priority:** Should · **Backend:** §10 Step 6

**Levels:** (1) default forensic heatmap combining ELA and noise maps, always available; (2) occlusion sensitivity map for images with `p_ai` above the medium threshold (about 49 forward passes; on demand if slow); (3) Grad-CAM only with spare time.

**UI rule:** the caption always says what the map means. "Regions with unusual compression or noise" (forensic) is a different thing from "regions the AI detector relied on" (occlusion), and must not be presented as the same.

**Acceptance criteria:** on the edited-photo sample the heatmap's strongest region overlaps the pasted area.

---

### F30. Document tampering detection

**Purpose:** problem-statement scope B: find altered values, inconsistent fonts and suspicious metadata in invoices, bills, reports and estimates, and flag each suspicious field with a reason and a box.
**Priority:** **Must** · **Backend:** §11

**Checks:**
1. **Kind:** digital PDF vs scanned PDF vs image.
2. **PDF metadata:** consumer / online editor as producer (`DOC-META-01`, 0.15), modified long after creation (`DOC-META-02`, 0.20), appended revisions (`DOC-META-03`, 0.20), creation date inconsistent with document or claim date (`DOC-META-04`, 0.35).
3. **Fonts and layout** (digital PDFs): different font within a field group (`DOC-FONT-01`, 0.40), size / baseline / stroke inconsistent within a line (`DOC-FONT-02`, 0.30), visible text differs from the hidden text layer (`DOC-OVERLAY-01`, 0.70, override O5).
4. **OCR** (PaddleOCR, Tesseract fallback) with word boxes and confidence; low-confidence words in numeric fields (`DOC-OCR-01`, 0.15).
5. **Field extraction:** regex for dates, amounts, ids, phones, emails; LLM for layout variety with strict JSON and a substring check so no value is invented.
6. **Consistency rules:** line items ≠ total (`DOC-LOGIC-01`, 0.80), tax / discount doesn't reproduce (`-02`, 0.50), invalid date logic (`-03`, 0.50), id / policy number fails format or checksum (`-04`, 0.50), same field differs across pages (`-05`, 0.60), inconsistent number formatting (`-06`, 0.25), amount in words ≠ digits (`-07`, 0.70). Each reason includes the actual numbers ("Line items add up to 1,000.00 but the total says 1,200.00").
7. **Tamper CNN** (trained by the team on synthetic tampering): EfficientNetB0 on ELA patches → page heatmap and up to three boxes (`DOC-CNN-01`, 0.50). Override O2 when it fires on the same region as a failed total rule.
8. **Word-level anomaly model:** Isolation Forest on per-word style features fitted on authentic pages (`DOC-ANOM-01`, 0.30), naming the deviating feature.
9. **Visual ELA on scans** (`DOC-VIS-01`, 0.25).
10. **Embedded images** (F31).

**Output:** document risk, authenticity, band, flagged-field table, annotated page artifact with boxes.

**Acceptance criteria:**
- Scenario C's bill shows `DOC-LOGIC-01`, `DOC-FONT-01` and `DOC-META-02`, each with a box on the right field.
- A clean invoice from the hard-negative set (mixed fonts by design) stays LOW.
- A password-protected PDF returns a clear error, not a crash.

---

### F31. Embedded-image bridge

**Purpose:** a fake damage photo pasted into a PDF report should be caught by the image checks. This links the two pipelines into one product.
**Priority:** Bonus · **Backend:** §11 Step 10

**Behaviour:** extract images from PDFs (skipping logos and tiny decorations), run each through F28, and relabel the evidence `DOC-IMG-*` with `source=embedded_image` and the page number. The Document tab shows the image crop with its own mini score.

**Acceptance criteria:** a PDF containing the AI-generated sample photo raises document risk via `DOC-IMG-AI-01`.

---

### F32. Face match: ID vs selfie, morph suspicion

**Purpose:** problem-statement bonus E: compare the face on the ID with the live selfie and flag mismatches or possible morphing.
**Priority:** Bonus · **Backend:** §12.1

**Behaviour:** InsightFace detection (one dominant face in the selfie; largest face on the ID) → quality check (size, blur, pose, brightness) → ArcFace cosine similarity → zones: same person (≥ upper threshold), ambiguous / possible morph (`ID-FACE-02`, 0.45), different person (`ID-FACE-01`, 0.85, override O3 → overall ≥ 0.80). The selfie also goes through the AI-image detector (`ID-DEEP-01`, 0.70). No usable face → `ID-QUAL-01` warning.

**Thresholds** are set on the team's own matched and mismatched pairs, never copied from elsewhere. Morph wording is always "suspicion", because two images can't prove a morph.

**Acceptance criteria:** two photos of the same team member match; two different members don't; embeddings are never stored.

---

### F33. Duplicate-image detection across claims

**Purpose:** recycled evidence is a classic fraud pattern: the same car photo submitted by two different people, or by one person across several claims.
**Priority:** Bonus · **Backend:** §13

**Behaviour:**
1. Cheapest first: exact SHA-256 of the file → pHash Hamming distance (≤ 6) → CLIP embedding cosine (≥ 0.95, tune) via FAISS. CLIP catches crops, resizes, colour changes and screenshots that defeat pHash.
2. Match → `IMG-DUP-01` (0.70) with the earlier claim id, similarity and match type (identical file / near duplicate), and an `image_match` entity link for the network (F25).
3. **Cross-person reuse** is flagged with "filed by a different claimant". **Same claimant, different claim** is flagged with that label. **Same claim** re-uploads (after an evidence request) are not flagged.
4. Add the image to the index only after analysis; never match an analysis against itself.

**Claimant side:** never told which claim matched; if rejected they see `PHOTO_PREVIOUSLY_USED`.

**Acceptance criteria:** seed a photo under claimant A; submit a cropped, re-compressed copy as claimant B → flagged with A's claim id; re-upload the same photo to B's own claim → no new match.

---

### F34. Cross-checks between image, document and claim

**Purpose:** catch contradictions that no single file reveals.
**Priority:** Bonus · **Backend:** §14

| ID | Check | Weight |
|---|---|---|
| `CLM-X-01` | Photo capture time outside the incident window | 0.40 |
| `CLM-X-02` | Document amount differs from the claimed amount | 0.50 |
| `CLM-X-03` | Name on ID differs from document or claim name | 0.45 |
| `CLM-X-04` | Same image reused across claims | inherits `IMG-DUP-01` |
| `CLM-X-05` | Document created after the claim was filed | 0.40 |
| `CLM-X-06` | Photo GPS far from the stated location (only if both exist) | 0.35 |
| `CLM-X-07` | Evidence dated before the policy started | 0.45 |
| `CLM-X-08` | Repair bill dated before the incident | 0.45 |

Missing inputs make a check `skipped`, never "clean". Reasons use the actual values ("The bill is dated 15 Sep, before the incident on 21 Sep").

**Acceptance criteria:** each rule has a unit test with one passing and one failing example.

---

### F35. Entity links

**Purpose:** connect claims that share contact or payment details, the backbone of the fraud network (F25).
**Priority:** Bonus · **Backend:** §14.3

**Behaviour:** after each analysis, write `phone`, `email`, `bank` (salted hashes, masked display) and `image_match` rows to `entities`; link to earlier claims sharing any of them. Same claimant's own repeated details do not count as a link. Evidence `CLM-NET-01` (0.40), `CLM-NET-02` (cluster of 3+, 0.55).

**Acceptance criteria:** two claims with the same bank account but different names produce `CLM-NET-01`; the raw account number is not in the database.

---

### F36. Risk scoring engine

**Purpose:** problem-statement scope C: turn evidence into an image authenticity score, a document authenticity score and an overall fraud likelihood (LOW / MEDIUM / HIGH), deterministically and explainably.
**Priority:** **Must** · **Backend:** §15

**Method:**
1. **Calibration:** temperature scaling for model outputs, Platt scaling for forensic statistics.
2. **Quality gating:** poor inputs reduce the weight of unreliable detectors (for example short side < 512 px → AI and forensic weights × 0.7); gated weights are visible on the evidence card.
3. **Per-pipeline noisy-OR:** `risk = 1 − Π(1 − wᵢ·pᵢ)` over risk evidence with `pᵢ ≥ 0.2` and `wᵢ·pᵢ ≥ 0.02`; per-source caps (metadata 0.4, Aadhaar QR 0.85, liveness 0.75, voice 0.55, LLM story 0.25 only if story scoring is on).
4. **Overall blend:** `0.7 · max(R_k) + 0.3 · mean(R_k)` across image, document, identity, voice and the claim pseudo-pipeline.
5. **Overrides O1–O7** for decisive evidence, each listed as an entry in "Why this score".
6. **Bands:** LOW < 0.35 ≤ MEDIUM < 0.65 ≤ HIGH (tuned on validation data and recorded in `models/calibration.json`).
7. **Confidence** (high / medium / low), stepped down for failed detectors, heavy quality gating, fewer than two independent sources, detector disagreement, liveness not performed on an ID claim, or an unreadable Aadhaar QR.
8. **Contributions** per evidence item for ranking and "Why this score".

**Rules:** the LLM never touches scoring; `info` and `warning` evidence never raise risk.

**Acceptance criteria:** the worked example in §15.8 reproduces exactly in `test_scoring.py` (image ≈ 0.748, document ≈ 0.905, overall ≈ 0.882); every override has a test.

---

### F37. Explanation engine

**Purpose:** scope C requires showing why a score was assigned. Investigators get plain-English reasons they can act on.
**Priority:** **Must** · **Backend:** §16

**Layers:**
1. **Templates** per evidence id with the real values filled in ("The document total (1,200.00) differs from the amount claimed (1,800.00).").
2. **Composer:** ranks evidence by contribution, writes the summary from the top reasons, adds the band's recommended action.
3. **Optional LLM rewording** of the summary into 2–3 natural sentences, with guardrails: only facts provided, every number in the output must appear in the input, timeout → template; `summary_source` records which one was used.

**Acceptance criteria:** with the LLM disabled every result still has a complete summary; an LLM output containing an invented number is discarded.

---

## 6. Platform features

### F38. Async jobs and live progress

**Purpose:** analyses take seconds; the UI must never freeze and must show what is happening.
**Priority:** **Must** · **Backend:** §7.3, §9.5

**Behaviour:** analyze endpoints return `202 {job_id}`; the frontend polls `GET /jobs/{id}` every second; the job reports steps (`queued / running / done / skipped / failed`) with durations; `MAX_CONCURRENT_JOBS` limits load; each detector has `DETECTOR_TIMEOUT_S`. On completion the response includes `result_id`.

**UI:** `PipelineProgress` checklist ("Reading metadata ✓ 0.2 s", "Checking for AI generation… ⟳").

**Acceptance criteria:** killing one detector mid-run marks it failed and the job still completes.

---

### F39. Mock mode and offline demo cache

**Purpose:** let the frontend be built before the ML is ready, and make the live demo work without internet.
**Priority:** Should · **Backend:** §7.4

**Behaviour:**
- `MOCK_ANALYSIS=1` (backend) or `VITE_MOCK=1` (frontend) returns canned LOW / MEDIUM / HIGH results including voice, liveness, Aadhaar QR, story, links, timeline and analytics blocks, and canned responses for every sync endpoint.
- `scripts/warm_demo_cache.py` runs every Bhashini and LLM call needed by scenarios A–D once and stores the responses in `data/demo_cache/` keyed by input hash. At runtime, a cache hit is used first when `DEMO_MODE=1`.

**Acceptance criteria:** with the network unplugged, the full 10-minute demo (§23) runs end to end.

---

### F40. Quality gating and robustness

**Purpose:** the problem statement requires handling low resolution, noise, compression and incomplete inputs.
**Priority:** **Must** · **Backend:** §15.3, §18

**Behaviour:** quality metrics at intake; gates reduce unreliable detectors' weights; screenshots and PNGs skip ELA with a note; missing EXIF or fields are `skipped`, never "clean"; HEIC / TIFF converted where possible, otherwise "unsupported"; corrupt or password-protected files give a clear message; multi-page PDFs are capped with a notice. Every reduction is shown in the Quality warnings banner.

**Acceptance criteria:** the degraded validation set (JPEG 50, blur, noise, resize) is reported separately in `docs/EVALUATION.md`.

---

### F41. Security and privacy

**Purpose:** handle uploads safely and personal data responsibly.
**Priority:** **Must** · **Backend:** §20

**Controls:** magic-byte validation; server-generated UUID file names; size, pixel and page limits; PDFs parsed and rendered only, never executed; job concurrency limit and timeouts; explicit CORS allow-list; secrets only in environment variables; internal errors hidden from users; uploads deleted after `RETENTION_HOURS`; face embeddings not stored; liveness frames deleted after the session; Aadhaar number, QR payload and QR photo never stored; phone / email / bank as salted hashes; no ID-card OCR text in logs; LLM use switchable (`LLM_ENABLED=false`) and disclosed; consent line in wizard step 5; claimant endpoints never return fraud internals.

**Acceptance criteria:** `test_claimant_safety.py` passes; `grep` of the database and logs after a demo run finds no full Aadhaar or bank number.

---

### F42. Seed data and demo scenarios

**Purpose:** a reliable, repeatable demo and realistic data for the queue, analytics and network.
**Priority:** Should

**`scripts/seed_demo.py` creates:** the three demo users and their policies; demo-key-signed Aadhaar-style cards; the FAISS index with the "earlier claim" photo; scenarios A–D as full claims; and, with `--history 30`, about 300 past claims for analytics (marked `is_seed=1`).

| ID | Scenario | Expected result |
|---|---|---|
| A | Genuine motor claim (Ravi), Hindi voice statement, liveness passed, valid card, camera photos | LOW, fast-track |
| B | AI-generated damage photo reused from an earlier claim (Anil), consistent invoice | HIGH (`IMG-AI-01`, `IMG-DUP-01`) |
| C | Health claim with a tampered hospital bill | HIGH (`DOC-LOGIC-01`, `DOC-FONT-01`, `DOC-META-02`) |
| D | Synthetic identity: liveness failed, face mismatch, edited printed DOB, bank account shared with 3 other claims | HIGH via O6, visible cluster in the network |

**Acceptance criteria:** `make seed` on a fresh clone produces all four scenarios with these bands every time.

---

### F43. Accessibility and bilingual UI

**Purpose:** usable by everyone, and judged on UI quality.
**Priority:** Should · **Backend:** §8.9

**Requirements:** keyboard navigation with visible focus; band = word + icon + colour; alt text on images; chart table views; contrast ratio ≥ 4.5:1; form errors announced to screen readers; claimant strings in `i18n/en.json` and `hi.json` with a switch on every claimant page; dates in Indian format (22 Sep 2026) and amounts as ₹1,80,000.

**Acceptance criteria:** the claimant wizard can be completed in Hindi end to end; Lighthouse accessibility score ≥ 90 on the case page **(target)**.

---

## 7. If time runs short: cut order

Cut from the top. Never cut a **Must**.

1. F25 Fraud network page (keep `CLM-NET-01` evidence on the case page)
2. F20 Story review tab
3. F12 claimant status page details (keep a simple status line)
4. F06 Synthetic-voice detection (keep transcription and auto-fill)
5. F26 analytics charts and F14 dashboard charts (keep KPI numbers)
6. F13 Claimant evidence timeline (keep F22)
7. Aadhaar QR photo comparison inside F09 (keep signature and field comparison)
8. Then: occlusion map (F29 level 2), PDF report (F27), identity pipeline (F32), duplicate detection (F33), LLM rewording (F37 layer 3)

**Never cut:** F16 Analyze page, F17 result page, F28 image detection with confidence, F30 document flags with reasons, F36 scoring with explanation, F37 templates, F38 jobs.

---

## 8. Final acceptance checklist (run before the demo)

- [ ] Image upload → score, band, confidence, heatmap, reasons (F16, F17, F28, F29)
- [ ] Document upload → flagged fields with boxes and reasons (F30)
- [ ] Full claim → image, document and overall scores first, with "Why this score" (F36, F37)
- [ ] Identity: liveness live in front of judges, face match, Aadhaar QR mismatch shown (F08, F09, F18, F32)
- [ ] Duplicate photo across two claimants flagged (F21, F33)
- [ ] Evidence timeline shows a red contradiction for scenario B (F22)
- [ ] Reject dialog opens pre-filled with a safe AI message; claimant sees it after Send (F24, F12)
- [ ] Analytics shows the seeded spike; network shows the ring (F25, F26)
- [ ] Claimant can't open `/app`; claimant API has no scores (F02, F41)
- [ ] Whole demo runs with the network unplugged (F39)
- [ ] Measured metrics written in `docs/EVALUATION.md`; targets labelled as targets
