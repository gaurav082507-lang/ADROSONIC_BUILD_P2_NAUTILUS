import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  AlertTriangle,
  Zap,
  Share2,
  ArrowRight,
  TrendingUp,
  ShieldAlert,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';
import { fetchClient } from '../../api/client';
import RiskBadge from '../../components/RiskBadge';

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [rings, setRings] = useState([]);
  const [recentFlagged, setRecentFlagged] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [sumData, ringsData, queueData] = await Promise.all([
        fetchClient('/analytics/summary').catch(() => null),
        fetchClient('/network/rings?status=open&limit=5').catch(() => ({ items: [] })),
        fetchClient('/queue?limit=6').catch(() => ({ items: [] })),
      ]);
      setSummary(sumData);
      setRings(ringsData?.items || []);
      setRecentFlagged(queueData?.items || []);
    } catch (err) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  // Compute simple SVG sparkline path
  function renderSparkline(data) {
    if (!data || data.length < 2) return null;
    const maxVal = Math.max(...data, 1);
    const minVal = Math.min(...data, 0);
    const range = maxVal - minVal || 1;
    const width = 120;
    const height = 36;
    const step = width / (data.length - 1);

    const points = data.map((val, idx) => {
      const x = idx * step;
      const y = height - ((val - minVal) / range) * (height - 8) - 4;
      return `${x},${y}`;
    }).join(' ');

    return (
      <svg width={width} height={height} className="overflow-visible">
        <polyline
          fill="none"
          stroke="#3B82F6"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points}
        />
        {data.map((val, idx) => {
          const x = idx * step;
          const y = height - ((val - minVal) / range) * (height - 8) - 4;
          return <circle key={idx} cx={x} cy={y} r="2.5" fill="#3B82F6" />;
        })}
      </svg>
    );
  }

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center gap-3 text-slate-500 text-sm">
          <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
          <span>Loading operational intelligence...</span>
        </div>
      </div>
    );
  }

  const flaggedRatePct = summary?.flagged_rate ? Math.round(summary.flagged_rate * 100) : 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-heading font-bold text-slate-900 tracking-tight">
            Forensic Intelligence Dashboard
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time multimodal cross-check metrics, active fraud networks, and claims priority queue.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <Link
            to="/app/analyze"
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-sm transition-colors"
          >
            <span>Analyze New Claim</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
          {error}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Claims Today */}
        <div className="bg-white rounded-2xl p-5 border border-[#E3E8EF] shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Claims Today</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-heading font-bold text-slate-900">
            {summary?.claims_today ?? 0}
          </div>
          <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-2">
            <span className="text-emerald-600 font-semibold">{summary?.total ?? 0} total</span>
            <span>indexed in database</span>
          </div>
        </div>

        {/* Flagged Rate */}
        <div className="bg-white rounded-2xl p-5 border border-[#E3E8EF] shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Flagged Rate</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-heading font-bold text-slate-900">
              {flaggedRatePct}%
            </span>
            <RiskBadge band={flaggedRatePct > 20 ? 'HIGH' : flaggedRatePct > 10 ? 'MEDIUM' : 'LOW'} size="sm" />
          </div>
          <div className="text-xs text-slate-500 mt-2">
            {summary?.flagged ?? 0} claims require manual SIU review
          </div>
        </div>

        {/* Fast-Tracked */}
        <div className="bg-white rounded-2xl p-5 border border-[#E3E8EF] shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Fast-Tracked</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-heading font-bold text-slate-900">
            {summary?.fast_tracked ?? 0}
          </div>
          <div className="text-xs text-emerald-600 font-medium mt-2 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Zero-anomaly auto-approvals</span>
          </div>
        </div>

        {/* Open Fraud Rings */}
        <div className="bg-white rounded-2xl p-5 border border-[#E3E8EF] shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Open Fraud Rings</span>
            <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <Share2 className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-heading font-bold text-purple-900">
              {summary?.open_rings ?? rings.length}
            </span>
            <Link to="/app/network" className="text-xs text-blue-600 hover:underline font-semibold ml-auto">
              View Graph &rarr;
            </Link>
          </div>
          <div className="text-xs text-purple-700/80 font-medium mt-2">
            Multi-claimant shared identifiers
          </div>
        </div>
      </div>

      {/* Sparkline & Top Signals Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 7-Day Velocity Sparkline */}
        <div className="bg-white rounded-2xl p-6 border border-[#E3E8EF] shadow-xs lg:col-span-1 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2 className="font-heading font-semibold text-slate-900 text-sm">
                7-Day Ingestion Velocity
              </h2>
              <span className="text-[11px] font-mono text-slate-400">Past 7 days</span>
            </div>
            <p className="text-xs text-slate-500">
              Daily claim arrival volume pattern
            </p>
          </div>

          <div className="py-6 flex items-center justify-center">
            {summary?.sparkline_7d && summary.sparkline_7d.length > 0 ? (
              <div className="flex flex-col items-center gap-2">
                {renderSparkline(summary.sparkline_7d)}
                <div className="flex items-center gap-4 text-[10px] text-slate-400 font-mono mt-1">
                  <span>Day -7</span>
                  <span className="text-blue-600 font-bold">Avg: {Math.round(summary.sparkline_7d.reduce((a, b) => a + b, 0) / 7)}/day</span>
                  <span>Today</span>
                </div>
              </div>
            ) : (
              <span className="text-xs text-slate-400">No recent velocity data</span>
            )}
          </div>

          <Link
            to="/app/analytics"
            className="text-xs text-blue-600 font-semibold hover:underline flex items-center justify-between pt-3 border-t border-slate-100"
          >
            <span>Detailed Longitudinal Trends</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Top Risk Signals Breakdown */}
        <div className="bg-white rounded-2xl p-6 border border-[#E3E8EF] shadow-xs lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-heading font-semibold text-slate-900 text-sm">
                Frequent Forensic Signals Triggered
              </h2>
              <p className="text-xs text-slate-500">
                Primary detector anomalies identified across flagged claims
              </p>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600">
              Evidence Catalog
            </span>
          </div>

          <div className="space-y-3">
            {summary?.top_reasons && summary.top_reasons.length > 0 ? (
              summary.top_reasons.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-md bg-white border border-slate-200 text-slate-700 font-mono text-xs flex items-center justify-center font-bold">
                      {idx + 1}
                    </span>
                    <div>
                      <div className="text-xs font-semibold text-slate-800">
                        {item.title || item.reason || 'Forensic Flag'}
                      </div>
                      <div className="text-[11px] font-mono text-slate-500">
                        Signal: {item.evidence_id || item.id || 'ANOMALY'}
                      </div>
                    </div>
                  </div>
                  <span className="text-xs font-mono font-bold px-2 py-1 rounded bg-blue-50 text-blue-700 border border-blue-100">
                    {item.count} claims
                  </span>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-400 py-6 text-center">
                No forensic flags recorded today.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Fraud Rings & Needs Attention Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Open Fraud Rings Section */}
        <div className="bg-white rounded-2xl p-6 border border-[#E3E8EF] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Share2 className="w-4 h-4 text-purple-600" />
                <h2 className="font-heading font-semibold text-slate-900 text-sm">
                  Active Fraud Rings Requiring Action
                </h2>
              </div>
              <Link to="/app/network" className="text-xs text-purple-700 font-semibold hover:underline">
                Explore Network Graph &rarr;
              </Link>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Clusters of 3+ claims sharing strong identifiers (bank account, phone, or duplicate damage photo).
            </p>

            <div className="space-y-3">
              {rings.length > 0 ? (
                rings.map((ring) => (
                  <div
                    key={ring.id}
                    className="p-4 rounded-xl border border-purple-100 bg-purple-50/40 hover:bg-purple-50 transition-colors flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-purple-900">
                          {ring.id}
                        </span>
                        <RiskBadge band={ring.band || 'MEDIUM'} size="sm" />
                      </div>
                      <div className="text-xs text-slate-600 mt-1">
                        {ring.claims_count} claims &bull; {ring.claimants_count} claimants &bull; ₹{Math.round(ring.total_amount || 0).toLocaleString()}
                      </div>
                      <div className="text-[11px] text-purple-800/80 mt-1">
                        {ring.reasons?.[0] || 'Shared financial / photographic identifier'}
                      </div>
                    </div>

                    <Link
                      to={`/app/network?ring=${ring.id}`}
                      className="px-3 py-1.5 rounded-lg bg-white border border-purple-200 text-purple-700 hover:bg-purple-600 hover:text-white text-xs font-semibold transition-colors shrink-0 shadow-xs"
                    >
                      Inspect Ring
                    </Link>
                  </div>
                ))
              ) : (
                <div className="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-xl">
                  No open fraud rings detected. Network graph is clear.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Needs Attention Priority Queue */}
        <div className="bg-white rounded-2xl p-6 border border-[#E3E8EF] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-red-600" />
                <h2 className="font-heading font-semibold text-slate-900 text-sm">
                  Priority Review Queue
                </h2>
              </div>
              <Link to="/app/queue" className="text-xs text-blue-600 font-semibold hover:underline">
                View All Queue &rarr;
              </Link>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Recently flagged claims sorted by urgency and forensic severity score.
            </p>

            <div className="space-y-2.5">
              {recentFlagged.length > 0 ? (
                recentFlagged.slice(0, 5).map((claim) => (
                  <Link
                    key={claim.id}
                    to={`/app/results/${claim.id}`}
                    className="flex items-center justify-between p-3 rounded-xl border border-slate-100 bg-slate-50 hover:bg-blue-50/50 hover:border-blue-200 transition-colors"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-900">
                          {claim.id}
                        </span>
                        <RiskBadge band={claim.risk_band || claim.overall_band || 'LOW'} size="sm" />
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {claim.claimant_name || 'Claimant'} &bull; {claim.claim_type || 'motor'} &bull; ₹{Math.round(claim.claimed_amount || 0).toLocaleString()}
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600" />
                  </Link>
                ))
              ) : (
                <div className="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-xl">
                  Review queue is currently empty.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
