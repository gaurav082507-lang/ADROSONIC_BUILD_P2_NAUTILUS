import type { Band } from '../types/vm';
import { RiskBadge } from './RiskBadge';
import { pct } from '../lib/format';
export function ScoreGauge({ label, risk, band }: { label: string; risk: number; band: Band }) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-semibold">{label}</div>
        <RiskBadge band={band} />
      </div>
      <div className="mt-3 font-display text-4xl font-bold">{pct(risk)}</div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-nile-soft">
        <div
          className="h-full rounded-full bg-primary-dark"
          style={{ width: `${Math.round(risk * 100)}%` }}
        />
      </div>
    </div>
  );
}
