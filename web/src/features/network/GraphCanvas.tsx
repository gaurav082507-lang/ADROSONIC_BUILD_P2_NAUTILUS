import { useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { GraphEdgeVM, GraphNodeVM, GraphVM } from '../../types/vm';
import { nodeColor, nodeSize, nodeTooltip } from './graphStyle';

type FGNode = GraphNodeVM & { x?: number; y?: number };
type FGLink = Omit<GraphEdgeVM, 'source' | 'target'> & {
  source: string | FGNode;
  target: string | FGNode;
};

/** Force-directed graph. Loaded lazily by NetworkPage so the library stays out of the main bundle. */
export default function GraphCanvas({
  graph,
  highlight,
  onSelect,
  height = 520,
}: {
  graph: GraphVM;
  highlight?: string[];
  onSelect: (node: GraphNodeVM) => void;
  height?: number;
}) {
  const wrap = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);
  useEffect(() => {
    if (!wrap.current) return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(Math.max(320, entry.contentRect.width)),
    );
    observer.observe(wrap.current);
    return () => observer.disconnect();
  }, []);
  const data = useMemo(
    () => ({
      nodes: graph.nodes.map((n) => ({ ...n })) as FGNode[],
      links: graph.edges.map((e) => ({ ...e })) as FGLink[],
    }),
    [graph],
  );
  const marked = useMemo(() => new Set(highlight ?? []), [highlight]);
  return (
    <div
      ref={wrap}
      className="overflow-hidden rounded-xl border bg-white"
      aria-label="Network graph"
    >
      <ForceGraph2D
        graphData={data}
        width={width}
        height={height}
        cooldownTicks={120}
        nodeLabel={(n) => nodeTooltip(n as FGNode)}
        nodeRelSize={1}
        nodeVal={(n) => nodeSize(n as FGNode) ** 2}
        linkWidth={(l) => 0.6 + (l as FGLink).strength * 2.2}
        linkColor={(l) => ((l as FGLink).weak ? '#CBD5E1' : '#64748B')}
        linkLineDash={(l) => ((l as FGLink).weak ? [3, 3] : null)}
        linkLabel={(l) => (l as FGLink).label}
        onNodeClick={(n) => onSelect(n as FGNode)}
        nodeCanvasObject={(n, ctx, scale) => {
          const node = n as FGNode;
          const r = nodeSize(node);
          ctx.beginPath();
          ctx.arc(node.x ?? 0, node.y ?? 0, r, 0, 2 * Math.PI);
          ctx.fillStyle = nodeColor(node);
          ctx.fill();
          if (marked.has(node.id)) {
            ctx.lineWidth = 2 / scale;
            ctx.strokeStyle = '#F5C518';
            ctx.stroke();
          }
          if (node.kind !== 'identifier' || scale > 1.6) {
            ctx.font = `${11 / scale}px Inter, sans-serif`;
            ctx.fillStyle = '#0B1220';
            ctx.textAlign = 'center';
            ctx.fillText(node.label, node.x ?? 0, (node.y ?? 0) + r + 10 / scale);
          }
        }}
      />
    </div>
  );
}
