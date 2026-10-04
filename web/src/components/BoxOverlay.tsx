import { useEffect, useRef, useState } from 'react';
import type { EvidenceVM } from '../types/vm';

type Props = {
  evidence: EvidenceVM[];
  width?: number;
  height?: number;
  onHover?: (id?: string) => void;
  activeId?: string;
};

export function bboxToPixels(bbox: NonNullable<EvidenceVM['bbox']>, width: number, height: number) {
  return {
    left: bbox.x * width,
    top: bbox.y * height,
    width: bbox.w * width,
    height: bbox.h * height,
  };
}

export default function BoxOverlay({
  evidence,
  width: initialWidth = 640,
  height: initialHeight = 480,
  onHover,
  activeId,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: initialWidth, height: initialHeight });

  useEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect) setSize({ width: rect.width, height: rect.height });
    });
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  const boxes = evidence.filter((item) => item.bbox && item.kind !== 'info');
  return (
    <div ref={ref} className="absolute inset-0" aria-label="Evidence markers">
      {boxes.map((item, index) => {
        const b = bboxToPixels(item.bbox!, size.width, size.height);
        return (
          <button
            type="button"
            key={item.id}
            className={`absolute border-2 border-yellow-300 bg-nile/10 ${activeId === item.id ? 'ring-4 ring-yellow-200' : ''}`}
            style={{ left: b.left, top: b.top, width: b.width, height: b.height }}
            onMouseEnter={() => onHover?.(item.id)}
            onFocus={() => onHover?.(item.id)}
            onMouseLeave={() => onHover?.(undefined)}
            aria-label={`Evidence ${index + 1}: ${item.title}`}
          >
            <span className="absolute -left-3 -top-3 grid h-6 w-6 place-items-center rounded-full bg-nile text-xs font-bold text-text">
              {index + 1}
            </span>
          </button>
        );
      })}
    </div>
  );
}
