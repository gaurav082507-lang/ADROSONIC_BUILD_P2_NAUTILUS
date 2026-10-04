import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useI18n } from '../../i18n/I18nContext';
import { getPoliciesApi, createClaimApi, startLivenessSessionApi, verifyLivenessApi } from '../../api/auth';

const CLAIM_TYPES = ['motor', 'health', 'property'];
const STEPS = ['step1', 'step2', 'step3', 'step4'];

const initForm = {
  policy_id: '',
  claim_type: '',
  peril: '',
  incident_date: '',
  incident_time: '',
  location_text: '',
  claimed_amount: '',
  description_text: '',
  consent: false,
};

export default function ClaimWizardPage() {
  const { t } = useI18n();
  const navigate = useNavigate();

  const [step, setStep]       = useState(0);
  const [policies, setPolicies] = useState([]);
  const [form, setForm]       = useState(initForm);
  const [evidenceFiles, setEvidenceFiles] = useState([]);
  const [idPhoto, setIdPhoto] = useState(null);
  const [selfie, setSelfie]   = useState(null);
  const [livenessSessionId, setLivenessSessionId] = useState(null);
  const [livenessPassed, setLivenessPassed]       = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingPolicies, setLoadingPolicies] = useState(true);
  const [error, setError]     = useState('');
  const [submitted, setSubmitted] = useState('');

  useEffect(() => {
    getPoliciesApi()
      .then(d => setPolicies(d?.policies || []))
      .catch(() => {})
      .finally(() => setLoadingPolicies(false));
  }, []);

  function set(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));
  }

  async function handleSubmit() {
    if (!form.consent) { setError(t('consentRequired')); return; }
    setError('');
    setLoading(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => {
        if (k === 'consent') fd.append(k, v ? 'true' : 'false');
        else if (v) fd.append(k, v);
      });
      if (form.location_text) {
        fd.append('location_text', form.location_text);
      }
      evidenceFiles.forEach(f => fd.append('evidence', f));
      if (idPhoto)  fd.append('id_photo', idPhoto);
      if (selfie)   fd.append('selfie', selfie);
      if (livenessSessionId) fd.append('liveness_session_id', livenessSessionId);

      const res = await createClaimApi(fd);
      setSubmitted(res?.claim_id || 'done');
    } catch (err) {
      setError(err.message || t('error'));
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div style={styles.successCard}>
        <div style={styles.successIcon}>✓</div>
        <h2 style={styles.successTitle}>{t('claimSubmitted')}</h2>
        <p style={styles.successId}><code>{submitted}</code></p>
        <button style={styles.btn} onClick={() => navigate('/claims/mine')}>{t('myClaimsNav')}</button>
      </div>
    );
  }

  return (
    <div>
      <h2 style={styles.h2}>{t('wizardTitle')}</h2>

      {/* Step indicator */}
      <div style={styles.steps}>
        {STEPS.map((s, i) => (
          <div key={s} style={{ ...styles.stepDot, background: i <= step ? '#38bdf8' : '#334155' }}>
            <span style={styles.stepNum}>{i + 1}</span>
          </div>
        ))}
      </div>
      <div style={styles.stepLabel}>{t(STEPS[step])}</div>

      <div style={styles.card}>
        {step === 0 && <Step1 form={form} set={set} policies={policies} loading={loadingPolicies} t={t} />}
        {step === 1 && <Step2 form={form} set={set} t={t} />}
        {step === 2 && (
          <Step3
            evidenceFiles={evidenceFiles}
            setEvidenceFiles={setEvidenceFiles}
            idPhoto={idPhoto}
            setIdPhoto={setIdPhoto}
            selfie={selfie}
            setSelfie={setSelfie}
            livenessSessionId={livenessSessionId}
            setLivenessSessionId={setLivenessSessionId}
            livenessPassed={livenessPassed}
            setLivenessPassed={setLivenessPassed}
            t={t}
          />
        )}
        {step === 3 && <Step4 form={form} set={set} error={error} t={t} />}
      </div>

      <div style={styles.navRow}>
        {step > 0 && <button style={styles.backBtn} onClick={() => setStep(s => s - 1)}>{t('back')}</button>}
        {step < 3 && <button style={styles.nextBtn} onClick={() => setStep(s => s + 1)}>{t('next')}</button>}
        {step === 3 && (
          <button style={styles.submitBtn} onClick={handleSubmit} disabled={loading}>
            {loading ? t('submitting') : t('submit')}
          </button>
        )}
      </div>
    </div>
  );
}

