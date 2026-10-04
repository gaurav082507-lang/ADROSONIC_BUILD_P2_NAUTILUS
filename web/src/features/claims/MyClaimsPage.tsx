import { Link } from 'react-router-dom';
import { useClaimsMine } from '../../api/hooks';
import { dateLabel } from '../../lib/format';
import { Loading, ErrorState, Empty } from '../../components/States';
import en from '../../i18n/en.json';
export default function MyClaimsPage() {
  const q = useClaimsMine();
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState message={en.claimsLoadError} retry={() => q.refetch()} />;
  const rows = q.data ?? [];
  return (
    <div className="min-h-screen bg-slate-50">
      <main className="mx-auto max-w-3xl px-5 py-8">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-muted">Lucen AI</div>
            <h1 className="font-display mt-1 text-3xl font-bold">{en.myClaims}</h1>
          </div>
          <Link
            to="/claim/new"
            className="rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-white"
          >
            {en.start}
          </Link>
        </div>
        <div className="mt-6 space-y-3">
          {rows.map((row: any) => (
            <Link
              key={row.id}
              to={`/claim/${row.id}`}
              className="block rounded-xl border bg-white p-5"
            >
              <div className="font-mono text-xs text-muted">{row.id}</div>
              <div className="mt-1 font-semibold capitalize">
                {String(row.status).replaceAll('_', ' ')}
              </div>
              <div className="mt-1 text-sm text-muted">
                {row.policyLabel ? `${row.policyLabel} · ` : ''}
                {row.claimType} · {dateLabel(row.submittedAt)}
              </div>
            </Link>
          ))}
          {!rows.length && <Empty label={en.noClaims} />}
        </div>
      </main>
    </div>
  );
}
