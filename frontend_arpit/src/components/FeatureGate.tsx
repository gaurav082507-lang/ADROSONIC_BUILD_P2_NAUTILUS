import type { ReactNode } from 'react';
import { useFeature, type FeatureName } from '../lib/featureFlags';

/** Renders children only when the backend feature is enabled; otherwise a clean "coming soon" card. */
export function FeatureGate({
  feature,
  title,
  children,
}: {
  feature: FeatureName;
  title: string;
  children: ReactNode;
}) {
  const on = useFeature(feature);
  if (on) return <>{children}</>;
  return (
    <div className="card p-6" data-testid={`feature-off-${feature}`}>
      <div className="font-semibold">{title} is not enabled</div>
      <p className="mt-2 text-sm text-muted">
        This backend capability is switched off. Enable it with VITE_FEATURES once the endpoint is
        available – Lucen never shows fabricated data in its place.
      </p>
    </div>
  );
}

export function SyntheticBadge({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <span
      className="ml-2 inline-flex items-center rounded-full border border-dashed border-slate-400 px-2 py-0.5 text-[11px] font-medium text-slate-600"
      title="Generated historical data used to illustrate patterns"
    >
      Synthetic history
    </span>
  );
}
