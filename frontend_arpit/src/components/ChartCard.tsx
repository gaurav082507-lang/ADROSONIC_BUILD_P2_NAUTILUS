import { useState, type ReactNode } from 'react';

/** Every chart carries a one-line text summary and a table alternative (accessibility). */
export function ChartCard({
  title,
  summary,
  columns,
  rows,
  children,
}: {
  title: string;
  summary: string;
  columns: string[];
  rows: (string | number)[][];
  children: ReactNode;
}) {
  const [table, setTable] = useState(false);
  return (
    <section className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-display font-semibold">{title}</h2>
          <p className="mt-1 text-sm text-muted">{summary}</p>
        </div>
        <button
          onClick={() => setTable((x) => !x)}
          className="shrink-0 rounded-lg border px-2.5 py-1 text-xs"
          aria-pressed={table}
        >
          {table ? 'Chart' : 'Table'}
        </button>
      </div>
      <div className="mt-4">
        {table ? (
          <div className="max-h-72 overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-slate-50 text-xs uppercase text-muted">
                <tr>
                  {columns.map((c) => (
                    <th key={c} className="px-2 py-1.5">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} className="border-b">
                    {r.map((cell, j) => (
                      <td key={j} className="mono px-2 py-1.5 text-xs">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="h-64">{children}</div>
        )}
      </div>
    </section>
  );
}
