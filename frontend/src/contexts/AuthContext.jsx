/**
 * Auth context – token stored in memory + sessionStorage (try/catch).
 * Never stored in localStorage for XSS safety.
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

const SESSION_KEY = 'lucen_token';
const USER_KEY = 'lucen_user';

function trySession(fn) {
  try { return fn(); } catch { return null; }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => trySession(() => sessionStorage.getItem(SESSION_KEY)));
  const [user, setUser]   = useState(() => {
    const raw = trySession(() => sessionStorage.getItem(USER_KEY));
    return raw ? JSON.parse(raw) : null;
  });

  const login = useCallback((tok, userObj) => {
    setToken(tok);
    setUser(userObj);
    trySession(() => { sessionStorage.setItem(SESSION_KEY, tok); sessionStorage.setItem(USER_KEY, JSON.stringify(userObj)); });
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    trySession(() => { sessionStorage.removeItem(SESSION_KEY); sessionStorage.removeItem(USER_KEY); });
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
