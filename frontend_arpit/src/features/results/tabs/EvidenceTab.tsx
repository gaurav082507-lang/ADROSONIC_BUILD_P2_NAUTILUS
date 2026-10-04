import type { ResultVM } from '../../../types/vm';
export default function EvidenceTab({ result }: { result: ResultVM }) {
  const evidence = [...result.evidence].sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999));
  const drivers = evidence.filter((item) => item.kind !== 'info');
  const context = evidence.filter((item) => item.kind === 'info');
  return (
    <div className="space-y-5">
      <div className="card p-5">
        <h3 className="font-display font-semibold">Evidence drivers</h3>
        <div className="mt-4 space-y-3">
          {drivers.map((item, index) => (
            <div key={item.id} className="rounded-xl border p-4">
              <div className="flex justify-between gap-4">
                <div>
                  <span className="mr-2 inline-flex h-7 w-7 items-center justify-center rounded-full bg-yellow-100 text-xs font-bold">
                    {index + 1}
                  </span>
                  <span className="font-semibold">{item.title}</span>
                  <span className="mono ml-2 text-xs text-muted">{item.id}</span>
                </div>
                <span className="mono text-xs">
                  {Math.round(item.contributionPct ?? 0)}% of risk
                </span>
              </div>
              <p className="mt-2 text-sm text-muted">{item.reason}</p>
              <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-muted">
                <span className="capitalize">Severity: {item.severity}</span>
                {item.score !== undefined && (
                  <span className="flex items-center gap-2">
                    Score
                    <span className="inline-block h-1.5 w-24 overflow-hidden rounded bg-slate-200">
                      <span
                        className="block h-full bg-ink"
                        style={{ width: `${Math.round(item.score * 100)}%` }}
                      />
                    </span>
                    {Math.round(item.score * 100)}%
                  </span>
                )}
                {item.weight !== undefined && <span>Weight {item.weight.toFixed(2)}</span>}
              </div>
            </div>
          ))}
          {!drivers.length && <div className="text-sm text-muted">Not analysed</div>}
        </div>
      </div>
      {context.length > 0 && (
        <div className="card p-5">
          <h3 className="font-display font-semibold">Supporting context</h3>
          <div className="mt-3 space-y-2">
            {context.map((item) => (
              <div key={item.id} className="rounded-lg bg-slate-50 p-3 text-sm">
                <b>{item.title}</b> <span className="mono text-xs text-muted">{item.id}</span>
                <div className="text-muted">{item.reason}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
