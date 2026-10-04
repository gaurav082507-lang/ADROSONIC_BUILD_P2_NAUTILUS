import { AlertTriangle, CheckCircle2, OctagonAlert } from 'lucide-react';
import type { Band } from '../types/vm';
const map = {
  LOW: { icon: CheckCircle2, cls: 'risk-low' },
  MEDIUM: { icon: AlertTriangle, cls: 'risk-medium' },
  HIGH: { icon: OctagonAlert, cls: 'risk-high' },
} as const;
export function RiskBadge({ band }: { band: Band }) {
  const x = map[band];
  const Icon = x.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${x.cls}`}
    >
      <Icon size={14} />
      {band}
    </span>
  );
}
