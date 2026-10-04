import os
import textwrap

BASE_DIR = r"c:\Users\gaura\Desktop\LUCENAI\frontend"

def write_file(path, content):
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).strip() + "\n")

# Configs
write_file("vite.config.js", """
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
""")

write_file("jsconfig.json", """
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
""")

write_file("tailwind.config.js", """
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: '#F3F5F7',
        surface: '#FFFFFF',
        ink: '#14213D',
        muted: '#5B6578',
        rule: '#D5DBE3',
        marker: '#F2C230',
        band: {
          low: '#2F7D5B',
          medium: '#B7791F',
          high: '#B4232C'
        }
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}
""")

write_file("components.json", """
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": false,
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "src/styles/globals.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils"
  }
}
""")

write_file("src/styles/globals.css", """
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 210 20% 96%;
    --foreground: 221 50% 16%;
    --card: 0 0% 100%;
    --card-foreground: 221 50% 16%;
  }
}
body {
  @apply bg-paper text-ink font-sans;
}
""")

# API
write_file("src/api/client.js", """
// TODO: Hook up AuthProvider token properly per F02

export class ApiError extends Error {
  constructor(status, error_code, details) {
    super(error_code);
    this.status = status;
    this.error_code = error_code;
    this.details = details;
  }
}

export async function fetchClient(endpoint, options = {}) {
  const useMocks = import.meta.env.VITE_USE_MOCKS === "1";
  
  if (useMocks) {
    // Basic mock router
    const mocks = await import('../mocks/handlers.js');
    return mocks.handleMock(endpoint, options);
  }

  const res = await fetch(`/api/v1${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    }
  });

  if (!res.ok) {
    let errBody;
    try {
      errBody = await res.json();
    } catch {
      throw new ApiError(res.status, 'unknown_error', {});
    }
    throw new ApiError(res.status, errBody.error, errBody.details);
  }
  
  if (res.status === 204) return null;
  return res.json();
}
""")

write_file("src/api/types.js", """
/**
 * JSDoc definitions based on openapi.json.
 * @typedef {Object} JobStatus
 * @property {string} job_id
 * @property {string} status
 * 
 * @typedef {Object} AnalysisResult
 * @property {string} id
 * @property {Object} overall
 */
export {};
""")

write_file("src/mocks/handlers.js", """
export async function handleMock(endpoint, options) {
  // Simulate delay
  await new Promise(r => setTimeout(r, 500));
  
  if (endpoint.startsWith('/analyze')) {
    return { job_id: 'mock-job-123' };
  }
  
  if (endpoint.startsWith('/jobs')) {
    return {
      job_id: 'mock-job-123',
      status: 'done',
      mode: 'claim',
      steps: [],
      result_id: 'mock-result-HIGH'
    };
  }

  if (endpoint.startsWith('/results')) {
    return {
      id: 'mock-result-HIGH',
      overall: {
        risk: 0.95,
        band: 'HIGH',
        confidence: 'high',
        summary: 'Mocked high fraud.'
      },
      evidence: []
    };
  }

  throw new Error(`Mock not implemented for ${endpoint}`);
}
""")

# Components
write_file("src/components/RiskBadge.jsx", """
import React from 'react';
import { AlertOctagon, AlertTriangle, ShieldCheck } from 'lucide-react';

const BAND_CONFIG = {
  HIGH: { color: 'text-band-high', bg: 'bg-band-high/10', icon: AlertOctagon, label: 'HIGH' },
  MEDIUM: { color: 'text-band-medium', bg: 'bg-band-medium/10', icon: AlertTriangle, label: 'MEDIUM' },
  LOW: { color: 'text-band-low', bg: 'bg-band-low/10', icon: ShieldCheck, label: 'LOW' }
};

export function RiskBadge({ band }) {
  const config = BAND_CONFIG[band] || BAND_CONFIG.LOW;
  const Icon = config.icon;
  
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-bold text-sm ${config.bg} ${config.color}`}>
      <Icon className="w-4 h-4" />
      <span>{config.label}</span>
    </div>
  );
}
""")

