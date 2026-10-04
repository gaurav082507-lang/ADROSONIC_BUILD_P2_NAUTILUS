import { Link } from 'react-router-dom';
import { useAnalyticsSummary, useHistory, useQueue, useBusinessAnalytics } from '../../api/hooks';
import { Loading, ErrorState } from '../../components/States';
import { friendlyError } from '../../lib/errorMessages';

export default function DashboardPage() {
  const q = useQueue({ limit: 50 });
  const h = useHistory({ page: 1, pageSize: 50 });
  const analyticsOn = true;
  const biz = useBusinessAnalytics('30d', analyticsOn);

  if (q.isLoading || h.isLoading || (analyticsOn && biz.isLoading)) return <Loading />;
  
  if (q.error)
    return (
      <ErrorState
        message={friendlyError((q.error as any).code, (q.error as any).message)}
        retry={() => q.refetch()}
      />
    );

  const rows = q.data ?? [];
  const flagged = rows.filter((x) => x.band !== 'LOW');

  return (
    <div>
      <div className="flex items-end justify-between">
        <div>
          <div className="text-sm text-muted">Investigator console</div>
          <h1 className="font-display mt-1 text-3xl font-bold">Good afternoon, Priya.</h1>
          <p className="mt-2 text-sm text-muted">Based on recent claims.</p>
        </div>
        <Link
          to="/app/analyze"
          className="rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-white"
        >
          New analysis
        </Link>
      </div>

      <div className="mt-7 grid gap-4 md:grid-cols-4">
        {biz.data && (
            [
              ['Claims processed', biz.data.claims_processed, 'Last 30 days'],
              ['Fast-track rate', `${biz.data.fast_track_rate}%`, 'Eligible for auto-approval'],
              ['Fraud prevented', `₹${(biz.data.fraud_prevented_amount / 100000).toFixed(1)}L`, 'Estimated exposure'],
              ['Open rings', biz.data.open_rings, 'Detected multi-claim fraud'],
            ]
        ).map(([label, value, note]) => (
          <div className="card p-5" key={String(label)}>
            <div className="text-sm text-muted">{label}</div>
            <div className="mt-2 font-display text-3xl font-bold">{value}</div>
            <div className="mt-1 text-xs text-muted">{note}</div>
          </div>
        ))}
      </div>

      <div className="mt-8 grid gap-8 md:grid-cols-2">
        <div className="card p-5">
          <h2 className="font-display font-semibold">Decisions (Last 30d)</h2>
          <div className="mt-4 h-64 border border-dashed flex items-center justify-center text-sm text-muted">Weekly chart</div>
        </div>
        <div className="card p-5">
          <h2 className="font-display font-semibold">Risk by Claim Type</h2>
          <div className="mt-4 h-64 border border-dashed flex items-center justify-center text-sm text-muted">Claim type risk chart</div>
        </div>
        <div className="card p-5 md:col-span-2">
          <h2 className="font-display font-semibold">Detected Fraud Patterns</h2>
          <div className="mt-4 flex flex-col gap-3">
             {biz.data?.patterns.map((p: any, i: number) => (
               <div key={i} className="flex justify-between border-b pb-2">
                 <span className="text-sm">{p.pattern}</span>
                 <span className="text-sm font-semibold">{p.count} claims</span>
               </div>
             ))}
          </div>
        </div>
      </div>
      
      {biz.data?.assumptions && (
        <div className="mt-6 text-xs text-muted max-w-3xl">
          * Assumptions: Manual processing cost = ₹{biz.data.assumptions.avg_manual_investigation_cost}, AI cost = ₹{biz.data.assumptions.ai_processing_cost}. ROI = {(biz.data.roi_multiple)}x.
        </div>
      )}
    </div>
  );
}
