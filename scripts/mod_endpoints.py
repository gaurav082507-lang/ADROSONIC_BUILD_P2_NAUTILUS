import os

file_path = 'web/src/api/raw/endpoints.ts'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

target = """  analytics: {
    getSummary: () =>
      api.get<AnalyticsSummaryRaw>('/analytics/summary', analyticsSummarySchema as any),
    getTrends: ({ range, type }: { range: '7d' | '30d' | '90d'; type?: string }) =>
      api.get<AnalyticsTrendsRaw>(
        `/analytics/trends${qs({ range, type })}`,
        analyticsTrendsSchema as any
      ),
  },"""

replacement = """  analytics: {
    getSummary: () =>
      api.get<AnalyticsSummaryRaw>('/analytics/summary', analyticsSummarySchema as any),
    getTrends: ({ range, type }: { range: '7d' | '30d' | '90d'; type?: string }) =>
      api.get<AnalyticsTrendsRaw>(
        `/analytics/trends${qs({ range, type })}`,
        analyticsTrendsSchema as any
      ),
    getBusiness: ({ range }: { range: '7d' | '30d' | '90d' | 'all' }) =>
      api.get<any>(`/analytics/business${qs({ range })}`, {} as any),
  },"""

text = text.replace(target, replacement)
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated endpoints.ts")
