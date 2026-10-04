import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import { AuthProvider } from './contexts/AuthContext';
import { I18nProvider } from './i18n/I18nContext';

import ClaimantLayout from './layouts/ClaimantLayout';
import InvestigatorLayout from './layouts/InvestigatorLayout';

import LandingPage from './routes/LandingPage';
import LoginPage from './routes/LoginPage';

// Claimant pages
import ClaimWizardPage from './routes/claimant/ClaimWizardPage';
import ClaimStatusPage from './routes/claimant/ClaimStatusPage';
import MyClaimsPage from './routes/claimant/MyClaimsPage';

// Investigator pages
import DashboardPage from './routes/app/DashboardPage';
import AnalyzePage from './routes/app/AnalyzePage';
import ResultPage from './routes/app/ResultPage';
import HistoryPage from './routes/app/HistoryPage';
import NetworkPage from './routes/app/NetworkPage';
import AnalyticsPage from './routes/app/AnalyticsPage';
import QueuePage from './routes/app/QueuePage';

export default function App() {
  return (
    <AuthProvider>
      <I18nProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />

            {/* Claimant portal */}
            <Route element={<ClaimantLayout />}>
              <Route path="/claims/mine" element={<MyClaimsPage />} />
              <Route path="/claim/new" element={<ClaimWizardPage />} />
              <Route path="/claim/:id" element={<ClaimStatusPage />} />
            </Route>

            {/* Investigator portal */}
            <Route path="/app" element={<InvestigatorLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="queue" element={<QueuePage />} />
              <Route path="history" element={<HistoryPage />} />
              <Route path="analyze" element={<AnalyzePage />} />
              <Route path="results/:id" element={<ResultPage />} />
              <Route path="network" element={<NetworkPage />} />
              <Route path="analytics" element={<AnalyticsPage />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </I18nProvider>
    </AuthProvider>
  );
}
