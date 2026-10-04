import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import {
  adaptClaimNetwork,
  adaptGraph,
  adaptLanguages,
  adaptResult,
  adaptRingDetail,
  adaptRings,
  adaptStory,
  adaptSummary,
  adaptTrends,
  adaptVoice,
  asList,
} from '../src/api/adapters';
import {
  claimNetwork,
  graph,
  ringDetail,
  ring,
  historicRing,
  analyticsSummary,
  trends,
} from '../src/mocks/fixtures/network';
import { high, low } from '../src/mocks/fixtures/results';
import NetworkTables from '../src/features/network/NetworkTables';
import StoryTab from '../src/features/results/tabs/StoryTab';
import VoiceTab from '../src/features/results/tabs/VoiceTab';
import { ringNoteRequired } from '../src/features/network/ringStatus';
import { nodeTooltip } from '../src/features/network/graphStyle';
import { summarise } from '../src/features/analytics/analyticsSummaries';

describe('network adapters', () => {
  it('maps graph nodes/edges and marks weak provider links', () => {
    const g = adaptGraph(graph);
    expect(g.nodes).toHaveLength(graph.nodes.length);
    const garage = g.edges.filter((e) => e.type === 'provider');
    expect(garage.length).toBe(2);
    expect(garage.every((e) => e.weak)).toBe(true);
    expect(g.edges.filter((e) => e.type === 'bank').every((e) => !e.weak)).toBe(true);
    expect(g.rings[0].memberIds).toContain('CLM-DEMO-HIGH');
  });
  it('drops edges pointing outside a truncated subgraph and keeps truncated flag', () => {
    const g = adaptGraph({
      nodes: [graph.nodes[0]],
      edges: graph.edges,
      truncated: true,
    });
    expect(g.edges).toHaveLength(0);
    expect(g.truncated).toBe(true);
  });
  it('handles missing optional graph fields', () => {
    const g = adaptGraph({ nodes: [{ id: 'X', type: 'mystery', label: 'X' }], edges: [] });
    expect(g.nodes[0].kind).toBe('other');
    expect(g.nodes[0].flags).toEqual([]);
    expect(g.rings).toEqual([]);
    expect(g.truncated).toBe(false);
  });
  it('maps ring lists (envelope or array) and flags synthetic history', () => {
    const fromEnvelope = adaptRings({ items: [ring, historicRing] });
    const fromArray = adaptRings([ring, historicRing]);
    expect(fromEnvelope).toEqual(fromArray);
    expect(fromEnvelope[1].synthetic).toBe(true);
    expect(fromEnvelope[0].synthetic).toBe(false);
  });
  it('derives a band from the ring score when the backend omits it', () => {
    const [r] = adaptRings([{ ...ring, band: undefined, ring_score: 0.4 }]);
    expect(r.band).toBe('MEDIUM');
  });
  it('maps ring detail with claims, timeline and graph', () => {
    const d = adaptRingDetail(ringDetail);
    expect(d.claims.map((c) => c.claimId)).toContain('CLM-R2');
    expect(d.timeline.length).toBe(3);
    expect(d.graph?.nodes.some((n) => n.id === 'ID-GARAGE-12')).toBe(false);
  });
  it('maps claim network evidence', () => {
    const n = adaptClaimNetwork(claimNetwork);
    expect(n.rings[0].ringId).toBe('RING-07');
    expect(n.sharedIdentifiers[0].otherClaims).toBe(2);
    expect(n.evidence.map((e) => e.id)).toEqual(['CLM-NET-01', 'CLM-NET-02']);
    expect(adaptClaimNetwork({}).evidence).toEqual([]);
  });
  it('tooltips always name the band in words', () => {
    const node = adaptGraph(graph).nodes.find((n) => n.id === 'CLM-DEMO-HIGH')!;
    expect(nodeTooltip(node)).toContain('HIGH');
  });
});

