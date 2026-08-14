import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import KillSwitchBanner from './KillSwitchBanner';

describe('KillSwitchBanner', () => {
  it('shows an unavailable state when the backend did not provide kill-switch state', () => {
    render(
      <KillSwitchBanner
        health={{
          status: 'down',
          services: [],
          timestamp: '2026-01-01T00:00:00.000Z',
        }}
      />,
    );

    expect(screen.getByRole('status').textContent).toMatch(/Kill switch state unavailable/i);
    expect(screen.queryByText(/System running normally/i)).toBeNull();
  });
});
