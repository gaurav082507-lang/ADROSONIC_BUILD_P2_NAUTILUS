import type { ResultVM } from '../../../types/vm';
import { inr, pct } from '../../../lib/format';
import { RiskBadge } from '../../../components/RiskBadge';
import { Empty } from '../../../components/States';

export default function VoiceTab({ result }: { result: ResultVM }) {
  const v = result.voiceDetails;
  if (!v) return <Empty label="No voice statement was submitted." />;
  const e = v.extracted;
  return (
    <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
      <div className="card p-5">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-semibold">Statement</h2>
          <span className="text-xs text-muted">
            {v.language?.toUpperCase() ?? '—'}
            {v.durationS != null && ` · ${v.durationS.toFixed(1)} s`}
          </span>
        </div>
        <div className="mt-3 text-xs uppercase text-muted">Original transcript</div>
        <p className="mt-1 rounded-lg bg-bg p-3 text-sm">
          {v.transcript || 'Transcription unavailable.'}
        </p>
        <div className="mt-4 text-xs uppercase text-muted">English translation</div>
        <p className="mt-1 rounded-lg bg-bg p-3 text-sm">{v.translationEn || '—'}</p>
        {v.status && v.status !== 'analysed' && (
          <p className="mt-3 text-xs text-muted">Status: {v.status}</p>
        )}
      </div>
      <div className="space-y-5">
        <div className="card p-5">
          <h2 className="font-display font-semibold">Synthetic-voice check</h2>
          {v.spoof?.probability != null ? (
            <div className="mt-3 flex items-center gap-3">
              {v.spoof.band && <RiskBadge band={v.spoof.band} />}
              <span className="text-sm">
                {pct(v.spoof.probability)} likelihood of synthetic speech
              </span>
            </div>
          ) : (
            <p className="mt-3 text-sm text-muted">Not available.</p>
          )}
          {!!v.spoof?.segments.length && (
            <ul className="mt-3 space-y-1 text-xs text-muted">
              {v.spoof.segments.map((s, i) => (
                <li key={i}>
                  {s.startS != null ? s.startS.toFixed(1) : '?'}–{s.endS != null ? s.endS.toFixed(1) : '?'} s
                  {s.score != null && ` · ${pct(s.score)}`}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="card p-5">
          <h2 className="font-display font-semibold">Extracted from speech</h2>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted">Date</dt>
            <dd>{e.incidentDate ?? '—'}</dd>
            <dt className="text-muted">Time</dt>
            <dd>{e.incidentTime ?? '—'}</dd>
            <dt className="text-muted">Amount</dt>
            <dd>{e.amount != null ? inr(e.amount) : '—'}</dd>
            <dt className="text-muted">Place</dt>
            <dd>{e.locationText ?? '—'}</dd>
            <dt className="text-muted">Items</dt>
            <dd>{e.damagedItems.join(', ') || '—'}</dd>
          </dl>
        </div>
      </div>
    </div>
  );
}
