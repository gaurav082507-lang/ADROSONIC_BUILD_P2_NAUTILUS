import { useState } from 'react';
import BoxOverlay from '../../../components/BoxOverlay';
import type { ResultVM } from '../../../types/vm';

export default function DocumentTab({ result }: { result: ResultVM }) {
  const [page, setPage] = useState(0);
  const [active, setActive] = useState<string>();
  const pages = result.artifacts.pages;
  const current = pages[page];
  if (!current) return <div className="card p-8 text-sm text-muted">Not analysed</div>;
  const fields = result.evidence.filter((item) => item.pipeline === 'document' && item.field);
  return (
    <div className="grid gap-5 lg:grid-cols-[1.4fr_.8fr]">
      <div className="card p-5">
        <div className="flex items-center justify-between">
          <button
            disabled={page === 0}
            onClick={() => setPage((x) => x - 1)}
            className="rounded-lg border px-3 py-2 text-sm disabled:opacity-30"
          >
            Previous
          </button>
          <span className="text-sm text-muted">Page {current.page}</span>
          <button
            disabled={page === pages.length - 1}
            onClick={() => setPage((x) => x + 1)}
            className="rounded-lg border px-3 py-2 text-sm disabled:opacity-30"
          >
            Next
          </button>
        </div>
        <div className="relative mt-5 overflow-auto rounded-xl bg-slate-100">
          <img
            src={current.imageUrl}
            alt={`Document page ${current.page}`}
            className="mx-auto max-w-full"
          />
          <BoxOverlay
            evidence={result.evidence.filter(
              (x) => x.page === current.page || x.bbox?.page === current.page,
            )}
            onHover={setActive}
            activeId={active}
          />
        </div>
      </div>
      <div className="card p-5">
        <h3 className="font-display font-semibold">Flagged fields</h3>
        <div className="mt-4 space-y-2">
          {fields.map((item) => (
            <button
              key={item.id}
              onMouseEnter={() => setActive(item.id)}
              onFocus={() => setActive(item.id)}
              className={`w-full rounded-lg border p-3 text-left ${active === item.id ? 'border-yellow-300 bg-yellow-50' : 'border-border'}`}
            >
              <div className="font-medium">{item.field}</div>
              <div className="mt-1 text-xs text-muted">{item.reason}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
