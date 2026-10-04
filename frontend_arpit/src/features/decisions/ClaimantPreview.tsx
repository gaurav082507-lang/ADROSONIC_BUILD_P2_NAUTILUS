export default function ClaimantPreview({ english, hindi }: { english: string; hindi: string }) {
  return (
    <div className="rounded-xl border border-border bg-white p-4">
      <div className="text-xs font-semibold uppercase text-muted">Claimant preview</div>
      <div className="mt-3 text-sm">{english}</div>
      <div className="mt-3 text-sm text-muted">{hindi}</div>
    </div>
  );
}
