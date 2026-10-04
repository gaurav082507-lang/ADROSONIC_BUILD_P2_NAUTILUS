import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { cameraProblemKey, mapCameraError } from '../src/lib/cameraErrors';
import { classifyQrText } from '../src/lib/qrCheck';
import IdCardInput from '../src/features/claims/IdCardInput';
import en from '../src/i18n/en.json';
import hi from '../src/i18n/hi.json';

describe('camera problems map to specific, fixable messages', () => {
  it('maps browser error names', () => {
    expect(mapCameraError({ name: 'NotAllowedError' })).toBe('denied');
    expect(mapCameraError({ name: 'NotFoundError' })).toBe('notFound');
    expect(mapCameraError({ name: 'NotReadableError' })).toBe('inUse');
    expect(mapCameraError(new Error('x'))).toBe('unknown');
  });
  it('every problem has an EN and HI message', () => {
    for (const k of Object.values(cameraProblemKey)) {
      expect((en as Record<string, string>)[k]).toBeTruthy();
      expect((hi as Record<string, string>)[k]).toBeTruthy();
    }
  });
});

describe('QR pre-check', () => {
  it('recognises Aadhaar Secure QR (long number) vs other QR text', () => {
    expect(classifyQrText('1'.repeat(1200))).toBe('secureQr');
    expect(classifyQrText('<?xml version="1.0"?><PrintLetterBarcodeData uid="xxxx"/>')).toBe('qr');
  });
  it('shows checking, then the found message, and passes the file up', async () => {
    const onId = vi.fn();
    let resolve!: (v: 'secureQr') => void;
    const check = vi.fn(() => new Promise<'secureQr'>((r) => (resolve = r)));
    render(<IdCardInput onId={onId} t={en as Record<string, string>} check={check} />);
    const file = new File(['x'], 'card.png', { type: 'image/png' });
    fireEvent.change(screen.getByLabelText(en.idUpload), { target: { files: [file] } });
    expect(await screen.findByText(en.qrChecking)).toBeInTheDocument();
    resolve('secureQr');
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Aadhaar Secure QR found'),
    );
    expect(onId).toHaveBeenCalledWith(file);
  });
  it('asks for a retake when no QR is readable', async () => {
    render(
      <IdCardInput
        onId={() => {}}
        t={en as Record<string, string>}
        check={async () => 'notFound'}
      />,
    );
    fireEvent.change(screen.getByLabelText(en.idUseCamera), {
      target: { files: [new File(['x'], 'c.jpg', { type: 'image/jpeg' })] },
    });
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent("couldn't read a QR"));
  });
});
