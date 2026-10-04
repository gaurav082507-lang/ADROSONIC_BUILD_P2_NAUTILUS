import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck, Lock, Activity } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg text-text font-sans">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 bg-surface border-b border-nile shadow-sm">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-primary text-white flex items-center justify-center font-bold">L</div>
          <span className="font-display font-bold text-xl text-primary-dark tracking-tight">Lucen AI</span>
        </div>
        <nav className="flex items-center gap-4">
          <Link to="/claim" className="text-sm font-medium text-text-muted hover:text-primary transition-colors">
            Track Claim
          </Link>
          <Link to="/login" className="rounded-lg bg-primary hover:bg-primary-hover px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors">
            Investigator Login
          </Link>
        </nav>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-20 pt-16">
        <div className="bg-nile-soft rounded-3xl p-8 md:p-16 border border-border shadow-sm text-center max-w-4xl mx-auto">
          <h1 className="font-display text-4xl font-bold leading-tight md:text-5xl text-primary-dark">
            File your claim securely.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-text-muted mx-auto">
            Submit your insurance claim in minutes with our fast, secure, and intelligent platform. We'll guide you through every step.
          </p>
          <div className="mt-8 flex gap-4 justify-center">
            <Link
              to="/claim/new"
              className="rounded-lg bg-primary hover:bg-primary-hover px-6 py-3.5 text-base font-bold text-white shadow-md transition-colors inline-flex items-center"
            >
              Start a New Claim <ArrowRight className="ml-2" size={18} />
            </Link>
          </div>
          
          <div className="mt-12 flex flex-col sm:flex-row gap-6 border-t border-border/50 pt-8 justify-center items-center">
            <div className="flex items-center gap-3">
              <div className="bg-surface p-1.5 rounded-md text-primary border border-border shadow-sm">
                <Lock size={16} />
              </div>
              <div className="text-left">
                <h3 className="text-sm font-semibold text-primary-dark">Secure Upload</h3>
                <p className="text-xs text-text-muted mt-0.5">Bank-grade encryption</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="bg-surface p-1.5 rounded-md text-primary border border-border shadow-sm">
                <Activity size={16} />
              </div>
              <div className="text-left">
                <h3 className="text-sm font-semibold text-primary-dark">AI Verification</h3>
                <p className="text-xs text-text-muted mt-0.5">Fast-tracked processing</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="bg-surface p-1.5 rounded-md text-primary border border-border shadow-sm">
                <ShieldCheck size={16} />
              </div>
              <div className="text-left">
                <h3 className="text-sm font-semibold text-primary-dark">Track Status</h3>
                <p className="text-xs text-text-muted mt-0.5">Real-time updates</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
