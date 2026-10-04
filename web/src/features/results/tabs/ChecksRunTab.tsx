import type { ResultVM } from '../../../types/vm';
export default function ChecksRunTab({ result }: { result: ResultVM }) {
  return (
    <div className="card p-5">
      <div className="space-y-2">
        {result.checksRun.map((item) => (
          <div
            key={item.detector}
            className="flex items-center justify-between rounded-lg border p-3 text-sm"
          >
            <div>
              <div className="font-medium">{item.detector}</div>
              <div className="text-xs text-muted">
                {item.reason ?? 'No additional reason returned.'}
              </div>
            </div>
            <div className="text-right">
              <div className="font-semibold uppercase">{item.status}</div>
              <div className="text-xs text-muted">{item.durationMs ?? '—'} ms</div>
            </div>
          </div>
        ))}
        {!result.checksRun.length && <div className="text-sm text-muted">Not analysed</div>}
      </div>
    </div>
  );
}
