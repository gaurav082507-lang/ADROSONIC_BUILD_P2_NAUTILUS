import { useState } from 'react';
import { raw } from '../../api/raw/endpoints';
import ClaimantPreview from './ClaimantPreview';

type Props = { id: string; onClose: () => void };
const actions = ['approve', 'reject', 'request_evidence', 'escalate'] as const;
const reasons = [
  'photo_unclear',
  'document_needs_verification',
  'details_mismatch',
  'identity_verification_needed',
  'duplicate_submission',
  'other',
] as const;
export default function DecisionDialog({ id, onClose }: Props) {
  const [action, setAction] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [draft, setDraft] = useState<any>();
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  async function generate() {
    setBusy(true);
    setError('');
    try {
      setDraft(await raw.decisionDraft(id, { action, reasonCategory: reason }));
    } catch (e: any) {
      setError(e.message ?? 'Could not generate draft.');
    } finally {
      setBusy(false);
    }
  }
  async function send() {
    if (!draft) return;
    setBusy(true);
    try {
      await raw.decision(id, {
        action,
        reasonCategory: reason,
        messageEn: draft.claimant_message_en,
        messageHi: draft.claimant_message_hi,
      });
      setSent(true);
    } catch (e: any) {
      setError(e.message ?? 'Could not send decision.');
    } finally {
      setBusy(false);
    }
  }
  if (sent)
    return (
      <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
        <div className="w-full max-w-lg rounded-2xl bg-white p-6">
          <h2 className="font-display text-xl font-bold">Decision sent</h2>
          <p className="mt-2 text-sm text-muted">The backend accepted the investigator decision.</p>
          <button
            onClick={onClose}
            className="mt-5 rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-white"
          >
            Close
          </button>
        </div>
      </div>
    );
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-2xl bg-white p-6">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl font-bold">Record decision</h2>
          <button onClick={onClose} className="text-muted">
            Close
          </button>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <label className="text-sm">
            Action
            <select
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="mt-1 w-full rounded-lg border p-2.5"
            >
              <option value="">Select</option>
              {actions.map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Reason category
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="mt-1 w-full rounded-lg border p-2.5"
            >
              <option value="">Select</option>
              {reasons.map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
        </div>
        <button
          disabled={!action || !reason || busy}
          onClick={generate}
          className="mt-4 rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
        >
          {busy ? 'Generating…' : 'Generate draft'}
        </button>
        {draft && (
          <div className="mt-5 rounded-xl bg-slate-50 p-4">
            <div className="text-xs font-semibold uppercase text-muted">
              What the claimant will see
            </div>
            <textarea
              value={draft.claimant_message_en}
              onChange={(e) => setDraft({ ...draft, claimant_message_en: e.target.value })}
              className="mt-3 min-h-28 w-full rounded-lg border p-3 text-sm"
            />
            <ClaimantPreview
              english={draft.claimant_message_en}
              hindi={draft.claimant_message_hi}
            />
            <textarea
              value={draft.claimant_message_hi}
              onChange={(e) => setDraft({ ...draft, claimant_message_hi: e.target.value })}
              className="mt-3 min-h-24 w-full rounded-lg border p-3 text-sm"
            />
            <button
              disabled={busy}
              onClick={send}
              className="mt-3 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white"
            >
              Send
            </button>
          </div>
        )}
        {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      </div>
    </div>
  );
}
