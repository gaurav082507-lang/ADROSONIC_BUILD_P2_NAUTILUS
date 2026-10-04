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
} from 'lucide-react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { logout } from '../api/session';
import { Logo } from '../components/Logo';

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

  return (
    <div className="min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-border bg-white lg:block">
        <div className="p-6">
          <Logo />
        </div>
        <nav className="space-y-1 px-3" aria-label="Investigator navigation">
          {nav.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm ${
                location.pathname === to
                  ? 'bg-slate-100 font-semibold'
                  : 'text-muted hover:bg-slate-50'
              }`}
            >
              <Icon size={18} aria-hidden="true" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="absolute bottom-5 left-4 right-4 rounded-xl border border-border bg-slate-50 p-4">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-ink text-xs font-bold text-white">
              PS
            </div>
            <div>
              <div className="text-sm font-semibold">Priya Sharma</div>
              <div className="text-xs text-muted">Investigator</div>
            </div>
          </div>
          <button
            onClick={() => {
              logout();
              navigate('/login');
            }}
            className="mt-3 flex items-center gap-2 text-xs text-muted"
          >
            <LogOut size={14} aria-hidden="true" />
            Log out
          </button>
        </div>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-border bg-white/90 backdrop-blur">
          <div className="flex h-16 items-center justify-between px-6">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 text-muted" size={17} aria-hidden="true" />
              <input
                className="h-10 w-72 rounded-lg border border-border bg-slate-50 pl-9 text-sm outline-none focus:ring-2 focus:ring-yellow-300"
                placeholder="Search claims"
                aria-label="Search claims"
              />
            </div>
            <div className="text-sm text-muted">Investigator console</div>
          </div>
        </header>
        <main className="mx-auto max-w-[1240px] px-6 py-7">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
