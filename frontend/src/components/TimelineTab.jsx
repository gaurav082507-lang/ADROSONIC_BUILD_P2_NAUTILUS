import React, { useState, useEffect } from 'react';
import { fetchClient } from '@/api/client';
import {
  Calendar,
  Camera,
  FileText,
  Clock,
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
  CheckCircle,
  User,
  Activity,
} from 'lucide-react';

export default function TimelineTab({ resultId }) {
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetchClient(`/results/${resultId}/timeline`)
      .then((data) => {
        setTimeline(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load timeline');
        setLoading(false);
      });
  }, [resultId]);

  if (loading) {
    return (
      <div className="bg-surface p-8 rounded-xl border border-rule shadow-sm text-center text-muted">
        <div className="animate-pulse">Loading chronological evidence timeline...</div>
      </div>
    );
  }

  if (error || !timeline) {
    return (
      <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm text-center text-sm text-red-600">
        Failed to load timeline: {error || 'No data'}
      </div>
    );
  }

  const events = timeline.events || [];
  const contradictions = timeline.contradictions || [];
  const undated = timeline.undated || [];

  const getSourceIcon = (kind, source) => {
    if (kind === 'photo_captured') return <Camera className="w-4 h-4 text-blue-600" />;
    if (kind === 'incident') return <AlertTriangle className="w-4 h-4 text-amber-600" />;
    if (kind === 'document_date' || kind === 'pdf_modified') return <FileText className="w-4 h-4 text-purple-600" />;
    if (source === 'investigator') return <User className="w-4 h-4 text-indigo-600" />;
    if (kind === 'policy_start' || kind === 'policy_end') return <Calendar className="w-4 h-4 text-teal-600" />;
    return <Clock className="w-4 h-4 text-gray-500" />;
  };

  const getBadgeStyle = (source) => {
    switch (source) {
      case 'claimant':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'photo metadata':
      case 'exif':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'document text':
      case 'ocr':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'pdf metadata':
        return 'bg-indigo-100 text-indigo-800 border-indigo-200';
      case 'investigator':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  // Map contradiction connections
  const getContradictionForIndex = (idx) => {
    return contradictions.find((c) => c.from_event === idx || c.to_event === idx);
  };

  return (
    <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-rule pb-4">
        <div>
          <h3 className="text-base font-bold text-ink flex items-center gap-2">
            <Activity className="w-4 h-4 text-marker" />
            Digital Evidence Timeline & Chronology
          </h3>
          <p className="text-xs text-muted mt-0.5">
            Full chronological order of claim facts, metadata timestamps, and physical document dates.
          </p>
        </div>
        <div className="text-[11px] text-muted font-mono bg-paper px-2.5 py-1 rounded border border-rule">
          Assumed Timezone: IST (UTC+05:30)
        </div>
      </div>

      {/* Contradictions summary banner if any */}
      {contradictions.length > 0 && (
        <div className="p-4 rounded-lg bg-red-50 border-2 border-red-400 space-y-2">
          <div className="flex items-center gap-2 text-red-900 font-bold text-xs uppercase tracking-wider">
            <ShieldAlert className="w-4 h-4 text-red-600" />
            {contradictions.length} Chronological Contradiction(s) Detected
          </div>
          {contradictions.map((ct, cIdx) => (
            <div
              key={cIdx}
              className="text-xs text-red-800 bg-white/70 p-2.5 rounded border border-red-200 flex items-start gap-2"
            >
              <span className="font-mono font-bold px-1.5 py-0.5 rounded bg-red-200 text-red-900 text-[10px]">
                {ct.rule_id || ct.rule}
              </span>
              <span>{ct.reason}</span>
            </div>
          ))}
        </div>
      )}

      {/* Vertical Timeline */}
      <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-rule">
        {events.map((ev, idx) => {
          const hasContradiction = getContradictionForIndex(idx);
          const formattedDate = ev.at || ev.timestamp;

          return (
            <div key={ev.id || idx} className="relative group">
              {/* Dot */}
              <div
                className={`absolute -left-[27px] top-1.5 w-6 h-6 rounded-full border-2 flex items-center justify-center bg-white shadow-sm ${
                  hasContradiction ? 'border-red-500 bg-red-50 text-red-600' : 'border-rule text-ink'
                }`}
              >
                {getSourceIcon(ev.kind, ev.source)}
              </div>

              {/* Event card */}
              <div
                className={`p-4 rounded-lg border transition-all ${
                  hasContradiction
                    ? 'border-red-300 bg-red-50/40 shadow-sm'
                    : 'border-rule bg-paper/60 hover:bg-paper'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-ink">{ev.label}</span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase ${getBadgeStyle(
                        ev.source
                      )}`}
                    >
                      {ev.source_badge || ev.source}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-xs font-mono text-muted">
                    <span>{formattedDate}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-rule">
                      {ev.confidence || 'exact'}
                    </span>
                  </div>
                </div>

                {ev.artifact_id && (
                  <div className="mt-2 text-[11px] text-muted">
                    Referenced Asset: <code className="font-bold">{ev.artifact_id}</code>
                  </div>
                )}

                {/* Red connector indicator */}
                {hasContradiction && (
                  <div className="mt-2 pt-2 border-t border-red-200 text-xs text-red-700 font-medium flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-red-600 flex-shrink-0" />
                    <span>
                      Timeline Contradiction ({hasContradiction.rule_id}): {hasContradiction.reason}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Undated group */}
      {undated.length > 0 && (
        <div className="p-4 rounded-lg bg-gray-50 border border-gray-200 space-y-2 mt-6">
          <div className="flex items-center gap-2 text-xs font-bold text-gray-700 uppercase tracking-wider">
            <HelpCircle className="w-4 h-4 text-gray-500" />
            Undated Items (Stripped EXIF Metadata)
          </div>
          <p className="text-xs text-muted">
            The following files carry no embedded capture timestamp (commonly stripped by messaging apps like WhatsApp/Telegram). Timestamps are never guessed:
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            {undated.map((u, uIdx) => (
              <span
                key={uIdx}
                className="px-2.5 py-1 rounded bg-white border border-gray-300 text-xs font-mono text-gray-700"
              >
                {u.label || u.artifact_id}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="text-[11px] text-muted italic bg-paper p-3 rounded border border-rule">
        <b>Timeline Rule:</b> The digital evidence timeline aggregates facts already extracted by individual detectors. It adds no independent score of its own, serving as an investigator audit trace.
      </div>
    </div>
  );
}
