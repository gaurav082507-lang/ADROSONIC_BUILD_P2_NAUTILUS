import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import DecisionDialog from '../src/features/decisions/DecisionDialog';
import { raw } from '../src/api/raw/endpoints';
vi.mock('../src/api/raw/endpoints', () => ({ raw: { decisionDraft: vi.fn(), decision: vi.fn() } }));
describe('decision dialog flow', () => {
  it('drafts, edits, previews and sends', async () => {
    vi.mocked(raw.decisionDraft).mockResolvedValue({
      claimant_message_en: 'Draft',
      claimant_message_hi: 'मसौदा',
      next_steps: [],
      slots_to_resubmit: [],
      source: 'provisional',
    } as any);
    vi.mocked(raw.decision).mockResolvedValue({ status: 'recorded' });
    render(<DecisionDialog id="R1" onClose={() => {}} />);
    fireEvent.change(screen.getByLabelText(/Action/), { target: { value: 'approve' } });
    fireEvent.change(screen.getByLabelText(/Reason category/), { target: { value: 'other' } });
    fireEvent.click(screen.getByText('Generate draft'));
    await waitFor(() => expect(screen.getByDisplayValue('Draft')).toBeInTheDocument());
    fireEvent.change(screen.getByDisplayValue('Draft'), { target: { value: 'Edited' } });
    fireEvent.click(screen.getByText('Send'));
    await waitFor(() =>
      expect(raw.decision).toHaveBeenCalledWith(
        'R1',
        expect.objectContaining({ messageEn: 'Edited' }),
      ),
    );
    expect(screen.getByText('Decision sent')).toBeInTheDocument();
  });
});
