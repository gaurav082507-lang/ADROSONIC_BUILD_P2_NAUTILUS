import React from 'react';
import { CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-react';

const BAND_CONFIG = {
  HIGH: {
    color: 'text-[#DC2626]',
    bg: 'bg-[#DC2626]/10',
    border: 'border-[#DC2626]/20',
    icon: AlertOctagon,
    label: 'HIGH'
  },
  MEDIUM: {
    color: 'text-[#D97706]',
    bg: 'bg-[#D97706]/10',
    border: 'border-[#D97706]/20',
    icon: AlertTriangle,
    label: 'MEDIUM'
  },
  LOW: {
    color: 'text-[#16A34A]',
    bg: 'bg-[#16A34A]/10',
    border: 'border-[#16A34A]/20',
    icon: CheckCircle2,
    label: 'LOW'
  }
};

export default function RiskBadge({ band, size = "md", className = "" }) {
  const b = (band || "LOW").toUpperCase();
  const config = BAND_CONFIG[b] || BAND_CONFIG.LOW;
  const Icon = config.icon;

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs gap-1",
    md: "px-2.5 py-1 text-xs gap-1.5",
    lg: "px-3.5 py-1.5 text-sm gap-2 font-bold",
  };

  return (
    <span
      className={`inline-flex items-center font-heading font-semibold rounded-full border ${config.bg} ${config.color} ${config.border} ${sizeClasses[size] || sizeClasses.md} ${className}`}
      aria-label={`Risk band: ${config.label}`}
    >
      <Icon className={size === "lg" ? "w-4 h-4 shrink-0" : "w-3.5 h-3.5 shrink-0"} />
      <span className="tracking-wide uppercase">{config.label}</span>
    </span>
  );
}

export { RiskBadge };
