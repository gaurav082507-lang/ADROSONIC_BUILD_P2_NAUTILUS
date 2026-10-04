import { useEffect, useRef, useState } from 'react';
import { raw } from '../../api/raw/endpoints';
import {
  cameraProblemKey,
  cameraSupport,
  mapCameraError,
  type CameraProblem,
} from '../../lib/cameraErrors';
import { loadFaceLandmarker } from '../../lib/mediapipeAssets';
import IdCardInput from './IdCardInput';

type Props = {
  onComplete: (url: string, sessionId?: string) => void;
  onId: (file: File) => void;
  t: any;
};
const FRAMES_PER_CHALLENGE = 4;
const BURST_GAP_MS = 250;

export default function VerifyStep({ onComplete, onId, t }: Props) {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const [session, setSession] = useState<any>();
  const [challengeIndex, setChallengeIndex] = useState(0);
  const [frames, setFrames] = useState<any[]>([]);
  const [problem, setProblem] = useState<CameraProblem | null>(null);
  const blocked = problem !== null;
  const [sessionError, setSessionError] = useState(false);
  const [verifyFailed, setVerifyFailed] = useState(false);
  const [verified, setVerified] = useState(false);
  const [guidance, setGuidance] = useState<'loading' | 'ready' | 'manual'>('loading');
  const [busy, setBusy] = useState(false);
  const landmarker = useRef<any>();
  const lastAutoCapture = useRef(0);

  // 1) Camera starts FIRST and independently – it never waits for the guidance model or session.
  useEffect(() => {
    let mounted = true;
    const unsupported = cameraSupport();
    if (unsupported) {
      setProblem(unsupported);
      return;
    }
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'user' }, audio: false })
      .then(async (media) => {
        if (!mounted) {
          media.getTracks().forEach((track) => track.stop());
          return;
        }
        stream.current = media;
        if (video.current) {
          video.current.srcObject = media;
          await video.current.play().catch(() => undefined);
        }
      })
      .catch((error) => mounted && setProblem(mapCameraError(error)));
    return () => {
      mounted = false;
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  // 2) Liveness session (server-issued random challenges), with a visible retry on failure.
  const startSession = () => {
    setSessionError(false);
    raw
      .livenessSession()
      .then((current) => {
        setSession(current);
        setChallengeIndex(0);
        setFrames([]);
        setVerified(false);
      })
      .catch(() => setSessionError(true));
  };
  useEffect(() => {
    startSession();
  }, []);

  // 3) Optional on-screen guidance (local model first, CDN fallback). Failure = manual capture.
  useEffect(() => {
    let mounted = true;
    loadFaceLandmarker()
      .then((model) => {
        if (!mounted) return;
        landmarker.current = model;
        setGuidance('ready');
      })
      .catch(() => mounted && setGuidance('manual'));
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!session || blocked || guidance !== 'ready' || !video.current || !landmarker.current)
      return;
    let raf = 0;
    const tick = () => {
      const current = video.current;
      if (current && current.readyState >= 2) {
        try {
          const result = landmarker.current.detectForVideo(current, performance.now());
          const challenge = String(session.challenges?.[challengeIndex] ?? '');
          let passed = false;
          if (challenge.includes('blink')) {
            const shapes = result.faceBlendshapes?.[0]?.categories ?? [];
            const left = shapes.find((x: any) => x.categoryName === 'eyeBlinkLeft')?.score ?? 0;
            const right = shapes.find((x: any) => x.categoryName === 'eyeBlinkRight')?.score ?? 0;
            passed = left > 0.45 || right > 0.45;
          } else if (challenge.includes('turn')) {
            const points = result.faceLandmarks?.[0] ?? [];
            const nose = points[1];
            const left = points[234];
            const right = points[454];
            if (nose && left && right) {
              const center = (left.x + right.x) / 2;
              passed = Math.abs(nose.x - center) > 0.055;
            }
          }
          if (passed && Date.now() - lastAutoCapture.current > 1200) {
            lastAutoCapture.current = Date.now();
            void capture();
          }
        } catch {
          /* guidance remains optional; server verification is authoritative */
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [session, challengeIndex, blocked, guidance]);
  const capture = async () => {
    if (!session || !video.current) return;
    // The backend verifies motion across frames and requires 8–40 frames in total, so each
    // challenge is captured as a short burst (FRAMES_PER_CHALLENGE frames, BURST_GAP_MS apart).
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext('2d');
    const burst: { frame: Blob; timestamp: number; challenge: string }[] = [];
    for (let k = 0; k < FRAMES_PER_CHALLENGE; k++) {
      ctx?.drawImage(video.current, 0, 0, 640, 480);
      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, 'image/jpeg', 0.86),
      );
      if (blob)
        burst.push({
          frame: blob,
          timestamp: Date.now(),
          challenge: String(session.challenges[challengeIndex]),
        });
      if (k < FRAMES_PER_CHALLENGE - 1) await new Promise((r) => setTimeout(r, BURST_GAP_MS));
    }
    if (!burst.length) return;
    const next = [...frames, ...burst];
    setFrames(next);
    if (challengeIndex + 1 < session.challenges.length) {
      setChallengeIndex((x) => x + 1);
      return;
    }
    setBusy(true);
    try {
      const result = await raw.livenessVerify({
        sessionId: session.session_id,
        nonce: session.nonce,
        frames: next,
      });
      if (result.passed === false) {
        setVerifyFailed(true);
        startSession();
        return;
      }
      setVerified(true);
      onComplete(result.best_frame ?? '', session.session_id);
    } catch {
      // network/server error or failed check: start a fresh session instead of abandoning the camera
      setVerifyFailed(true);
      startSession();
    } finally {
      setBusy(false);
    }
  };
  return (
    <div>
      <h2 className="font-display text-xl font-semibold">{t.verify}</h2>
      {blocked ? (
        <div className="mt-5 rounded-xl bg-slate-50 p-5">
          <p className="text-sm font-medium">{t[cameraProblemKey[problem ?? 'unknown']]}</p>
          <p className="mt-1 text-xs text-muted">{t.cameraFallback}</p>
          <label className="mt-4 block rounded-lg border p-4 text-sm">
            {t.selfie}
            <input
              className="mt-2 block"
              type="file"
              accept="image/*"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onComplete(URL.createObjectURL(file));
              }}
            />
          </label>
          <IdCardInput onId={onId} t={t} />
        </div>
      ) : (
        <>
          <div className="relative mt-5 overflow-hidden rounded-2xl bg-ink p-3">
            <video
              ref={video}
              muted
              playsInline
              className="aspect-[4/3] w-full rounded-xl object-cover"
            />
            <div className="pointer-events-none absolute inset-0 grid place-items-center">
              <div className="h-64 w-44 rounded-[50%] border-2 border-yellow-300" />
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm">
              {String(session?.challenges?.[challengeIndex] ?? t.preparing).replace(/_/g, ' ')}
            </span>
            {session?.spoken_code && (
              <span className="rounded-full bg-yellow-100 px-3 py-1 text-sm">
                {t.readCode}: <b className="mono">{session.spoken_code}</b>
              </span>
            )}
            <button
              disabled={busy || !session}
              onClick={capture}
              aria-label={t.capture}
              className="rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-white"
            >
              {busy ? t.preparing : t.capture}
            </button>
          </div>
          <div className="mt-2 text-xs text-muted" role="status">
            {verified ? (
              <span className="font-semibold text-green-700">{t.livenessDone}</span>
            ) : verifyFailed ? (
              <span className="text-amber-800">{t.livenessRetry}</span>
            ) : sessionError ? (
              <span>
                {t.sessionError}{' '}
                <button className="underline" onClick={startSession}>
                  {t.retry}
                </button>
              </span>
            ) : guidance === 'ready' ? (
              t.guidanceAuto
            ) : guidance === 'manual' ? (
              t.guidanceManual
            ) : (
              t.guidanceLoading
            )}
          </div>
          <IdCardInput onId={onId} t={t} />
        </>
      )}
    </div>
  );
}
