/** Why the live camera could not start – each maps to a specific, fixable message. */
export type CameraProblem = 'insecure' | 'denied' | 'notFound' | 'inUse' | 'unknown';

/** getUserMedia only works on https:// or http://localhost – not on a LAN IP like 192.168.x.x. */
export function cameraSupport(): CameraProblem | null {
  if (typeof window === 'undefined') return 'unknown';
  if (!window.isSecureContext) return 'insecure';
  if (!navigator.mediaDevices?.getUserMedia) return 'insecure';
  return null;
}

export function mapCameraError(error: unknown): CameraProblem {
  const name = (error as { name?: string } | null)?.name ?? '';
  if (name === 'NotAllowedError' || name === 'SecurityError' || name === 'PermissionDeniedError')
    return 'denied';
  if (
    name === 'NotFoundError' ||
    name === 'OverconstrainedError' ||
    name === 'DevicesNotFoundError'
  )
    return 'notFound';
  if (name === 'NotReadableError' || name === 'TrackStartError' || name === 'AbortError')
    return 'inUse';
  return 'unknown';
}

export const cameraProblemKey: Record<CameraProblem, string> = {
  insecure: 'camInsecure',
  denied: 'camDenied',
  notFound: 'camNotFound',
  inUse: 'camInUse',
  unknown: 'cameraBlocked',
};
