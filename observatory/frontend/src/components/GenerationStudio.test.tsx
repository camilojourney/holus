import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import GenerationStudio from '@/components/GenerationStudio';

vi.mock('@/lib/connection', () => ({
  resolveConnection: () => ({
    kind: 'demo',
    label: 'Demo data',
    liveEventsAllowed: false,
    generationTransport: 'local-demo',
    detail: 'Live events require an authenticated backend connection.',
  }),
}));

describe('GenerationStudio', () => {
  afterEach(() => {
    cleanup();
  });

  it('labels the local demo and never calls fetch', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    render(<GenerationStudio variant="page" />);
    expect(screen.getByText(/Demo data/)).toBeTruthy();
    expect(screen.getByText(/No live job is created/i)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Run demonstration' }));
    expect(await screen.findByText(/holus-demo-/)).toBeTruthy();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
