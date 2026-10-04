import { useEffect, useState } from 'react';
import { UploadCloud } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useJobPolling } from '../../api/hooks';
import { raw } from '../../api/raw/endpoints';
import { friendlyError } from '../../lib/errorMessages';
import { Loading } from '../../components/States';

type Mode = 'image' | 'document' | 'claim';
const sampleByMode: Record<Mode, string[]> = {
  image: ['/samples/ai_car.jpg', '/samples/genuine_car.jpg'],
  document: ['/samples/tampered_invoice.pdf', '/samples/clean_invoice.pdf'],
  claim: [
    '/samples/ai_car.jpg',
    '/samples/tampered_invoice.pdf',
    '/samples/id_card.png',
    '/samples/selfie.jpg',
  ],
};
async function fetchSample(path: string) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Sample unavailable: ${path}`);
  const blob = await response.blob();
  const name = path.split('/').pop()!;
  return new File([blob], name, { type: blob.type || guessMime(name) });
}
function guessMime(name: string) {
  if (name.endsWith('.pdf')) return 'application/pdf';
  if (name.endsWith('.png')) return 'image/png';
  if (name.endsWith('.jpg') || name.endsWith('.jpeg')) return 'image/jpeg';
  return 'application/octet-stream';
}
export default function AnalyzePage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('image');
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState('');
  const [error, setError] = useState('');
  const job = useJobPolling(jobId);
  useEffect(() => {
    if (job.data?.status === 'done' && job.data.resultId)
      navigate(`/app/results/${job.data.resultId}`);
    if (job.data?.status === 'failed') setError(job.data.error ?? 'Analysis failed.');
  }, [job.data, navigate]);
  const validate = (next: File[]) => {
    const max = 15 * 1024 * 1024;
    if (next.some((x) => x.size > max)) throw new Error('This file is over 15 MB.');
    if (mode === 'image' && next.length !== 1) throw new Error('Choose one image.');
    if (mode === 'document' && next.length !== 1) throw new Error('Choose one PDF or bill image.');
    if (mode === 'claim' && next.length > 6) throw new Error('Up to 6 photos per claim.');
  };
  const submit = async () => {
    try {
      validate(files);
      setError('');
      setBusy(true);
      const result =
        mode === 'claim'
          ? await raw.analyze('claim', {
              images: files.filter((x) => x.type.startsWith('image/')),
              document: files.find((x) => x.type === 'application/pdf'),
              metadata: { claim_type: 'motor' },
            })
          : await raw.analyze(mode, { file: files[0] });
      setJobId(result.job_id);
    } catch (e: any) {
      setError(friendlyError(e.code, e.message));
      setBusy(false);
    }
  };
  const trySample = async () => {
    try {
      setError('');
      setBusy(true);
      const fs = await Promise.all(sampleByMode[mode].map(fetchSample));
      setFiles(mode === 'claim' ? fs : fs.slice(0, 1));
      setBusy(false);
    } catch (e: any) {
      setError(e.message);
      setBusy(false);
    }
  };
  return (
    <div>
      <div className="text-sm text-muted">Analysis workspace</div>
      <h1 className="font-display mt-1 text-3xl font-bold">Examine a claim</h1>
      <p className="mt-2 text-sm text-muted">
        The backend remains the source of truth for every result.
      </p>
      <div className="mt-6 flex gap-1 rounded-lg border bg-white p-1 w-fit">
        {(['image', 'document', 'claim'] as Mode[]).map((x) => (
          <button
            key={x}
            onClick={() => {
              setMode(x);
              setFiles([]);
              setError('');
            }}
            className={`rounded-md px-4 py-2 text-sm ${mode === x ? 'bg-ink text-white' : 'text-muted'}`}
          >
            {x === 'claim' ? 'Full claim' : x[0].toUpperCase() + x.slice(1)}
          </button>
        ))}
      </div>
      {busy && (
        <div className="mt-5">
          <Loading
            label={job.data?.status === 'running' ? 'Analysis running…' : 'Submitting analysis…'}
          />
          {job.data?.steps?.length && (
            <div className="card mt-3 p-5 space-y-2">
              {job.data.steps.map((x) => (
                <div key={x.name} className="flex justify-between text-sm">
                  <span>{x.name}</span>
                  <span>
                    {x.status}
                    {x.durationMs ? ` · ${x.durationMs} ms` : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      <div className="card mt-5 p-6">
        <label className="flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-border bg-slate-50 p-8 text-center">
          <input
            type="file"
            className="sr-only"
            multiple={mode === 'claim'}
            accept={mode === 'document' ? 'application/pdf,image/*' : 'image/*'}
            onChange={(e) => {
              const fs = Array.from(e.target.files ?? []) as File[];
              try {
                validate(fs);
                setFiles(fs);
                setError('');
              } catch (err: any) {
                setError(err.message);
              }
            }}
          />
          <UploadCloud size={32} className="text-signal" />
          <div className="mt-4 font-semibold">
            {mode === 'claim' ? 'Upload claim evidence' : 'Upload file'}
          </div>
          <div className="mt-1 text-sm text-muted">JPG, PNG, WebP or PDF · max 15 MB</div>
        </label>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            onClick={trySample}
            disabled={busy}
            className="rounded-lg border px-4 py-2.5 text-sm"
          >
            Try a sample
          </button>
          <span className="text-sm text-muted">{files.length} file(s) selected</span>
        </div>
        {files.length > 0 && (
          <div className="mt-4 space-y-2">
            {files.map((f) => (
              <div key={`${f.name}-${f.size}`} className="rounded-lg bg-slate-50 p-3 text-sm">
                <b>{f.name}</b>
                <span className="ml-2 text-muted">{f.type}</span>
              </div>
            ))}
          </div>
        )}
        {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <button
          onClick={submit}
          disabled={busy || !files.length}
          className="mt-5 w-full rounded-lg bg-ink px-4 py-3 text-sm font-semibold text-white disabled:opacity-30"
        >
          Analyze
        </button>
      </div>
    </div>
  );
}
