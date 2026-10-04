import { useEffect, useRef, useState } from 'react';
import { raw } from '../../api/raw/endpoints';

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
  const [blocked, setBlocked] = useState(false);
  const [busy, setBusy] = useState(false);
  const landmarker = useRef<any>();
  const lastAutoCapture = useRef(0);
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const vision = await import('@mediapipe/tasks-vision');
        const fileset = await vision.FilesetResolver.forVisionTasks(
          'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/wasm',
        );
        landmarker.current = await vision.FaceLandmarker.createFromOptions(fileset, {
          baseOptions: {
            modelAssetPath:
              'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
          },
          runningMode: 'VIDEO',
          numFaces: 1,
          outputFaceBlendshapes: true,
        });
        const current = await raw.livenessSession();
        if (!mounted) return;
        setSession(current);
        stream.current = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user' },
          audio: false,
        });
        if (video.current) video.current.srcObject = stream.current;
        await video.current?.play();
      } catch {
        setBlocked(true);
      }
    })();
    return () => {
      mounted = false;
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (!session || blocked || !video.current || !landmarker.current) return;
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
  }, [session, challengeIndex, blocked]);
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
      onComplete(result.best_frame ?? '', session.session_id);
    } catch {
      setBlocked(true);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div>
      <h2 className="font-display text-xl font-semibold">{t.verify}</h2>
      {blocked ? (
        <div className="mt-5 rounded-xl bg-slate-50 p-5">
          <p className="text-sm text-muted">{t.cameraBlocked}</p>
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
          <label className="mt-3 block rounded-lg border p-4 text-sm">
            {t.idCard}
            <input
              className="mt-2 block"
              type="file"
              accept="image/*"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onId(file);
              }}
            />
          </label>
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
              className="rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-white"
            >
              {busy ? t.preparing : t.capture}
            </button>
          </div>
          <label className="mt-5 block rounded-lg border p-4 text-sm">
            {t.idCard}
            <input
              className="mt-2 block"
              type="file"
              accept="image/*"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onId(file);
              }}
            />
          </label>
        </>
      )}
    </div>
  );
}
