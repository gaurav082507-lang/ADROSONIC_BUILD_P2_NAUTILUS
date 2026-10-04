import { useState } from 'react';
import BoxOverlay from '../../../components/BoxOverlay';
import type { ResultVM } from '../../../types/vm';

export default function ImageTab({ result }: { result: ResultVM }) {
  const [mode, setMode] = useState<'original' | 'heatmap' | 'side'>('original');
  const [opacity, setOpacity] = useState(0.65);
  const [active, setActive] = useState<string>();
  const original = result.imageResults[0]?.url;
  const heatmap =
    result.artifacts.heatmap ??
    result.imageResults.find((x) => x.label.toLowerCase().includes('heat'))?.url;
  if (!original && !heatmap) return <div className="card p-8 text-sm text-muted">Not analysed</div>;
  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-center gap-2">
        {(['original', 'heatmap', 'side'] as const).map((value) => (
          <button
            key={value}
            onClick={() => setMode(value)}
            className={`rounded-lg px-3 py-2 text-sm ${mode === value ? 'bg-ink text-white' : 'bg-slate-100'}`}
          >
            {value}
          </button>
        ))}
        <label className="ml-auto text-xs text-muted">
          Heatmap opacity{' '}
          <input
            aria-label="Heatmap opacity"
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={opacity}
            onChange={(e) => setOpacity(Number(e.target.value))}
          />
        </label>
      </div>
      <div className="relative mt-5 overflow-hidden rounded-xl bg-slate-900 p-2">
        <div className={mode === 'side' ? 'grid grid-cols-2 gap-2' : ''}>
          <div className="relative aspect-[4/3] overflow-hidden rounded-lg bg-black">
            {original && (
              <img
                src={original}
                alt="Original submitted image"
                className="h-full w-full object-contain"
              />
            )}
            {mode !== 'original' && (
              <BoxOverlay evidence={result.evidence} onHover={setActive} activeId={active} />
            )}
          </div>
          {mode !== 'original' && (
            <div className="relative aspect-[4/3] overflow-hidden rounded-lg bg-black">
              <img
                src={heatmap ?? original}
                alt="Analysis heatmap"
                className="h-full w-full object-contain"
                style={{ opacity }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
