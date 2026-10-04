import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, UserCheck, ArrowRight, Lock, Mail, Sparkles } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useI18n } from '../i18n/I18nContext';
import { loginApi } from '../api/auth';
import Logo from '../components/Logo';

const DEMO_USERS = {
  claimant: { email: 'ravi@demo.in', password: 'demo', role: 'claimant', title: 'Claimant Portal', desc: 'File claims, submit photos & verify identity safely' },
  investigator: { email: 'investigator@demo.in', password: 'demo', role: 'investigator', title: 'Investigator Workspace', desc: 'Forensic analysis, fraud ring graph & decision queue' },
};

export default function LoginPage() {
  const { login } = useAuth();
  const { t, toggleLang, lang } = useI18n();
  const navigate = useNavigate();

  const [activeRole, setActiveRole] = useState('investigator');
  const [email, setEmail] = useState(DEMO_USERS.investigator.email);
  const [password, setPassword] = useState(DEMO_USERS.investigator.password);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function selectRole(role) {
    setActiveRole(role);
    setEmail(DEMO_USERS[role].email);
    setPassword(DEMO_USERS[role].password);
    setError('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await loginApi(email, password);
      login(data.token, data.user);
      if (data.user?.role === 'investigator') {
        navigate('/app', { replace: true });
      } else {
        navigate('/claims/mine', { replace: true });
      }
    } catch (err) {
      setError(err.message || t('loginError') || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0B1220] text-slate-100 flex flex-col justify-between relative overflow-hidden font-sans">
      {/* Background forensic grid overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-20"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, #3B82F6 1px, transparent 0)`,
          backgroundSize: '36px 36px',
        }}
      />
      <div className="absolute -top-32 -right-32 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -left-32 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Bar */}
      <header className="relative z-10 w-full max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
        <Logo size="lg" dark={true} />
        <button
          onClick={toggleLang}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/60 hover:bg-slate-750 text-xs font-semibold text-slate-300 transition-colors shadow-sm"
        >
          <Sparkles className="w-3.5 h-3.5 text-accent" />
          <span>{lang === 'en' ? 'हिन्दी (Hindi)' : 'English'}</span>
        </button>
      </header>

      {/* Main Hero & Portal Selection */}
      <main className="relative z-10 w-full max-w-4xl mx-auto px-6 py-6 flex-1 flex flex-col justify-center">
        <div className="text-center max-w-xl mx-auto mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-xs font-medium mb-3">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            Multimodal Insurance Fraud Forensics
          </div>
          <h1 className="text-3xl sm:text-4xl font-heading font-bold text-white tracking-tight">
            Sign in to Lucen AI
          </h1>
          <p className="text-sm text-slate-400 mt-2">
            Select a portal below to sign in or test with instant demo credentials.
          </p>
        </div>

        {/* Portal Role Selector Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          {/* Investigator Card */}
          <button
            type="button"
            onClick={() => selectRole('investigator')}
            className={`p-5 rounded-xl border text-left transition-all relative ${
              activeRole === 'investigator'
                ? 'bg-[#0F1B2D] border-blue-500 shadow-lg shadow-blue-500/10 ring-1 ring-blue-500'
                : 'bg-slate-900/50 border-slate-800 hover:border-slate-700 hover:bg-slate-900'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-semibold uppercase">
                Investigator
              </span>
            </div>
            <h3 className="font-heading font-semibold text-white text-base">
              Investigator Workspace
            </h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Full access to fraud network graph, forensic signals, OCR inspection & decision audits.
            </p>
          </button>

          {/* Claimant Card */}
          <button
            type="button"
            onClick={() => selectRole('claimant')}
            className={`p-5 rounded-xl border text-left transition-all relative ${
              activeRole === 'claimant'
                ? 'bg-[#0F1B2D] border-amber-500 shadow-lg shadow-amber-500/10 ring-1 ring-amber-500'
                : 'bg-slate-900/50 border-slate-800 hover:border-slate-700 hover:bg-slate-900'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center">
                <UserCheck className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold uppercase">
                Claimant
              </span>
            </div>
            <h3 className="font-heading font-semibold text-white text-base">
              Claimant Portal
            </h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Submit damage claims, photo evidence, Aadhaar verification & track status transparently.
            </p>
          </button>
        </div>

        {/* Credentials Form Box */}
        <div className="bg-[#0F1B2D] border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                />
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-heading font-semibold text-sm flex items-center justify-center gap-2 transition-all shadow-md shadow-blue-600/20 disabled:opacity-60"
            >
              {loading ? (
                <span>Signing in...</span>
              ) : (
                <>
                  <span>Continue to {activeRole === 'investigator' ? 'Investigator Workspace' : 'Claimant Portal'}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>Demo credential quick-fills active</span>
            <span className="font-mono text-[11px] text-slate-500">lucen-v1.0-release</span>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 py-4 text-center text-xs text-slate-500">
        Lucen AI Multimodal Forensic Intelligence &bull; Production Fallback UI
      </footer>
    </div>
  );
}
