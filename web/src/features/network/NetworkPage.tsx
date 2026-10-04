import { Suspense, lazy, useState } from 'react';
import { Link } from 'react-router-dom';
import { useNetworkGraph, useRings, type GraphParams } from '../../api/hooks';
import type { GraphNodeVM } from '../../types/vm';
import { friendlyError } from '../../lib/errorMessages';
import { inr, pct } from '../../lib/format';
import { RiskBadge } from '../../components/RiskBadge';
import { FeatureGate, SyntheticBadge } from '../../components/FeatureGate';
import { Empty, ErrorState, Loading } from '../../components/States';
import NetworkTables from './NetworkTables';
import RingDrawer from './RingDrawer';
import { nodeTooltip } from './graphStyle';
import { ringStatusLabel } from './ringStatus';

const GraphCanvas = lazy(() => import('./GraphCanvas'));

export default function NetworkPage() {
  return (
    <div>
      <div className="text-sm text-muted">Connected intelligence</div>
      <h1 className="font-display mt-1 text-3xl font-bold">Claims network</h1>
      <p className="mt-2 max-w-3xl text-sm text-muted">
        Claims linked by shared bank accounts, phones, reused photos or invoice numbers. A shared
        garage or hospital alone is a weak link and never forms a ring.
      </p>
      <div className="mt-6">
        <FeatureGate feature="network" title="Claims network">
          <NetworkWorkspace />
        </FeatureGate>
      </div>
    </div>
  );
}

