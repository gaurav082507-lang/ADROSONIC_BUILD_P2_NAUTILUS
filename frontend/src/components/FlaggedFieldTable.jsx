import React from 'react';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';

const SEVERITY_ICONS = {
  high: <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />,
  medium: <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />,
  low: <Info className="w-4 h-4 text-blue-500 shrink-0" />,
};

export function FlaggedFieldTable({ evidence = [] }) {
  const flagged = evidence.filter(e => e.field || (e.details && (e.details.expected || e.details.found)));

  if (flagged.length === 0) {
    return (
      <div className="p-4 rounded-lg border border-rule bg-surface text-sm text-muted text-center">
        No specific document fields flagged with mathematical or font discrepancies.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-rule bg-surface shadow-sm">
      <table className="w-full text-left text-sm text-ink">
        <thead className="bg-paper text-xs uppercase text-muted border-b border-rule">
          <tr>
            <th className="px-4 py-3">Severity</th>
            <th className="px-4 py-3">Field</th>
            <th className="px-4 py-3">Observed Value</th>
            <th className="px-4 py-3">Expected Value</th>
            <th className="px-4 py-3">Finding</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {flagged.map((item, idx) => {
            const sev = (item.severity || 'medium').toLowerCase();
            const d = item.details || {};
            const observed = d.found !== undefined ? String(d.found) : (d.doc !== undefined ? String(d.doc) : '-');
            const expected = d.expected !== undefined ? String(d.expected) : (d.claimed !== undefined ? String(d.claimed) : '-');

            return (
              <tr key={idx} className="hover:bg-paper/50 transition-colors">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5 font-medium capitalize">
                    {SEVERITY_ICONS[sev] || SEVERITY_ICONS.medium}
                    <span className="text-xs">{sev}</span>
                  </div>
                </td>
                <td className="px-4 py-3 font-mono text-xs font-semibold">
                  {item.field || item.id}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-red-600">
                  {observed}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-green-700">
                  {expected}
                </td>
                <td className="px-4 py-3 text-xs text-muted max-w-xs">
                  {item.reason || item.title}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
