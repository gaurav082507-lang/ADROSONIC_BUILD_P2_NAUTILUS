import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

describe('feature gate', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });
  it('hides a feature that is not enabled and shows the gate card instead', async () => {
    vi.stubEnv('VITE_USE_MOCKS', '0');
    vi.stubEnv('VITE_FEATURES', 'analytics');
    const { FeatureGate } = await import('../src/components/FeatureGate');
    render(
      <FeatureGate feature="network" title="Claims network">
        <div>graph content</div>
      </FeatureGate>,
    );
    expect(screen.queryByText('graph content')).toBeNull();
    expect(screen.getByTestId('feature-off-network')).toBeInTheDocument();
  });
  it('renders the feature when enabled', async () => {
    vi.stubEnv('VITE_USE_MOCKS', '0');
    vi.stubEnv('VITE_FEATURES', 'network,analytics');
    const { FeatureGate } = await import('../src/components/FeatureGate');
    render(
      <FeatureGate feature="network" title="Claims network">
        <div>graph content</div>
      </FeatureGate>,
    );
    expect(screen.getByText('graph content')).toBeInTheDocument();
  });
  it('turns every feature on in mock mode when VITE_FEATURES is unset', async () => {
    vi.stubEnv('VITE_USE_MOCKS', '1');
    vi.stubEnv('VITE_FEATURES', '');
    const { featureFlags } = await import('../src/lib/featureFlags');
    expect(featureFlags).toEqual({ voice: true, network: true, analytics: true, story: true });
  });
  it('turns every feature off in real mode when VITE_FEATURES is unset', async () => {
    vi.stubEnv('VITE_USE_MOCKS', '0');
    vi.stubEnv('VITE_FEATURES', '');
    const { featureFlags } = await import('../src/lib/featureFlags');
    expect(featureFlags).toEqual({ voice: false, network: false, analytics: false, story: false });
  });
});
