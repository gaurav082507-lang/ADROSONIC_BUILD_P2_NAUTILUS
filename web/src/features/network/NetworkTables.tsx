import type { GraphVM } from '../../types/vm';
import { RiskBadge } from '../../components/RiskBadge';
import { SyntheticBadge } from '../../components/FeatureGate';

/** Accessible table alternative to the canvas graph: the same nodes and edges. */
export default function NetworkTables({ graph }: { graph: GraphVM }) {
  const labelOf = (id: string) => graph.nodes.find((n) => n.id === id)?.label ?? id;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card overflow-x-auto">
        <table className="w-full text-left text-sm" aria-label="Network nodes">
          <caption className="p-4 text-left font-semibold">Nodes ({graph.nodes.length})</caption>
          <thead className="border-y bg-bg text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-2">Label</th>
              <th>Type</th>
              <th>Band</th>
            </tr>
          </thead>
          <tbody>
            {graph.nodes.map((n) => (
              <tr key={n.id} className="border-b">
                <td className="px-4 py-2">
                  {n.label}
                  <SyntheticBadge show={n.synthetic} />
                </td>
                <td className="capitalize">{n.kind}</td>
                <td>{n.band ? <RiskBadge band={n.band} /> : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card overflow-x-auto">
        <table className="w-full text-left text-sm" aria-label="Network links">
          <caption className="p-4 text-left font-semibold">Links ({graph.edges.length})</caption>
          <thead className="border-y bg-bg text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-2">From</th>
              <th>To</th>
              <th>Link</th>
              <th>Strength</th>
            </tr>
          </thead>
          <tbody>
            {graph.edges.map((e) => (
              <tr key={e.id} className="border-b">
                <td className="px-4 py-2">{labelOf(e.source)}</td>
                <td>{labelOf(e.target)}</td>
                <td>{e.label}</td>
                <td className="mono">
                  {e.strength.toFixed(1)}
                  {e.weak ? ' (weak)' : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
