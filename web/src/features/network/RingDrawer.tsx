import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Download, X } from 'lucide-react';
import { useRing, useRingStatus } from '../../api/hooks';
import { raw } from '../../api/raw/endpoints';
import { downloadBlob } from '../../lib/download';
import { friendlyError } from '../../lib/errorMessages';
import { dateLabel, inr, pct } from '../../lib/format';
import { RiskBadge } from '../../components/RiskBadge';
import { SyntheticBadge } from '../../components/FeatureGate';
import { ErrorState, Loading } from '../../components/States';
import { RING_STATUSES, ringNoteRequired, ringStatusLabel } from './ringStatus';

export default function RingDrawer({ ringId, onClose }: { ringId: string; onClose: () => void }) {
  const ring = useRing(ringId);
  const update = useRingStatus(ringId);
  const [status, setStatus] = useState('');
  const [note, setNote] = useState('');
  const [message, setMessage] = useState('');
  const download = async (format: 'pdf' | 'json') => {
    try {
      downloadBlob(await raw.ringReport(ringId, format), `lucen-${ringId}.${format}`);
    } catch (e: any) {
      setMessage(friendlyError(e.code, e.message));
    }
  };
  const save = async () => {
    setMessage('');
    if (!status) return;
    if (ringNoteRequired(status) && !note.trim()) {
      setMessage('A note is required to confirm or dismiss a ring.');
      return;
    }
    try {
      await update.mutateAsync({ status, note: note.trim() });
      setMessage(`Status updated to ${ringStatusLabel(status)}.`);
      setNote('');
      ring.refetch();
    } catch (e: any) {
      setMessage(friendlyError(e.code, e.message));
    }
  };
  return (
    <aside
      role="dialog"
      aria-label={`Ring ${ringId}`}
      className="fixed inset-y-0 right-0 z-40 w-full max-w-xl overflow-y-auto border-l bg-white p-6 shadow-2xl"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="mono text-xs text-muted">{ringId}</div>
          <h2 className="font-display mt-1 text-2xl font-bold">Linked-claims ring</h2>
        </div>
        <button onClick={onClose} aria-label="Close ring details" className="rounded-lg border p-2">
          <X size={16} />
        </button>
      </div>
      {ring.isLoading && <Loading label="Loading ring…" />}
      {ring.error && (
        <ErrorState
          message={friendlyError((ring.error as any).code, (ring.error as any).message)}
          retry={() => ring.refetch()}
        />
      )}
      {ring.data && (
        <div className="mt-5 space-y-5">
          <div className="flex flex-wrap items-center gap-3">
            <RiskBadge band={ring.data.band} />
            <span className="text-sm">Ring score {pct(ring.data.ringScore)}</span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">
              {ringStatusLabel(ring.data.status)}
            </span>
            <SyntheticBadge show={ring.data.synthetic} />
          </div>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <Stat label="Claims" value={ring.data.claimsCount} />
            <Stat label="Claimants" value={ring.data.claimantsCount} />
            <Stat
              label="Total claimed"
              value={
                ring.data.totalClaimedAmount !== undefined ? inr(ring.data.totalClaimedAmount) : '—'
              }
            />
          </div>
          <section>
            <h3 className="font-semibold">Why these claims are linked</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
              {ring.data.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </section>
          <section>
            <h3 className="font-semibold">Claims</h3>
            <div className="mt-2 space-y-2">
              {ring.data.claims.map((c) => (
                <Link
                  key={c.claimId}
                  to={`/app/results/${c.claimId}`}
                  className="flex items-center justify-between rounded-lg border p-3 text-sm hover:bg-slate-50"
                >
                  <span className="mono">{c.claimId}</span>
                  <span className="flex items-center gap-3">
                    {c.amount !== undefined && <span>{inr(c.amount)}</span>}
                    {c.band && <RiskBadge band={c.band} />}
                  </span>
                </Link>
              ))}
              {!ring.data.claims.length && (
                <div className="text-sm text-muted">No claim details.</div>
              )}
            </div>
          </section>
          {!!ring.data.timeline.length && (
            <section>
              <h3 className="font-semibold">Timeline</h3>
              <ol className="mt-2 space-y-2 border-l pl-4 text-sm">
                {ring.data.timeline.map((t, i) => (
                  <li key={i}>
                    <span className="mono text-xs text-muted">{dateLabel(t.date)}</span>
                    <div>{t.event}</div>
                  </li>
                ))}
              </ol>
            </section>
          )}
          <section className="rounded-xl border p-4">
            <h3 className="font-semibold">Investigator status</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {RING_STATUSES.map((s) => (
                <button
                  key={s.value}
                  onClick={() => setStatus(s.value)}
                  aria-pressed={status === s.value}
                  className={`rounded-lg border px-3 py-1.5 text-sm ${status === s.value ? 'bg-ink text-white' : ''}`}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <label className="mt-3 block text-sm">
              <span className="mb-1 block text-muted">
                Note {status && ringNoteRequired(status) ? '(required)' : '(optional)'}
              </span>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="min-h-20 w-full rounded-lg border p-2"
              />
            </label>
            <button
              disabled={!status || update.isPending}
              onClick={save}
              className="mt-3 rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              Save status
            </button>
            {message && <div className="mt-2 text-sm">{message}</div>}
          </section>
          {!!ring.data.audit.length && (
            <section>
              <h3 className="font-semibold">Audit log</h3>
              <div className="mt-2 space-y-1 text-sm">
                {ring.data.audit.map((a, i) => (
                  <div key={i} className="rounded-lg bg-slate-50 p-2">
                    {a.at} · {a.action} · {a.actor}
                    {a.note ? ` · ${a.note}` : ''}
                  </div>
                ))}
              </div>
            </section>
          )}
          <div className="flex gap-2">
            <button onClick={() => download('pdf')} className="rounded-lg border px-3 py-2 text-sm">
              <Download size={14} className="mr-1 inline" />
              Case file PDF
            </button>
            <button
              onClick={() => download('json')}
              className="rounded-lg border px-3 py-2 text-sm"
            >
              JSON
            </button>
          </div>
          <p className="text-xs text-muted">
            Linked claims are context for review, not proof of wrongdoing.
          </p>
        </div>
      )}
    </aside>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
    </div>
  );
}
