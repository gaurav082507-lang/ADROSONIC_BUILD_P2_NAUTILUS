import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ShieldCheck, Eye, Search, Lock } from 'lucide-react';
import { TopMenu } from '../components/public/TopMenu';
import { setToken } from '../api/session';
import { raw } from '../api/raw/endpoints';
import { friendlyError } from '../lib/errorMessages';
import { adaptLogin } from '../api/adapters';
import { Logo } from '../components/Logo';

const DEMO = {
  investigator: import.meta.env.VITE_DEMO_INVESTIGATOR_EMAIL || 'investigator@demo.in',
  claimant: import.meta.env.VITE_DEMO_CLAIMANT_EMAIL || 'ravi@demo.in',
  password: import.meta.env.VITE_DEMO_PASSWORD || 'demo',
};

export default function LoginPage() {
  const nav = useNavigate();
  const location = useLocation();
  const [role, setRole] = useState<'investigator' | 'claimant'>('investigator');
  const [email, setEmail] = useState(DEMO.investigator);
  const [password, setPassword] = useState(DEMO.password);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  // Handle ?role= query param
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const roleParam = params.get('role');
    if (roleParam === 'claimant' || roleParam === 'investigator') {
      setRole(roleParam);
      setEmail(roleParam === 'investigator' ? DEMO.investigator : DEMO.claimant);
    }
  }, [location.search]);

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
    <div className="min-h-screen bg-bg text-text font-sans flex flex-col selection:bg-nile selection:text-primary-dark">
      <TopMenu />
      
      <div className="flex-1 flex flex-col md:flex-row mt-16 md:mt-20">
        {/* LEFT PANEL */}
        <div className="hidden md:flex md:w-5/12 lg:w-1/2 bg-primary-dark text-white p-12 flex-col justify-between relative overflow-hidden">
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-4">
              <Logo dark />
              <span className="font-display font-bold text-xl tracking-tight">Lucen AI</span>
            </div>
            <p className="text-xl text-nile-soft/80 mb-12 max-w-sm">Forensic claim intelligence</p>
            
            <div className="space-y-8">
              <div className="flex gap-4">
                <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                  <Eye size={20} className="text-nile" />
                </div>
                <div>
                  <h3 className="font-bold mb-1">Explainable flags</h3>
                  <p className="text-sm text-white/60">No black boxes. See exactly why a file was flagged.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                  <Search size={20} className="text-nile" />
                </div>
                <div>
                  <h3 className="font-bold mb-1">Multi-modal analysis</h3>
                  <p className="text-sm text-white/60">Cross-checks photos, documents, and identity seamlessly.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                  <Lock size={20} className="text-nile" />
                </div>
                <div>
                  <h3 className="font-bold mb-1">Privacy built in</h3>
                  <p className="text-sm text-white/60">Data is processed locally and immediately redacted.</p>
                </div>
              </div>
            </div>
          </div>
          
          <div className="absolute -bottom-24 -right-12 w-96 h-96 bg-nile-soft rounded-3xl rotate-12 opacity-10 blur-sm mix-blend-overlay"></div>
          
          <div className="relative z-10 mt-12 w-full max-w-sm rounded-xl overflow-hidden shadow-2xl border border-white/10">
            <img 
              src="/samples/ai_car.jpg" 
              alt="Car damage analysis" 
              className="w-full h-48 object-cover mix-blend-overlay opacity-80"
            />
            <div className="absolute inset-0 bg-gradient-to-tr from-danger/40 via-transparent to-transparent mix-blend-multiply" />
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="flex-1 bg-surface flex flex-col justify-center px-6 py-12 md:px-16 lg:px-24 border-l border-border">
          <div className="max-w-md w-full mx-auto">
            <button onClick={() => nav('/')} className="text-sm text-text-muted hover:text-primary mb-8 flex items-center gap-2 transition-colors focus-visible:outline-primary">
              &larr; Back to home
            </button>
            <h1 className="font-display text-3xl font-bold text-primary-dark mb-8">Sign in</h1>
            
            <div className="grid grid-cols-2 gap-4 mb-8">
              <button
                onClick={() => choose('claimant')}
                className={`relative rounded-xl border-2 p-5 text-left transition-all ${
                  role === 'claimant' 
                    ? 'border-primary bg-nile-soft/30 shadow-sm' 
                    : 'border-border bg-white hover:border-nile hover:bg-bg'
                }`}
                aria-pressed={role === 'claimant'}
              >
                {role === 'claimant' && (
                  <div className="absolute top-3 right-3 text-primary">
                    <ShieldCheck size={18} />
                  </div>
                )}
                <div className="mb-2 text-primary opacity-80"><Eye size={24} /></div>
                <div className="font-semibold text-sm">I'm filing a claim</div>
              </button>
              
              <button
                onClick={() => choose('investigator')}
                className={`relative rounded-xl border-2 p-5 text-left transition-all ${
                  role === 'investigator' 
                    ? 'border-primary bg-nile-soft/30 shadow-sm' 
                    : 'border-border bg-white hover:border-nile hover:bg-bg'
                }`}
                aria-pressed={role === 'investigator'}
              >
                {role === 'investigator' && (
                  <div className="absolute top-3 right-3 text-primary">
                    <ShieldCheck size={18} />
                  </div>
                )}
                <div className="mb-2 text-primary opacity-80"><Search size={24} /></div>
                <div className="font-semibold text-sm">I work at an insurer</div>
              </button>
            </div>

            <div className="bg-nile-soft/50 rounded-lg p-4 mb-6 border border-nile text-sm">
              <span className="font-semibold text-primary-dark">Demo account:</span>{' '}
              {role === 'investigator' ? 'Priya Sharma (Investigator)' : 'Ravi Kumar (Claimant)'}
            </div>

            <div className="space-y-4">
              <label className="block">
                <span className="block text-sm font-medium text-primary-dark mb-1">Email address</span>
                <input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-border px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-shadow"
                />
              </label>
              <label className="block">
                <span className="block text-sm font-medium text-primary-dark mb-1">Password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && submit()}
                  className="w-full rounded-lg border border-border px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-shadow"
                />
              </label>
              
              {error && (
                <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700 border border-red-200">
                  {error}
                </div>
              )}

              <button
                disabled={busy}
                onClick={submit}
                className="w-full mt-4 rounded-lg bg-primary hover:bg-primary-hover px-4 py-3.5 font-bold text-white shadow-sm transition-colors disabled:opacity-50 focus-visible:outline-primary focus-visible:outline-offset-2"
              >
                {busy ? 'Signing in...' : 'Sign in'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
