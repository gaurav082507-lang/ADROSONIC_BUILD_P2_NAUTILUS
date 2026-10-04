import type { ResultVM } from '../../../types/vm';
import { useResultTimeline } from '../../../api/hooks';
import { dateLabel } from '../../../lib/format';
import { Loading } from '../../../components/States';

/** Timeline comes from GET /results/{id}/timeline; an inline result.timeline is used if present. */
export default function TimelineTab({ result }: { result: ResultVM }) {
  const inline = result.timeline;
  const q = useResultTimeline(result.id, !inline?.length);
  if (!inline?.length && q.isLoading) return <Loading label="Loading timeline…" />;
  const rows = inline?.length ? inline : (q.data ?? []);
  const dated = rows.filter((x) => x.date && !x.contradiction);
  const contradictions = rows.filter((x) => x.contradiction);
  const undated = rows.filter((x) => !x.date && !x.contradiction);
  return (
    <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
      <div className="card p-6">
        <h3 className="font-display font-semibold">Evidence timeline</h3>
        <div className="mt-5 space-y-5 border-l pl-6">
          {dated.map((x, i) => (
            <div key={`${x.title}-${i}`} className="relative">
              <span className="absolute -left-[31px] top-1 h-3 w-3 rounded-full bg-ink" />
              <div className="mono text-xs text-muted">{dateLabel(x.date!)}</div>
              <div className="font-semibold">{x.title}</div>
              {x.detail && <div className="text-sm text-muted">{x.detail}</div>}
            </div>
          ))}
          {!dated.length && <div className="text-sm text-muted">No dated events.</div>}
        </div>
        {!!undated.length && (
          <div className="mt-6">
            <div className="text-xs uppercase tracking-wide text-muted">Undated</div>
            <ul className="mt-2 list-disc pl-5 text-sm">
              {undated.map((x, i) => (
                <li key={i}>
                  {x.title}
                  {x.detail ? ` · ${x.detail}` : ''}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <div className="card p-6">
        <h3 className="font-display font-semibold">Contradictions ({contradictions.length})</h3>
        <div className="mt-4 space-y-3">
          {contradictions.map((x, i) => (
            <div key={i} className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm">
              <div className="font-semibold text-red-800">{x.title}</div>
              <div className="mt-1 text-red-900">{x.detail}</div>
            </div>
          ))}
          {!contradictions.length && <div className="text-sm text-muted">None found.</div>}
        </div>
      </div>
    </div>
  );
}
