import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid, Legend } from 'recharts';
import { useQueue } from '../../api/hooks';
import { Loading, ErrorState } from '../../components/States';
import { api } from '../../api/client';

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => {
      return api.get<any>('/dashboard/stats');
    },
    refetchInterval: 30000,
  });

  const { data: queueData, isLoading: queueLoading } = useQueue({ limit: 10 });

  if (statsLoading || queueLoading) return <Loading />;
  if (statsError) return <ErrorState message="Failed to load dashboard data" retry={() => window.location.reload()} />;

  if (!stats) return <Loading />;
  const { kpis, verdicts, signals, timeData, riskDist } = stats;

  const COLORS = {
    Genuine: 'var(--success)',
    Suspicious: 'var(--warning)',
    'Deepfake-Fraud': 'var(--danger)'
  };

  return (
    <div className="pb-10">
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-nile">Investigator Dashboard</span>
            <span className="rounded-full bg-nile-soft px-2 py-0.5 text-xs font-medium text-primary-dark border border-nile">Data: test-case runs</span>
          </div>
          <h1 className="font-display mt-1 text-3xl font-bold text-primary-dark">Good afternoon, Investigator.</h1>
          <p className="mt-2 text-sm text-text-muted">Overview of recent AI claims analysis.</p>
        </div>
        <Link
          to="/app/analyze"
          className="rounded-lg bg-primary hover:bg-primary-hover px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors"
        >
          New analysis
        </Link>
      </div>

      <div className="mt-7 grid gap-4 md:grid-cols-5">
        <div className="card p-5">
          <div className="text-sm font-medium text-text-muted">Total Cases</div>
          <div className="mt-2 font-display text-3xl font-bold text-primary-dark">{kpis.total}</div>
        </div>
        <div className="card p-5">
          <div className="text-sm font-medium text-text-muted">Flagged / High Risk</div>
          <div className="mt-2 font-display text-3xl font-bold text-danger">{kpis.flagged}</div>
        </div>
        <div className="card p-5">
          <div className="text-sm font-medium text-text-muted">Cleared / Genuine</div>
          <div className="mt-2 font-display text-3xl font-bold text-success">{kpis.cleared}</div>
        </div>
        <div className="card p-5">
          <div className="text-sm font-medium text-text-muted">Pending Review</div>
          <div className="mt-2 font-display text-3xl font-bold text-warning">{kpis.pending}</div>
        </div>
        <div className="card p-5">
          <div className="text-sm font-medium text-text-muted">Avg Risk Score</div>
          <div className="mt-2 font-display text-3xl font-bold text-primary-dark">{kpis.avgRisk}%</div>
        </div>
      </div>

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <div className="card p-5">
          <h2 className="font-display font-semibold text-primary-dark mb-4">Verdict Breakdown</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={verdicts} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                  {verdicts.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[entry.name as keyof typeof COLORS] || 'var(--primary)'} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-5">
          <h2 className="font-display font-semibold text-primary-dark mb-4">Fraud Signals Detected</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={signals} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="var(--warning)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-5">
          <h2 className="font-display font-semibold text-primary-dark mb-4">Cases Over Time</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="Total Cases" stroke="var(--primary)" strokeWidth={2} />
                <Line type="monotone" dataKey="Flagged" stroke="var(--danger)" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-5">
          <h2 className="font-display font-semibold text-primary-dark mb-4">Risk Score Distribution</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskDist}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="bucket" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="cases" fill="var(--nile)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="mt-8 card overflow-hidden">
        <div className="p-5 border-b border-border flex justify-between items-center bg-nile-soft/30">
          <h2 className="font-display font-semibold text-primary-dark">Recent Cases</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-nile-soft text-primary-dark text-xs uppercase">
              <tr>
                <th className="px-5 py-3 font-semibold">Claim ID</th>
                <th className="px-5 py-3 font-semibold">Claimant</th>
                <th className="px-5 py-3 font-semibold">Type</th>
                <th className="px-5 py-3 font-semibold">Date</th>
                <th className="px-5 py-3 font-semibold">Risk Score</th>
                <th className="px-5 py-3 font-semibold">Verdict</th>
                <th className="px-5 py-3 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-surface">
              {queueData?.length === 0 && (
                <tr><td colSpan={7} className="px-5 py-8 text-center text-text-muted">No cases yet.</td></tr>
              )}
              {queueData?.slice(0, 10).map((c: any) => (
                <tr key={c.id} className="hover:bg-nile-soft/20 transition-colors">
                  <td className="px-5 py-3 font-mono text-xs text-text-muted">{c.id}</td>
                  <td className="px-5 py-3 font-medium">{c.claimantMasked || 'Unknown'}</td>
                  <td className="px-5 py-3 capitalize">{c.type}</td>
                  <td className="px-5 py-3 text-text-muted">{new Date(c.submitted).toLocaleDateString()}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-16 overflow-hidden rounded-full bg-border">
                        <div className="h-full bg-danger" style={{ width: `${(c.risk || 0) * 100}%` }} />
                      </div>
                      <span className="text-xs">{((c.risk || 0) * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                      c.band === 'HIGH' ? 'bg-danger/10 text-danger' : 
                      c.band === 'MEDIUM' ? 'bg-warning/10 text-warning' : 
                      'bg-success/10 text-success'
                    }`}>
                      {c.band === 'HIGH' ? 'Deepfake' : c.band === 'MEDIUM' ? 'Suspicious' : 'Genuine'}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <Link to={`/app/claims/${c.id}`} className="text-primary hover:text-primary-hover font-medium">View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
