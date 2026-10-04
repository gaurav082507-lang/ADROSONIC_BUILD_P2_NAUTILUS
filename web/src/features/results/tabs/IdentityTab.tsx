import type { ResultVM } from '../../../types/vm';

export default function IdentityTab({ result }: { result: ResultVM }) {
  const id = result.identityDetails;
  if (!id && !result.identity)
    return <div className="card p-8 text-sm text-muted">Not analysed</div>;
  const qr = id?.aadhaarQr;
  const face = result.artifacts.identityFaceComparison;
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="card p-5">
          <h3 className="font-display font-semibold">Face match</h3>
          {face?.idFace && (
            <img
              src={face.idFace}
              alt="ID photo and selfie side by side"
              className="mt-4 max-h-56 w-full rounded-lg border object-contain"
            />
          )}
          <div className="mt-4 grid grid-cols-2 gap-3">
            {[
              [
                'Similarity',
                id?.similarity != null ? `${Math.round(id.similarity * 100)}%` : 'Not analysed',
              ],
              ['Verdict', id?.verdict ?? 'Not analysed'],
              ['AI-generated selfie check', id?.aiGeneratedSelfie ?? 'Not analysed'],
              ['Match threshold', 'cosine ≥ 0.363 (SFace)'],
            ].map(([a, b]) => (
              <div key={a} className="rounded-lg bg-bg p-4">
                <div className="text-xs text-muted">{a}</div>
                <div className="mt-1 font-semibold">{b}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="card p-5">
          <h3 className="font-display font-semibold">Liveness checklist</h3>
          <div className="mt-2 text-sm">
            {id?.livenessPerformed === false
              ? 'Not attempted'
              : id?.livenessPassed === undefined
                ? ''
                : id.livenessPassed
                  ? 'Passed – verified on the server'
                  : 'Failed'}
          </div>
          <div className="mt-4 space-y-2">
            {id?.challenges?.map((x) => (
              <div key={x.name} className="flex justify-between rounded-lg border p-3 text-sm">
                <span className="capitalize">{x.name.replace(/_/g, ' ')}</span>
                <span
                  className={`font-semibold ${x.status === 'passed' ? 'text-green-700' : 'text-red-700'}`}
                >
                  {x.status}
                </span>
              </div>
            ))}
            {!id?.challenges?.length && (
              <div className="text-sm text-muted">No liveness challenges recorded.</div>
            )}
          </div>
        </div>
      </div>
      {qr && (
        <div className="card p-5">
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="font-display font-semibold">Aadhaar Secure QR</h3>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-semibold ${qr.signatureStatus === 'valid' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}
            >
              Signature {qr.signatureStatus}
            </span>
            {qr.testKey && (
              <span className="rounded-full border border-dashed border-slate-400 px-2 py-0.5 text-xs">
                Verified with TEST key (demo)
              </span>
            )}
            {qr.photoSimilarity !== undefined && (
              <span className="text-xs text-muted">
                QR photo vs selfie: {Math.round(qr.photoSimilarity * 100)}%
              </span>
            )}
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b text-xs uppercase text-muted">
                <tr>
                  <th className="py-2">Field</th>
                  <th>Printed on card (OCR)</th>
                  <th>Signed in QR</th>
                  <th>Match</th>
                </tr>
              </thead>
              <tbody>
                {(qr.rows ?? []).map((r) => (
                  <tr key={r.field} className={`border-b ${r.match ? '' : 'bg-red-50'}`}>
                    <td className="py-2 capitalize">{r.field}</td>
                    <td>{r.printed || '—'}</td>
                    <td>{r.signed || '—'}</td>
                    <td className={`font-semibold ${r.match ? 'text-green-700' : 'text-red-700'}`}>
                      {r.match ? 'Yes' : 'No'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!qr.rows?.length && <div className="mt-3 text-sm text-muted">No fields compared.</div>}
          </div>
        </div>
      )}
    </div>
  );
}
