import type { LucideIcon } from 'lucide-react';
import {
  BarChart3,
  History,
  LayoutDashboard,
  ListFilter,
  LogOut,
  Network,
  ScanSearch,
  Search,
  Menu,
} from 'lucide-react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { logout } from '../api/session';

type NavItem = { to: string; label: string; icon: LucideIcon };

const nav: NavItem[] = [
  { to: '/app', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/app/queue', label: 'Queue', icon: ListFilter },
  { to: '/app/analyze', label: 'Analyze', icon: ScanSearch },
  { to: '/app/history', label: 'History', icon: History },
  { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/app/network', label: 'Network', icon: Network },
];

export default function InvestigatorLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const getPageTitle = () => {
    const item = nav.find(n => n.to === location.pathname);
    return item ? item.label : 'Investigator Console';
  };

  return (
    <div className="min-h-screen bg-bg">
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-primary-dark text-white transition-transform duration-300 ease-in-out ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>
        <div className="p-6 flex items-center justify-between">
          <div className="text-xl font-bold font-display text-white">Lucen AI</div>
          <button className="lg:hidden text-white" onClick={() => setMobileMenuOpen(false)}>
             &times;
          </button>
        </div>
        <nav className="space-y-1 px-3 mt-4" aria-label="Investigator navigation">
          {nav.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all ${
                location.pathname === to
                  ? 'bg-primary-hover font-semibold border-l-4 border-nile text-white'
                  : 'text-nile-soft hover:bg-primary hover:text-white border-l-4 border-transparent'
              }`}
            >
              <Icon size={18} aria-hidden="true" />
              {label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="lg:pl-64 flex flex-col min-h-screen">
        <header className="sticky top-0 z-10 border-b border-border bg-surface/90 backdrop-blur">
          <div className="flex h-16 items-center justify-between px-6">
            <div className="flex items-center gap-4">
              <button className="lg:hidden text-primary-dark" onClick={() => setMobileMenuOpen(true)}>
                <Menu size={24} />
              </button>
              <div className="hidden md:block relative">
                <Search className="absolute left-3 top-2.5 text-text-muted" size={17} aria-hidden="true" />
                <input
                  className="h-10 w-72 rounded-lg border border-border bg-bg pl-9 text-sm outline-none focus-ring"
                  placeholder="Search claims"
                  aria-label="Search claims"
                />
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="hidden md:flex items-center gap-3 text-right">
                <div>
                  <div className="text-sm font-semibold text-text">Priya Sharma</div>
                  <div className="text-xs text-text-muted">Investigator</div>
                </div>
                <div className="grid h-9 w-9 place-items-center rounded-full bg-primary text-xs font-bold text-white shadow-sm">
                  PS
                </div>
              </div>
              <button
                onClick={() => {
                  logout();
                  navigate('/login');
                }}
                className="text-text-muted hover:text-primary transition-colors"
                title="Log out"
              >
                <LogOut size={18} aria-hidden="true" />
              </button>
            </div>
          </div>
        </header>
        <main className="flex-1 mx-auto w-full max-w-[1240px] px-4 md:px-6 py-7">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
