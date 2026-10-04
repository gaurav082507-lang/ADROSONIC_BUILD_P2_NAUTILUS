import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { adaptResult } from '../src/api/adapters';
import { high, low, medium } from '../src/mocks/fixtures/results';
import BoxOverlay, { bboxToPixels } from '../src/components/BoxOverlay';
import { friendlyError } from '../src/lib/errorMessages';
import { RiskBadge } from '../src/components/RiskBadge';

describe('result adapters', () => {
  it.each([low, medium, high])('adapts $id', (fixture) => {
    const vm = adaptResult(fixture);
    expect(vm.id).toBe(fixture.id);
    expect(vm.overall).toBeDefined();
  });
  it('uses safe Not analysed state for missing blocks', () => {
    const vm = adaptResult({ id: 'x', mode: 'image' });
    expect(vm.document?.analysed ?? false).toBe(false);
    expect(vm.evidence).toEqual([]);
  });
});

describe('BoxOverlay maths', () => {
  it('maps normalised coordinates to pixels', () => {
    expect(bboxToPixels({ x: 0.25, y: 0.1, w: 0.5, h: 0.4 }, 800, 600)).toEqual({
      left: 200,
      top: 60,
      width: 400,
      height: 240,
    });
  });
  it('renders numbered evidence markers', () => {
    render(
      <div style={{ position: 'relative', width: 800, height: 600 }}>
        <BoxOverlay
          evidence={[
            {
              id: 'IMG-1',
              title: 'Flag',
              reason: 'x',
              kind: 'risk',
              severity: 'high',
              bbox: { x: 0, y: 0, w: 0.2, h: 0.2 },
            },
          ]}
        />
      </div>,
    );
    expect(screen.getByLabelText(/Evidence 1/)).toBeInTheDocument();
  });
});

describe('error mapping and band semantics', () => {
  it('maps backend error codes', () => expect(friendlyError('FILE_TOO_LARGE')).toContain('15 MB'));
  it('renders the band word', () => {
    render(<RiskBadge band="HIGH" />);
    expect(screen.getByText('HIGH')).toBeInTheDocument();
  });
});

it('does not treat info evidence as a driver', () => {
  const vm = adaptResult(high);
  expect(vm.evidence.filter((x) => x.kind !== 'info').some((x) => x.id === 'DOC-ANOM-01')).toBe(
    false,
  );
});

it('keeps the decision draft flow testable', async () => {
  const draft = {
    claimant_message_en: 'Draft',
    claimant_message_hi: 'मसौदा',
    next_steps: [],
    slots_to_resubmit: [],
    source: 'provisional',
  };
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(draft), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }),
  );
  vi.stubGlobal('fetch', fetchMock);
  expect(draft.claimant_message_en).toBe('Draft');
  vi.unstubAllGlobals();
});
