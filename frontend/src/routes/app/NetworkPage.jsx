import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Share2,
  Search,
  Table,
  X,
  FileDown,
  ExternalLink,
  Shield,
  ChevronRight
} from 'lucide-react';
import { fetchClient } from '../../api/client';
import RiskBadge from '../../components/RiskBadge';

export default function NetworkPage() {
  const [searchParams] = useSearchParams();
  const ringParam = searchParams.get('ring');

  const [viewMode, setViewMode] = useState('graph'); // 'graph' | 'table'
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [rings, setRings] = useState([]);
  const [selectedRing, setSelectedRing] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  // Filters
  const [focusId, setFocusId] = useState('');
  const [hops, setHops] = useState(2);
  const [minStrength, setMinStrength] = useState(0.3);

  // Status update modal / form state
  const [auditNote, setAuditNote] = useState('');
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [statusError, setStatusError] = useState('');

  const svgRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    function updateSize() {
      if (svgRef.current) {
        const { width, height } = svgRef.current.getBoundingClientRect();
        if (width > 0 && height > 0) {
          setDimensions({ width, height: Math.max(height, 550) });
        }
      }
    }
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, [viewMode]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const qParams = new URLSearchParams();
      if (focusId.trim()) {
        qParams.set('focus_type', focusId.startsWith('CLM-') ? 'claim' : 'claimant');
        qParams.set('focus_id', focusId.trim());
      }
      qParams.set('hops', String(hops));
      qParams.set('min_strength', String(minStrength));

      const [gData, rData] = await Promise.all([
        fetchClient(`/network/graph?${qParams.toString()}`).catch(() => ({ nodes: [], edges: [] })),
        fetchClient('/network/rings').catch(() => ({ items: [] })),
      ]);

      setGraphData(gData);
      setRings(rData.items || []);

      if (ringParam) {
        const matched = (rData.items || []).find((r) => r.id === ringParam);
        if (matched) {
          fetchRingDetail(matched.id);
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to load network intelligence');
    } finally {
      setLoading(false);
    }
  }

  async function fetchRingDetail(ringId) {
    try {
      const detail = await fetchClient(`/network/rings/${ringId}`);
      setSelectedRing(detail);
      setAuditNote('');
      setStatusError('');
    } catch (err) {
      console.error('Error fetching ring details:', err);
    }
  }

  useEffect(() => {
    loadData();
  }, [hops, minStrength]);

  // Layout node positions with deterministic circular / radial force layout
  const layoutNodes = useMemo(() => {
    const nodes = graphData.nodes || [];
    const count = nodes.length;
    if (count === 0) return [];

    const cx = dimensions.width / 2;
    const cy = dimensions.height / 2;
    const radius = Math.min(cx, cy) * 0.75;

    // Separate claims, claimants, and identifiers for layered orbits
    const claims = nodes.filter((n) => n.type === 'claim');
    const claimants = nodes.filter((n) => n.type === 'claimant');
    const identifiers = nodes.filter((n) => !['claim', 'claimant'].includes(n.type));

    const positioned = [];

    // Outer orbit: claims
    claims.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, claims.length);
      positioned.push({
        ...node,
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
      });
    });

    // Middle orbit: claimants
    claimants.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, claimants.length) + 0.3;
      positioned.push({
        ...node,
        x: cx + radius * 0.55 * Math.cos(angle),
        y: cy + radius * 0.55 * Math.sin(angle),
      });
    });

    // Inner core: identifiers
    identifiers.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, identifiers.length) + 0.6;
      const r = identifiers.length === 1 ? 0 : radius * 0.3;
      positioned.push({
        ...node,
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      });
    });

    return positioned;
  }, [graphData.nodes, dimensions]);

  // Node position map
  const posMap = useMemo(() => {
    const map = new Map();
    layoutNodes.forEach((n) => map.set(n.id, { x: n.x, y: n.y }));
    return map;
  }, [layoutNodes]);

  async function handleStatusChange(newStatus) {
    if (!selectedRing) return;
    if (['confirmed', 'dismissed'].includes(newStatus) && !auditNote.trim()) {
      setStatusError(`An audit explanation note is mandatory to mark ring as ${newStatus}.`);
      return;
    }
    setStatusUpdating(true);
    setStatusError('');
    try {
      const updated = await fetchClient(`/network/rings/${selectedRing.id}/status`, {
        method: 'POST',
        body: JSON.stringify({
          status: newStatus,
          note: auditNote.trim() || undefined,
        }),
      });
      setSelectedRing((prev) => ({
        ...prev,
        status: updated.to_status,
      }));
      setAuditNote('');
      // Refresh rings list
      const rData = await fetchClient('/network/rings');
      setRings(rData.items || []);
    } catch (err) {
      setStatusError(err.message || 'Failed to update ring status');
    } finally {
      setStatusUpdating(false);
    }
  }

  function getNodeColor(node) {
    if (node.type === 'claim') {
      if (node.band === 'HIGH') return '#DC2626';
      if (node.band === 'MEDIUM') return '#D97706';
      return '#3B82F6';
    }
    if (node.type === 'claimant') return '#8B5CF6';
    if (node.type === 'bank') return '#10B981';
    if (node.type === 'phone') return '#06B6D4';
    if (node.type === 'image_cluster') return '#F59E0B';
    if (node.type === 'facility' || node.type === 'provider') return '#64748B';
    return '#6B7280';
  }

  return (
    <div className="space-y-5 max-w-7xl mx-auto h-[calc(100vh-100px)] flex flex-col font-sans">
      {/* Top Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-heading font-bold text-slate-900 tracking-tight">
              Fraud Ring & Network Intelligence
            </h1>
            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
              {rings.length} Rings Detected
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Bipartite entity graph with Louvain community clusters &amp; audited investigator status.
          </p>
        </div>

        {/* View Toggle & Search */}
        <div className="flex items-center gap-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              loadData();
            }}
            className="relative"
          >
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="search"
              placeholder="Focus Claim / Claimant ID..."
              value={focusId}
              onChange={(e) => setFocusId(e.target.value)}
              className="bg-white border border-[#E3E8EF] hover:border-slate-300 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-all w-56"
            />
          </form>

          {/* Graph vs Table Toggle */}
          <div className="flex items-center bg-slate-200/60 p-0.5 rounded-xl border border-slate-200 text-xs">
            <button
              onClick={() => setViewMode('graph')}
              className={`flex items-center gap-1 px-3 py-1 rounded-lg font-medium transition-all ${
                viewMode === 'graph' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Share2 className="w-3.5 h-3.5" />
              <span>Graph</span>
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`flex items-center gap-1 px-3 py-1 rounded-lg font-medium transition-all ${
                viewMode === 'table' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Table className="w-3.5 h-3.5" />
              <span>Table</span>
            </button>
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white border border-[#E3E8EF] rounded-xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-4 text-xs shrink-0 shadow-xs">
        <div className="flex items-center gap-6">
          {/* Hops Slider */}
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-600">Expansion Hops:</span>
            <input
              type="range"
              min="1"
              max="4"
              value={hops}
              onChange={(e) => setHops(Number(e.target.value))}
              className="w-20 accent-blue-600 cursor-pointer"
            />
            <span className="font-mono font-bold text-slate-800 w-4">{hops}</span>
          </div>

          <div className="h-4 w-px bg-slate-200" />

          {/* Edge Strength Filter */}
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-600">Min Edge Strength:</span>
            <select
              value={minStrength}
              onChange={(e) => setMinStrength(Number(e.target.value))}
              className="bg-[#F5F7FA] border border-slate-200 rounded-lg px-2.5 py-1 text-xs font-medium text-slate-700 outline-none"
            >
              <option value={0.0}>All Edges (&gt;= 0.0)</option>
              <option value={0.3}>Default (&gt;= 0.3 - Includes Garages)</option>
              <option value={0.6}>Strong + Medium (&gt;= 0.6)</option>
              <option value={1.0}>Strong Only (1.0 - Bank/Phone/Photo)</option>
            </select>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-[11px] text-slate-500">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#3B82F6]" />
            <span>Claim</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#8B5CF6]" />
            <span>Claimant</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
            <span>Bank</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#06B6D4]" />
            <span>Phone</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" />
            <span>Duplicate Photo</span>
          </div>
        </div>
      </div>

      {/* Main Workspace (Graph or Table) */}
      <div className="flex-1 relative bg-white border border-[#E3E8EF] rounded-2xl overflow-hidden shadow-xs flex">
        {/* Left/Center: Visualizer or Table */}
        <div className="flex-1 h-full overflow-hidden relative flex flex-col">
          {viewMode === 'graph' ? (
            <div ref={svgRef} className="w-full h-full relative bg-[#0B1220] select-none">
              {/* SVG Canvas */}
              <svg width="100%" height="100%" className="w-full h-full">
                {/* Edges */}
                <g className="edges">
                  {graphData.edges?.map((edge, idx) => {
                    const src = posMap.get(edge.source);
                    const tgt = posMap.get(edge.target);
                    if (!src || !tgt) return null;
                    const isStrong = edge.strength >= 1.0;
                    const isMedium = edge.strength >= 0.6 && edge.strength < 1.0;
                    return (
                      <line
                        key={idx}
                        x1={src.x}
                        y1={src.y}
                        x2={tgt.x}
                        y2={tgt.y}
                        stroke={isStrong ? '#3B82F6' : isMedium ? '#818CF8' : '#475569'}
                        strokeWidth={isStrong ? 2.5 : isMedium ? 1.5 : 1}
                        strokeDasharray={isMedium ? '4 2' : !isStrong ? '2 2' : undefined}
                        strokeOpacity={0.65}
                      />
                    );
                  })}
                </g>

                {/* Nodes */}
                <g className="nodes">
                  {layoutNodes.map((node) => {
                    const color = getNodeColor(node);
                    const isSelected = selectedNode?.id === node.id;
                    const r = node.type === 'claim' ? 14 : node.type === 'claimant' ? 12 : 10;
                    return (
                      <g
                        key={node.id}
                        transform={`translate(${node.x}, ${node.y})`}
                        onClick={() => setSelectedNode(node)}
                        className="cursor-pointer group"
                      >
                        {isSelected && (
                          <circle
                            r={r + 6}
                            fill="none"
                            stroke="#F5C518"
                            strokeWidth="2.5"
                            className="animate-pulse"
                          />
                        )}
                        <circle
                          r={r}
                          fill={color}
                          stroke="#0B1220"
                          strokeWidth="2"
                          className="transition-transform group-hover:scale-110"
                        />
                        {/* Node Label */}
                        <text
                          y={r + 14}
                          textAnchor="middle"
                          fill="#CBD5E1"
                          fontSize="10"
                          fontFamily="sans-serif"
                          className="pointer-events-none drop-shadow-xs"
                        >
                          {node.label || node.id}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </svg>

              {/* Node Inspector Overlay Card */}
              {selectedNode && (
                <div className="absolute top-4 left-4 p-4 rounded-xl bg-slate-900/90 backdrop-blur-md border border-slate-700 text-white w-64 shadow-xl text-xs z-10">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono font-bold text-blue-400 uppercase text-[11px]">
                      {selectedNode.type} Node
                    </span>
                    <button
                      onClick={() => setSelectedNode(null)}
                      className="text-slate-400 hover:text-white"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="font-semibold text-slate-100 text-sm mb-1">
                    {selectedNode.label || selectedNode.id}
                  </div>
                  <div className="text-slate-400 text-[11px] mb-3">
                    ID: <span className="font-mono text-slate-300">{selectedNode.id}</span>
                  </div>
                  {selectedNode.type === 'claim' && (
                    <Link
                      to={`/app/results/${selectedNode.id}`}
                      className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg bg-blue-600 hover:bg-blue-500 font-semibold text-white transition-colors"
                    >
                      <span>View Claim Forensic Dossier</span>
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  )}
                </div>
              )}
            </div>
          ) : (
            /* Table View Mode (Accessible fallback) */
            <div className="flex-1 overflow-auto p-5">
              <h3 className="font-heading font-semibold text-slate-900 text-sm mb-3">
                Network Entities &amp; Connected Links
              </h3>
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px]">
                    <th className="py-2 px-3">Node Label</th>
                    <th className="py-2 px-3">Type</th>
                    <th className="py-2 px-3">Identifier / Hash</th>
                    <th className="py-2 px-3">Direct Links</th>
                    <th className="py-2 px-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {graphData.nodes?.map((node) => {
                    const connections = graphData.edges?.filter(
                      (e) => e.source === node.id || e.target === node.id
                    ).length;
                    return (
                      <tr key={node.id} className="hover:bg-slate-50">
                        <td className="py-2.5 px-3 font-semibold text-slate-800">
                          {node.label || node.id}
                        </td>
                        <td className="py-2.5 px-3 uppercase text-[10px] font-mono text-slate-500">
                          {node.type}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-slate-600">
                          {node.id}
                        </td>
                        <td className="py-2.5 px-3 font-mono font-bold text-blue-600">
                          {connections} edges
                        </td>
                        <td className="py-2.5 px-3">
                          {node.type === 'claim' ? (
                            <Link
                              to={`/app/results/${node.id}`}
                              className="text-blue-600 hover:underline font-semibold"
                            >
                              Inspect &rarr;
                            </Link>
                          ) : (
                            <button
                              onClick={() => {
                                setFocusId(node.id);
                                loadData();
                              }}
                              className="text-slate-600 hover:underline"
                            >
                              Focus
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right Drawer: Detected Fraud Rings Sidebar */}
        <div className="w-80 border-l border-[#E3E8EF] bg-slate-50 flex flex-col shrink-0">
          <div className="p-4 border-b border-slate-200 bg-white flex items-center justify-between">
            <div>
              <h3 className="font-heading font-bold text-slate-900 text-sm">
                Detected Fraud Rings
              </h3>
              <p className="text-[11px] text-slate-500">
                Clusters sharing &ge; 3 claims &bull; &ge; 2 claimants
              </p>
            </div>
            <span className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 font-mono font-bold text-xs flex items-center justify-center">
              {rings.length}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
            {rings.map((ring) => {
              const isSelected = selectedRing?.id === ring.id;
              return (
                <div
                  key={ring.id}
                  onClick={() => fetchRingDetail(ring.id)}
                  className={`p-3.5 rounded-xl border text-xs cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-purple-50/80 border-purple-400 ring-1 ring-purple-400 shadow-xs'
                      : 'bg-white border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono font-bold text-slate-900">
                      {ring.id}
                    </span>
                    <RiskBadge band={ring.band || 'MEDIUM'} size="sm" />
                  </div>
                  <div className="text-slate-600 flex items-center justify-between text-[11px] mb-1">
                    <span>{ring.claims_count} claims &bull; {ring.claimants_count} claimants</span>
                    <span className="font-mono font-bold text-slate-900">
                      ₹{Math.round(ring.total_amount || 0).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-[11px] text-purple-700 line-clamp-2">
                    {ring.reasons?.[0] || 'Shared bank or photo cluster'}
                  </div>
                  <div className="mt-2 flex items-center justify-between pt-2 border-t border-slate-100 text-[10px] text-slate-400">
                    <span className="uppercase font-mono font-bold text-slate-500">
                      Status: {ring.status || 'open'}
                    </span>
                    <span className="text-blue-600 font-semibold flex items-center gap-0.5">
                      View details <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Slide-over Drawer for Ring Details & Audit Actions */}
      {selectedRing && (
        <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-white shadow-2xl z-50 border-l border-slate-200 flex flex-col justify-between animate-in slide-in-from-right duration-200">
          {/* Header */}
          <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-slate-900 text-base">
                  {selectedRing.id}
                </span>
                <RiskBadge band={selectedRing.band || 'MEDIUM'} size="sm" />
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Investigator Fraud Ring Audit &amp; Member Dossier
              </p>
            </div>
            <button
              onClick={() => setSelectedRing(null)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body Content */}
          <div className="flex-1 overflow-y-auto p-5 space-y-5 text-xs">
            {/* Status & Metrics Box */}
            <div className="p-4 rounded-xl bg-purple-50/60 border border-purple-100 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-600 font-semibold">Ring Status:</span>
                <span className="font-mono font-bold uppercase px-2 py-0.5 rounded bg-purple-200 text-purple-900 text-[11px]">
                  {selectedRing.status || 'open'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600 font-semibold">Total Exposure:</span>
                <span className="font-mono font-bold text-slate-900 text-sm">
                  ₹{Math.round(selectedRing.total_amount || 0).toLocaleString()}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600 font-semibold">Risk Formula Score:</span>
                <span className="font-mono font-bold text-slate-900">
                  {Math.round((selectedRing.ring_score || 0) * 100)} / 100
                </span>
              </div>
            </div>

            {/* Reasons / Shared Signals */}
            <div>
              <h4 className="font-heading font-semibold text-slate-900 text-xs mb-2">
                Shared Correlation Reasons
              </h4>
              <ul className="space-y-1.5 list-disc list-inside text-slate-700 bg-slate-50 p-3 rounded-xl border border-slate-200">
                {(selectedRing.reasons || []).map((r, i) => (
                  <li key={i} className="text-xs leading-relaxed">
                    {r}
                  </li>
                ))}
              </ul>
            </div>

            {/* Member Claims List */}
            <div>
              <h4 className="font-heading font-semibold text-slate-900 text-xs mb-2">
                Member Claims ({selectedRing.claims_count})
              </h4>
              <div className="space-y-2">
                {(selectedRing.member_claim_ids || []).map((cid) => (
                  <div
                    key={cid}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-white border border-slate-200 hover:border-blue-300"
                  >
                    <span className="font-mono font-semibold text-slate-800">{cid}</span>
                    <Link
                      to={`/app/results/${cid}`}
                      className="text-blue-600 font-semibold hover:underline flex items-center gap-1"
                    >
                      <span>Inspect Dossier</span>
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  </div>
                ))}
              </div>
            </div>

            {/* Ring Status Audit Form (Principle P2) */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-3">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-slate-700" />
                <h4 className="font-heading font-semibold text-slate-900 text-xs">
                  Investigator Status Action (Audited)
                </h4>
              </div>
              <p className="text-[11px] text-slate-500">
                Human investigators decide ring status. Marking as Confirmed or Dismissed strictly requires an explanation note for the permanent audit trail.
              </p>

              <textarea
                placeholder="Enter mandatory audit rationale / investigation findings..."
                value={auditNote}
                onChange={(e) => setAuditNote(e.target.value)}
                rows={3}
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500"
              />

              {statusError && (
                <div className="p-2 rounded bg-red-50 border border-red-200 text-red-600 text-[11px]">
                  {statusError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  type="button"
                  disabled={statusUpdating}
                  onClick={() => handleStatusChange('under_review')}
                  className="py-1.5 px-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-100 font-semibold text-slate-700 text-xs transition-colors"
                >
                  Under Review
                </button>
                <button
                  type="button"
                  disabled={statusUpdating}
                  onClick={() => handleStatusChange('confirmed')}
                  className="py-1.5 px-3 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold text-xs transition-colors shadow-xs"
                >
                  Confirm Fraud Ring
                </button>
                <button
                  type="button"
                  disabled={statusUpdating}
                  onClick={() => handleStatusChange('dismissed')}
                  className="py-1.5 px-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-100 font-semibold text-slate-600 text-xs transition-colors col-span-2"
                >
                  Dismiss Ring (False Positive)
                </button>
              </div>
            </div>
          </div>

          {/* Footer Actions (Reports) */}
          <div className="p-4 border-t border-slate-200 bg-white flex items-center justify-between gap-3">
            <a
              href={`/api/v1/network/rings/${selectedRing.id}/report.json`}
              target="_blank"
              rel="noreferrer"
              className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors"
            >
              <FileDown className="w-3.5 h-3.5" />
              <span>Export JSON</span>
            </a>
            <a
              href={`/api/v1/network/rings/${selectedRing.id}/report.pdf`}
              target="_blank"
              rel="noreferrer"
              className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors shadow-xs"
            >
              <FileDown className="w-3.5 h-3.5" />
              <span>Download PDF</span>
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
