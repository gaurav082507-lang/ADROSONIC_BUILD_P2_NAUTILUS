import { useRef, useState } from 'react';
type Item = { file: File; slot: string; captureSource: 'camera' | 'upload' };
type Props = { claimType: string; onChange: (items: Item[]) => void; t: any };
const slots: Record<string, string[]> = {
  motor: ['vehicle_full', 'damage_closeup', 'number_plate', 'repair_estimate'],
  health: ['bill', 'discharge_summary', 'prescription'],
  property: ['wide_shot', 'closeup', 'invoice'],
};
export default function EvidenceStep({ claimType, onChange, t }: Props) {
  const [items, setItems] = useState<Item[]>([]);
  const [active, setActive] = useState<string>();
  const video = useRef<HTMLVideoElement>(null);
  const update = (item: Item) => {
    const next = [...items, item];
    setItems(next);
    onChange(next);
  };
  const upload = (slot: string, file?: File) =>
    file && update({ file, slot, captureSource: 'upload' });
  const camera = async (slot: string) => {
    setActive(slot);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      const current = video.current;
      if (!current) return;
      current.srcObject = stream;
      await current.play();
      window.setTimeout(() => {
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 480;
        canvas.getContext('2d')?.drawImage(current, 0, 0, 640, 480);
        canvas.toBlob(
          (blob) => {
            stream.getTracks().forEach((track) => track.stop());
            if (blob)
              update({
                file: new File([blob], `${slot}.jpg`, { type: 'image/jpeg' }),
                slot,
                captureSource: 'camera',
              });
            setActive(undefined);
          },
          'image/jpeg',
          0.88,
        );
      }, 1200);
    } catch {
      setActive(undefined);
    }
  };
  return (
    <div>
      <h2 className="font-display text-xl font-semibold">{t.evidence}</h2>
      <p className="mt-2 text-sm text-muted">{t.evidenceHint}</p>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {(slots[claimType] ?? slots.motor).map((slot) => (
          <div key={slot} className="rounded-xl border p-4">
            <div className="font-medium capitalize">{slot.replaceAll('_', ' ')}</div>
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => camera(slot)}
                className="rounded-lg bg-primary-dark px-3 py-2 text-xs font-semibold text-white"
              >
                {t.useCamera}
              </button>
              <label className="rounded-lg border px-3 py-2 text-xs font-semibold">
                {t.upload}
                <input
                  type="file"
                  className="sr-only"
                  accept="image/*,.pdf"
                  onChange={(event) => upload(slot, event.target.files?.[0])}
                />
              </label>
            </div>
            {active === slot && <div className="mt-2 text-xs text-muted">{t.capturing}</div>}
          </div>
        ))}
      </div>
      <video
        ref={video}
        muted
        playsInline
        className="pointer-events-none fixed -left-[9999px] h-1 w-1"
      />
      <div className="mt-4 text-sm text-muted">
        {items.length} {t.readyItems}
      </div>
    </div>
  );
}