# Layouts
write_file("src/layouts/InvestigatorLayout.jsx", """
import React from 'react';
import { Outlet, Link } from 'react-router-dom';

export default function InvestigatorLayout() {
  return (
    <div className="flex h-screen w-full text-ink bg-paper">
      <aside className="w-64 bg-surface border-r border-rule flex flex-col">
        <div className="p-4 font-bold text-xl border-b border-rule flex items-center gap-2">
          <div className="w-4 h-4 bg-marker rounded-full"></div> Lucen AI
        </div>
        <nav className="flex-1 p-4 flex flex-col gap-2">
          <Link to="/app" className="hover:bg-paper p-2 rounded">Dashboard</Link>
          <Link to="/app/queue" className="hover:bg-paper p-2 rounded">Queue</Link>
          <Link to="/app/analyze" className="hover:bg-paper p-2 rounded">Analyze</Link>
          <Link to="/app/analytics" className="hover:bg-paper p-2 rounded">Analytics</Link>
          <Link to="/app/network" className="hover:bg-paper p-2 rounded">Network</Link>
        </nav>
      </aside>
      <main className="flex-1 flex flex-col min-w-0 bg-paper">
        <header className="h-14 border-b border-rule bg-surface flex items-center px-4 justify-between">
          <input type="search" placeholder="Search claim ID..." className="border border-rule rounded px-3 py-1" />
          <div className="text-sm text-muted">Investigator View</div>
        </header>
        <div className="flex-1 overflow-auto p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
""")

write_file("src/layouts/ClaimantLayout.jsx", """
import React from 'react';
import { Outlet } from 'react-router-dom';

export default function ClaimantLayout() {
  return (
    <div className="min-h-screen w-full flex flex-col bg-paper text-ink">
      <header className="h-14 border-b border-rule bg-surface flex items-center px-4 justify-between">
        <div className="font-bold">Lucen AI Portal</div>
        <button className="text-sm border border-rule px-2 py-1 rounded">EN / हिंदी</button>
      </header>
      <main className="flex-1 p-4 md:max-w-md md:mx-auto w-full">
        <Outlet />
      </main>
    </div>
  );
}
""")

# Shell Pages
write_file("src/routes/LandingPage.jsx", """
import React from 'react';
import { Link } from 'react-router-dom';

export default function LandingPage() {
  return (
    <div className="p-8 text-center min-h-screen flex flex-col items-center justify-center bg-paper text-ink">
      <h1 className="text-4xl font-bold mb-4">Lucen AI</h1>
      <p className="mb-8">Catch AI-faked claims before they're paid.</p>
      <div className="flex justify-center gap-4">
        <Link to="/claim/new" className="bg-ink text-white px-4 py-2 rounded">File a claim</Link>
        <Link to="/login" className="border border-rule bg-surface px-4 py-2 rounded">Investigator Demo</Link>
      </div>
    </div>
  );
}
""")

write_file("src/routes/LoginPage.jsx", """
import React from 'react';
import { Link } from 'react-router-dom';
export default function LoginPage() {
  return <div className="p-8 max-w-sm mx-auto mt-20 bg-surface border border-rule shadow-sm rounded-lg">
    <h1 className="text-2xl font-bold mb-4">Login Page (Auth TODO)</h1>
    <ul className="space-y-4">
      <li><Link to="/app" className="text-blue-500 underline block">Enter Investigator Portal (Priya)</Link></li>
      <li><Link to="/claim/new" className="text-blue-500 underline block">Enter Claimant Portal (Ravi/Anil)</Link></li>
    </ul>
  </div>;
}
""")

write_file("src/routes/claimant/ClaimWizardPage.jsx", """
import React from 'react';
export default function ClaimWizardPage() {
  return <div className="bg-surface p-4 border border-rule rounded-lg">Claim Wizard (TODO)</div>;
}
""")

write_file("src/routes/claimant/ClaimStatusPage.jsx", """
import React from 'react';
export default function ClaimStatusPage() {
  return <div className="bg-surface p-4 border border-rule rounded-lg">Claim Status (TODO)</div>;
}
""")

write_file("src/routes/app/DashboardPage.jsx", """
import React from 'react';
export default function DashboardPage() {
  return <div className="bg-surface p-6 border border-rule rounded-lg shadow-sm">Investigator Dashboard (TODO)</div>;
}
""")

