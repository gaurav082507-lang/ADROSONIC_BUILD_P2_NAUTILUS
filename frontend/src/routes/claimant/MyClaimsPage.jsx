import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useI18n } from '../../i18n/I18nContext';
import { getMyClaimsApi } from '../../api/auth';

const STATUS_COLORS = {
  submitted: '#f59e0b',
  under_review: '#38bdf8',
  needs_evidence: '#fb923c',
  approved: '#34d399',
  rejected: '#94a3b8',
  closed: '#64748b',
};

export default function MyClaimsPage() {
  const { t } = useI18n();
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getMyClaimsApi()
      .then(data => setClaims(Array.isArray(data) ? data : data?.claims || []))
      .catch(() => setError(t('error')))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={styles.muted}>{t('loading')}</p>;
  if (error)   return <p style={styles.err}>{error}</p>;

  return (
    <div>
      <div style={styles.titleRow}>
        <h2 style={styles.h2}>{t('myClaimsTitle')}</h2>
        <Link to="/claim/new" style={styles.newBtn}>{t('newClaimBtn')}</Link>
      </div>

      {claims.length === 0 ? (
        <p style={styles.muted}>{t('noClaimsYet')}</p>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr>
              {[t('claimId'), t('policyLabel'), t('claimType'), t('claimedAmount'), t('status'), t('submittedAt'), ''].map(h => (
                <th key={h} style={styles.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {claims.map(c => (
              <tr key={c.claim_id} style={styles.tr}>
                <td style={styles.td}><code style={styles.code}>{c.claim_id}</code></td>
                <td style={styles.td}>{c.policy_label || t('na')}</td>
                <td style={styles.td}>{c.claim_type}</td>
                <td style={styles.td}>—</td>
                <td style={styles.td}>
                  <span style={{ ...styles.badge, background: STATUS_COLORS[c.status] || '#334155' }}>
                    {t(c.status) || c.status}
                  </span>
                </td>
                <td style={styles.td}>{c.submitted_at ? c.submitted_at.slice(0, 10) : t('na')}</td>
                <td style={styles.td}>
                  <Link to={`/claim/${c.claim_id}`} style={styles.viewLink}>{t('viewDetails')}</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const styles = {
  titleRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 },
  h2: { color: '#e2e8f0', margin: 0, fontSize: 20, fontWeight: 700 },
  newBtn: { background: '#38bdf8', color: '#0f172a', borderRadius: 7, padding: '8px 16px', textDecoration: 'none', fontWeight: 600, fontSize: 13 },
  muted: { color: '#64748b', fontSize: 14 },
  err: { color: '#f87171', fontSize: 14 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: '8px 10px', color: '#64748b', borderBottom: '1px solid #334155' },
  tr: { borderBottom: '1px solid #1e293b' },
  td: { padding: '10px 10px', color: '#cbd5e1', verticalAlign: 'middle' },
  code: { fontFamily: 'monospace', fontSize: 11, color: '#94a3b8', background: '#0f172a', padding: '2px 5px', borderRadius: 4 },
  badge: { borderRadius: 12, padding: '2px 10px', fontSize: 11, color: '#0f172a', fontWeight: 600 },
  viewLink: { color: '#38bdf8', textDecoration: 'none', fontSize: 12 },
};