describe('ring status rule', () => {
  it('requires a note to confirm or dismiss only', () => {
    expect(ringNoteRequired('confirmed')).toBe(true);
    expect(ringNoteRequired('dismissed')).toBe(true);
    expect(ringNoteRequired('under_review')).toBe(false);
    expect(ringNoteRequired('open')).toBe(false);
  });
});

describe('graph table view parity', () => {
  it('shows exactly the same nodes and links as the graph', () => {
    const g = adaptGraph(graph);
    render(<NetworkTables graph={g} />);
    const nodes = screen.getByRole('table', { name: 'Network nodes' });
    const links = screen.getByRole('table', { name: 'Network links' });
    expect(within(nodes).getAllByRole('row')).toHaveLength(g.nodes.length + 1);
    expect(within(links).getAllByRole('row')).toHaveLength(g.edges.length + 1);
    expect(within(links).getAllByText(/\(weak\)/)).toHaveLength(2);
  });
});

describe('analytics adapters', () => {
  it('maps summary and trends with defaults', () => {
    const s = adaptSummary(analyticsSummary);
    expect(s.sparkline).toHaveLength(7);
    const t = adaptTrends(trends('7d'));
    expect(t.daily).toHaveLength(7);
    expect(t.spike.detected).toBe(true);
    const minimal = adaptTrends({ daily: [] });
    expect(minimal.topSignals).toEqual([]);
    expect(minimal.spike.detected).toBe(false);
  });
  it('builds plain-language chart summaries', () => {
    const text = summarise(adaptTrends(trends('30d')));
    expect(text.volume).toMatch(/claims in this period/);
    expect(text.signals).toMatch(/AI-generated image patterns/);
    expect(summarise(adaptTrends({ daily: [] })).signals).toBe('No signals recorded.');
  });
});

describe('voice + story', () => {
  it('keeps voice details even when the voice block has no pipeline score', () => {
    const r = adaptResult({ ...low, voice: { transcript: 'hello', status: 'analysed' } });
    expect(r.voice).toBeUndefined();
    expect(r.voiceDetails?.transcript).toBe('hello');
    expect(r.voiceDetails?.extracted.damagedItems).toEqual([]);
  });
  it('maps voice extraction and spoof segments', () => {
    const v = adaptVoice(high.voice_details!);
    expect(v.extracted.amount).toBe(120000); // contract field: amount_claimed
    expect(v.spoof?.segments[0].startS).toBe(4.2);
  });
  it('maps languages from array or envelope', () => {
    expect(adaptLanguages([{ code: 'hi', name: 'Hindi', native_name: 'हिंदी' }])[0].label).toBe(
      'Hindi · हिंदी',
    );
    expect(adaptLanguages({ languages: [{ code: 'ta' }] })[0].label).toBe('ta');
  });
  it('story tab always shows the not-part-of-score note', () => {
    render(<StoryTab result={adaptResult(high)} />);
    expect(screen.getByRole('note')).toHaveTextContent('not part of the score');
    expect(screen.getByText(/Contradictions \(1\)/)).toBeInTheDocument();
  });
  it('story adapter supplies the note when the backend omits it', () => {
    expect(adaptStory({}).note).toMatch(/not part of the score/);
  });
  it('voice tab renders transcript, translation and spoof check', () => {
    render(<VoiceTab result={adaptResult(high)} />);
    expect(screen.getByText(/hit from behind in Ranchi/)).toBeInTheDocument();
    expect(screen.getByText(/likelihood of synthetic speech/)).toBeInTheDocument();
  });
  it('voice tab shows an empty state without a recording', () => {
    render(<VoiceTab result={adaptResult(low)} />);
    expect(screen.getByText(/No voice statement/)).toBeInTheDocument();
  });
});

describe('list envelopes', () => {
  it('asList accepts arrays, envelopes and nullish values', () => {
    expect(asList([1, 2])).toEqual([1, 2]);
    expect(asList({ items: [3] })).toEqual([3]);
    expect(asList(undefined)).toEqual([]);
  });
});
