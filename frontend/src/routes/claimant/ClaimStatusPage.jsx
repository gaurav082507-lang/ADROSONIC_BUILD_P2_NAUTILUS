import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useI18n } from '../../i18n/I18nContext';
import { getClaimStatusApi, getClaimEvidenceTimelineApi } from '../../api/auth';
import { fetchClient } from '../../api/client';

const STATUS_COLORS = {
  submitted: '#f59e0b',
  under_review: '#38bdf8',
  needs_evidence: '#fb923c',
  approved: '#34d399',
  rejected: '#94a3b8',
  closed: '#64748b',
};

export default function ClaimStatusPage() {
  const { id } = useParams();
  const { t } = useI18n();
  const [status, setStatus]     = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [files, setFiles]       = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitMsg, setSubmitMsg]   = useState('');

  useEffect(() => {
    Promise.all([
      getClaimStatusApi(id),
      getClaimEvidenceTimelineApi(id).catch(() => ({ timeline: [] }))
    ])
      .then(([s, tl]) => {
        setStatus(s);
        setTimeline(tl?.timeline || []);
      })
      .catch(() => setError(t('error')))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleResubmit(e) {
    e.preventDefault();
    if (!files.length) return;
    setSubmitting(true);
    setSubmitMsg('');
    const fd = new FormData();
    for (const f of files) fd.append('evidence', f);
    try {
      await fetchClient(`/claims/${id}/resubmit`, { method: 'POST', body: fd });
      setSubmitMsg(t('resubmitSuccess'));
      setFiles([]);
      // Re-fetch status
      const s = await getClaimStatusApi(id);
      setStatus(s);
    } catch {
      setSubmitMsg(t('error'));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <p style={styles.muted}>{t('loading')}</p>;
  if (error)   return <p style={styles.err}>{error}</p>;
  if (!status) return null;

  // ClaimantStatusResponse: { claim_id, status, timeline, decision }
  const claimId  = status.claim_id;
  const claimStatus = status.status;
  const needsEvidence = claimStatus === 'needs_evidence';
  const decisionData  = status.decision;

  return (
    <div>
      <Link to="/claims/mine" style={styles.backLink}>← {t('myClaimsNav')}</Link>

      <div style={styles.card}>
        <div style={styles.cardTop}>
          <div>
            <h2 style={styles.h2}>{t('claimStatus')}</h2>
            <code style={styles.code}>{claimId}</code>
          </div>
          <span style={{ ...styles.badge, background: STATUS_COLORS[claimStatus] || '#334155' }}>
            {t(claimStatus) || claimStatus}
          </span>
        </div>
      </div>

      {/* Decision message shown to claimant (no scores/bands) */}
      {decisionData && (
        <div style={styles.decisionCard}>
          <h3 style={styles.decisionTitle}>{decisionData.outcome}</h3>
          <p style={styles.decisionBody}>{decisionData.claimant_message}</p>
          {decisionData.next_steps?.length > 0 && (
            <ul style={styles.actionItems}>
              {decisionData.next_steps.map((step, i) => <li key={i} style={styles.actionItem}>{step}</li>)}
            </ul>
          )}
          {decisionData.slots_to_resubmit?.length > 0 && (
            <p style={{ color: '#fb923c', fontSize: 12, marginTop: 10 }}>
              Requested evidence: {decisionData.slots_to_resubmit.join(', ')}
            </p>
          )}
        </div>
      )}

      {/* Status timeline */}
      {status.timeline?.length > 0 && (
        <div style={styles.card}>
          <h3 style={styles.sectionTitle}>{t('evidenceTimeline')}</h3>
          <ul style={styles.timelineList}>
            {status.timeline.map((item, i) => (
              <li key={i} style={styles.timelineItem}>
                <div style={{ ...styles.timelineDot, background: item.status === 'done' ? '#34d399' : '#334155' }} />
                <div>
                  <div style={styles.timelineLabel}>{item.name}</div>
                  {item.date && <div style={styles.timelineDate}>{item.date.slice(0, 16).replace('T', ' ')}</div>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Evidence items from separate endpoint */}
      {timeline.length > 0 && (
        <div style={styles.card}>
          <h3 style={styles.sectionTitle}>Uploaded Evidence</h3>
          <ul style={styles.timelineList}>
            {timeline.map((item, i) => (
              <li key={i} style={styles.timelineItem}>
                <div style={styles.timelineDot} />
                <div>
                  <div style={styles.timelineLabel}>{item.slot} — {item.file_label}</div>
                  <div style={styles.timelineDate}>{item.state} · {item.updated_at?.slice(0, 16)?.replace('T', ' ')}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Resubmit form – only when needs_evidence */}
      {needsEvidence && (
        <div style={styles.card}>
          <h3 style={styles.sectionTitle}>{t('resubmitBtn')}</h3>
          <form onSubmit={handleResubmit}>
            <input
              type="file"
              multiple
              accept="image/*,application/pdf"
              style={styles.fileInput}
              onChange={e => setFiles(Array.from(e.target.files))}
            />
            {submitMsg && <p style={submitMsg === t('resubmitSuccess') ? styles.ok : styles.err}>{submitMsg}</p>}
            <button style={styles.submitBtn} type="submit" disabled={submitting || !files.length}>
              {submitting ? t('resubmitting') : t('resubmitBtn')}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ color: '#64748b', fontSize: 11, marginBottom: 2 }}>{label}</div>
      <div style={{ color: '#e2e8f0', fontSize: 14 }}>{value || '—'}</div>
    </div>
  );
}

const styles = {
  backLink: { color: '#38bdf8', textDecoration: 'none', fontSize: 13, display: 'inline-block', marginBottom: 16 },
  card: { background: '#1e293b', borderRadius: 10, padding: '20px 24px', marginBottom: 16 },
  cardTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 },
  h2: { color: '#e2e8f0', margin: '0 0 4px', fontSize: 18, fontWeight: 700 },
  code: { fontFamily: 'monospace', fontSize: 11, color: '#94a3b8', background: '#0f172a', padding: '2px 6px', borderRadius: 4 },
  badge: { borderRadius: 12, padding: '4px 14px', fontSize: 12, color: '#0f172a', fontWeight: 700, flexShrink: 0 },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 24px' },
  fieldLabel: { color: '#64748b', fontSize: 11, display: 'block', marginBottom: 4 },
  descBox: { marginTop: 12, borderTop: '1px solid #334155', paddingTop: 12 },
  desc: { color: '#cbd5e1', fontSize: 13, margin: 0 },
  decisionCard: { background: '#1e3a2f', borderRadius: 10, padding: '20px 24px', marginBottom: 16, border: '1px solid #34d39940' },
  decisionTitle: { color: '#34d399', margin: '0 0 10px', fontSize: 16 },
  decisionBody: { color: '#cbd5e1', fontSize: 13, lineHeight: 1.6, margin: '0 0 10px' },
  actionItems: { color: '#94a3b8', paddingLeft: 18, margin: 0, fontSize: 13 },
  actionItem: { marginBottom: 4 },
  sectionTitle: { color: '#94a3b8', fontSize: 13, fontWeight: 600, margin: '0 0 14px' },
  timelineList: { listStyle: 'none', margin: 0, padding: 0 },
  timelineItem: { display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 14 },
  timelineDot: { width: 8, height: 8, borderRadius: '50%', background: '#38bdf8', marginTop: 4, flexShrink: 0 },
  timelineLabel: { color: '#cbd5e1', fontSize: 13 },
  timelineDate: { color: '#64748b', fontSize: 11, marginTop: 2 },
  fileInput: { marginBottom: 10, color: '#94a3b8', fontSize: 13 },
  submitBtn: { background: '#38bdf8', border: 'none', borderRadius: 7, color: '#0f172a', fontWeight: 700, fontSize: 13, padding: '8px 18px', cursor: 'pointer' },
  ok: { color: '#34d399', fontSize: 13 },
  err: { color: '#f87171', fontSize: 13 },
  muted: { color: '#64748b', fontSize: 14 },
};
