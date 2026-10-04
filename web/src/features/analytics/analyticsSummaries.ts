import type { TrendsVM } from '../../types/vm';

const pct = (n: number) => `${Math.round(n * 100)}%`;

/** Plain-language one-liners for each chart (shown above the chart and read by screen readers). */
export function summarise(t: TrendsVM) {
  const total = t.daily.reduce((a, d) => a + d.low + d.medium + d.high, 0);
  const high = t.daily.reduce((a, d) => a + d.high, 0);
  const avgFlag = t.daily.length
    ? t.daily.reduce((a, d) => a + d.flaggedRate, 0) / t.daily.length
    : 0;
  const peak = t.daily.reduce(
    (best, d) => (d.flaggedRate > best.flaggedRate ? d : best),
    t.daily[0] ?? { date: '—', flaggedRate: 0 },
  );
  const topSignal = t.topSignals[0];
  const topType = [...t.byType].sort(
    (a, b) => b.flagged / (b.total || 1) - a.flagged / (a.total || 1),
  )[0];
  const topModality = [...t.byModality].sort((a, b) => b.flagged - a.flagged)[0];
  const recycled = t.recycledWeekly.reduce((a, w) => a + w.count, 0);
  const rings = t.ringsWeekly.reduce((a, w) => a + w.count, 0);
  const decided = t.decisionsWeekly.reduce((a, w) => a + w.approved + w.rejected + w.requested, 0);
  return {
    volume: `${total} claims in this period, ${high} rated HIGH.`,
    rate: `Average flagged rate ${pct(avgFlag)}; peak ${pct(peak.flaggedRate)} on ${peak.date}.`,
    signals: topSignal
      ? `Most frequent signal: ${topSignal.title} (${topSignal.count}).`
      : 'No signals recorded.',
    byType: topType
      ? `${topType.type} has the highest flagged share (${topType.flagged} of ${topType.total}).`
      : 'No claim-type data.',
    modality: topModality
      ? `Most flags come from ${topModality.modality} checks.`
      : 'No modality data.',
    recycled: `${recycled} recycled-evidence matches across the period.`,
    rings: `${rings} new linked-claims rings detected.`,
    decisions: `${decided} investigator decisions recorded.`,
  };
}
