import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Guard } from '../src/App';
import * as session from '../src/api/session';
vi.mock('../src/api/session');
describe('route guards', () => {
  it('redirects unauthenticated users', () => {
    vi.mocked(session.getToken).mockReturnValue(null);
    vi.mocked(session.getRole).mockReturnValue(null);
    render(
      <MemoryRouter initialEntries={['/app']}>
        <Guard role="investigator">
          <div>Private</div>
        </Guard>
      </MemoryRouter>,
    );
    expect(screen.queryByText('Private')).not.toBeInTheDocument();
  });
  it('allows the matching role', () => {
    vi.mocked(session.getToken).mockReturnValue('token');
    vi.mocked(session.getRole).mockReturnValue('investigator');
    render(
      <MemoryRouter>
        <Guard role="investigator">
          <div>Private</div>
        </Guard>
      </MemoryRouter>,
    );
    expect(screen.getByText('Private')).toBeInTheDocument();
  });
});
