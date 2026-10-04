import { Link } from 'react-router-dom';
import { ShieldCheck, Lock, Activity, FileSearch, Eye, Users, Search, CheckCircle, Database, LayoutDashboard, Smartphone, Mail } from 'lucide-react';
import { TopMenu } from '../components/public/TopMenu';

const TEAM = [
  { name: 'Arpit Agarwal', role: 'AI & product' },
  { name: 'Gaurav Gupta', role: 'AI AND ML LEAD' },
  { name: 'Punyasha Kar', role: 'Web dev and design lead' },
  { name: 'Srijeet Roy', role: 'Web dev and Business lead' },
];

const CONTACT_EMAIL = 'team@lucen.ai';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg text-text font-sans selection:bg-nile selection:text-primary-dark">
      <TopMenu />

      <main className="pt-24 md:pt-32 pb-16">
        {/* A. HERO */}
        <section className="mx-auto max-w-7xl px-6 grid md:grid-cols-2 gap-12 items-center">
          <div className="max-w-2xl">
            <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-6xl text-primary-dark leading-tight">
              Every claim, examined.
            </h1>
            <p className="mt-6 text-xl leading-relaxed text-text-muted">
              AI that checks photos, bills and identity in seconds ?" so genuine claims get paid faster and fraud gets caught.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-4">
              <Link
                to="/claim/new"
                className="rounded-lg bg-primary hover:bg-primary-hover px-6 py-3.5 text-base font-bold text-white shadow-md transition-colors inline-flex items-center justify-center focus-visible:outline-primary"
              >
                File a claim
              </Link>
              <Link
                to="/login?role=investigator"
                className="rounded-lg border-2 border-primary-dark text-primary-dark hover:bg-nile-soft px-6 py-3.5 text-base font-bold transition-colors inline-flex items-center justify-center focus-visible:outline-primary"
              >
                Insurer login
              </Link>
            </div>
          </div>
          
          <div className="relative isolate rounded-2xl overflow-hidden bg-nile-soft shadow-xl aspect-square md:aspect-auto md:h-[500px]">
            <img 
              src="/samples/ai_car.jpg" 
              alt="Car damage analysis" 
              className="absolute inset-0 w-full h-full object-cover mix-blend-overlay opacity-90"
            />
            {/* Heatmap overlay simulation */}
            <div className="absolute inset-0 bg-gradient-to-tr from-danger/20 via-warning/20 to-transparent mix-blend-multiply" />
            <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMiIgY3k9IjIiIHI9IjIiIGZpbGw9IiMzRDczNTYiIGZpbGwtb3BhY2l0eT0iMC4yIi8+PC9zdmc+')] opacity-30" />
            
            {/* Scan line animation */}
            <div className="absolute top-0 left-0 w-full h-1 bg-nile animate-[scan_3s_ease-in-out_infinite]" />
            
            {/* Floating Card */}
            <div className="absolute bottom-6 right-6 left-6 md:left-auto md:w-80 bg-white rounded-xl shadow-2xl p-5 border border-danger/20">
              <div className="flex justify-between items-center mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-danger bg-danger/10 px-2 py-1 rounded">HIGH risk</span>
                <span className="font-mono font-bold text-lg">88%</span>
              </div>
              <ul className="text-sm space-y-2 text-text-muted">
                <li className="flex gap-2 items-start"><CheckCircle size={16} className="text-danger shrink-0 mt-0.5" /> AI-generated image patterns</li>
                <li className="flex gap-2 items-start"><CheckCircle size={16} className="text-danger shrink-0 mt-0.5" /> Bill total doesn't add up</li>
                <li className="flex gap-2 items-start"><CheckCircle size={16} className="text-danger shrink-0 mt-0.5" /> Photo reused in another claim</li>
              </ul>
            </div>
          </div>
        </section>

        {/* B. PROOF STRIP */}
        <section className="mt-16 mx-auto max-w-7xl px-6 border-y border-border py-8 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          <div>
            <div className="font-display font-bold text-2xl text-primary-dark">1?"13 s</div>
            <div className="text-sm text-text-muted mt-1">per claim</div>
          </div>
          <div>
            <div className="font-display font-bold text-2xl text-primary-dark">0.96</div>
            <div className="text-sm text-text-muted mt-1">AI-image detection AUC</div>
          </div>
          <div>
            <div className="font-display font-bold text-2xl text-primary-dark">13+</div>
            <div className="text-sm text-text-muted mt-1">Indian languages</div>
          </div>
          <div>
            <div className="font-display font-bold text-2xl text-primary-dark">Offline</div>
            <div className="text-sm text-text-muted mt-1">Runs locally (except voice)</div>
          </div>
        </section>

        {/* C. HOW IT WORKS */}
        <section id="how-it-works" className="pt-24 mx-auto max-w-7xl px-6 scroll-mt-24">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="font-display text-3xl font-bold text-primary-dark">How it works</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              { icon: FileSearch, title: 'Submit evidence', desc: 'Claimants upload photos, documents, and voice statements securely.' },
              { icon: Activity, title: 'AI checks every file', desc: 'Models scan for manipulation, synthetic generation, and identity matches.' },
              { icon: Eye, title: 'Clear reasons, not black boxes', desc: 'Every flagged item comes with a highlighted heatmap and specific explanation.' },
              { icon: Users, title: 'A human makes the final call', desc: 'Investigators review the evidence dashboard and make informed decisions.' }
            ].map((step, i) => (
              <div key={i} className="relative">
                <div className="bg-nile-soft w-12 h-12 rounded-xl flex items-center justify-center text-primary mb-6">
                  <step.icon size={24} />
                </div>
                <h3 className="font-bold text-lg mb-2">{i+1}. {step.title}</h3>
                <p className="text-text-muted text-sm leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* D. WHAT WE CHECK */}
        <section id="what-we-check" className="pt-24 mx-auto max-w-7xl px-6 scroll-mt-24">
          <div className="bg-surface rounded-3xl p-8 md:p-12 border border-border shadow-sm">
            <div className="mb-12">
              <h2 className="font-display text-3xl font-bold text-primary-dark">What we check</h2>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                { icon: ShieldCheck, title: 'Photos', desc: 'AI-generated and edited images, reused photos' },
                { icon: Search, title: 'Bills', desc: 'Changed totals, mismatched fonts, broken maths' },
                { icon: Lock, title: 'Identity', desc: 'Face match, live selfie check, Aadhaar Secure QR' },
                { icon: Activity, title: 'Voice', desc: 'Statements in Indian languages via Bhashini' },
                { icon: Database, title: 'Linked claims', desc: 'Shared bank accounts, phones and photos across claims' }
              ].map((item, i) => (
                <div key={i} className="flex gap-4 p-5 rounded-2xl bg-bg border border-border">
                  <item.icon className="text-primary shrink-0" size={24} />
                  <div>
                    <h4 className="font-bold mb-1 text-primary-dark">{item.title}</h4>
                    <p className="text-sm text-text-muted leading-relaxed">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* E. TWO PORTALS */}
        <section id="portals" className="pt-24 mx-auto max-w-7xl px-6 scroll-mt-24">
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-nile-soft rounded-3xl p-8 md:p-12 flex flex-col justify-between items-start border border-border overflow-hidden relative">
              <div className="relative z-10 w-full">
                <h2 className="font-display text-3xl font-bold text-primary-dark mb-4">For claimants</h2>
                <p className="text-text-muted mb-8">Guided steps, Hindi/English support, and live status tracking.</p>
                <Link to="/claim/new" className="rounded-lg bg-primary hover:bg-primary-hover px-6 py-3 font-bold text-white shadow-sm transition-colors inline-block focus-visible:outline-primary">
                  File a claim
                </Link>
              </div>
              <div className="mt-12 bg-white w-3/4 max-w-sm rounded-t-3xl border-x-4 border-t-4 border-slate-800 shadow-2xl p-4 self-center relative z-10 translate-y-8">
                <div className="w-12 h-1 bg-slate-200 rounded-full mx-auto mb-4" />
                <div className="space-y-4">
                  <div className="h-4 bg-slate-100 rounded w-1/2" />
                  <div className="h-24 bg-nile/20 rounded-xl border border-nile/30 flex items-center justify-center">
                    <Smartphone className="text-primary opacity-50" size={32} />
                  </div>
                  <div className="h-10 bg-primary/10 rounded-lg" />
                </div>
              </div>
            </div>

            <div className="bg-primary-dark text-white rounded-3xl p-8 md:p-12 flex flex-col justify-between items-start overflow-hidden relative">
              <div className="relative z-10 w-full">
                <h2 className="font-display text-3xl font-bold mb-4">For insurers</h2>
                <p className="text-white/70 mb-8">Risk-sorted queue, explainable score, and one-click decisions.</p>
                <Link to="/login?role=investigator" className="rounded-lg bg-white text-primary-dark hover:bg-nile-soft px-6 py-3 font-bold transition-colors inline-block focus-visible:outline-white">
                  Insurer login
                </Link>
              </div>
              <div className="mt-12 bg-surface w-full max-w-md rounded-t-xl border-x-4 border-t-4 border-slate-700 shadow-2xl p-4 self-center relative z-10 translate-y-8">
                <div className="flex gap-1.5 mb-4">
                  <div className="w-3 h-3 rounded-full bg-red-400" />
                  <div className="w-3 h-3 rounded-full bg-yellow-400" />
                  <div className="w-3 h-3 rounded-full bg-green-400" />
                </div>
                <div className="grid grid-cols-[1fr_2fr] gap-4">
                  <div className="space-y-2">
                    <div className="h-2 bg-slate-200 rounded w-full" />
                    <div className="h-2 bg-slate-200 rounded w-5/6" />
                    <div className="h-2 bg-slate-200 rounded w-4/6" />
                  </div>
                  <div className="h-24 bg-slate-100 rounded-lg flex items-center justify-center border border-slate-200">
                    <LayoutDashboard className="text-slate-400" size={32} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* F. TRUST ROW */}
        <section className="mt-24 mx-auto max-w-7xl px-6">
          <div className="flex flex-wrap justify-center gap-x-12 gap-y-6 text-sm font-semibold text-text-muted">
            <span className="flex items-center gap-2"><CheckCircle size={16} className="text-primary" /> Human decides</span>
            <span className="flex items-center gap-2"><CheckCircle size={16} className="text-primary" /> No Aadhaar numbers stored</span>
            <span className="flex items-center gap-2"><CheckCircle size={16} className="text-primary" /> DPDP consent built in</span>
            <span className="flex items-center gap-2"><CheckCircle size={16} className="text-primary" /> Every score explained</span>
          </div>
        </section>

        {/* G. ABOUT US */}
        <section id="about" className="pt-24 mx-auto max-w-7xl px-6 scroll-mt-24">
          <div className="mb-12">
            <h2 className="font-display text-3xl font-bold text-primary-dark">About Lucen AI</h2>
            <p className="mt-4 text-lg text-text-muted max-w-3xl leading-relaxed">
              We help insurers trust what they see. Generative AI makes fake damage photos, edited bills and synthetic identities easy to create ?" Lucen AI checks the evidence itself, explains every flag, and keeps a human in charge of every decision.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6 mb-16">
            <div className="bg-surface border border-border p-6 rounded-2xl">
              <h4 className="font-bold text-primary-dark mb-2">Explainable by design</h4>
              <p className="text-sm text-text-muted">No black boxes. Every flag provides visual evidence and specific reasoning.</p>
            </div>
            <div className="bg-surface border border-border p-6 rounded-2xl">
              <h4 className="font-bold text-primary-dark mb-2">Built for India</h4>
              <p className="text-sm text-text-muted">Supports Aadhaar Secure QR, Bhashini translation, GST verification, and lakh/crore checks.</p>
            </div>
            <div className="bg-surface border border-border p-6 rounded-2xl">
              <h4 className="font-bold text-primary-dark mb-2">Privacy first</h4>
              <p className="text-sm text-text-muted">DPDP consent built in. PII is redacted, and no Aadhaar numbers are stored.</p>
            </div>
          </div>
          
          <div className="bg-nile-soft rounded-3xl p-8 md:p-12 border border-border">
            <h3 className="font-display text-2xl font-bold text-primary-dark mb-8 text-center">Team Nautilus ?" Adrosonic Build 2026</h3>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {TEAM.map((member) => (
                <div key={member.name} className="bg-surface p-6 rounded-2xl text-center shadow-sm border border-border/50 hover:border-nile transition-colors">
                  <div className="w-16 h-16 rounded-full bg-primary-dark text-white flex items-center justify-center text-xl font-bold mx-auto mb-4">
                    {member.name.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase()}
                  </div>
                  <div className="font-bold text-primary-dark">{member.name}</div>
                  <div className="text-xs text-text-muted mt-1 uppercase tracking-wide">{member.role}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* H. CONTACT */}
        <section id="contact" className="py-24 mx-auto max-w-3xl px-6 text-center scroll-mt-24">
          <h2 className="font-display text-3xl font-bold text-primary-dark mb-6">Want to run a shadow pilot on your historical claims?</h2>
          <a 
            href={`mailto:${CONTACT_EMAIL}`} 
            className="inline-flex items-center gap-2 rounded-lg bg-primary hover:bg-primary-hover px-8 py-4 text-lg font-bold text-white shadow-md transition-colors focus-visible:outline-primary"
          >
            <Mail size={20} /> Request a pilot
          </a>
        </section>
      </main>

      {/* I. FOOTER */}
      <footer className="bg-surface border-t border-border py-12 px-6">
        <div className="mx-auto max-w-7xl flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex flex-col items-center md:items-start">
            <div className="flex items-center gap-2 mb-2">
              <div className="h-6 w-6 rounded border bg-primary text-white flex items-center justify-center font-bold text-xs">L</div>
              <span className="font-display font-bold text-primary-dark tracking-tight">Lucen AI</span>
            </div>
            <p className="text-sm text-text-muted">Forensic claim intelligence</p>
          </div>
          
          <nav className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm font-medium text-text-muted">
            <a href="#what-we-check" className="hover:text-primary transition-colors">Product</a>
            <a href="#how-it-works" className="hover:text-primary transition-colors">How it works</a>
            <a href="#portals" className="hover:text-primary transition-colors">For insurers</a>
            <a href="#about" className="hover:text-primary transition-colors">About us</a>
            <a href="#contact" className="hover:text-primary transition-colors">Contact</a>
          </nav>

          <div className="text-xs text-text-muted text-center md:text-right">
            © 2026 Lucen AI Â· Built for Adrosonic Build
          </div>
        </div>
      </footer>
    </div>
  );
}
