import React, { useState } from 'react';
import { fetchClient } from '@/api/client';

const DECISION_ACTIONS = ['approve', 'reject', 'request_evidence'];
const DECISION_CATEGORIES = ['ai_image_verified', 'document_verified', 'policy_violation', 'coverage_exclusion', 'manual_review', 'field_investigation'];

/**
 * Decision Bar – investigator-only panel to draft and submit a claim decision.
 * Never renders band/score/risk/detector names to the investigator or claimant.
 * Guardrails are enforced on the backend; the frontend just submits.
 */
export default function DecisionBar({ resultId }) {
  const [expanded, setExpanded]       = useState(false);
  const [action, setAction]           = useState('approve');
  const [category, setCategory]       = useState('manual_review');
  const [lang, setLang]               = useState('en');
  const [draft, setDraft]             = useState(null);
  const [letterBody, setLetterBody]   = useState('');
  const [actionItems, setActionItems] = useState('');
  const [loading, setLoading]         = useState(false);
  const [submitted, setSubmitted]     = useState(false);
  const [error, setError]             = useState('');

  async function fetchDraft() {
    setLoading(true); setError('');
    try {
      const d = await fetchClient(`/results/${resultId}/decision/draft`, {
        method: 'POST',
        body: JSON.stringify({ action, reason_category: category, lang })
      });
      setDraft(d);
      const msg = lang === 'hi' ? (d.claimant_message_hi || d.claimant_message_en) : (d.claimant_message_en || d.letter_body || '');
      setLetterBody(msg || '');
      const steps = d.next_steps || d.action_items || [];
      setActionItems(Array.isArray(steps) ? steps.map(s => typeof s === 'string' ? s : s.description || '').join('\n') : '');
    } catch (err) { setError(err.message || 'Draft failed'); }
    finally { setLoading(false); }
  }

  async function submitDecision() {
    setLoading(true); setError('');
    try {
      const slots = actionItems.split('\n').map(s => s.trim()).filter(Boolean);
      await fetchClient(`/results/${resultId}/decision`, {
        method: 'POST',
        body: JSON.stringify({
          action,
          reason_category: category,
          claimant_message: letterBody,
          internal_note: 'Investigator decision via portal',
          slots_to_resubmit: slots
        })
      });
      setSubmitted(true);
    } catch (err) { setError(err.message || 'Submit failed'); }
    finally { setLoading(false); }
  }

  if (submitted) {
    return (
      <div style={{ background: '#1e3a2f', border: '1px solid #34d39940', borderRadius: 8, padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <span style={{ color: '#34d399', fontWeight: 700, fontSize: 14 }}>✓ Decision submitted</span>
      </div>
    );
  }

  return (
    <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, overflow: 'hidden', marginBottom: 16 }}>
      <button
        onClick={() => setExpanded(e => !e)}
        style={{ width: '100%', background: 'transparent', border: 'none', padding: '14px 20px', textAlign: 'left', color: '#38bdf8', fontWeight: 700, cursor: 'pointer', fontSize: 14, display: 'flex', alignItems: 'center', gap: 8 }}
      >
        {expanded ? '▾' : '▸'} Decision Bar
        <span style={{ color: '#64748b', fontWeight: 400, fontSize: 12 }}>— approve, reject, or request evidence</span>
      </button>

      {expanded && (
        <div style={{ padding: '0 20px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <LabeledSelect label="Action" value={action} onChange={setAction} options={DECISION_ACTIONS} />
            <LabeledSelect label="Reason Category" value={category} onChange={setCategory} options={DECISION_CATEGORIES} />
            <LabeledSelect label="Letter Language" value={lang} onChange={setLang}
              options={['en', 'hi']} labels={{ en: 'English', hi: 'Hindi' }} />
            <button style={ds.draftBtn} onClick={fetchDraft} disabled={loading}>
              {loading ? '…' : 'Get AI Draft'}
            </button>
          </div>

          {draft && (
            <div>
              <label style={ds.label}>Letter Body (editable – no scores, bands, or detector names)</label>
              <textarea
                style={{ ...ds.ta, height: 130 }}
                value={letterBody}
                onChange={e => setLetterBody(e.target.value)}
              />
              <label style={{ ...ds.label, marginTop: 10 }}>Action Items (one per line, optional)</label>
              <textarea
                style={{ ...ds.ta, height: 60 }}
                value={actionItems}
                onChange={e => setActionItems(e.target.value)}
              />
              <div style={{ marginTop: 12 }}>
                <button style={ds.submitBtn} onClick={submitDecision} disabled={loading}>
                  {loading ? 'Submitting…' : 'Submit Decision'}
                </button>
              </div>
            </div>
          )}

          {error && <p style={{ color: '#f87171', fontSize: 13, margin: 0 }}>{error}</p>}
        </div>
      )}
    </div>
  );
}

function LabeledSelect({ label, value, onChange, options, labels = {} }) {
  return (
    <div>
      <label style={ds.label}>{label}</label>
      <select style={ds.select} value={value} onChange={e => onChange(e.target.value)}>
        {options.map(o => <option key={o} value={o}>{labels[o] || o}</option>)}
      </select>
    </div>
  );
}

const ds = {
  label: { display: 'block', color: '#64748b', fontSize: 11, marginBottom: 4 },
  select: { padding: '7px 10px', borderRadius: 6, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0', fontSize: 13, cursor: 'pointer' },
  ta: { width: '100%', boxSizing: 'border-box', padding: '8px 10px', borderRadius: 6, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0', fontSize: 13, display: 'block', resize: 'vertical' },
  draftBtn: { background: '#334155', border: 'none', color: '#cbd5e1', borderRadius: 6, padding: '7px 14px', cursor: 'pointer', fontSize: 12, height: 33 },
  submitBtn: { background: '#38bdf8', border: 'none', color: '#0f172a', borderRadius: 6, padding: '9px 20px', fontWeight: 700, cursor: 'pointer', fontSize: 13 },
};
