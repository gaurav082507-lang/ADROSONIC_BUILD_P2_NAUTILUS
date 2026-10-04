import { useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useAnalyticsTrends, useBusinessAnalytics } from '../../api/hooks';
import { friendlyError } from '../../lib/errorMessages';
import { ChartCard } from '../../components/ChartCard';
import { FeatureGate } from '../../components/FeatureGate';
import { ErrorState, Loading } from '../../components/States';
import { summarise } from './analyticsSummaries';

const C = { low: '#16A34A', medium: '#D97706', high: '#DC2626', blue: '#3B82F6', ink: '#0B1220' };
type Range = '7d' | '30d' | '90d';

export default function AnalyticsPage() {
  return (
    <div>
      <div className="text-sm text-muted">Signals</div>
      <h1 className="font-display mt-1 text-3xl font-bold">Risk analytics</h1>
      <div className="mt-6">
        <FeatureGate feature="analytics" title="Analytics">
          <Analytics />
        </FeatureGate>
      </div>
    </div>
  );
}

function Analytics() {
  const [range, setRange] = useState<Range>('30d');
  const [type, setType] = useState('');
  const q = useAnalyticsTrends(range, type || undefined);
  const biz = useBusinessAnalytics(range);
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-3">
        <div
          className="flex rounded-lg border bg-white p-1 text-sm"
          role="tablist"
          aria-label="Date range"
        >
          {(['7d', '30d', '90d'] as Range[]).map((r) => (
            <button
              key={r}
              role="tab"
              aria-selected={range === r}
              onClick={() => setRange(r)}
              className={`rounded-md px-3 py-1.5 ${range === r ? 'bg-primary-dark text-white' : ''}`}
            >
              {r}
            </button>
          ))}
        </div>
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="rounded-lg border bg-white px-3 text-sm"
          aria-label="Claim type"
        >
          <option value="">All claim types</option>
          <option value="motor">Motor</option>
          <option value="health">Health</option>
          <option value="property">Property</option>
        </select>
      </div>
      {(q.isLoading || biz.isLoading) && <Loading label="Loading analytics…" />}
      {q.error && (
        <ErrorState
          message={friendlyError((q.error as any).code, (q.error as any).message)}
          retry={() => q.refetch()}
        />
      )}
      {q.data && <Charts data={q.data} />}
    </div>
  );
}

function Charts({ data }: { data: NonNullable<ReturnType<typeof useAnalyticsTrends>['data']> }) {
  const s = summarise(data);
  const daily = data.daily.map((d) => ({
    ...d,
    day: d.date.slice(5),
    flaggedPct: Math.round(d.flaggedRate * 100),
    avgRiskPct: Math.round(d.avgRisk * 100),
  }));
  return (
    <div className="space-y-5">
      {data.spike.detected && (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          <b>Spike detected.</b> {data.spike.message}
        </div>
      )}
      <div className="grid gap-5 xl:grid-cols-2">
        <ChartCard
          title="Claims per day by band"
          summary={s.volume}
          columns={['Date', 'LOW', 'MEDIUM', 'HIGH']}
          rows={data.daily.map((d) => [d.date, d.low, d.medium, d.high])}
        >
          <ResponsiveContainer>
            <BarChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Legend />
              <Bar dataKey="low" name="LOW" stackId="b" fill={C.low} />
              <Bar dataKey="medium" name="MEDIUM" stackId="b" fill={C.medium} />
              <Bar dataKey="high" name="HIGH" stackId="b" fill={C.high} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard
          title="Flagged rate and average risk"
          summary={s.rate}
          columns={['Date', 'Flagged %', 'Avg risk %']}
          rows={daily.map((d) => [d.date, d.flaggedPct, d.avgRiskPct])}
        >
          <ResponsiveContainer>
            <LineChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" fontSize={11} />
              <YAxis fontSize={11} unit="%" />
              <Tooltip />
              <Legend />
              <Line dataKey="flaggedPct" name="Flagged %" stroke={C.high} dot={false} />
              <Line
                dataKey="avgRiskPct"
                name="Avg risk %"
                stroke={C.blue}
                dot={false}
                strokeDasharray="5 4"
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard
          title="Top signals"
          summary={s.signals}
          columns={['Signal', 'Count']}
          rows={data.topSignals.map((x) => [`${x.title} (${x.id})`, x.count])}
        >
          <ResponsiveContainer>
            <BarChart data={data.topSignals} layout="vertical" margin={{ left: 40 }}>
              <XAxis type="number" fontSize={11} />
              <YAxis type="category" dataKey="title" width={170} fontSize={11} />
              <Tooltip />
              <Bar dataKey="count" name="Count" fill={C.ink} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard
          title="By claim type"
          summary={s.byType}
          columns={['Type', 'Total', 'Flagged']}
          rows={data.byType.map((x) => [x.type, x.total, x.flagged])}
        >
          <ResponsiveContainer>
            <BarChart data={data.byType}>
              <XAxis dataKey="type" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Legend />
              <Bar dataKey="total" name="Total" fill="#CBD5E1" />
              <Bar dataKey="flagged" name="Flagged" fill={C.high} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard
          title="Flags by modality"
          summary={s.modality}
          columns={['Modality', 'Flagged']}
          rows={data.byModality.map((x) => [x.modality, x.flagged])}
        >
          <ResponsiveContainer>
            <BarChart data={data.byModality}>
              <XAxis dataKey="modality" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Bar dataKey="flagged" name="Flagged" fill={C.medium} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard
          title="Recycled evidence and rings per week"
          summary={`${s.recycled} ${s.rings}`}
          columns={['Week', 'Recycled evidence', 'New rings']}
          rows={data.recycledWeekly.map((w, i) => [
            w.week,
            w.count,
            data.ringsWeekly[i]?.count ?? 0,
          ])}
        >
          <ResponsiveContainer>
            <BarChart
              data={data.recycledWeekly.map((w, i) => ({
                week: w.week,
                recycled: w.count,
                rings: data.ringsWeekly[i]?.count ?? 0,
              }))}
            >
              <XAxis dataKey="week" fontSize={11} />
              <YAxis fontSize={11} allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="recycled" name="Recycled evidence" fill={C.medium} />
              <Bar dataKey="rings" name="New rings" fill={C.high} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard
          title="Investigator decisions per week"
          summary={s.decisions}
          columns={['Week', 'Approved', 'Rejected', 'Evidence requested']}
          rows={data.decisionsWeekly.map((w) => [w.week, w.approved, w.rejected, w.requested])}
        >
          <ResponsiveContainer>
            <BarChart data={data.decisionsWeekly}>
              <XAxis dataKey="week" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Legend />
              <Bar dataKey="approved" name="Approved" stackId="d" fill={C.low} />
              <Bar dataKey="requested" name="Evidence requested" stackId="d" fill={C.medium} />
              <Bar dataKey="rejected" name="Rejected" stackId="d" fill={C.high} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}
