import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useHistory } from '../../api/hooks';
import { Loading, ErrorState, Empty } from '../../components/States';
import { RiskBadge } from '../../components/RiskBadge';
import { friendlyError } from '../../lib/errorMessages';
import { dateLabel, pct } from '../../lib/format';
export default function HistoryPage() {
  const [band, setBand] = useState('');
  const query = useMemo(() => ({ page: 1, pageSize: 50, band: band || undefined }), [band]);
  const q = useHistory(query);
  if (q.isLoading) return <Loading />;
  if (q.error)
    return (
      <ErrorState
        message={friendlyError((q.error as any).code, (q.error as any).message)}
        retry={() => q.refetch()}
      />
    );
  const rows = q.data ?? [];
  return (
    <div>
      <div className="flex items-end justify-between">
        <div>
          <div className="text-sm text-muted">Archive</div>
          <h1 className="font-display mt-1 text-3xl font-bold">Analysis history</h1>
        </div>
        <select
          value={band}
          onChange={(e) => setBand(e.target.value)}
          className="rounded-lg border px-3 py-2 text-sm"
        >
          <option value="">All bands</option>
          <option>LOW</option>
          <option>MEDIUM</option>
          <option>HIGH</option>
        </select>
      </div>
      <div className="card mt-6 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-bg text-xs uppercase text-muted">
            <tr>
              <th className="px-5 py-4">Date</th>
              <th>Result</th>
              <th>Mode</th>
              <th>Top reason</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b">
                <td className="px-5 py-4">{dateLabel(r.date)}</td>
                <td>
                  <Link to={`/app/results/${r.id}`} className="font-mono text-signal">
                    {r.id}
                  </Link>
                </td>
                <td className="capitalize">{r.mode}</td>
                <td className="max-w-xs truncate">
                  {r.topReason ?? (r.fileNames.join(', ') || '—')}
                </td>
                <td>
                  <RiskBadge band={r.band} />
                  <span className="ml-2 text-xs">{pct(r.risk)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!rows.length && <Empty label="No analysis history yet." />}
    </div>
  );
}
