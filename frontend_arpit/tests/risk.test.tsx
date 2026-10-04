import { render, screen } from '@testing-library/react';
import { RiskBadge } from '../src/components/RiskBadge';
import { describe, it, expect } from 'vitest';
describe('RiskBadge', () => {
  it('shows the band word and icon', () => {
    render(<RiskBadge band="HIGH" />);
    expect(screen.getByText('HIGH')).toBeInTheDocument();
  });
});