// ───── Step Components ─────

function Step1({ form, set, policies, loading, t }) {
  return (
    <div>
      <FormField label={t('selectPolicy')}>
        <select style={styles.select} value={form.policy_id} onChange={set('policy_id')} required>
          <option value="">{loading ? t('loading') : t('selectPolicy')}</option>
          {policies.map(p => (
            <option key={p.policy_id} value={p.policy_id}>
              {p.policy_number} — {p.policy_type} (₹{Number(p.sum_insured).toLocaleString('en-IN')})
            </option>
          ))}
        </select>
      </FormField>
      <FormField label={t('selectClaimType')}>
        <select style={styles.select} value={form.claim_type} onChange={set('claim_type')} required>
          <option value="">{t('selectClaimType')}</option>
          {CLAIM_TYPES.map(ct => <option key={ct} value={ct}>{ct}</option>)}
        </select>
      </FormField>
    </div>
  );
}

function Step2({ form, set, t }) {
  return (
    <div>
      <FormField label={t('perilLabel')}>
        <input style={styles.input} type="text" value={form.peril} onChange={set('peril')} placeholder="e.g. Accident, Fire, Theft" />
      </FormField>
      <FormField label={t('incidentDateLabel')}>
        <input style={styles.input} type="date" value={form.incident_date} onChange={set('incident_date')} />
      </FormField>
      <FormField label={t('incidentTimeLabel')}>
        <input style={styles.input} type="time" value={form.incident_time} onChange={set('incident_time')} />
      </FormField>
      <FormField label={t('locationTextLabel')}>
        <input style={styles.input} type="text" value={form.location_text} onChange={set('location_text')} placeholder="e.g. NH-48 near Gurgaon toll" />
      </FormField>
      <FormField label={t('claimedAmountLabel')}>
        <input style={styles.input} type="number" value={form.claimed_amount} onChange={set('claimed_amount')} min="0" />
      </FormField>
      <FormField label={t('descriptionLabel')}>
        <textarea style={{ ...styles.input, height: 80, resize: 'vertical' }} value={form.description_text} onChange={set('description_text')} />
      </FormField>
    </div>
  );
}

