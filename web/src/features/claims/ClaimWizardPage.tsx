import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { raw } from '../../api/raw/endpoints';
import { usePolicies } from '../../api/hooks';
import { getToken } from '../../api/session';
import { Logo } from '../../components/Logo';
import en from '../../i18n/en.json';
import hi from '../../i18n/hi.json';
import PolicyStep from './PolicyStep';
import StoryStep from './StoryStep';
import VerifyStep from './VerifyStep';
import EvidenceStep from './EvidenceStep';
import ReviewStep from './ReviewStep';

type EvidenceItem = { file: File; slot: string; captureSource: 'camera' | 'upload' };
const steps = ['policy', 'story', 'verify', 'evidence', 'review'] as const;
export default function ClaimWizardPage() {
  const nav = useNavigate();
  const policies = usePolicies();
  const [lang, setLang] = useState<'en' | 'hi'>('en');
  const t: any = lang === 'en' ? en : hi;
  const [step, setStep] = useState(0);
  const [policy, setPolicy] = useState<any>();
  const [type, setType] = useState('motor');
    const [claimantName, setClaimantName] = useState('');
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [consent, setConsent] = useState(false);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [location, setLocation] = useState<[number, number] | null>(null);
  const [voice, setVoice] = useState<Blob | null>(null);
  const [voiceLang, setVoiceLang] = useState<string>('hi');
  const [consentVoice, setConsentVoice] = useState(false);
  const [incidentDate, setIncidentDate] = useState('');
  const [incidentTime, setIncidentTime] = useState('');
  const [idPhoto, setIdPhoto] = useState<File>();
  const [selfie, setSelfie] = useState<File>();
  const [sessionId, setSessionId] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const next = async () => {
    setError('');
    if (step === 0 && !policy) {
      setError(t.policyMissing);
      return;
    }
    if (step === 1 && !description.trim()) {
      setError(t.descriptionMissing);
      return;
    }
    if (step === 1 && !incidentDate) {
      setError(t.dateMissing);
      return;
    }
    if (step === 2) {
      if (!selfie && !idPhoto) {
        setError("Both a live selfie and an ID card are required.");
        return;
      }
      if (!selfie) {
        setError("Couldn't save your live photo – please capture again.");
        return;
      }
      if (!idPhoto) {
        setError("Please upload an ID card.");
        return;
      }
    }
    if (step === 3) {
      if (type === 'health') {
        if (!evidence.some(e => e.slot === 'bill')) {
           setError('A bill is required for health claims.');
           return;
        }
      } else {
        if (!evidence.some(e => e.slot.includes('damage') || e.slot.includes('shot') || e.slot.includes('closeup'))) {
           setError('At least one damage photo is required.');
           return;
        }
      }
    }
    if (step < 4) {
      setStep((x) => x + 1);
      return;
    }
    if (!consent) {
      setError(t.consent);
      return;
    }
    if (voice && !consentVoice) {
      setError(t.voiceConsentMissing);
      return;
    }
    setBusy(true);
    try {
      const result = await raw.createClaim({
        policyId: policy.id,
        claimType: type,
        peril: 'collision',
        incidentDate,
        incidentTime,
        // Sent as a JSON object string per the claim-metadata contract (§6.8): {lat, lng, text}.
        location: location ? JSON.stringify({ lat: location[0], lng: location[1], text: '' }) : '',
        claimedAmount: amount || '0',
        damagedItems: [],
        description,
        consent,
        evidence,
        idPhoto,
        selfie,
        voiceAudio: voice ?? undefined,
        consentVoiceProcessing: consentVoice,
        descriptionLang: voice ? voiceLang : lang,
          claimantName: claimantName,
        livenessSessionId: sessionId,
      });
      nav(`/claim/${result.claim_id ?? result.id ?? ''}`);
    } catch (e: any) {
      setError(e.message || 'Could not submit the claim.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-5 py-5">
          <Logo />
          <div className="flex gap-2">
            <button
              onClick={() => setLang('en')}
              className={`rounded-lg px-3 py-1.5 text-xs ${lang === 'en' ? 'bg-primary-dark text-white' : 'bg-nile-soft'}`}
            >
              English
            </button>
            <button
              onClick={() => setLang('hi')}
              className={`rounded-lg px-3 py-1.5 text-xs ${lang === 'hi' ? 'bg-primary-dark text-white' : 'bg-nile-soft'}`}
            >
              हिंदी
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-5 py-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <div className="text-sm text-muted">{t.brand}</div>
            <h1 className="font-display mt-1 text-3xl font-bold">{t.start}</h1>
          </div>
          <div className="text-sm text-muted">{step + 1} / 5</div>
        </div>
        <div className="mb-8 flex gap-2">
          {steps.map((s, i) => (
            <div
              key={s}
              className={`h-1.5 flex-1 rounded-full ${i <= step ? 'bg-primary-dark' : 'bg-slate-200'}`}
            />
          ))}
        </div>
        <div className="card p-6">
          {step === 0 && (
            <PolicyStep
              policies={policies.data ?? []}
              selected={policy?.id ?? ''}
              onSelect={(p) => {
                setPolicy(p);
                setType(p.claimType);
              }}
              t={t}
            />
          )}{' '}
          {step === 1 && (
            <StoryStep
                claimantName={claimantName}
                setClaimantName={setClaimantName}
              description={description}
              setDescription={setDescription}
              amount={amount}
              setAmount={setAmount}
              location={location}
              setLocation={setLocation}
              onAudio={setVoice}
              incidentDate={incidentDate}
              setIncidentDate={setIncidentDate}
              incidentTime={incidentTime}
              setIncidentTime={setIncidentTime}
              voiceLang={voiceLang}
              setVoiceLang={setVoiceLang}
              t={t}
            />
          )}{' '}
          {step === 2 && (
            <VerifyStep
              onComplete={(url, sid, file?: File) => {
                setSessionId(sid);
                if (file) {
                  setSelfie(file);
                } else if (url) {
                  fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
                    .then((r) => { if (!r.ok) throw new Error(); return r.blob(); })
                    .then((b) => setSelfie(new File([b], 'selfie.jpg', { type: 'image/jpeg' })))
                    .catch(() => { setSelfie(undefined); });
                }
              }}
              onId={setIdPhoto}
              t={t}
            />
          )}{' '}
          {step === 3 && <EvidenceStep claimType={type} onChange={setEvidence} t={t} />}{' '}
          {step === 4 && (
            <ReviewStep
              policy={policy?.policyNumber ?? ''}
              description={description}
              amount={amount}
              evidence={evidence.length}
              consent={consent}
              setConsent={setConsent}
              hasVoice={!!voice}
              consentVoice={consentVoice}
              setConsentVoice={setConsentVoice}
              t={t}
            />
          )}{' '}
          {error && (
            <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
          )}
          <div className="mt-7 flex justify-between">
            <button
              disabled={step === 0}
              onClick={() => setStep((x) => x - 1)}
              className="rounded-lg border px-4 py-2.5 text-sm disabled:opacity-30"
            >
              {t.back}
            </button>
            <button
              onClick={next}
              disabled={busy}
              className="rounded-lg bg-primary-dark px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-30"
            >
              {busy ? t.submitting : step === 4 ? t.submit : t.next}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
