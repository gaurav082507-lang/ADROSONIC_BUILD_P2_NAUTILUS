import React, { useState } from 'react';

const SEVERITY_COLORS = {
  high: 'border-red-600 bg-red-500/20 text-red-700',
  medium: 'border-amber-500 bg-amber-400/20 text-amber-800',
  low: 'border-blue-500 bg-blue-400/20 text-blue-800',
};

export function BoxOverlay({ imageUrl, boxes = [], onBoxClick }) {
  const [activeBox, setActiveBox] = useState(null);

  return (
    <div className="relative inline-block w-full max-w-2xl mx-auto overflow-hidden rounded-lg border border-rule bg-paper">
      {/* Base Rendered Image */}
      <img
        src={imageUrl}
        alt="Analyzed Document / Image"
        className="w-full h-auto block select-none"
      />

      {/* Normalized Bounding Box Overlays */}
      {boxes.map((b, idx) => {
        const severity = (b.severity || 'medium').toLowerCase();
        const colorClass = SEVERITY_COLORS[severity] || SEVERITY_COLORS.medium;
        const isHovered = activeBox === idx;

        // Normalized fractions [0..1] to CSS percentage strings
        const style = {
          left: `${(b.x || 0) * 100}%`,
          top: `${(b.y || 0) * 100}%`,
          width: `${(b.w || 0.1) * 100}%`,
          height: `${(b.h || 0.05) * 100}%`,
        };

        return (
          <div
            key={idx}
            style={style}
            onClick={() => onBoxClick && onBoxClick(b)}
            onMouseEnter={() => setActiveBox(idx)}
            onMouseLeave={() => setActiveBox(null)}
            className={`absolute border-2 rounded cursor-pointer transition-all duration-150 ${colorClass} ${
              isHovered ? 'ring-2 ring-offset-1 ring-marker scale-[1.02] z-20' : 'z-10'
            }`}
            title={`${b.evidence_id || b.field || 'Flagged item'}: ${b.reason || ''}`}
          >
            {/* Box Label Tag */}
            <span className="absolute -top-5 left-0 text-[10px] font-bold px-1 rounded bg-surface/90 border border-rule shadow-sm truncate max-w-[120px]">
              {b.field || b.evidence_id || `#${idx + 1}`}
            </span>
          </div>
        );
      })}
    </div>
  );
}