function Step3({
  evidenceFiles, setEvidenceFiles,
  idPhoto, setIdPhoto,
  selfie, setSelfie,
  livenessSessionId, setLivenessSessionId,
  livenessPassed, setLivenessPassed,
  t
}) {
  const [mode, setMode] = useState('camera'); // 'camera' | 'upload'
  const [cameraActive, setCameraActive] = useState(false);
  const [session, setSession] = useState(null);
  const [activeChallengeIdx, setActiveChallengeIdx] = useState(0);
  const [statusMsg, setStatusMsg] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [livenessError, setLivenessError] = useState('');
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  const CHALLENGE_LABELS = {
    blink: '👁️ Blink your eyes naturally',
    turn_left: '⬅️ Turn your head slowly to the left',
    turn_right: '➡️ Turn your head slowly to the right',
    look_up: '⬆️ Tilt your head slightly up'
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(tr => tr.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  const startLiveness = async () => {
    setLivenessError('');
    setStatusMsg('Initializing secure liveness session...');
    try {
      const sess = await startLivenessSessionApi();
      setSession(sess);
      setActiveChallengeIdx(0);

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
      });
      streamRef.current = stream;
      setCameraActive(true);

      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
        runChallengeSequence(sess);
      }, 400);
    } catch (err) {
      console.error(err);
      setLivenessError('Camera access unavailable or session expired. You may use static photo upload.');
      stopCamera();
    }
  };

  const runChallengeSequence = async (sess) => {
    const challenges = sess.challenges || ['blink', 'turn_left', 'turn_right'];
    const capturedFrames = [];
    const canvas = document.createElement('canvas');
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext('2d');

    for (let cIdx = 0; cIdx < challenges.length; cIdx++) {
      setActiveChallengeIdx(cIdx);
      const ch = challenges[cIdx];
      setStatusMsg(`Challenge ${cIdx + 1}/3: ${CHALLENGE_LABELS[ch] || ch}`);

      for (let f = 0; f < 4; f++) {
        await new Promise(r => setTimeout(r, 450));
        if (videoRef.current && videoRef.current.readyState >= 2) {
          ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
          const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.85));
          if (blob) {
            capturedFrames.push({ blob, challenge: ch, index: capturedFrames.length });
          }
        }
      }
    }

    setStatusMsg('Verifying liveness against AI security model...');
    setVerifying(true);

    try {
      const fd = new FormData();
      fd.append('session_id', sess.session_id);
      fd.append('nonce', sess.nonce);

      const frameMeta = {};
      capturedFrames.forEach((item, i) => {
        const fname = `frame_${i}.jpg`;
        fd.append('frames', item.blob, fname);
        frameMeta[fname] = { challenge: item.challenge, timestamp: i * 0.45 };
      });
      fd.append('frame_metadata', JSON.stringify(frameMeta));

      const res = await verifyLivenessApi(fd);
      if (res && res.passed) {
        setLivenessPassed(true);
        setLivenessSessionId(sess.session_id);
        setStatusMsg('Liveness Verified Successfully! ✓');

        if (capturedFrames.length > 0) {
          const selfieFile = new File([capturedFrames[0].blob], 'verified_selfie.jpg', { type: 'image/jpeg' });
          setSelfie(selfieFile);
        }
        stopCamera();
      } else {
        const failReasons = res?.reasons?.join(' ') || 'Verification failed.';
        setLivenessError(`Liveness verification not met: ${failReasons}. Please try again or switch to upload.`);
        stopCamera();
      }
    } catch (err) {
      console.error(err);
      setLivenessError('Liveness verification failed. You may retry or upload a static selfie.');
      stopCamera();
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div>
      <FormField label={t('evidenceFilesLabel') || 'Claim Supporting Evidence (Photos / Estimates)'}>
        <input style={styles.fileInput} type="file" multiple accept="image/*,application/pdf" onChange={e => setEvidenceFiles(Array.from(e.target.files))} />
        {evidenceFiles.length > 0 && <div style={styles.fileCount}>{evidenceFiles.length} file(s) selected</div>}
      </FormField>

      <FormField label={t('idPhotoLabel') || 'Government ID Photo (Aadhaar / Driving License)'}>
        <input style={styles.fileInput} type="file" accept="image/*" onChange={e => setIdPhoto(e.target.files[0] || null)} />
        {idPhoto && <div style={styles.fileCount}>Selected: {idPhoto.name}</div>}
      </FormField>

      <div style={{ marginTop: 24, padding: '16px', background: '#0f172a', borderRadius: 8, border: '1px solid #334155' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <div style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 14 }}>
              Identity & Liveness Verification
            </div>
            <div style={{ color: '#94a3b8', fontSize: 12 }}>
              Verifies physical presence to prevent digital impersonation
            </div>
          </div>
          <button
            type="button"
            onClick={() => { stopCamera(); setMode(m => m === 'camera' ? 'upload' : 'camera'); }}
            style={{ background: 'transparent', border: '1px solid #475569', color: '#94a3b8', borderRadius: 5, padding: '4px 10px', fontSize: 11, cursor: 'pointer' }}
          >
            {mode === 'camera' ? 'Use Photo Upload' : 'Use Live Camera'}
          </button>
        </div>

        {mode === 'camera' ? (
          <div>
            {livenessPassed ? (
              <div style={{ background: '#064e3b', border: '1px solid #059669', borderRadius: 6, padding: '14px', textAlign: 'center', color: '#34d399' }}>
                <div style={{ fontSize: 24, marginBottom: 4 }}>✓</div>
                <div style={{ fontWeight: 700, fontSize: 14 }}>Live Biometric Check Completed</div>
                <div style={{ fontSize: 12, color: '#a7f3d0', marginTop: 2 }}>Session: {livenessSessionId}</div>
              </div>
            ) : cameraActive ? (
              <div style={{ textAlign: 'center' }}>
                <div style={{ position: 'relative', width: 320, height: 240, margin: '0 auto', background: '#000', borderRadius: 8, overflow: 'hidden' }}>
                  <video ref={videoRef} playsInline muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    width: 130,
                    height: 180,
                    borderRadius: '50%',
                    border: '2px dashed #38bdf8',
                    pointerEvents: 'none',
                    boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.45)'
                  }} />
                </div>
                <div style={{ marginTop: 12, color: '#38bdf8', fontWeight: 600, fontSize: 14 }}>
                  {statusMsg}
                </div>
                {verifying && <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 4 }}>Analyzing 3D landmark kinematics...</div>}
              </div>
            ) : (
              <div>
                {livenessError && (
                  <div style={{ background: '#7f1d1d', border: '1px solid #dc2626', borderRadius: 6, padding: '10px', color: '#fca5a5', fontSize: 12, marginBottom: 12 }}>
                    {livenessError}
                  </div>
                )}
                <div style={{ textAlign: 'center', padding: '16px 0' }}>
                  <button
                    type="button"
                    onClick={startLiveness}
                    style={{ background: '#38bdf8', color: '#0f172a', border: 'none', borderRadius: 7, padding: '10px 22px', fontWeight: 700, fontSize: 13, cursor: 'pointer' }}
                  >
                    Start Live Face Verification
                  </button>
                  <div style={{ color: '#64748b', fontSize: 11, marginTop: 8 }}>
                    Requires camera permission. 3 interactive facial movements verified in ~8 seconds.
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div>
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, padding: '10px', color: '#fbbf24', fontSize: 12, marginBottom: 12 }}>
              ⚠️ Camera fallback mode: Uploading a static selfie skips live biometric challenge.
            </div>
            <FormField label={t('selfieLabel') || 'Selfie Photo'}>
              <input style={styles.fileInput} type="file" accept="image/*" onChange={e => setSelfie(e.target.files[0] || null)} />
            </FormField>
          </div>
        )}
      </div>
    </div>
  );
}