write_file("src/routes/app/QueuePage.jsx", """
import React from 'react';
export default function QueuePage() {
  return <div className="bg-surface p-6 border border-rule rounded-lg shadow-sm">Triage Queue (TODO)</div>;
}
""")

write_file("src/routes/app/AnalyzePage.jsx", """
import React, { useState } from 'react';
import { fetchClient } from '@/api/client';
import { useNavigate } from 'react-router-dom';

export default function AnalyzePage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleUpload = async () => {
    setLoading(true);
    try {
      // Mock upload
      const res = await fetchClient('/analyze/image', { method: 'POST', body: JSON.stringify({}) });
      if (res && res.job_id) {
        // Poll logic would go here, simulating redirect to result for now
        setTimeout(() => {
          navigate(`/app/results/${res.job_id}`);
        }, 1500);
      }
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <div className="p-6 bg-surface rounded-lg border border-rule shadow-sm">
      <h2 className="text-2xl font-bold mb-4">Analyze Page (TODO)</h2>
      <button 
        onClick={handleUpload}
        disabled={loading}
        className="bg-ink text-white px-4 py-2 rounded"
      >
        {loading ? 'Analyzing...' : 'Simulate Upload & Analyze'}
      </button>
    </div>
  );
}
""")

write_file("src/routes/app/ResultPage.jsx", """
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { RiskBadge } from '@/components/RiskBadge';
import { fetchClient } from '@/api/client';

export default function ResultPage() {
  const { id } = useParams();
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetchClient(`/results/${id}`).then(setResult).catch(console.error);
  }, [id]);

  return (
    <div className="bg-surface p-6 rounded-lg border border-rule shadow-sm">
      <h2 className="text-2xl font-bold mb-4">Case Result: {id}</h2>
      {result ? (
        <div>
          <RiskBadge band={result.overall.band} />
          <p className="mt-4 text-ink font-semibold">Risk Score: {result.overall.risk * 100}%</p>
          <p className="mt-2 text-muted">{result.overall.summary}</p>
          <pre className="mt-4 p-4 bg-paper text-sm overflow-auto rounded border border-rule">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      ) : (
        <p>Loading result...</p>
      )}
    </div>
  );
}
""")

write_file("src/routes/app/NetworkPage.jsx", """
import React from 'react';
export default function NetworkPage() {
  return <div className="bg-surface p-6 border border-rule rounded-lg shadow-sm">Fraud Network (TODO)</div>;
}
""")

write_file("src/routes/app/AnalyticsPage.jsx", """
import React from 'react';
export default function AnalyticsPage() {
  return <div className="bg-surface p-6 border border-rule rounded-lg shadow-sm">Analytics (TODO)</div>;
}
""")

# App.jsx
write_file("src/App.jsx", """
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import ClaimantLayout from './layouts/ClaimantLayout';
import InvestigatorLayout from './layouts/InvestigatorLayout';

import LandingPage from './routes/LandingPage';
import LoginPage from './routes/LoginPage';
import ClaimWizardPage from './routes/claimant/ClaimWizardPage';
import ClaimStatusPage from './routes/claimant/ClaimStatusPage';
import DashboardPage from './routes/app/DashboardPage';
import QueuePage from './routes/app/QueuePage';
import AnalyzePage from './routes/app/AnalyzePage';
import ResultPage from './routes/app/ResultPage';
import NetworkPage from './routes/app/NetworkPage';
import AnalyticsPage from './routes/app/AnalyticsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        
        <Route element={<ClaimantLayout />}>
          <Route path="/claim/new" element={<ClaimWizardPage />} />
          <Route path="/claim/:id" element={<ClaimStatusPage />} />
        </Route>
        
        <Route path="/app" element={<InvestigatorLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="queue" element={<QueuePage />} />
          <Route path="analyze" element={<AnalyzePage />} />
          <Route path="results/:id" element={<ResultPage />} />
          <Route path="network" element={<NetworkPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
""")

write_file("src/main.jsx", """
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
""")

write_file(".env", "VITE_USE_MOCKS=1\n")
