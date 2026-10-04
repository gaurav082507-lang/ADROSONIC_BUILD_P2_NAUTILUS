import React, { createContext, useContext, useState } from 'react';
import strings from './strings';

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [lang, setLang] = useState('en');
  const t = (key) => strings[lang]?.[key] ?? strings.en[key] ?? key;
  const toggleLang = () => setLang(l => l === 'en' ? 'hi' : 'en');

  return (
    <I18nContext.Provider value={{ lang, t, toggleLang }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}
