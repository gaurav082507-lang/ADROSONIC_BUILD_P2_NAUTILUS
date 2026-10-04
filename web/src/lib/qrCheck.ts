/**
 * Claimant-side pre-check of the QR code on an ID card photo. It only tells the claimant
 * whether a QR code is readable so they can retake a blurry photo. The cryptographic
 * Aadhaar Secure QR verification happens on the server during analysis and is shown only to
 * the investigator.
 */
export type QrStatus = 'checking' | 'secureQr' | 'qr' | 'notFound' | 'error';

/** Aadhaar Secure QR = a very long decimal number; older Aadhaar QR = XML text. */
export function classifyQrText(text: string): Exclude<QrStatus, 'checking' | 'notFound' | 'error'> {
  const compact = text.replace(/\s/g, '');
  return /^\d{300,}$/.test(compact) ? 'secureQr' : 'qr';
}

let prepared = false;
export async function checkIdQr(file: Blob): Promise<QrStatus> {
  try {
    const zxing = await import('zxing-wasm/reader');
    if (!prepared) {
      // load the decoder WASM from our own server (copied to /public/zxing by scripts/copy-assets.mjs)
      zxing.prepareZXingModule({
        overrides: {
          locateFile: (path: string, prefix: string) =>
            path.endsWith('.wasm') ? `/zxing/${path}` : prefix + path,
        },
      });
      prepared = true;
    }
    const results = await zxing.readBarcodes(file, {
      formats: ['QRCode'],
      tryHarder: true,
      maxNumberOfSymbols: 1,
    });
    const hit = results.find((r) => r.isValid && r.text);
    return hit ? classifyQrText(hit.text) : 'notFound';
  } catch {
    return 'error';
  }
}
