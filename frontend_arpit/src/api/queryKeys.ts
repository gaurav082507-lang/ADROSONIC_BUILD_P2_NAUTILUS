export const queryKeys = {
  queue: (query: string) => ['queue', query] as const,
  history: (query: string) => ['history', query] as const,
  result: (id: string) => ['result', id] as const,
  job: (id: string) => ['job', id] as const,
  policies: ['policies'] as const,
  claimStatus: (id: string) => ['claimStatus', id] as const,
  networkGraph: (params: Record<string, unknown>) => ['network', 'graph', params] as const,
  rings: (params: Record<string, unknown>) => ['network', 'rings', params] as const,
  ring: (id: string) => ['network', 'ring', id] as const,
  claimNetwork: (id: string) => ['claims', id, 'network'] as const,
  analyticsSummary: ['analytics', 'summary'] as const,
  analyticsTrends: (range: string, type?: string) =>
    ['analytics', 'trends', range, type ?? ''] as const,
  voiceLanguages: ['voice', 'languages'] as const,
};
