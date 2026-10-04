import { Link } from 'react-router-dom';
import { useClaimNetwork } from '../../../api/hooks';
import { friendlyError } from '../../../lib/errorMessages';
import { pct } from '../../../lib/format';
import { RiskBadge } from '../../../components/RiskBadge';
import { Empty, ErrorState, Loading } from '../../../components/States';

export default function NetworkTab({ claimId }: { claimId: string }) {
  const q = useClaimNetwork(claimId);
  if (q.isLoading) return <Loading label="Loading linked claims…" />;
  if (q.error)
    return (
      <ErrorState
        message={friendlyError((q.error as any).code, (q.error as any).message)}
        retry={() => q.refetch()}
      />
    );
  const data = q.data!;
  if (!data.rings.length && !data.sharedIdentifiers.length && !data.evidence.length)
    return <Empty label="No links to other claims were found." />;
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="card p-5">
        <h2 className="font-display font-semibold">Rings</h2>
        <div className="mt-3 space-y-2">
          {data.rings.map((r) => (
            <div
              key={r.ringId}
              className="flex items-center justify-between rounded-lg border p-3 text-sm"
            >
              <span className="mono">{r.ringId}</span>
              <span className="flex items-center gap-3">
                score {pct(r.ringScore)}
                {r.band && <RiskBadge band={r.band} />}
              </span>
            </div>
          ))}
          {!data.rings.length && (
            <div className="text-sm text-muted">Not part of a detected ring.</div>
          )}
        </div>
        <h3 className="mt-5 font-semibold">Shared identifiers</h3>
        <div className="mt-2 space-y-2">
          {data.sharedIdentifiers.map((s) => (
            <div
              key={`${s.type}-${s.label}`}
              className="flex justify-between rounded-lg bg-slate-50 p-3 text-sm"
            >
              <span>{s.label}</span>
              <span className="text-muted">
                also on {s.otherClaims} other claim{s.otherClaims === 1 ? '' : 's'}
              </span>
            </div>
          ))}
          {!data.sharedIdentifiers.length && <div className="text-sm text-muted">None.</div>}
        </div>
        <Link to="/app/network" className="mt-5 inline-block rounded-lg border px-3 py-2 text-sm">
          Open in network
        </Link>
      </div>
      <div className="card p-5">
        <h2 className="font-display font-semibold">Network evidence</h2>
        <p className="mt-1 text-xs text-muted">
          Context for review: network evidence is capped and never makes a claim HIGH on its own.
        </p>
        <div className="mt-3 space-y-2">
          {data.evidence.map((e) => (
            <div key={e.id} className="rounded-lg border p-3 text-sm">
              <div className="flex justify-between">
                <span className="font-medium">{e.title}</span>
                <span className="mono text-xs text-muted">{e.id}</span>
              </div>
              <p className="mt-1 text-muted">{e.reason}</p>
            </div>
          ))}
          {!data.evidence.length && <div className="text-sm text-muted">No network evidence.</div>}
        </div>
      </div>
    </div>
  );
}