function Step4({ form, set, error, t }) {
  return (
    <div>
      <p style={styles.consentText}>{t('consentText')}</p>
      <label style={styles.consentLabel}>
        <input type="checkbox" checked={form.consent} onChange={set('consent')} style={{ marginRight: 8 }} />
        {t('consentText')}
      </label>
      {error && <p style={styles.err}>{error}</p>}
    </div>
  );
}

function FormField({ label, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={styles.label}>{label}</label>
      {children}
    </div>
  );
}

const styles = {
  h2: { color: '#e2e8f0', fontSize: 20, fontWeight: 700, marginBottom: 20 },
  steps: { display: 'flex', gap: 10, marginBottom: 8 },
  stepDot: { width: 28, height: 28, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  stepNum: { color: '#0f172a', fontSize: 12, fontWeight: 700 },
  stepLabel: { color: '#64748b', fontSize: 12, marginBottom: 16 },
  card: { background: '#1e293b', borderRadius: 10, padding: '24px', marginBottom: 16 },
  label: { display: 'block', color: '#94a3b8', fontSize: 12, marginBottom: 5 },
  input: { width: '100%', boxSizing: 'border-box', padding: '9px 12px', borderRadius: 7, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0', fontSize: 13 },
  select: { width: '100%', padding: '9px 12px', borderRadius: 7, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0', fontSize: 13 },
  fileInput: { color: '#94a3b8', fontSize: 12, display: 'block' },
  fileCount: { color: '#64748b', fontSize: 11, marginTop: 4 },
  consentText: { color: '#94a3b8', fontSize: 13, marginBottom: 14, lineHeight: 1.6 },
  consentLabel: { display: 'flex', alignItems: 'flex-start', color: '#cbd5e1', fontSize: 13, cursor: 'pointer' },
  err: { color: '#f87171', fontSize: 13, marginTop: 8 },
  navRow: { display: 'flex', gap: 12, justifyContent: 'flex-end' },
  backBtn: { background: '#334155', border: 'none', color: '#cbd5e1', borderRadius: 7, padding: '9px 20px', cursor: 'pointer', fontSize: 13 },
  nextBtn: { background: '#38bdf8', border: 'none', color: '#0f172a', borderRadius: 7, padding: '9px 20px', fontWeight: 700, cursor: 'pointer', fontSize: 13 },
  submitBtn: { background: '#34d399', border: 'none', color: '#0f172a', borderRadius: 7, padding: '9px 24px', fontWeight: 700, cursor: 'pointer', fontSize: 13 },
  successCard: { background: '#1e293b', borderRadius: 12, padding: '48px 24px', textAlign: 'center' },
  successIcon: { fontSize: 40, color: '#34d399', marginBottom: 16 },
  successTitle: { color: '#e2e8f0', fontSize: 20, marginBottom: 8 },
  successId: { color: '#94a3b8', marginBottom: 24 },
  btn: { background: '#38bdf8', border: 'none', color: '#0f172a', borderRadius: 7, padding: '10px 24px', fontWeight: 700, cursor: 'pointer', fontSize: 14 },
};
