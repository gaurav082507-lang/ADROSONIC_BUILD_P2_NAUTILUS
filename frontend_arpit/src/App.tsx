import { Suspense, lazy, type ReactElement } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import LandingPage from './routes/LandingPage';
import LoginPage from './routes/LoginPage';
import InvestigatorLayout from './layouts/InvestigatorLayout';
import { getRole, getToken } from './api/session';
import MyClaimsPage from './features/claims/MyClaimsPage';
import DashboardPage from './features/dashboard/DashboardPage';
import QueuePage from './features/queue/QueuePage';
import HistoryPage from './features/history/HistoryPage';

const ClaimWizardPage = lazy(() => import('./features/claims/ClaimWizardPage'));
const ClaimStatusPage = lazy(() => import('./features/claims/ClaimStatusPage'));
const AnalyticsPage = lazy(() => import('./features/analytics/AnalyticsPage'));
const NetworkPage = lazy(() => import('./features/network/NetworkPage'));
const AnalyzePage = lazy(() => import('./features/analyze/AnalyzePage'));
const ResultPage = lazy(() => import('./features/results/ResultPage'));

export function Guard({
  role,
  children,
}: {
  role: 'investigator' | 'claimant';
  children: ReactElement;
}) {
  if (!getToken()) return <Navigate to="/login" replace />;
  if (getRole() !== role)
    return <Navigate to={role === 'investigator' ? '/app' : '/claim'} replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="p-10 text-sm text-muted">Loading…</div>}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/claim"
            element={
              <Guard role="claimant">
                <MyClaimsPage />
              </Guard>
            }
          />
          <Route
            path="/claim/new"
            element={
              <Guard role="claimant">
                <ClaimWizardPage />
              </Guard>
            }
          />
          <Route
            path="/claim/:id"
            element={
              <Guard role="claimant">
                <ClaimStatusPage />
              </Guard>
            }
          />
          <Route
            path="/app"
            element={
              <Guard role="investigator">
                <InvestigatorLayout />
              </Guard>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="queue" element={<QueuePage />} />
            <Route path="analyze" element={<AnalyzePage />} />
            <Route path="history" element={<HistoryPage />} />
            <Route path="results/:id" element={<ResultPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="network" element={<NetworkPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
