import React from 'react';

export default function Logo({ size = "md", dark = false, className = "" }) {
  const iconSizes = {
    sm: "w-5 h-5",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  };

  const textSizes = {
    sm: "text-lg",
    md: "text-xl",
    lg: "text-2xl",
  };

  return (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      {/* Evidence-yellow lens mark (circle with forensic scan line) */}
      <div className={`relative flex items-center justify-center shrink-0 ${iconSizes[size] || iconSizes.md}`}>
        <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
          {/* Outer lens ring */}
          <circle cx="16" cy="16" r="14" stroke="#0F1B2D" strokeWidth="2.5" className={dark ? "stroke-white/90" : "stroke-ink"} />
          {/* Optical lens highlight */}
          <circle cx="16" cy="16" r="10" stroke="#F5C518" strokeWidth="2" strokeDasharray="3 2" />
          {/* Scan line */}
          <line x1="6" y1="16" x2="26" y2="16" stroke="#F5C518" strokeWidth="2.5" strokeLinecap="round" />
          {/* Core focal spark */}
          <circle cx="16" cy="16" r="2.5" fill="#F5C518" />
        </svg>
      </div>

      {/* Wordmark */}
      <div className="flex items-baseline tracking-tight">
        <span className={`font-heading font-bold ${dark ? "text-white" : "text-ink"} ${textSizes[size] || textSizes.md}`}>
          Lucen
        </span>
        <span className={`font-heading font-semibold ml-1 text-accent ${textSizes[size] || textSizes.md}`}>
          AI
        </span>
      </div>
    </div>
  );
}
