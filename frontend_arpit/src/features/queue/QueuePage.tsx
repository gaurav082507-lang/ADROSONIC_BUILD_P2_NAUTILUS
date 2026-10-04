import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Filter } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useQueue } from '../../api/hooks';
import { raw } from '../../api/raw/endpoints';
import { RiskBadge } from '../../components/RiskBadge';
import { Loading, ErrorState, Empty } from '../../components/States';
import { friendlyError } from '../../lib/errorMessages';
import { pct } from '../../lib/format';
export default function QueuePage() {
  const [q, setQ] = useState('');
  const [band, setBand] = useState('');
  const [status, setStatus] = useState('');
  const query = useMemo(
    () => ({
      q: q || undefined,
      band: band || undefined,
      status: status || undefined,
      limit: 50,
      offset: 0,
    }),
    [q, band, status],
  );
  const data = useQueue(query);
  const qc = useQueryClient();
  const [notice, setNotice] = useState('');
  if (data.isLoading) return <Loading label="Loading queue…" />;
  if (data.error)
    return (
      <ErrorState
        message={friendlyError((data.error as any).code, (data.error as any).message)}
        retry={() => data.refetch()}
      />
    );
  const rows = data.data ?? [];
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-sm text-muted">Triage</div>
          <h1 className="font-display mt-1 text-3xl font-bold">Claims queue</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="relative">
            <Filter className="absolute left-3 top-2.5 text-muted" size={16} />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="h-10 w-64 rounded-lg border bg-white pl-9 text-sm"
              placeholder="Search claims"
            />
          </div>
          <select
            value={band}
            onChange={(e) => setBand(e.target.value)}
            className="rounded-lg border px-3 text-sm"
          >
            <option value="">All bands</option>
            <option>LOW</option>
            <option>MEDIUM</option>
            <option>HIGH</option>
          </select>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-lg border px-3 text-sm"
            aria-label="Filter by status"
          >
            <option value="">All statuses</option>
            <option value="submitted">Submitted</option>
            <option value="under_review">Under review</option>
            <option value="needs_evidence">Needs evidence</option>
            <option value="resubmitted">Resubmitted</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>
      {notice && (
        <div className="mt-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">{notice}</div>
      )}
      <div className="card mt-6 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-slate-50 text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-5 py-4">Claim</th>
                <th>Type</th>
                <th>Risk</th>
                <th>Top reason</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b last:border-0">
                  <td className="px-5 py-4">
                    <Link className="font-mono text-signal" to={`/app/results/${r.resultId}`}>
                      {r.id}
                    </Link>
                    <div className="mt-1 text-xs text-muted">{r.claimantMasked}</div>
                  </td>
                  <td>{r.type}</td>
                  <td>
                    <RiskBadge band={r.band} />
                    <span className="ml-2 mono text-xs">{pct(r.risk)}</span>
                  </td>
                  <td>{r.topReason}</td>
                  <td>{r.status}</td>
                  <td>
                    {r.eligibleFastTrack ? (
                      <button
                        onClick={async () => {
                          await raw.fastTrack(r.id);
                          setNotice(`${r.id} fast-tracked.`);
                          qc.invalidateQueries({ queryKey: ['queue'] });
                        }}
                        className="rounded-lg border px-3 py-1.5 text-xs"
                      >
                        Fast-track
                      </button>
                    ) : (
                      <span className="text-xs text-muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {!rows.length && <Empty label="No claims match these filters." />}
    </div>
  );
}
