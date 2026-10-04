import type { ResultVM } from '../../../types/vm';

/** Displays backend-provided contributions and formulas. The UI never recomputes the score. */
export default function WhyThisScoreTab({ result }: { result: ResultVM }) {
  const { formulas, overrides, gates } = result.whyDetail;
  return (
    <div className="space-y-5">
      <div className="card p-5">
        <p className="text-sm text-muted">
          Each detector pushes risk by w × p (weight × calibrated score). They combine with
          noisy-OR: risk = 1 − Π(1 − w·p).
        </p>
        <div className="mt-5 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-xs uppercase text-muted">
                <th className="py-3">Pipeline</th>
                <th>Evidence</th>
                <th className="text-right">w</th>
                <th className="text-right">p</th>
                <th className="text-right">w·p</th>
                <th className="text-right">Contribution</th>
              </tr>
            </thead>
            <tbody>
              {result.whyThisScore.map((item, i) => (
                <tr key={`${item.pipeline}-${item.evidenceId}-${i}`} className="border-b">
                  <td className="py-3 capitalize">{item.pipeline}</td>
                  <td>
                    {item.title ?? '—'}{' '}
                    {item.evidenceId && (
                      <span className="mono text-xs text-muted">{item.evidenceId}</span>
                    )}
                  </td>
                  <td className="mono text-right">{item.w.toFixed(2)}</td>
                  <td className="mono text-right">{item.p.toFixed(2)}</td>
                  <td className="mono text-right">{item.push.toFixed(3)}</td>
                  <td className="mono text-right">{Math.round(item.contributionPct)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!result.whyThisScore.length && <div className="mt-4 text-sm text-muted">Not analysed</div>}
      </div>
      {!!formulas.length && (
        <div className="card p-5">
          <h3 className="font-display font-semibold">Formulas with the real numbers</h3>
          <div className="mt-3 space-y-2">
            {formulas.map((f) => (
              <div key={f.pipeline} className="rounded-lg bg-slate-50 p-3 text-sm">
                <span className="font-semibold capitalize">{f.pipeline}: </span>
                <span className="mono">{f.formula}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {(!!overrides.length || !!gates.length) && (
        <div className="grid gap-5 lg:grid-cols-2">
          <div className="card p-5">
            <h3 className="font-display font-semibold">Override rules applied</h3>
            <ul className="mt-3 list-disc pl-5 text-sm">
              {overrides.map((o) => (
                <li key={o}>{o}</li>
              ))}
            </ul>
            {!overrides.length && <div className="mt-3 text-sm text-muted">None.</div>}
          </div>
          <div className="card p-5">
            <h3 className="font-display font-semibold">Quality gates applied</h3>
            <ul className="mt-3 space-y-1 text-sm">
              {gates.map((g, i) => (
                <li key={i}>
                  <span className="font-medium">{g.detector}</span> × {g.factor} – {g.reason}
                </li>
              ))}
            </ul>
            {!gates.length && <div className="mt-3 text-sm text-muted">None.</div>}
          </div>
        </div>
      )}
    </div>
  );
}
