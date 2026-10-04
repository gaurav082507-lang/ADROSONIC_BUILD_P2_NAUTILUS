import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchClient } from '@/api/client';
import { RiskBadge } from '@/components/RiskBadge';
import { Layers, ChevronLeft, ChevronRight, ArrowRight } from 'lucide-react';

export default function HistoryPage() {
  const [history, setHistory] = useState({ items: [], total: 0, page: 1, page_size: 20 });
  const [page, setPage] = useState(1);
  const [modeFilter, setModeFilter] = useState('');
  const [bandFilter, setBandFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    let url = `/history?page=${page}&page_size=15`;
    if (modeFilter) url += `&mode=${modeFilter}`;
    if (bandFilter) url += `&band=${bandFilter}`;

    fetchClient(url)
      .then((data) => {
        if (active) {
          setHistory(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message || 'Failed to load case history');
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [page, modeFilter, bandFilter]);

  const totalPages = Math.ceil(history.total / (history.page_size || 15)) || 1;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">Investigation History & Queue</h1>
          <p className="text-muted text-sm mt-0.5">
            Audit log of all analyzed claims, documents, and forensic inspection reports.
          </p>
        </div>
        <Link
          to="/app/analyze"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-ink text-surface text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          <Layers className="w-4 h-4" />
          <span>New Analysis</span>
        </Link>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-xl border border-rule bg-surface shadow-sm flex flex-wrap items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-muted">Mode:</span>
          <select
            value={modeFilter}
            onChange={(e) => { setModeFilter(e.target.value); setPage(1); }}
            className="p-1.5 rounded border border-rule bg-paper"
          >
            <option value="">All Modes</option>
            <option value="claim">Claim Package</option>
            <option value="image">Single Image</option>
            <option value="document">Document</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-semibold text-muted">Risk Band:</span>
          <select
            value={bandFilter}
            onChange={(e) => { setBandFilter(e.target.value); setPage(1); }}
            className="p-1.5 rounded border border-rule bg-paper"
          >
            <option value="">All Bands</option>
            <option value="HIGH">HIGH Risk</option>
            <option value="MEDIUM">MEDIUM Risk</option>
            <option value="LOW">LOW Risk</option>
          </select>
        </div>

        <div className="ml-auto text-muted">
          Showing {history.items.length} of {history.total} cases
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="p-12 text-center text-muted">Loading investigation history...</div>
      ) : error ? (
        <div className="p-6 text-center text-red-600 bg-red-50 rounded-lg">{error}</div>
      ) : history.items.length === 0 ? (
        <div className="p-12 text-center text-muted border border-rule rounded-xl bg-surface">
          No analysis cases found matching the selected filters.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-rule bg-surface shadow-sm">
          <table className="w-full text-left text-xs text-ink">
            <thead className="bg-paper uppercase text-muted font-semibold border-b border-rule">
              <tr>
                <th className="px-4 py-3">Case ID</th>
                <th className="px-4 py-3">Created Date</th>
                <th className="px-4 py-3">Mode</th>
                <th className="px-4 py-3">Risk Assessment</th>
                <th className="px-4 py-3">Flagged Items</th>
                <th className="px-4 py-3">Primary Finding</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule font-medium">
              {history.items.map((item) => (
                <tr key={item.id} className="hover:bg-paper/50 transition-colors">
                  <td className="px-4 py-3 font-mono font-semibold text-blue-900">
                    <Link to={`/app/results/${item.id}`} className="hover:underline">
                      {item.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted">
                    {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                  <td className="px-4 py-3 capitalize font-semibold">
                    {item.mode}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <RiskBadge band={item.overall_band} />
                      <span className="font-bold">{Math.round(item.overall_risk * 100)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted">
                    {item.evidence_count} evidence items
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate text-muted" title={item.top_reason || ''}>
                    {item.top_reason || 'No major findings'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/app/results/${item.id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-ink hover:underline"
                    >
                      <span>View</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-muted pt-2">
          <span>Page {page} of {totalPages}</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded border border-rule bg-surface disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded border border-rule bg-surface disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
