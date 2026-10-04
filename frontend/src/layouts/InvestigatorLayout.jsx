import React, { useState } from 'react';
import { Outlet, Link, useLocation, Navigate, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Inbox,
  ScanEye,
  History,
  Share2,
  BarChart3,
  Search,
  LogOut,
  Shield,
  ChevronRight,
  Bell
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Logo from '../components/Logo';

export default function InvestigatorLayout() {
  const { user, logout, isAuthenticated } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (user?.role !== 'investigator') return <Navigate to="/claims/mine" replace />;

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  function handleSearch(e) {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) return;
    if (q.toUpperCase().startsWith('CLM-')) {
      navigate(`/app/results/${encodeURIComponent(q)}`);
    } else {
      navigate(`/app/queue?q=${encodeURIComponent(q)}`);
    }
  }

  const navItems = [
    { label: 'Dashboard', path: '/app', icon: LayoutDashboard, exact: true },
    { label: 'Review Queue', path: '/app/queue', icon: Inbox },
    { label: 'Analyze Claim', path: '/app/analyze', icon: ScanEye },
    { label: 'Audit History', path: '/app/history', icon: History },
    { label: 'Fraud Network', path: '/app/network', icon: Share2 },
    { label: 'Analytics & Trends', path: '/app/analytics', icon: BarChart3 },
  ];

  function isActive(item) {
    if (item.exact) return location.pathname === item.path;
    return location.pathname.startsWith(item.path);
  }

  // Derive breadcrumb title
  const currentNav = navItems.find((n) => isActive(n)) || { label: 'Investigation' };

  return (
    <div className="flex h-screen w-full bg-[#F5F7FA] text-[#0B1220] font-sans overflow-hidden">
      {/* 240px Investigator Sidebar */}
      <aside
        style={{ width: '240px' }}
        className="shrink-0 bg-[#0B1220] border-r border-slate-800 text-slate-300 flex flex-col justify-between select-none z-20"
      >
        <div>
          {/* Brand Header */}
          <div className="h-16 px-5 border-b border-slate-800/80 flex items-center justify-between">
            <Logo size="md" dark={true} />
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 font-semibold border border-blue-500/30">
              SIU
            </span>
          </div>

          {/* Navigation Items */}
          <nav className="p-3 space-y-1">
            <div className="px-3 pt-2 pb-1.5 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              Investigation Desk
            </div>
            {navItems.map((item) => {
              const active = isActive(item);
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                    active
                      ? 'bg-blue-600 text-white font-semibold shadow-sm shadow-blue-600/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${active ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Card & Logout */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-950/40">
          <div className="flex items-center gap-2.5 px-2 py-1.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-400 flex items-center justify-center font-bold text-xs">
              <Shield className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-white truncate">
                {user?.name || user?.email || 'SIU Officer'}
              </div>
              <div className="text-[10px] text-slate-400 truncate">
                Senior Investigator
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full mt-2 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-900/80 hover:bg-slate-900 text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="h-16 bg-white border-b border-[#E3E8EF] px-6 flex items-center justify-between shrink-0 z-10 shadow-xs">
          {/* Breadcrumbs */}
          <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
            <span className="text-slate-400 font-normal">Workspace</span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-semibold text-slate-800">{currentNav.label}</span>
          </div>

          {/* Quick Search & Actions */}
          <div className="flex items-center gap-4">
            <form onSubmit={handleSearch} className="relative w-64 sm:w-72">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="search"
                placeholder="Search Claim ID (e.g. CLM-001)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#F5F7FA] border border-[#E3E8EF] hover:border-slate-300 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all"
              />
            </form>

            <div className="h-4 w-px bg-slate-200" />

            <div className="flex items-center gap-2 text-xs text-slate-500">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="hidden sm:inline font-mono text-[11px]">System Online</span>
            </div>
          </div>
        </header>

        {/* Page Outlet */}
        <main className="flex-1 overflow-y-auto p-6 bg-[#F5F7FA]">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
