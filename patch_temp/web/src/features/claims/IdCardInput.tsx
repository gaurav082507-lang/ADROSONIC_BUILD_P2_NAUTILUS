import { useState } from 'react';
import { checkIdQr, type QrStatus } from '../../lib/qrCheck';

const tone: Record<QrStatus, string> = {
  checking: 'bg-slate-100 text-slate-700',
  secureQr: 'bg-green-50 text-green-800',
  qr: 'bg-green-50 text-green-800',
  notFound: 'bg-amber-50 text-amber-900',
  error: 'bg-slate-100 text-slate-700',
};
const key: Record<QrStatus, string> = {
  checking: 'qrChecking',
  secureQr: 'qrSecureFound',
  qr: 'qrFound',
  notFound: 'qrNotFound',
  error: 'qrError',
};

/** ID card capture/upload with an instant, claimant-safe QR readability check. */
export default function IdCardInput({
  onId,
  t,
  check = checkIdQr,
}: {
  onId: (file: File) => void;
  t: Record<string, string>;
  check?: (file: Blob) => Promise<QrStatus>;
}) {
  const [status, setStatus] = useState<QrStatus>();
  const [preview, setPreview] = useState<string>();
  const handle = async (file?: File) => {
    if (!file) return;
    onId(file);
    setPreview(URL.createObjectURL(file));
    setStatus('checking');
    setStatus(await check(file));
  };
  return (
    <div className="mt-5 rounded-lg border p-4 text-sm">
      <div className="font-medium">{t.idCard}</div>
      <p className="mt-1 text-xs text-muted">{t.idCardHint}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <label className="cursor-pointer rounded-lg bg-ink px-3 py-2 text-xs font-semibold text-white">
          {t.idUseCamera}
          <input
            className="sr-only"
            type="file"
            accept="image/*"
            capture="environment"
            aria-label={t.idUseCamera}
            onChange={(e) => void handle(e.target.files?.[0])}
          />
        </label>
        <label className="cursor-pointer rounded-lg border px-3 py-2 text-xs font-semibold">
          {t.idUpload}
          <input
            className="sr-only"
            type="file"
            accept="image/*"
            aria-label={t.idUpload}
            onChange={(e) => void handle(e.target.files?.[0])}
          />
        </label>
      </div>
      {preview && (
        <img
          src={preview}
          alt={t.idCard}
          className="mt-3 max-h-40 rounded-lg border object-contain"
        />
      )}
      {status && (
        <div role="status" className={`mt-3 rounded-lg p-3 text-xs ${tone[status]}`}>
          {t[key[status]]}
        </div>
      )}
    </div>
  );
}
