import { Link, useParams } from 'react-router-dom';
import { useClaimStatus } from '../../api/hooks';
import { raw } from '../../api/raw/endpoints';
import { useState } from 'react';
import { Logo } from '../../components/Logo';
import { Loading, ErrorState } from '../../components/States';
import { friendlyError } from '../../lib/errorMessages';
import en from '../../i18n/en.json';
import { dateLabel } from '../../lib/format';
export default function ClaimStatusPage() {
  const { id = '' } = useParams();
  const q = useClaimStatus(id);
  const [file, setFile] = useState<File>();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  if (q.isLoading)
    return (
      <div className="min-h-screen grid place-items-center bg-bg">
        <Loading />
      </div>
    );
  if (q.error)
    return (
      <div className="min-h-screen bg-bg p-6">
        <ErrorState
          message={friendlyError((q.error as any).code, (q.error as any).message)}
          retry={() => q.refetch()}
        />
      </div>
    );
  const d = q.data!;
  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border bg-white">
        <div className="mx-auto max-w-3xl px-5 py-5">
          <Logo />
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-5 py-8">
        <div className="card p-6">
          <div className="text-sm text-muted">{d.id}</div>
          <h1 className="font-display mt-1 text-3xl font-bold">{en.status}</h1>
          <div className="mt-6 rounded-xl bg-bg p-5">
            <div className="font-semibold capitalize">{d.status.replaceAll('_', ' ')}</div>
            {d.reasonLabel && <div className="mt-1 text-sm font-medium">{d.reasonLabel}</div>}
            {d.message && <p className="mt-2 text-sm text-muted">{d.message}</p>}
            {!!d.nextSteps.length && (
              <ul className="mt-3 list-disc pl-5 text-sm">
                {d.nextSteps.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            )}
          </div>
          <div className="mt-7">
            <h2 className="font-display text-lg font-semibold">{en.progress}</h2>
            <div className="mt-4 space-y-5">
              {d.timeline.map((x, i) => (
                <div key={i} className="relative pl-7">
                  <span className="absolute left-0 top-1 h-3 w-3 rounded-full bg-primary-dark" />
                  <div className="text-xs text-muted">{x.date ? dateLabel(x.date) : ''}</div>
                  <div className="font-semibold capitalize">{x.status.replaceAll('_', ' ')}</div>
                  <div className="text-sm text-muted">{x.detail}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-7">
            <h2 className="font-display text-lg font-semibold">{en.submittedItems}</h2>
            <div className="mt-3 space-y-2">
              {d.evidence.map((e, i) => (
                <div key={i} className="flex justify-between rounded-lg border p-3 text-sm">
                  <span>{e.label ?? e.slot.replaceAll('_', ' ')}</span>
                  <span
                    className={`capitalize ${e.status === 'needs_replacing' ? 'font-semibold text-amber-700' : 'text-muted'}`}
                  >
                    {e.status.replaceAll('_', ' ')}
                  </span>
                </div>
              ))}
            </div>
          </div>
          {d.canResubmit && (
            <div className="mt-7 rounded-xl border p-4">
              <div className="text-sm font-semibold">Upload the requested item</div>
              {!!d.slotsToResubmit.length && (
                <div className="mt-1 text-sm text-muted">
                  Requested: {d.slotsToResubmit.map((x) => x.replaceAll('_', ' ')).join(', ')}
                </div>
              )}
              <input
                className="mt-3 block text-sm"
                type="file"
                accept="image/*,.pdf"
                onChange={(event) => setFile(event.target.files?.[0])}
              />
              <button
                disabled={!file || busy}
                onClick={async () => {
                  if (!file) return;
                  setBusy(true);
                  try {
                    await raw.resubmit(id, [file]);
                    setMessage('Evidence submitted.');
                  } finally {
                    setBusy(false);
                  }
                }}
                className="mt-3 rounded-lg bg-primary-dark px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-30"
              >
                Submit
              </button>
              {message && <div className="mt-2 text-sm text-muted">{message}</div>}
            </div>
          )}
          <div className="mt-7">
            <Link to="/claim/new" className="rounded-lg border px-4 py-2.5 text-sm">
              {en.startNew}
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
