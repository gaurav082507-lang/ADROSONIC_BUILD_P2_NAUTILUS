with open('web/src/features/analytics/AnalyticsPage.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

target1 = """function Analytics() {
  const [range, setRange] = useState<Range>('30d');
  const [type, setType] = useState('');
  const q = useAnalyticsTrends(range, type || undefined);"""
replacement1 = """function Analytics() {
  const [range, setRange] = useState<Range>('30d');
  const [type, setType] = useState('');
  const q = useAnalyticsTrends(range, type || undefined);
  const biz = useBusinessAnalytics(range);"""

target2 = """      {q.isLoading && <Loading label="Loading analytics…" />}"""
replacement2 = """      {(q.isLoading || biz.isLoading) && <Loading label="Loading analytics…" />}"""

target3 = """      {q.data && ("""
replacement3 = """      {biz.data && (
        <div className="grid gap-4 md:grid-cols-4 mb-6">
            <div className="card p-5 bg-blue-50">
              <div className="text-sm text-blue-900/80">Total Processed</div>
              <div className="mt-2 font-display text-3xl font-bold text-blue-900">{biz.data.claims_processed}</div>
            </div>
            <div className="card p-5 bg-green-50">
              <div className="text-sm text-green-900/80">Fast-Track Rate</div>
              <div className="mt-2 font-display text-3xl font-bold text-green-900">{biz.data.fast_track_rate}%</div>
            </div>
            <div className="card p-5 bg-red-50">
              <div className="text-sm text-red-900/80">Fraud Prevented</div>
              <div className="mt-2 font-display text-3xl font-bold text-red-900">₹{(biz.data.fraud_prevented_amount / 100000).toFixed(1)}L</div>
            </div>
            <div className="card p-5 bg-purple-50">
              <div className="text-sm text-purple-900/80">Platform ROI</div>
              <div className="mt-2 font-display text-3xl font-bold text-purple-900">{biz.data.roi_multiple}x</div>
            </div>
        </div>
      )}
      {q.data && ("""

text = text.replace(target1, replacement1).replace(target2, replacement2).replace(target3, replacement3)

with open('web/src/features/analytics/AnalyticsPage.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
