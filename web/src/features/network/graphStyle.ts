import type { Band, GraphNodeVM } from '../../types/vm';

export const BAND_COLOR: Record<Band, string> = {
  LOW: '#16A34A',
  MEDIUM: '#D97706',
  HIGH: '#DC2626',
};

export function nodeColor(node: GraphNodeVM) {
  if (node.kind === 'claim') return node.band ? BAND_COLOR[node.band] : '#5B6B82';
  if (node.kind === 'claimant') return '#3B82F6';
  if (node.kind === 'ring') return '#F5C518';
  return '#94A3B8';
}

export function nodeSize(node: GraphNodeVM) {
  if (node.kind === 'claim') return 7;
  if (node.kind === 'claimant') return 5;
  return 3.5;
}

/** Tooltip text always includes the band word, never colour alone. */
export function nodeTooltip(node: GraphNodeVM) {
  const kind = node.kind === 'other' ? 'node' : node.kind;
  const band = node.band ? ` · ${node.band}` : '';
  const risk = node.risk !== undefined ? ` · ${Math.round(node.risk * 100)}% risk` : '';
  const synthetic = node.synthetic ? ' · synthetic history' : '';
  return `${node.label} (${kind}${band}${risk})${synthetic}`;
}
