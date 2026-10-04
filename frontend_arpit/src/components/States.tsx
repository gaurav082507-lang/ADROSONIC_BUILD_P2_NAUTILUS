export function Loading({ label = 'Loading…' }: { label?: string }) {
  return <div className="card p-8 text-center text-sm text-muted">{label}</div>;
}
export function Empty({ label }: { label: string }) {
  return <div className="card p-10 text-center text-sm text-muted">{label}</div>;
}
export function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div className="card border-red-200 bg-red-50 p-6">
      <div className="font-semibold text-red-900">Something needs attention</div>
      <p className="mt-1 text-sm text-red-700">{message}</p>
      <button
        onClick={retry}
        className="mt-4 rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white"
      >
        Retry
      </button>
    </div>
  );
}
