export function ConfidencePill({ value }: { value: 'high' | 'medium' | 'low' }) {
  return (
    <span className="rounded-full border border-border bg-white px-2.5 py-1 text-xs font-medium capitalize text-muted">
      {value} confidence
    </span>
  );
}
