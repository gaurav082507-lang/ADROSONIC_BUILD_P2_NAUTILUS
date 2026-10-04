import type { RingStatus } from '../../types/vm';

export const RING_STATUSES: { value: RingStatus; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'under_review', label: 'Under review' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'dismissed', label: 'Dismissed' },
];

/** Confirming or dismissing a ring is a consequential decision and must carry a note. */
export function ringNoteRequired(status: string) {
  return status === 'confirmed' || status === 'dismissed';
}

export function ringStatusLabel(status: string) {
  return RING_STATUSES.find((s) => s.value === status)?.label ?? status;
}
