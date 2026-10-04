import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck, ScanSearch, FileCheck2 } from 'lucide-react';
import { Logo } from '../components/Logo';
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-ink text-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Logo dark />
        <Link to="/login" className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-ink">
          Open console
        </Link>
      </header>
      <section className="mx-auto grid max-w-6xl gap-12 px-6 pb-20 pt-16 lg:grid-cols-2 lg:items-center">
        <div>
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/65">
            <ShieldCheck size={14} className="text-yellow-300" /> Insurance evidence intelligence
          </div>
          <h1 className="font-display text-5xl font-bold leading-tight lg:text-6xl">
            See the evidence behind every claim.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-white/55">
            Lucen brings media authenticity, document checks, identity signals and claim context
            into one investigator workspace.
          </p>
          <div className="mt-8 flex gap-3">
            <Link
              to="/login"
              className="rounded-lg bg-yellow-400 px-5 py-3 text-sm font-bold text-ink"
            >
              Start demo <ArrowRight className="ml-2 inline" size={16} />
            </Link>
            <Link
              to="/claim/new"
              className="rounded-lg border border-white/10 px-5 py-3 text-sm font-semibold text-white"
            >
              Claimant portal
            </Link>
          </div>
        </div>
        <div className="grid-blueprint rounded-3xl border border-white/10 bg-white/[.03] p-5">
          <div className="rounded-2xl bg-white p-6 text-ink shadow-2xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted">
                Live case overview
              </span>
              <span className="rounded-full bg-red-50 px-2 py-1 text-xs font-semibold text-red-700">
                HIGH
              </span>
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl bg-slate-50 p-4">
                <ScanSearch className="text-signal" size={20} />
                <div className="mt-3 font-semibold">Media</div>
                <div className="mt-1 text-2xl font-bold">81%</div>
              </div>
              <div className="rounded-xl bg-slate-50 p-4">
                <FileCheck2 size={20} />
                <div className="mt-3 font-semibold">Document</div>
                <div className="mt-1 text-2xl font-bold">74%</div>
              </div>
              <div className="rounded-xl bg-slate-50 p-4">
                <ShieldCheck size={20} />
                <div className="mt-3 font-semibold">Identity</div>
                <div className="mt-1 text-2xl font-bold">91%</div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
