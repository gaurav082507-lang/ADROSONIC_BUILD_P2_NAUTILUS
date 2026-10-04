import type { ResultVM } from '../../../types/vm';
export default function ClaimChecksTab({ result }: { result: ResultVM }) {
  return (
    <div className="card p-5">
      {result.claimChecks?.length ? (
        <div className="space-y-3">
          {result.claimChecks.map((x) => (
            <div key={x.name} className="rounded-lg border p-4">
              <div className="flex justify-between">
                <span className="font-medium">{x.name}</span>
                <span className="text-xs font-semibold uppercase">{x.status}</span>
              </div>
              <p className="mt-1 text-sm text-muted">{x.reason ?? 'No reason returned.'}</p>
            </div>
          ))}
        </div>
      ) : (
        <span className="text-sm text-muted">Not analysed</span>
      )}
    </div>
  );
}
