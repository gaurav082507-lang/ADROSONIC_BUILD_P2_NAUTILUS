/**
 * Feature flags for backend capabilities that may not exist yet.
 * VITE_FEATURES is a comma list, e.g. "voice,network,analytics,story".
 * In mock mode with no VITE_FEATURES set, every feature is on so the full UI can be reviewed.
 */
export type FeatureName = 'voice' | 'network' | 'analytics' | 'story';
const ALL: FeatureName[] = ['voice', 'network', 'analytics', 'story'];

function resolve(): Set<string> {
  const rawValue = import.meta.env.VITE_FEATURES;
  if (rawValue === undefined || rawValue === null || rawValue === '') {
    return new Set(import.meta.env.VITE_USE_MOCKS === '1' ? ALL : []);
  }
  return new Set(
    String(rawValue)
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean),
  );
}
const configured = resolve();

export function isFeatureOn(name: FeatureName | string) {
  return configured.has(name);
}
export function useFeature(name: FeatureName | string) {
  return configured.has(name);
}
export const featureFlags = {
  voice: configured.has('voice'),
  network: configured.has('network'),
  analytics: configured.has('analytics'),
  story: configured.has('story'),
};
