export default function ReviewStep({
  policy,
  description,
  amount,
  evidence,
  consent,
  setConsent,
  hasVoice = false,
  consentVoice = false,
  setConsentVoice = () => {},
  t,
}: {
  policy: string;
  description: string;
  amount: string;
  evidence: number;
  consent: boolean;
  setConsent: (x: boolean) => void;
  hasVoice?: boolean;
  consentVoice?: boolean;
  setConsentVoice?: (x: boolean) => void;
  t: any;
}) {
  return (
    <div>
      <h2 className="font-display text-xl font-semibold">{t.review}</h2>
      <div className="mt-5 space-y-3 rounded-xl bg-bg p-5 text-sm">
        <div>
          <span className="text-muted">{t.policyLabel}</span>
          <div className="font-semibold">{policy || t.notSelected}</div>
        </div>
        <div>
          <span className="text-muted">{t.descriptionLabel}</span>
          <div className="font-semibold">{description || t.notAdded}</div>
        </div>
        <div>
          <span className="text-muted">{t.amount}</span>
          <div className="font-semibold">₹{Number(amount || 0).toLocaleString('en-IN')}</div>
        </div>
        <div>
          <span className="text-muted">{t.evidenceLabel}</span>
          <div className="font-semibold">{evidence} item(s)</div>
        </div>
      </div>
      <label className="mt-5 flex gap-3 text-sm">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        <span>{t.consentText}</span>
      </label>
      {hasVoice && (
        <label className="mt-3 flex gap-3 text-sm">
          <input
            type="checkbox"
            checked={consentVoice}
            onChange={(e) => setConsentVoice(e.target.checked)}
          />
          <span>{t.consentVoice}</span>
        </label>
      )}
    </div>
  );
}
