import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { Logo } from '../Logo';

export function TopMenu() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && mobileOpen) {
        setMobileOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileOpen]);

  const closeMenu = () => setMobileOpen(false);

  // Smooth scroll helper
  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, hash: string) => {
    if (location.pathname === '/') {
      e.preventDefault();
      const el = document.getElementById(hash.substring(1));
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
      closeMenu();
    }
  };

  const links = [
    { name: 'Product', hash: '#what-we-check' },
    { name: 'How it works', hash: '#how-it-works' },
    { name: 'For insurers', hash: '#portals' },
    { name: 'About us', hash: '#about' },
    { name: 'Contact', hash: '#contact' },
  ];

  return (
    <>
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled ? 'bg-white shadow-sm' : 'bg-transparent'
        }`}
      >
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-2" onClick={closeMenu}>
            <Logo />
            <span className="font-display font-bold text-xl text-primary-dark tracking-tight">Lucen AI</span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-6">
            {links.map((link) => (
              <Link
                key={link.hash}
                to={location.pathname === '/' ? link.hash : `/${link.hash}`}
                onClick={(e) => handleNavClick(e, link.hash)}
                className="text-sm font-medium text-text hover:text-primary transition-colors focus-visible:outline-primary"
              >
                {link.name}
              </Link>
            ))}
          </nav>

          {/* Desktop Actions */}
          <div className="hidden md:flex items-center gap-4">
            <Link
              to="/claim"
              className="text-sm font-medium text-primary-dark hover:text-primary transition-colors focus-visible:outline-primary"
            >
              Track claim
            </Link>
            <Link
              to="/login?role=investigator"
              className="rounded-lg border-2 border-primary-dark text-primary-dark hover:bg-nile-soft px-4 py-2 text-sm font-semibold transition-colors focus-visible:outline-primary"
            >
              Insurer login
            </Link>
            <Link
              to="/claim/new"
              className="rounded-lg bg-primary hover:bg-primary-hover px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors focus-visible:outline-primary"
            >
              File a claim
            </Link>
          </div>

          {/* Mobile Toggle */}
          <button
            className="md:hidden p-2 text-primary-dark focus-visible:outline-primary"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </header>

      {/* Mobile Drawer */}
      <div
        className={`fixed inset-0 z-40 bg-white transform transition-transform duration-300 md:hidden flex flex-col pt-24 px-6 pb-6 ${
          mobileOpen ? 'translate-y-0' : '-translate-y-full'
        }`}
      >
        <nav className="flex flex-col gap-6 text-lg font-medium text-text flex-1">
          {links.map((link) => (
            <Link
              key={link.hash}
              to={location.pathname === '/' ? link.hash : `/${link.hash}`}
              onClick={(e) => handleNavClick(e, link.hash)}
              className="hover:text-primary transition-colors focus-visible:outline-primary"
            >
              {link.name}
            </Link>
          ))}
        </nav>
        <div className="flex flex-col gap-4 mt-8">
          <Link
            to="/claim"
            onClick={closeMenu}
            className="text-center font-medium text-primary-dark py-3 focus-visible:outline-primary"
          >
            Track claim
          </Link>
          <Link
            to="/login?role=investigator"
            onClick={closeMenu}
            className="w-full text-center rounded-lg border-2 border-primary-dark text-primary-dark hover:bg-nile-soft px-4 py-3 font-semibold transition-colors focus-visible:outline-primary"
          >
            Insurer login
          </Link>
          <Link
            to="/claim/new"
            onClick={closeMenu}
            className="w-full text-center rounded-lg bg-primary hover:bg-primary-hover px-4 py-3 font-semibold text-white shadow-sm transition-colors focus-visible:outline-primary"
          >
            File a claim
          </Link>
        </div>
      </div>
    </>
  );
}
