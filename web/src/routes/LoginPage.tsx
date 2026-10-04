import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { Logo } from '../components/Logo';
import { setToken } from '../api/session';
import { raw } from '../api/raw/endpoints';
import { friendlyError } from '../lib/errorMessages';
import { adaptLogin } from '../api/adapters';

const DEMO = {
  investigator: import.meta.env.VITE_DEMO_INVESTIGATOR_EMAIL || 'investigator@demo.in',
  claimant: import.meta.env.VITE_DEMO_CLAIMANT_EMAIL || 'ravi@demo.in',
  password: import.meta.env.VITE_DEMO_PASSWORD || 'demo',
};
export default function LoginPage() {
  const nav = useNavigate();
  const [role, setRole] = useState<'investigator' | 'claimant'>('investigator');
  const [email, setEmail] = useState(DEMO.investigator);
  const [password, setPassword] = useState(DEMO.password);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const choose = (r: 'investigator' | 'claimant') => {
    setRole(r);
    setEmail(r === 'investigator' ? DEMO.investigator : DEMO.claimant);
    setError('');
  };
  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      const r = adaptLogin(await raw.login(email, password));
      setToken(r.token, r.user.role);
      nav(r.user.role === 'investigator' ? '/app' : '/claim');
    } catch (e: any) {
      setError(friendlyError(e.code, e.message));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="min-h-screen bg-primary-dark grid place-items-center px-6">
      <div className="w-full max-w-4xl">
        <Logo dark />
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          <button
            onClick={() => choose('claimant')}
            className={`rounded-2xl border p-7 text-left ${role === 'claimant' ? 'border-yellow-300 bg-white text-text' : 'border-white/10 bg-white/[.03] text-white'}`}
          >
            <div className="text-sm opacity-50">CLAIMANT PORTAL</div>
            <div className="mt-2 text-xl font-semibold">I’m filing a claim</div>
            <div className="mt-2 text-sm opacity-50">Ravi Kumar · demo access</div>
          </button>
          <button
            onClick={() => choose('investigator')}
            className={`rounded-2xl border p-7 text-left ${role === 'investigator' ? 'border-yellow-300 bg-white text-text' : 'border-white/10 bg-white/[.03] text-white'}`}
          >
            <div className="text-sm opacity-50">INVESTIGATOR CONSOLE</div>
            <div className="mt-2 text-xl font-semibold">I work at an insurer</div>
            <div className="mt-2 text-sm opacity-50">Priya Sharma · demo access</div>
          </button>
        </div>
        <div className="mt-5 rounded-2xl bg-white p-6">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck size={17} className="text-green-600" /> Demo sign in
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-[1fr_1fr_auto]">
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-border px-3 py-2.5 text-sm"
            />
            <input
              type="password"
              aria-label="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submit()}
              className="rounded-lg border border-border px-3 py-2.5 text-sm"
            />
            <button
              disabled={busy}
              onClick={submit}
              className="rounded-lg bg-primary-dark px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
          </div>
          {error && (
            <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
          )}
          <div className="mt-3 text-xs text-muted">
            Demo accounts are prefilled (set VITE_DEMO_* in .env to match the backend seed).
          </div>
        </div>
      </div>
    </div>
  );
}
