import { Link } from 'react-router-dom';
import { Line, LineChart, ResponsiveContainer } from 'recharts';
import { useAnalyticsSummary, useHistory, useQueue } from '../../api/hooks';
import { isFeatureOn } from '../../lib/featureFlags';
import { Loading, ErrorState } from '../../components/States';
import { RiskBadge } from '../../components/RiskBadge';
import { pct } from '../../lib/format';
import { friendlyError } from '../../lib/errorMessages';
export default function DashboardPage() {
  const q = useQueue({ limit: 50 });
  const h = useHistory({ page: 1, pageSize: 50 });
  const analyticsOn = isFeatureOn('analytics');
  const summary = useAnalyticsSummary(analyticsOn);
  if (q.isLoading || h.isLoading) return <Loading />;
  if (q.error)
    return (
      <ErrorState
        message={friendlyError((q.error as any).code, (q.error as any).message)}
        retry={() => q.refetch()}
      />
    );
  const rows = q.data ?? [];
  const flagged = rows.filter((x) => x.band !== 'LOW');
  const avg = rows.length ? rows.reduce((a, b) => a + b.risk, 0) / rows.length : 0;
  return (
    <div>
      <div className="flex items-end justify-between">
        <div>
          <div className="text-sm text-muted">Investigator console</div>
          <h1 className="font-display mt-1 text-3xl font-bold">Good afternoon, Priya.</h1>
          <p className="mt-2 text-sm text-muted">Based on recent claims.</p>
        </div>
        <Link
          to="/app/analyze"
          className="rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-white"
        >
          New analysis
        </Link>
      </div>
      <div className="mt-7 grid gap-4 md:grid-cols-4">
        {(summary.data
          ? [
              ['Claims today', summary.data.claimsToday, 'All channels'],
              ['Fast-tracked', summary.data.fastTracked, 'Today'],
              ['Flagged', summary.data.flagged, `${pct(summary.data.flaggedRate)} of claims`],
              ['Open rings', summary.data.openRings ?? '—', 'Linked-claims network'],
            ]
          : [
              ['Claims loaded', rows.length, 'Recent claims'],
              [
                'Fast-track eligible',
                rows.filter((x) => x.eligibleFastTrack).length,
                'Recent claims',
              ],
              ['Flagged', flagged.length, 'Recent claims'],
              ['Average risk', pct(avg), 'Recent claims'],
            ]
        ).map(([label, value, note]) => (
          <div className="card p-5" key={String(label)}>
            <div className="text-sm text-muted">{label}</div>
            <div className="mt-2 font-display text-3xl font-bold">{value}</div>
            <div className="mt-1 text-xs text-muted">{note}</div>
          </div>
        ))}
      </div>
      {summary.data && (
        <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_1.4fr]">
          <div className="card p-5">
            <div className="text-sm text-muted">Claims, last 7 days</div>
            <div
              className="mt-3 h-20"
              aria-label={`Daily claims: ${summary.data.sparkline.join(', ')}`}
            >
              <ResponsiveContainer>
                <LineChart data={summary.data.sparkline.map((v, i) => ({ i, v }))}>
                  <Line dataKey="v" stroke="#3B82F6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="card p-5">
            <div className="text-sm text-muted">Top reasons today</div>
            <div className="mt-3 space-y-2">
              {summary.data.topReasons.map((r) => (
                <div key={r.id} className="flex justify-between text-sm">
                  <span>
                    {r.title} <span className="mono text-xs text-muted">{r.id}</span>
                  </span>
                  <span className="mono">{r.count}</span>
                </div>
              ))}
              {!summary.data.topReasons.length && (
                <div className="text-sm text-muted">No flags today.</div>
              )}
            </div>
          </div>
        </div>
      )}
      <div className="mt-6 grid gap-5 lg:grid-cols-[1.4fr_.8fr]">
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold">Needs attention</h2>
            <Link to="/app/queue" className="text-sm text-signal">
              View queue
            </Link>
          </div>
          <div className="mt-4 space-y-2">
            {flagged.slice(0, 5).map((x) => (
              <Link
                to={`/app/results/${x.id}`}
                key={x.id}
                className="flex items-center justify-between rounded-lg border p-4 hover:bg-slate-50"
              >
                <div>
                  <div className="mono text-xs text-muted">{x.id}</div>
                  <div className="mt-1 font-medium">{x.topReason}</div>
                </div>
                <RiskBadge band={x.band} />
              </Link>
            ))}
            {!flagged.length && <div className="text-sm text-muted">No flagged recent claims.</div>}
          </div>
        </div>
        <div className="card p-5">
          <h2 className="font-display text-lg font-semibold">Recent history</h2>
          <div className="mt-4 space-y-3">
            {(h.data ?? []).slice(0, 4).map((x) => (
              <div key={x.id} className="flex items-center justify-between border-b pb-3 text-sm">
                <span>{x.mode}</span>
                <RiskBadge band={x.band} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
