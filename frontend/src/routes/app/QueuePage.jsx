import React, { useEffect, useState } from 'react';
import { getQueueApi } from '../../api/auth';

const RISK_COLORS = { HIGH: '#f87171', MEDIUM: '#fb923c', LOW: '#34d399' };
const STATUS_COLORS = { submitted: '#f59e0b', under_review: '#38bdf8', needs_evidence: '#fb923c', approved: '#34d399', rejected: '#94a3b8', closed: '#64748b' };

export default function QueuePage() {
  const [items, setItems]   = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getQueueApi()
      .then(d => setItems(d?.items || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={s.muted}>Loading queue…</p>;

  return (
    <div>
      <h2 style={s.h2}>Claim Queue <span style={s.count}>{items.length}</span></h2>

      {items.length === 0 ? (
        <p style={s.muted}>No open claims in queue.</p>
      ) : (
        <table style={s.table}>
          <thead>
            <tr>
              {['Claim ID', 'Claimant', 'Type', 'Amount', 'Status', 'Risk Band', 'Submitted', 'Top Reason'].map(h => (
                <th key={h} style={s.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.claim_id} style={s.tr}>
                <td style={s.td}><code style={s.code}>{item.claim_id}</code></td>
                <td style={s.td}>{item.claimant_name}</td>
                <td style={s.td}>{item.type}</td>
                <td style={s.td}>—</td>
                <td style={s.td}>
                  <span style={{ ...s.badge, background: STATUS_COLORS[item.status] || '#334155' }}>
                    {item.status}
                  </span>
                </td>
                <td style={s.td}>
                  {item.band ? (
                    <span style={{ ...s.badge, background: RISK_COLORS[item.band] || '#334155' }}>
                      {item.band}
                    </span>
                  ) : <span style={s.muted}>—</span>}
                </td>
                <td style={s.td}>{item.submitted_at?.slice(0, 10) || '—'}</td>
                <td style={s.td}>
                  <span style={{ color: '#94a3b8', fontSize: 11 }}>{item.top_reason}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const s = {
  h2: { color: '#e2e8f0', margin: '0 0 20px', fontSize: 20, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 10 },
  count: { background: '#334155', color: '#94a3b8', borderRadius: 12, padding: '2px 10px', fontSize: 13 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: { textAlign: 'left', padding: '8px 10px', color: '#64748b', borderBottom: '1px solid #334155', fontWeight: 600 },
  tr: { borderBottom: '1px solid #1e293b' },
  td: { padding: '10px 10px', color: '#cbd5e1', verticalAlign: 'middle' },
  badge: { borderRadius: 12, padding: '2px 10px', fontSize: 11, color: '#0f172a', fontWeight: 600 },
  code: { fontFamily: 'monospace', fontSize: 10, color: '#94a3b8', background: '#0f172a', padding: '2px 5px', borderRadius: 4 },
  link: { color: '#38bdf8', textDecoration: 'none', fontSize: 12 },
  muted: { color: '#64748b', fontSize: 13 },
};
