import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { RiskBadge } from '@/components/RiskBadge';
import { BoxOverlay } from '@/components/BoxOverlay';
import { FlaggedFieldTable } from '@/components/FlaggedFieldTable';
import DecisionBar from '@/components/DecisionBar';
import DuplicateBanner from '@/components/DuplicateBanner';
import TimelineTab from '@/components/TimelineTab';
import LocationTab from '@/components/LocationTab';
import { fetchClient } from '@/api/client';
import {
  ArrowLeft,
  Download,
  Trash2,
  Sliders,
  UserCheck,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  QrCode,
  Clock,
  Navigation,
  Share2,
  BookOpen,
  ExternalLink,
} from 'lucide-react';

export default function ResultPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' | 'image' | 'document' | 'evidence' | 'why' | 'checks'
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.7);
  const [selectedDocPage, setSelectedDocPage] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchClient(`/results/${id}`)
      .then(setResult)
      .catch((err) => setError(err.message || 'Failed to load case result'));
  }, [id]);

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to permanently delete this forensic result and all uploaded files?')) {
      return;
    }
    setDeleting(true);
    try {
      await fetchClient(`/results/${id}`, { method: 'DELETE' });
      navigate('/app/history');
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
      setDeleting(false);
    }
  };

  if (error) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center space-y-4">
        <div className="text-red-600 font-bold text-lg">Error loading result</div>
        <p className="text-muted text-sm">{error}</p>
        <Link to="/app/analyze" className="inline-block text-sm text-ink underline">
          Back to Analyze
        </Link>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="p-12 text-center text-muted">
        <div className="animate-pulse">Loading case result {id}...</div>
      </div>
    );
  }

  const overall = result.overall || {};
  const evidenceList = result.evidence || [];
  const why = result.why_this_score || {};
  const checksRun = result.checks_run || [];
  const artifacts = result.artifacts || {};
  const pages = artifacts.pages || [];
  const imageResults = result.image_results || [];

  // Determine primary preview image
  const primaryPreview = artifacts.preview_image || artifacts.preview_img_1 || (pages[0]?.image_url);
  const heatmapUrl = artifacts.heatmap;

  // Normalised boxes for current document page
  const currentPageInfo = pages[selectedDocPage] || null;
  const currentBoxes = evidenceList
    .filter((e) => e.bbox && (e.page || 1) === (selectedDocPage + 1))
    .map((e) => ({
      x: e.bbox.x,
      y: e.bbox.y,
      w: e.bbox.w,
      h: e.bbox.h,
      field: e.field,
      evidence_id: e.id,
      severity: e.severity,
      reason: e.reason,
    }));

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-16">
      {/* Top Header & Actions */}
      <div className="flex items-center justify-between">
        <Link
          to="/app/analyze"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-ink transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>New Analysis</span>
        </Link>
        <div className="flex items-center gap-2">
          <a
            href={`/api/v1/results/${id}/report.pdf`}
            download
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded border border-rule bg-surface hover:bg-paper shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            PDF Report
          </a>
          <a
            href={`/api/v1/results/${id}/report.json`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded border border-rule bg-surface hover:bg-paper shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            JSON Audit
          </a>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Delete
          </button>
        </div>
      </div>

      {/* DUPLICATE EVIDENCE BANNER */}
      <DuplicateBanner evidenceList={evidenceList} artifacts={artifacts} />

      {/* OVERALL SCORE BANNER */}
      <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">Composite Fraud Assessment</span>
            <div className="flex items-center gap-3 mt-1.5">
              <RiskBadge band={overall.band || 'LOW'} />
              <span className="text-3xl font-extrabold text-ink">
                {Math.round((overall.risk || 0) * 100)}% Risk
              </span>
              <span className="text-xs px-2.5 py-1 rounded-full border border-rule bg-paper text-muted font-semibold uppercase">
                {overall.confidence || 'high'} confidence
              </span>
            </div>
          </div>
          <div className="text-xs text-muted sm:text-right font-mono">
            <div>Case ID: {id}</div>
            <div>{new Date(result.created_at).toLocaleString()}</div>
          </div>
        </div>

        {/* Summary & Recommended Action */}
        <div className="p-4 rounded-lg bg-paper border-l-4 border-marker text-ink text-sm leading-relaxed space-y-2">
          <div><b>Investigator Summary:</b> {overall.summary}</div>
          {result.recommended_action && (
            <div className="text-xs text-blue-900 font-semibold pt-1">
              Recommended Action: {result.recommended_action}
            </div>
          )}
        </div>

        {/* Fraud Ring Alert Callout if linked */}
        {(result.network?.rings?.length > 0 || result.extras?.network?.rings?.length > 0 || evidenceList.some(e => e.id === 'CLM-NET-01' || e.id === 'CLM-NET-02')) && (
          <div className="p-3.5 rounded-xl bg-purple-50 border border-purple-300 text-purple-900 flex items-center justify-between text-xs shadow-xs">
            <div className="flex items-center gap-2.5">
              <Share2 className="w-4 h-4 text-purple-600 shrink-0" />
              <div>
                <span className="font-bold">Fraud Ring Association Detected: </span>
                <span>This claim shares high-strength identifiers with other claimants. Association is context, not proof (Principle P1).</span>
              </div>
            </div>
            <button
              onClick={() => setActiveTab('network')}
              className="px-3 py-1 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold shrink-0 transition-colors"
            >
              View Network Intelligence &rarr;
            </button>
          </div>
        )}

        {/* Pipeline Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
          {result.image && (
            <div className="p-3.5 rounded-lg border border-rule bg-surface flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-muted">Image Forensics</div>
                <div className="text-base font-bold text-ink mt-0.5">{Math.round(result.image.risk * 100)}% Risk</div>
                <div className="text-[11px] text-muted">{Math.round(result.image.authenticity * 100)}% Authentic</div>
              </div>
              <RiskBadge band={result.image.band} />
            </div>
          )}
          {result.document && (
            <div className="p-3.5 rounded-lg border border-rule bg-surface flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-muted">Document Tampering</div>
                <div className="text-base font-bold text-ink mt-0.5">{Math.round(result.document.risk * 100)}% Risk</div>
                <div className="text-[11px] text-muted">{Math.round(result.document.authenticity * 100)}% Authentic</div>
              </div>
              <RiskBadge band={result.document.band} />
            </div>
          )}
          {result.identity && (
            <div className="p-3.5 rounded-lg border border-rule bg-surface flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-muted">Identity & Biometrics</div>
                <div className="text-base font-bold text-ink mt-0.5">{Math.round(result.identity.risk * 100)}% Risk</div>
                <div className="text-[11px] text-muted">{Math.round(result.identity.authenticity * 100)}% Authentic</div>
              </div>
              <RiskBadge band={result.identity.band} />
            </div>
          )}
          <div className="p-3.5 rounded-lg border border-rule bg-surface flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-muted">Top Contributing Evidence</div>
              <div className="text-xs font-bold text-ink mt-1 truncate max-w-[150px]">
                {evidenceList[0]?.id || 'None'}
              </div>
              <div className="text-[11px] text-muted">{evidenceList.length} indicators flagged</div>
            </div>
            <span className="text-xs px-2 py-0.5 rounded border border-rule bg-paper font-semibold">
              Rank #1
            </span>
          </div>
        </div>
      </div>

      {/* Decision Bar (investigator only) */}
      <DecisionBar resultId={id} />

      {/* Tabs navigation */}
      <div className="flex border-b border-rule gap-1 overflow-x-auto text-sm">
        <button
          onClick={() => setActiveTab('summary')}
          className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap ${
            activeTab === 'summary' ? 'border-marker text-ink font-semibold' : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          Top Reasons & Overview
        </button>
        {result.image && (
          <button
            onClick={() => setActiveTab('image')}
            className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap ${
              activeTab === 'image' ? 'border-marker text-ink font-semibold' : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            Image Forensic Viewer
          </button>
        )}
        {result.document && (
          <button
            onClick={() => setActiveTab('document')}
            className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap ${
              activeTab === 'document' ? 'border-marker text-ink font-semibold' : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            Document Viewer & Boxes
          </button>
        )}
        {(result.identity || result.liveness || result.aadhaar_qr) && (
          <button
            onClick={() => setActiveTab('identity')}
            className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap ${
              activeTab === 'identity' ? 'border-marker text-ink font-semibold' : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            Identity & Aadhaar QR
          </button>
        )}
        <button
          onClick={() => setActiveTab('evidence')}
          className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap ${
            activeTab === 'evidence' ? 'border-marker text-ink font-semibold' : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          All Evidence ({evidenceList.length})
        </button>
        <button
          onClick={() => setActiveTab('why')}
          className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap ${
            activeTab === 'why' ? 'border-marker text-ink font-semibold' : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          Why This Score (Math)
        </button>
        <button
          onClick={() => setActiveTab('checks')}
          className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap ${
            activeTab === 'checks' ? 'border-marker text-ink font-semibold' : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          Checks Run ({checksRun.length})
        </button>
        <button
          onClick={() => setActiveTab('timeline')}
          className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'timeline' ? 'border-marker text-ink font-semibold' : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          Timeline
        </button>
        <button
          onClick={() => setActiveTab('location')}
          className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'location' ? 'border-marker text-ink font-semibold' : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          <Navigation className="w-3.5 h-3.5" />
          Location
        </button>
        <button
          onClick={() => setActiveTab('network')}
          className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'network' ? 'border-marker text-ink font-semibold' : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          <Share2 className="w-3.5 h-3.5" />
          Network Intelligence
        </button>
        <button
          onClick={() => setActiveTab('story')}
          className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'story' ? 'border-marker text-ink font-semibold' : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          Story Review
        </button>
      </div>

      {/* TAB CONTENTS */}

      {/* TAB 1: SUMMARY */}
      {activeTab === 'summary' && (
        <div className="space-y-6">
          <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-4">
            <h3 className="text-base font-bold text-ink">Key Fraud Indicators (Top Reasons)</h3>
            <div className="space-y-2.5">
              {(result.top_reasons || []).map((reason, idx) => (
                <div key={idx} className="flex items-start gap-2.5 p-3 rounded-lg bg-paper border border-rule text-sm">
                  <span className="font-bold text-xs bg-ink text-surface rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <div className="text-ink font-medium leading-relaxed">{reason}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: IMAGE VIEWER */}
      {activeTab === 'image' && (
        <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-ink">Forensic Image Inspection</h3>
              <p className="text-xs text-muted">Inspect original photo and localized ELA / AI heatmaps.</p>
            </div>
            {heatmapUrl && (
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-muted" />
                <span className="text-xs font-semibold text-muted">Heatmap Overlay</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={heatmapOpacity}
                  onChange={(e) => setHeatmapOpacity(parseFloat(e.target.value))}
                  className="w-24 h-1.5 bg-paper rounded cursor-pointer"
                />
                <span className="text-xs font-mono">{Math.round(heatmapOpacity * 100)}%</span>
              </div>
            )}
          </div>

          {/* Photo viewer with Heatmap Overlay */}
          <div className="relative max-w-2xl mx-auto rounded-lg border border-rule bg-paper overflow-hidden">
            {primaryPreview ? (
              <img src={primaryPreview} alt="Original uploaded image" className="w-full h-auto block" />
            ) : (
              <div className="p-16 text-center text-muted text-sm">No preview image available</div>
            )}
            {heatmapUrl && (
              <img
                src={heatmapUrl}
                alt="Forensic heatmap"
                style={{ opacity: heatmapOpacity }}
                className="absolute inset-0 w-full h-full object-cover pointer-events-none transition-opacity"
              />
            )}
          </div>

          {/* Gallery if multiple images */}
          {imageResults.length > 1 && (
            <div className="space-y-2 pt-2 border-t border-rule">
              <h4 className="text-xs font-semibold text-muted uppercase">All Analyzed Photos ({imageResults.length})</h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {imageResults.map((img, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg border border-rule bg-paper text-xs space-y-1">
                    <div className="font-semibold text-ink">{img.pipeline}</div>
                    <div className="flex items-center justify-between">
                      <span className="font-bold">{Math.round(img.risk * 100)}% Risk</span>
                      <RiskBadge band={img.band} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: DOCUMENT VIEWER & BOXES */}
      {activeTab === 'document' && (
        <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-ink">Document Forensics & Bounding Boxes</h3>
              <p className="text-xs text-muted">Interactive page view with highlighted suspicious fields and arithmetic errors.</p>
            </div>
            {pages.length > 1 && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-muted font-medium">Page:</span>
                {pages.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedDocPage(idx)}
                    className={`px-2.5 py-1 text-xs font-semibold rounded border ${
                      selectedDocPage === idx ? 'bg-ink text-surface border-ink' : 'bg-surface text-muted border-rule'
                    }`}
                  >
                    {p.page}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* BoxOverlay on page */}
          {currentPageInfo ? (
            <div className="flex justify-center">
              <BoxOverlay
                imageUrl={currentPageInfo.image_url}
                boxes={currentBoxes}
              />
            </div>
          ) : (
            <div className="p-12 text-center text-muted text-sm border border-rule rounded-lg">
              No rendered document pages found for this case.
            </div>
          )}

          {/* Flagged Field Discrepancies Table */}
          <div className="pt-2 border-t border-rule space-y-2">
            <h4 className="text-xs font-semibold text-muted uppercase">Flagged Document Discrepancies</h4>
            <FlaggedFieldTable evidence={evidenceList} />
          </div>
        </div>
      )}

      {/* TAB 4: ALL EVIDENCE */}
      {activeTab === 'evidence' && (
        <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-ink">Evidence Catalog (Sorted by Contribution)</h3>
            <span className="text-xs text-muted">{evidenceList.length} total items</span>
          </div>

          <div className="overflow-x-auto rounded-lg border border-rule">
            <table className="w-full text-left text-xs text-ink">
              <thead className="bg-paper uppercase text-muted font-semibold border-b border-rule">
                <tr>
                  <th className="px-3.5 py-2.5">Rank</th>
                  <th className="px-3.5 py-2.5">ID</th>
                  <th className="px-3.5 py-2.5">Indicator Title</th>
                  <th className="px-3.5 py-2.5">Severity</th>
                  <th className="px-3.5 py-2.5">Calibrated Score</th>
                  <th className="px-3.5 py-2.5">Weight</th>
                  <th className="px-3.5 py-2.5">Contribution %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule font-medium">
                {evidenceList.map((e, idx) => (
                  <tr key={idx} className="hover:bg-paper/50">
                    <td className="px-3.5 py-2.5 font-bold">{e.rank ? `#${e.rank}` : '-'}</td>
                    <td className="px-3.5 py-2.5 font-mono text-[11px]">{e.id}</td>
                    <td className="px-3.5 py-2.5 max-w-xs truncate" title={e.reason || e.title}>
                      {e.title || e.reason}
                    </td>
                    <td className="px-3.5 py-2.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        e.severity === 'high' ? 'bg-red-100 text-red-700' :
                        e.severity === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'
                      }`}>
                        {e.severity}
                      </span>
                    </td>
                    <td className="px-3.5 py-2.5 font-mono">
                      {e.calibrated_score !== undefined ? e.calibrated_score.toFixed(2) : '-'}
                    </td>
                    <td className="px-3.5 py-2.5 font-mono">
                      {e.effective_weight !== undefined ? e.effective_weight.toFixed(2) : (e.weight?.toFixed(2) || '-')}
                    </td>
                    <td className="px-3.5 py-2.5 font-bold text-ink">
                      {e.contribution_pct !== undefined && e.contribution_pct !== null ? `${e.contribution_pct.toFixed(1)}%` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 5: WHY THIS SCORE */}
      {activeTab === 'why' && (
        <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-6">
          <div>
            <h3 className="text-base font-bold text-ink">Transparent Scoring Methodology (§15)</h3>
            <p className="text-xs text-muted mt-0.5">Every score is mathematically derived using Noisy-OR fusion and non-linear blend formulas.</p>
          </div>

          {/* Overall Blend */}
          {why.overall && (
            <div className="p-4 rounded-lg bg-paper border border-rule space-y-2">
              <div className="text-xs font-semibold text-muted uppercase tracking-wider">Overall Composite Blend Formula</div>
              <div className="font-mono text-xs bg-surface p-3 rounded border border-rule text-blue-900 leading-relaxed overflow-x-auto">
                {why.overall.formula}
              </div>
            </div>
          )}

          {/* Image Fusion */}
          {why.image && (
            <div className="p-4 rounded-lg bg-paper border border-rule space-y-2">
              <div className="text-xs font-semibold text-muted uppercase tracking-wider">Image Forensics Noisy-OR Fusion</div>
              <div className="font-mono text-xs bg-surface p-3 rounded border border-rule text-blue-900 leading-relaxed overflow-x-auto">
                {why.image.formula}
              </div>
            </div>
          )}

          {/* Document Fusion */}
          {why.document && (
            <div className="p-4 rounded-lg bg-paper border border-rule space-y-2">
              <div className="text-xs font-semibold text-muted uppercase tracking-wider">Document Tampering Noisy-OR Fusion</div>
              <div className="font-mono text-xs bg-surface p-3 rounded border border-rule text-blue-900 leading-relaxed overflow-x-auto">
                {why.document.formula}
              </div>
            </div>
          )}

          {/* Identity Fusion */}
          {why.identity && (
            <div className="p-4 rounded-lg bg-paper border border-rule space-y-2">
              <div className="text-xs font-semibold text-muted uppercase tracking-wider">Identity & Biometrics Noisy-OR Fusion</div>
              <div className="font-mono text-xs bg-surface p-3 rounded border border-rule text-blue-900 leading-relaxed overflow-x-auto">
                {why.identity.formula}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB: IDENTITY & BIOMETRICS */}
      {activeTab === 'identity' && (
        <div className="space-y-6">
          {/* Identity Pipeline Score Banner */}
          {result.identity && (
            <div className="bg-surface p-5 rounded-xl border border-rule shadow-sm flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-muted uppercase tracking-wider">Identity Verification Pipeline</div>
                <div className="flex items-center gap-3 mt-1">
                  <RiskBadge band={result.identity.band} />
                  <span className="text-2xl font-bold text-ink">{Math.round(result.identity.risk * 100)}% Risk</span>
                  <span className="text-xs text-muted">({Math.round(result.identity.authenticity * 100)}% Authentic)</span>
                </div>
              </div>
              <div className="text-xs text-muted text-right font-mono">
                <div>Engine: {result.versions?.face_engine || 'sface'}</div>
                <div>Confidence: {result.identity.confidence || 'high'}</div>
              </div>
            </div>
          )}

          {/* 1. Face Match & Deepfake Section */}
          <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-rule pb-3">
              <div>
                <h3 className="text-base font-bold text-ink flex items-center gap-2">
                  <UserCheck className="w-5 h-5 text-marker" />
                  Facial Match & Liveness Comparison
                </h3>
                <p className="text-xs text-muted mt-0.5">
                  1:1 Facial embedding verification between Government ID and Live Selfie
                </p>
              </div>
              {artifacts.identity_face_comparison && (
                <a
                  href={artifacts.identity_face_comparison}
                  download="face_comparison.jpg"
                  className="text-xs px-2.5 py-1 rounded border border-rule text-muted hover:text-ink flex items-center gap-1"
                >
                  <Download className="w-3.5 h-3.5" /> Download Comparison
                </a>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              {/* Comparison Visual / Crops */}
              <div className="space-y-3">
                {artifacts.identity_face_comparison ? (
                  <div className="rounded-lg overflow-hidden border border-rule bg-black text-center">
                    <img
                      src={artifacts.identity_face_comparison}
                      alt="Face Comparison Artifact"
                      className="w-full max-h-64 object-contain mx-auto"
                    />
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    <div className="border border-rule rounded-lg p-2 text-center bg-paper">
                      <div className="text-[11px] font-semibold text-muted mb-1">ID Document Face</div>
                      {artifacts.id_face_crop ? (
                        <img src={artifacts.id_face_crop} alt="ID Face" className="w-24 h-24 object-cover mx-auto rounded border border-rule" />
                      ) : (
                        <div className="w-24 h-24 bg-surface rounded mx-auto flex items-center justify-center text-xs text-muted">No crop</div>
                      )}
                    </div>
                    <div className="border border-rule rounded-lg p-2 text-center bg-paper">
                      <div className="text-[11px] font-semibold text-muted mb-1">Live Selfie Face</div>
                      {artifacts.selfie_face_crop ? (
                        <img src={artifacts.selfie_face_crop} alt="Selfie Face" className="w-24 h-24 object-cover mx-auto rounded border border-rule" />
                      ) : (
                        <div className="w-24 h-24 bg-surface rounded mx-auto flex items-center justify-center text-xs text-muted">No crop</div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Match Metrics & Deepfake Badge */}
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-paper border border-rule space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted font-semibold">Biometric Similarity</span>
                    <span className="text-sm font-bold text-ink">
                      {result.aadhaar_qr?.photo_similarity !== undefined
                        ? result.aadhaar_qr.photo_similarity.toFixed(2)
                        : (evidenceList.find(e => e.id === 'ID-FACE-00' || e.id === 'ID-FACE-01')?.raw_score?.toFixed(2) || 'N/A')}
                    </span>
                  </div>

                  {/* Similarity Zones Bar */}
                  <div className="space-y-1">
                    <div className="w-full bg-surface rounded-full h-2 overflow-hidden flex border border-rule">
                      <div className="bg-red-500 w-[30%]" title="Mismatch zone (< 0.30)" />
                      <div className="bg-amber-400 w-[15%]" title="Ambiguous zone (0.30 - 0.45)" />
                      <div className="bg-green-500 w-[55%]" title="Match zone (>= 0.45)" />
                    </div>
                    <div className="flex justify-between text-[10px] text-muted font-mono">
                      <span>0.0 (Mismatch)</span>
                      <span>0.30</span>
                      <span>0.45</span>
                      <span>1.0 (Match)</span>
                    </div>
                  </div>

                  {/* Deepfake status */}
                  <div className="pt-2 border-t border-rule flex items-center justify-between text-xs">
                    <span className="text-muted">Selfie AI / Deepfake Check:</span>
                    {evidenceList.some(e => e.id === 'ID-DEEP-01') ? (
                      <span className="px-2 py-0.5 rounded bg-red-100 text-red-700 font-bold text-[11px]">
                        AI Generated / Deepfake Detected
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-green-100 text-green-700 font-bold text-[11px]">
                        Genuine Human Capture
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 2. Liveness Challenge Audit */}
          <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-rule pb-3">
              <div>
                <h3 className="text-base font-bold text-ink flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-marker" />
                  Active Server-Side Liveness Evaluation
                </h3>
                <p className="text-xs text-muted mt-0.5">
                  Anti-spoofing challenge verification via MediaPipe 3D landmark kinematics
                </p>
              </div>
              <span className={`px-2.5 py-1 rounded text-xs font-bold uppercase ${
                result.liveness?.passed
                  ? 'bg-green-100 text-green-700 border border-green-200'
                  : result.liveness?.performed
                  ? 'bg-red-100 text-red-700 border border-red-200'
                  : 'bg-amber-100 text-amber-700 border border-amber-200'
              }`}>
                {result.liveness?.passed ? 'Liveness Verified' : result.liveness?.performed ? 'Liveness Failed' : 'Not Attempted (Static)'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="p-3 rounded-lg border border-rule bg-paper space-y-1">
                <div className="text-[11px] font-semibold text-muted">Anti-Replay Nonce</div>
                <div className="text-xs font-mono text-ink">
                  {result.liveness?.performed ? 'Verified (Single-use token)' : 'N/A'}
                </div>
              </div>
              <div className="p-3 rounded-lg border border-rule bg-paper space-y-1">
                <div className="text-[11px] font-semibold text-muted">Session Validity</div>
                <div className="text-xs font-mono text-ink">
                  {result.liveness?.performed ? '120s TTL Enforced' : 'N/A'}
                </div>
              </div>
              <div className="p-3 rounded-lg border border-rule bg-paper space-y-1">
                <div className="text-[11px] font-semibold text-muted">Frontal Selection</div>
                <div className="text-xs font-mono text-ink">
                  {result.liveness?.performed ? 'Best frontal frame extracted' : 'Fallback static'}
                </div>
              </div>
            </div>

            <div className="text-[11px] text-muted bg-paper p-3 rounded border border-rule">
              <b>Security Scope:</b> Active random challenge defeats recorded screen replays, paper cutouts, and static digital photos. High-quality 3D silicone masks and real-time optical projector injections require specialized hardware depth sensors.
            </div>
          </div>

          {/* 3. Aadhaar Secure QR Forensic Validation */}
          <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-rule pb-3">
              <div>
                <h3 className="text-base font-bold text-ink flex items-center gap-2">
                  <QrCode className="w-5 h-5 text-marker" />
                  Aadhaar Secure QR Forensic Validation
                </h3>
                <p className="text-xs text-muted mt-0.5">
                  Offline RSA-2048 digital signature verification & OCR cross-examination
                </p>
              </div>
              {result.aadhaar_qr?.mode && (
                <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-paper border border-rule text-muted">
                  Mode: {result.aadhaar_qr.mode}
                </span>
              )}
            </div>

            {result.aadhaar_qr?.found ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 rounded-lg border border-rule bg-paper">
                  {result.aadhaar_qr.signature_valid ? (
                    <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                  )}
                  <div>
                    <div className="text-xs font-bold text-ink">
                      {result.aadhaar_qr.signature_valid
                        ? 'Cryptographic Signature Valid (UIDAI / Test Certificate)'
                        : 'Invalid Digital Signature — Tampered QR Payload Detected'}
                    </div>
                    <div className="text-[11px] text-muted">
                      {result.aadhaar_qr.signature_valid
                        ? 'QR payload is digitally signed and uncorrupted.'
                        : 'Rule O7 applied: The high-density QR payload does not match UIDAI public key.'}
                    </div>
                  </div>
                </div>

                {/* Printed vs Signed QR Comparison Table */}
                {result.aadhaar_qr.comparisons && result.aadhaar_qr.comparisons.length > 0 && (
                  <div className="overflow-x-auto rounded-lg border border-rule">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-paper uppercase text-muted font-semibold border-b border-rule">
                        <tr>
                          <th className="px-4 py-2.5">Field</th>
                          <th className="px-4 py-2.5">Printed on Card (OCR)</th>
                          <th className="px-4 py-2.5">Signed in Secure QR</th>
                          <th className="px-4 py-2.5">Match Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-rule font-medium">
                        {result.aadhaar_qr.comparisons.map((cmp, idx) => (
                          <tr key={idx} className={cmp.match ? 'hover:bg-paper/50' : 'bg-red-50/50'}>
                            <td className="px-4 py-2.5 font-semibold text-ink capitalize">{cmp.field}</td>
                            <td className="px-4 py-2.5 font-mono text-muted">{cmp.printed || '—'}</td>
                            <td className="px-4 py-2.5 font-mono text-muted">{cmp.qr || '—'}</td>
                            <td className="px-4 py-2.5">
                              {cmp.match ? (
                                <span className="inline-flex items-center gap-1 text-green-700 font-semibold text-[11px]">
                                  <CheckCircle2 className="w-3.5 h-3.5" /> Match
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-red-700 font-bold text-[11px]">
                                  <AlertTriangle className="w-3.5 h-3.5" /> Mismatch (Tampered)
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-4 rounded-lg bg-paper border border-rule text-xs text-muted">
                No high-density Aadhaar Secure QR code detected on uploaded document.
              </div>
            )}

            <div className="text-[11px] text-muted bg-paper p-3 rounded border border-rule">
              <b>UIDAI Privacy Compliance (§20):</b> 12-digit Aadhaar numbers and raw biometric templates are never collected, logged, or persisted to database. Only cryptographic verification statuses, field hashes, and last-4 references are stored.
            </div>
          </div>
        </div>
      )}

      {/* TAB 6: CHECKS RUN */}
      {activeTab === 'checks' && (
        <div className="space-y-6">
          {/* Claim Cross-Checks Section (§14) */}
          <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-ink">Claim Cross-Checks (R_claim)</h3>
                <p className="text-xs text-muted">Cross-examination across dates, locations, entities, and policy terms (§14)</p>
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-paper border border-rule font-semibold text-muted">
                {checksRun.filter((c) => c.detector && c.detector.startsWith('claim:')).length} checks
              </span>
            </div>

            <div className="overflow-x-auto rounded-lg border border-rule">
              <table className="w-full text-left text-xs text-ink">
                <thead className="bg-paper uppercase text-muted font-semibold border-b border-rule">
                  <tr>
                    <th className="px-4 py-3">Cross-Check Rule</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Diagnostic & Concrete Numbers</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-rule font-medium">
                  {checksRun.filter((c) => c.detector && c.detector.startsWith('claim:')).map((chk, idx) => (
                    <tr key={idx} className="hover:bg-paper/50">
                      <td className="px-4 py-3 font-mono font-semibold">{chk.detector}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          chk.status === 'ok' ? 'bg-green-100 text-green-700' :
                          chk.status === 'skipped' ? 'bg-gray-100 text-gray-600' : 'bg-red-100 text-red-700'
                        }`}>
                          {chk.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted text-xs">
                        {chk.reason || 'Rule passed without discrepancy.'}
                      </td>
                    </tr>
                  ))}
                  {checksRun.filter((c) => c.detector && c.detector.startsWith('claim:')).length === 0 && (
                    <tr>
                      <td colSpan={3} className="px-4 py-6 text-center text-muted text-xs">
                        No claim-level cross-checks executed for this case.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Automated Forensics & Pipeline Audits */}
          <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-ink">Automated Forensics & Pipeline Audits</h3>
                <p className="text-xs text-muted">Per-detector execution status and forensic diagnostic benchmarks</p>
              </div>
              <span className="text-xs text-muted">
                {checksRun.filter((c) => !c.detector || !c.detector.startsWith('claim:')).length} checks
              </span>
            </div>

            <div className="overflow-x-auto rounded-lg border border-rule">
              <table className="w-full text-left text-xs text-ink">
                <thead className="bg-paper uppercase text-muted font-semibold border-b border-rule">
                  <tr>
                    <th className="px-4 py-3">Detector / Task</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Execution Time</th>
                    <th className="px-4 py-3">Diagnostic Note</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-rule font-medium">
                  {checksRun.filter((c) => !c.detector || !c.detector.startsWith('claim:')).map((chk, idx) => (
                    <tr key={idx} className="hover:bg-paper/50">
                      <td className="px-4 py-3 font-mono font-semibold">{chk.detector}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          chk.status === 'ok' ? 'bg-green-100 text-green-700' :
                          chk.status === 'skipped' ? 'bg-gray-100 text-gray-600' : 'bg-red-100 text-red-700'
                        }`}>
                          {chk.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono">{chk.duration_ms} ms</td>
                      <td className="px-4 py-3 text-muted text-xs">
                        {chk.reason || 'Completed successfully'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 7: TIMELINE */}
      {activeTab === 'timeline' && (
        <TimelineTab resultId={id} />
      )}

      {/* TAB 8: LOCATION */}
      {activeTab === 'location' && (
        <LocationTab location={result.location} evidenceList={evidenceList} />
      )}

      {/* TAB 9: NETWORK INTELLIGENCE */}
      {activeTab === 'network' && (
        <div className="space-y-6">
          <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-ink flex items-center gap-2">
                  <Share2 className="w-5 h-5 text-purple-600" />
                  <span>Fraud Ring & Cross-Claim Association</span>
                </h3>
                <p className="text-xs text-muted mt-1">
                  Shared entity linkages across claims. Network signals are capped at 0.35 (Principle P1).
                </p>
              </div>
              <Link
                to={`/app/network?focus_type=claim&focus_id=${id}`}
                className="px-3.5 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shadow-xs"
              >
                <span>Open in Full Network Graph</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>

            {/* Network Summary Cards */}
            {result.network || result.extras?.network ? (
              (() => {
                const net = result.network || result.extras?.network || {};
                const ringsList = net.rings || [];
                const shared = net.shared_identifiers || [];
                const linkedClaims = net.linked_claims || [];

                return (
                  <div className="space-y-4">
                    {/* Ring Association Box */}
                    {ringsList.length > 0 ? (
                      <div className="p-4 rounded-xl bg-purple-50/60 border border-purple-200 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-purple-900 text-sm">
                            Ring Membership: {ringsList[0].ring_id || ringsList[0].id}
                          </span>
                          <RiskBadge band={ringsList[0].band || 'MEDIUM'} size="sm" />
                        </div>
                        <div className="text-xs text-purple-800">
                          {ringsList[0].claims_count} connected claims &bull; {ringsList[0].claimants_count} claimants &bull; Status: <span className="font-bold uppercase font-mono">{ringsList[0].status || 'open'}</span>
                        </div>
                        <div className="text-xs text-slate-700 bg-white p-3 rounded-lg border border-purple-100">
                          <b>Primary Reason:</b> {ringsList[0].reasons?.[0] || 'Shared financial or photographic identifier.'}
                        </div>
                      </div>
                    ) : (
                      <div className="p-4 rounded-xl bg-paper border border-rule text-xs text-muted">
                        No active multi-claimant fraud ring cluster detected for this claim.
                      </div>
                    )}

                    {/* Shared Identifiers List */}
                    <div>
                      <h4 className="font-bold text-ink text-xs uppercase tracking-wider mb-2">
                        Shared Identifiers ({shared.length})
                      </h4>
                      {shared.length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {shared.map((item, idx) => (
                            <div key={idx} className="p-3 rounded-lg bg-paper border border-rule text-xs flex items-center justify-between">
                              <div>
                                <span className="font-mono font-bold text-ink uppercase text-[10px] bg-white px-1.5 py-0.5 rounded border border-rule">
                                  {item.kind || item.type}
                                </span>
                                <div className="font-mono text-ink mt-1 font-semibold">
                                  {item.label || item.value}
                                </div>
                              </div>
                              <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                                item.strength >= 1.0 ? 'bg-red-100 text-red-700' :
                                item.strength >= 0.6 ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'
                              }`}>
                                {item.strength >= 1.0 ? 'Strong (1.0)' : item.strength >= 0.6 ? 'Medium (0.6)' : 'Weak (0.3)'}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-muted">No shared identifiers detected.</div>
                      )}
                    </div>

                    {/* Linked Claims Table */}
                    <div>
                      <h4 className="font-bold text-ink text-xs uppercase tracking-wider mb-2">
                        Directly Linked Claims ({linkedClaims.length})
                      </h4>
                      {linkedClaims.length > 0 ? (
                        <div className="overflow-x-auto border border-rule rounded-lg">
                          <table className="w-full text-xs text-left">
                            <thead className="bg-paper text-muted uppercase text-[10px]">
                              <tr>
                                <th className="px-3 py-2">Claim ID</th>
                                <th className="px-3 py-2">Claimant</th>
                                <th className="px-3 py-2">Shared Entity</th>
                                <th className="px-3 py-2">Strength</th>
                                <th className="px-3 py-2">Action</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-rule font-medium">
                              {linkedClaims.map((lc, idx) => (
                                <tr key={idx} className="hover:bg-paper/40">
                                  <td className="px-3 py-2 font-mono font-bold text-ink">{lc.claim_id}</td>
                                  <td className="px-3 py-2 text-muted">{lc.claimant_name || lc.claimant_id || 'Another Claimant'}</td>
                                  <td className="px-3 py-2 text-ink">{lc.shared_kind}</td>
                                  <td className="px-3 py-2 font-mono font-bold text-blue-600">{lc.strength}</td>
                                  <td className="px-3 py-2">
                                    <Link to={`/app/results/${lc.claim_id}`} className="text-blue-600 hover:underline font-semibold">
                                      Inspect &rarr;
                                    </Link>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="text-xs text-muted">No directly linked external claims.</div>
                      )}
                    </div>
                  </div>
                );
              })()
            ) : (
              <div className="p-6 text-center text-muted text-xs">
                No network association signals flagged for this claim.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 10: STORY REVIEW */}
      {activeTab === 'story' && (
        <div className="space-y-6">
          <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-ink flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-blue-600" />
                  <span>Claimant Statement & Story Review</span>
                </h3>
                <p className="text-xs text-muted mt-1">
                  Cross-checks narrative against OCR facts and metadata. Emits CLM-STORY-00 (weight 0.0, info-only).
                </p>
              </div>
              <span className="text-xs px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 font-semibold border border-blue-200">
                Rule-Based Story Consistency
              </span>
            </div>

            {/* Narrative Quote Box */}
            <div className="p-4 rounded-xl bg-paper border border-rule space-y-2">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider">
                Submitted Claimant Narrative
              </span>
              <p className="text-xs text-ink italic leading-relaxed">
                "{result.description_text || result.metadata?.description || result.metadata?.description_text || 'No typed narrative provided; evaluated via structured inputs.'}"
              </p>
            </div>

            {/* Story Contradictions Table */}
            {(() => {
              const story = result.story || result.extras?.story || {};
              const contradictions = story.contradictions || [];
              const consistent = story.consistent_points || [];

              return (
                <div className="space-y-4">
                  <div>
                    <h4 className="font-bold text-ink text-xs uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                      <span>Contradictions & Discrepancies ({contradictions.length})</span>
                    </h4>
                    {contradictions.length > 0 ? (
                      <div className="space-y-2">
                        {contradictions.map((item, idx) => (
                          <div key={idx} className="p-3 rounded-lg bg-amber-50/60 border border-amber-200 text-xs flex items-start gap-2.5">
                            <span className="w-5 h-5 rounded-full bg-amber-200 text-amber-900 font-bold flex items-center justify-center shrink-0 mt-0.5 text-[11px]">
                              !
                            </span>
                            <div className="flex-1 space-y-1">
                              <div className="font-semibold text-amber-900">{item.text}</div>
                              <div className="text-[11px] text-amber-800/80 flex items-center gap-3">
                                <span>Sources: {Array.isArray(item.sources) ? item.sources.join(' vs ') : 'Statement vs Form'}</span>
                                {item.evidence_ids && (
                                  <span className="font-mono bg-white px-1.5 py-0.5 rounded border border-amber-300 text-amber-900">
                                    Flag: {item.evidence_ids.join(', ')}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                        <span>No factual contradictions detected between the statement and verified evidence.</span>
                      </div>
                    )}
                  </div>

                  {/* Consistent Points Table */}
                  <div>
                    <h4 className="font-bold text-ink text-xs uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Consistent Story Anchors ({consistent.length})</span>
                    </h4>
                    {consistent.length > 0 ? (
                      <div className="space-y-1.5">
                        {consistent.map((cp, idx) => (
                          <div key={idx} className="p-2.5 rounded-lg bg-paper border border-rule text-xs flex items-center justify-between">
                            <span className="text-ink font-medium">{cp.detail || cp.statement_quote}</span>
                            <span className="font-mono text-[10px] text-muted">{cp.evidence_ref || 'Verified match'}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-xs text-muted">No explicit consistent anchor points extracted.</div>
                    )}
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}
