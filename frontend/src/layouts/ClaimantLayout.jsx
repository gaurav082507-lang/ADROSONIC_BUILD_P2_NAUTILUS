import React from 'react';
import { Outlet, Link, useLocation, useNavigate, Navigate } from 'react-router-dom';
import { FileText, PlusCircle, LogOut, Globe, ShieldCheck } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useI18n } from '../i18n/I18nContext';
import Logo from '../components/Logo';

export default function ClaimantLayout() {
  const { user, logout, isAuthenticated } = useAuth();
  const { t, toggleLang, lang } = useI18n();
  const location = useLocation();
  const navigate = useNavigate();

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (user?.role === 'investigator') return <Navigate to="/app" replace />;

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  const navItems = [
    { label: t('myClaimsNav') || 'My Claims', path: '/claims/mine', icon: FileText },
    { label: t('newClaimNav') || 'File New Claim', path: '/claim/new', icon: PlusCircle },
  ];

  return (
    <div className="min-h-screen bg-[#FFFBF2] text-slate-800 font-sans flex flex-col justify-between selection:bg-amber-100">
      {/* Top Navbar */}
      <header className="bg-white/90 backdrop-blur-md border-b border-amber-100 sticky top-0 z-30 shadow-xs">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/claims/mine" className="hover:opacity-90 transition-opacity">
            <Logo size="sm" dark={false} />
          </Link>

          <div className="flex items-center gap-2">
            <button
              onClick={toggleLang}
              className="flex items-center gap-1 px-2.5 py-1 rounded-full border border-amber-200 bg-amber-50 hover:bg-amber-100 text-xs font-medium text-amber-900 transition-colors"
            >
              <Globe className="w-3.5 h-3.5 text-amber-700" />
              <span>{lang === 'en' ? 'हिन्दी' : 'English'}</span>
            </button>

            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-amber-50 transition-colors"
              title={t('logout') || 'Sign Out'}
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area (centered container) */}
      <main className="flex-1 w-full max-w-2xl mx-auto px-4 py-6 pb-24">
        <Outlet />
      </main>

      {/* Mobile-first Sticky Bottom Navigation */}
      <nav className="fixed bottom-0 inset-x-0 bg-white/95 backdrop-blur-md border-t border-amber-200/80 z-30 py-2 px-6 shadow-lg sm:max-w-md sm:mx-auto sm:rounded-t-2xl sm:bottom-0">
        <div className="flex items-center justify-around">
          {navItems.map((item) => {
            const active = location.pathname.startsWith(item.path);
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center gap-1 py-1 px-4 rounded-xl text-xs font-semibold transition-all ${
                  active
                    ? 'text-blue-600 font-bold scale-105'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Icon className={`w-5 h-5 ${active ? 'text-blue-600 stroke-[2.5]' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
