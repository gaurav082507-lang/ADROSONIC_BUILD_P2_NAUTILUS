import React from 'react';
import { Copy, AlertOctagon } from 'lucide-react';

export default function DuplicateBanner({ evidenceList, artifacts }) {
  const dupEvidence = evidenceList.filter(
    (e) =>
      e.id === 'IMG-DUP-01' ||
      e.id === 'IMG-DUP-02' ||
      e.id === 'DOC-DUP-01' ||
      e.id === 'CLM-X-04'
  );

  if (!dupEvidence || dupEvidence.length === 0) {
    return null;
  }

  const primaryDup = dupEvidence[0];
  const details = primaryDup.details || {};
  const otherClaimId = details.other_claim_id || details.other_id || 'Earlier Claim';
  const otherClaimant = details.other_claimant || 'Another Claimant';
  const matchType = details.match_type || 'duplicate';
  const sim = details.similarity || details.sim || 0.9;
  const simPct = Math.round(sim * 100);

  // Thumbnails
  const currentThumb =
    details.thumbnail_current ||
    artifacts?.preview_image ||
    artifacts?.preview_img_1 ||
    artifacts?.preview_img_2 ||
    artifacts?.thumbnail;

  const earlierThumb = details.thumbnail_earlier;

  return (
    <div className="rounded-xl border-2 border-red-500 bg-red-50/80 p-5 shadow-sm space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-red-600 text-white">
            <AlertOctagon className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-red-900">
                Recycled Evidence: Reused in Another Claim
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-red-200 text-red-800">
                {matchType} Match
              </span>
            </div>
            <p className="text-xs text-red-700 mt-0.5">
              This evidence matches an earlier submission in claim{' '}
              <span className="font-bold underline">{otherClaimId}</span> filed by{' '}
              <span className="font-semibold">{otherClaimant}</span> ({simPct}% similarity).
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-red-100 text-red-800 border border-red-200">
            {simPct}% Similar
          </span>
        </div>
      </div>

      {/* Side-by-side thumbnail comparison */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-white/70 p-3 rounded-lg border border-red-200">
        <div className="space-y-1.5 text-center">
          <span className="text-[11px] font-bold text-ink uppercase tracking-wider">
            Current Claim Photo
          </span>
          <div className="h-44 rounded-md border border-rule bg-paper overflow-hidden flex items-center justify-center">
            {currentThumb ? (
              <img
                src={currentThumb}
                alt="Current claim upload"
                className="max-h-full max-w-full object-contain"
              />
            ) : (
              <div className="text-xs text-muted">Preview available in Image tab</div>
            )}
          </div>
        </div>

        <div className="space-y-1.5 text-center">
          <span className="text-[11px] font-bold text-red-800 uppercase tracking-wider">
            Earlier Claim Photo ({otherClaimId})
          </span>
          <div className="h-44 rounded-md border border-red-300 bg-red-50/50 overflow-hidden flex items-center justify-center">
            {earlierThumb ? (
              <img
                src={earlierThumb.startsWith('http') || earlierThumb.startsWith('/') ? earlierThumb : `/api/v1/artifacts/${earlierThumb}`}
                alt="Earlier claim match"
                className="max-h-full max-w-full object-contain"
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            ) : (
              <div className="text-xs text-muted flex flex-col items-center gap-1 p-4">
                <Copy className="w-6 h-6 text-red-400" />
                <span>Indexed signature match in {otherClaimId}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-red-800 pt-1">
        <span>
          <b>Diagnostic Note:</b> {primaryDup.reason}
        </span>
        <span className="font-semibold text-red-900">
          Rule O4 Activated: Escalate to Fraud Investigation
        </span>
      </div>
    </div>
  );
}
