import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useJobPolling } from '../src/api/hooks';
import { raw } from '../src/api/raw/endpoints';
vi.mock('../src/api/raw/endpoints', () => ({ raw: { job: vi.fn() } }));
describe('job polling', () => {
  beforeEach(() => vi.clearAllMocks());
  it('stops after done', async () => {
    vi.mocked(raw.job).mockResolvedValue({ status: 'done', steps: [], result_id: 'R' } as any);
    const qc = new QueryClient();
    const { result } = renderHook(() => useJobPolling('J'), {
      wrapper: ({ children }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>,
    });
    await waitFor(() => expect(result.current.data?.status).toBe('done'));
    expect(raw.job).toHaveBeenCalledTimes(1);
  });
  it('does not keep polling after failed', async () => {
    vi.mocked(raw.job).mockResolvedValue({
      status: 'failed',
      steps: [],
      error: { message: 'x' },
    } as any);
    const qc = new QueryClient();
    const { result } = renderHook(() => useJobPolling('J2'), {
      wrapper: ({ children }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>,
    });
    await waitFor(() => expect(result.current.data?.status).toBe('failed'));
    expect(raw.job).toHaveBeenCalledTimes(1);
  });
});
