/**
 * Loads the MediaPipe face landmarker used ONLY for live on-screen guidance (the server does the
 * real liveness verification). Local copies in /public/mediapipe are tried first so the demo
 * works offline; the public CDN is the fallback. Failure is non-fatal: the user can still
 * capture each challenge manually.
 */
const LOCAL_WASM = '/mediapipe/wasm';
const LOCAL_MODEL = '/mediapipe/face_landmarker.task';
const CDN_WASM = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/wasm';
const CDN_MODEL =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';

async function exists(url: string) {
  try {
    const r = await fetch(url, { method: 'HEAD' });
    return r.ok && !(r.headers.get('content-type') ?? '').includes('text/html');
  } catch {
    return false;
  }
}

export async function loadFaceLandmarker(timeoutMs = 15000): Promise<any> {
  const work = (async () => {
    const vision = await import('@mediapipe/tasks-vision');
    const wasm = (await exists(`${LOCAL_WASM}/vision_wasm_internal.wasm`)) ? LOCAL_WASM : CDN_WASM;
    const model = (await exists(LOCAL_MODEL)) ? LOCAL_MODEL : CDN_MODEL;
    const fileset = await vision.FilesetResolver.forVisionTasks(wasm);
    return vision.FaceLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: model },
      runningMode: 'VIDEO',
      numFaces: 1,
      outputFaceBlendshapes: true,
    });
  })();
  const timeout = new Promise<never>((_, reject) =>
    setTimeout(() => reject(new Error('guidance model timeout')), timeoutMs),
  );
  return Promise.race([work, timeout]);
}
