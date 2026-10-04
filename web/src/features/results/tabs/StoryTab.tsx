import type { ResultVM } from '../../../types/vm';
import { Empty } from '../../../components/States';

export default function StoryTab({ result }: { result: ResultVM }) {
  const story = result.story;
  if (!story) return <Empty label="Story review was not run for this result." />;
  return (
    <div className="space-y-4">
      <div role="note" className="rounded-lg bg-nile-soft p-3 text-sm text-slate-700">
        {story.note} · source:{' '}
        {story.source === 'llm' ? 'AI summary (validated)' : 'rule-based checks'}
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="font-display font-semibold">
            Contradictions ({story.contradictions.length})
          </h2>
          <div className="mt-3 space-y-2">
            {story.contradictions.map((c, i) => (
              <div key={i} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
                <p>{c.text}</p>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted">
                  {c.sources.map((s) => (
                    <span key={s} className="rounded-full bg-white px-2 py-0.5">
                      {s}
                    </span>
                  ))}
                  {c.evidenceIds.map((id) => (
                    <span key={id} className="mono">
                      {id}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            {!story.contradictions.length && <div className="text-sm text-muted">None found.</div>}
          </div>
        </div>
        <div className="card p-5">
          <h2 className="font-display font-semibold">Consistent points</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
            {story.consistentPoints.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
          {!story.consistentPoints.length && <div className="text-sm text-muted">None listed.</div>}
        </div>
      </div>
    </div>
  );
}
