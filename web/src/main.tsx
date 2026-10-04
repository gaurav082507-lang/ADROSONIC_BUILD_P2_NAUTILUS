import React from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './styles/globals.css';

class ErrorBoundary extends React.Component<
  React.PropsWithChildren<object>,
  { error: Error | null }
> {
  declare props: React.PropsWithChildren<object>;
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  componentDidCatch(error: Error) {
    console.error('[Lucen AI]', error);
  }
  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'grid',
            placeItems: 'center',
            padding: 24,
            fontFamily: 'Inter,system-ui',
            background: '#F5F7FA',
          }}
        >
          <div
            style={{
              maxWidth: 760,
              background: '#fff',
              padding: 28,
              borderRadius: 16,
              border: '1px solid #E3E8EF',
            }}
          >
            <strong>Lucen AI startup error</strong>
            <pre style={{ whiteSpace: 'pre-wrap', marginTop: 16 }}>
              {this.state.error.stack || this.state.error.message}
            </pre>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 10_000 },
  },
});

async function bootstrap() {
  if (import.meta.env.VITE_USE_MOCKS !== '1' && 'serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(regs => {
      for (const reg of regs) {
        if (reg.active?.scriptURL.includes('mockServiceWorker')) {
          reg.unregister();
        }
      }
    });
  }

  createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <App />
          <div style={{ position: 'fixed', bottom: 16, right: 16, background: '#10B981', color: 'white', padding: '4px 12px', borderRadius: 999, fontSize: 12, fontWeight: 700, pointerEvents: 'none', zIndex: 9999, boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)' }}>LIVE</div>
        </QueryClientProvider>
      </ErrorBoundary>
    </React.StrictMode>,
  );
}
bootstrap().catch((error) => console.error('[Lucen AI bootstrap]', error));
