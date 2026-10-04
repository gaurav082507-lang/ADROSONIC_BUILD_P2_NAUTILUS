import { ShieldCheck } from 'lucide-react';
export function Logo({ dark = false }: { dark?: boolean }) {
  return (
    <div className={`flex items-center gap-3 ${dark ? 'text-white' : 'text-text'}`}>
      <div className="grid h-9 w-9 place-items-center rounded-xl bg-primary text-text">
        <ShieldCheck size={20} />
      </div>
      <div>
        <div className="font-display text-lg font-bold tracking-tight">Lucen AI</div>
        <div
          className={`text-[10px] uppercase tracking-[.22em] ${dark ? 'text-white/45' : 'text-muted'}`}
        >
          Forensic claim intelligence
        </div>
      </div>
    </div>
  );
}
