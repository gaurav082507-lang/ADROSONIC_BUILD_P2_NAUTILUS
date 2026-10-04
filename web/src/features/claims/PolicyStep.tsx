import type { PolicyVM } from '../../types/vm';

type Props = {
  policies: PolicyVM[];
  selected: string;
  onSelect: (policy: PolicyVM) => void;
  t: any;
};

export default function PolicyStep({ policies, selected, onSelect, t }: Props) {
  return (
    <div>
      <h2 className="font-display text-xl font-semibold">{t.policy}</h2>
      <div className="mt-5 space-y-3">
        {policies.map((policy) => (
          <button
            key={policy.id}
            onClick={() => onSelect(policy)}
            className={`w-full rounded-xl border p-4 text-left ${selected === policy.id ? 'border-ink bg-slate-50' : 'border-border'}`}
          >
            <div className="font-semibold">{policy.policyNumber}</div>
            <div className="mt-1 text-sm text-muted">
              {policy.asset} · {policy.claimType}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
