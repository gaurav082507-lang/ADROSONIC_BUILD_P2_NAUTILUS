/**
 * Captured REAL backend responses (synced by `npm run fixtures:sync`). When a file exists here,
 * the mock server serves it instead of the provisional fixture, so mock mode behaves exactly
 * like the backend.
 */
const files = import.meta.glob('./captured/*.json', { eager: true, import: 'default' }) as Record<
  string,
  unknown
>;

export function captured<T>(name: string): T | undefined {
  return files[`./captured/${name}.json`] as T | undefined;
}

/** All captured analysis results, keyed by their id. */
export function capturedResults<T extends { id: string }>(): T[] {
  return Object.entries(files)
    .filter(([key]) => /\/result_[^/]+\.json$/.test(key) && !key.endsWith('result_evidence.json'))
    .map(([, value]) => value as T)
    .filter((r) => r && typeof r === 'object' && 'id' in r);
}