function NetworkWorkspace() {
  const [search, setSearch] = useState('');
  const [params, setParams] = useState<GraphParams>({ hops: 2, minStrength: 0.3, limit: 300 });
  const [ringsOnly, setRingsOnly] = useState(false);
  const [view, setView] = useState<'graph' | 'table'>('graph');
  const [selected, setSelected] = useState<GraphNodeVM>();
  const [openRing, setOpenRing] = useState<string>();
  const graph = useNetworkGraph(params);
  const rings = useRings();
  const focus = () => {
    const id = search.trim();
    if (!id) return setParams((p) => ({ ...p, focusId: undefined, focusType: undefined }));
    const focusType = id.toUpperCase().startsWith('RING')
      ? 'ring'
      : id.toUpperCase().startsWith('CLT')
        ? 'claimant'
        : 'claim';
    setParams((p) => ({ ...p, focusId: id, focusType }));
  };
  const ringMembers = new Set((graph.data?.rings ?? []).flatMap((r) => r.memberIds));
  const shown =
    graph.data && ringsOnly
      ? {
          ...graph.data,
          nodes: graph.data.nodes.filter(
            (n) =>
              ringMembers.has(n.id) ||
              graph.data!.edges.some(
                (e) =>
                  (ringMembers.has(e.source) && e.target === n.id) ||
                  (ringMembers.has(e.target) && e.source === n.id),
              ),
          ),
        }
      : graph.data;
  const visible = shown
    ? {
        ...shown,
        edges: shown.edges.filter(
          (e) =>
            shown.nodes.some((n) => n.id === e.source) &&
            shown.nodes.some((n) => n.id === e.target),
        ),
      }
    : undefined;
  return (
    <div className="grid gap-5 xl:grid-cols-[320px_1fr]">
      <div className="space-y-3">
        <div className="card p-4">
          <h2 className="font-display font-semibold">Detected rings</h2>
          {rings.isLoading && <Loading label="Loading rings…" />}
          {rings.error && (
            <ErrorState
              message={friendlyError((rings.error as any).code, (rings.error as any).message)}
              retry={() => rings.refetch()}
            />
          )}
          <div className="mt-3 space-y-2">
            {(rings.data ?? []).map((r) => (
              <button
                key={r.ringId}
                onClick={() => setOpenRing(r.ringId)}
                className="w-full rounded-lg border p-3 text-left hover:bg-slate-50"
              >
                <div className="flex items-center justify-between">
                  <span className="mono text-xs">{r.ringId}</span>
                  <RiskBadge band={r.band} />
                </div>
                <div className="mt-2 text-sm">
                  {r.claimsCount} claims · {r.claimantsCount} claimants · score {pct(r.ringScore)}
                </div>
                <div className="mt-1 text-xs text-muted">
                  {r.shared.map((s) => s.label).join(' · ') || 'No shared identifiers listed'}
                </div>
                <div className="mt-1 flex items-center text-xs text-muted">
                  {ringStatusLabel(r.status)}
                  {r.totalClaimedAmount !== undefined && ` · ${inr(r.totalClaimedAmount)}`}
                  <SyntheticBadge show={r.synthetic} />
                </div>
              </button>
            ))}
            {rings.data && !rings.data.length && <Empty label="No rings detected." />}
          </div>
        </div>
      </div>
      <div className="space-y-3">
        <div className="card flex flex-wrap items-end gap-3 p-4">
          <label className="text-sm">
            <span className="mb-1 block text-muted">Focus on claim, claimant or ring id</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && focus()}
              className="h-10 w-64 rounded-lg border px-3"
              placeholder="e.g. CLM-DEMO-HIGH"
            />
          </label>
          <button
            onClick={focus}
            className="h-10 rounded-lg bg-ink px-4 text-sm font-semibold text-white"
          >
            Focus
          </button>
          <label className="text-sm">
            <span className="mb-1 block text-muted">Hops</span>
            <select
              value={params.hops}
              onChange={(e) => setParams((p) => ({ ...p, hops: Number(e.target.value) }))}
              className="h-10 rounded-lg border px-2"
            >
              {[1, 2, 3].map((h) => (
                <option key={h}>{h}</option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-muted">
              Minimum link strength {params.minStrength?.toFixed(1)}
            </span>
            <input
              type="range"
              min={0.3}
              max={1}
              step={0.1}
              value={params.minStrength}
              onChange={(e) => setParams((p) => ({ ...p, minStrength: Number(e.target.value) }))}
            />
          </label>
          <label className="flex h-10 items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={ringsOnly}
              onChange={(e) => setRingsOnly(e.target.checked)}
            />
            Rings only
          </label>
          <div
            className="ml-auto flex rounded-lg border p-1 text-sm"
            role="tablist"
            aria-label="View"
          >
            {(['graph', 'table'] as const).map((v) => (
              <button
                key={v}
                role="tab"
                aria-selected={view === v}
                onClick={() => setView(v)}
                className={`rounded-md px-3 py-1.5 capitalize ${view === v ? 'bg-ink text-white' : ''}`}
              >
                {v === 'graph' ? 'Graph' : 'Table view'}
              </button>
            ))}
          </div>
        </div>
        {graph.data?.truncated && (
          <div className="rounded-lg bg-yellow-50 p-3 text-sm text-yellow-900">
            Showing a partial network (node limit reached). Focus on a claim to see its
            neighbourhood.
          </div>
        )}
        {graph.isLoading && <Loading label="Loading network…" />}
        {graph.error && (
          <ErrorState
            message={friendlyError((graph.error as any).code, (graph.error as any).message)}
            retry={() => graph.refetch()}
          />
        )}
        {visible && !visible.nodes.length && <Empty label="No linked claims for this view." />}
        {visible && !!visible.nodes.length && view === 'graph' && (
          <Suspense fallback={<Loading label="Preparing graph…" />}>
            <GraphCanvas graph={visible} highlight={[...ringMembers]} onSelect={setSelected} />
          </Suspense>
        )}
        {visible && !!visible.nodes.length && view === 'table' && <NetworkTables graph={visible} />}
        <div className="flex flex-wrap gap-4 text-xs text-muted">
          <span>● Claim colour = band (LOW / MEDIUM / HIGH, named in the tooltip)</span>
          <span>● Blue = claimant</span>
          <span>● Grey = shared identifier</span>
          <span>– – Dashed = weak link (shared garage/hospital)</span>
        </div>
        {selected && (
          <div
            className="card flex flex-wrap items-center justify-between gap-3 p-4"
            aria-live="polite"
          >
            <div>
              <div className="text-sm font-semibold">{nodeTooltip(selected)}</div>
              {!!selected.flags.length && (
                <div className="mt-1 text-xs text-muted">Flags: {selected.flags.join(', ')}</div>
              )}
            </div>
            {selected.kind === 'claim' && (
              <Link
                to={`/app/results/${selected.id}`}
                className="rounded-lg border px-3 py-2 text-sm"
              >
                Open claim
              </Link>
            )}
          </div>
        )}
      </div>
      {openRing && <RingDrawer ringId={openRing} onClose={() => setOpenRing(undefined)} />}
    </div>
  );
}
