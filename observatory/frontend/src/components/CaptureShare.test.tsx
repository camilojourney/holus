import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import CaptureShare from '@/components/CaptureShare';

const { suggestCapture, previewCapture, confirmCapture } = vi.hoisted(() => ({
  suggestCapture: vi.fn(),
  previewCapture: vi.fn(),
  confirmCapture: vi.fn(),
}));

vi.mock('@/lib/api', () => ({ suggestCapture, previewCapture, confirmCapture }));
vi.mock('@/lib/connection', () => ({
  resolveConnection: () => ({
    kind: 'local_dev',
    label: 'Local development',
    liveEventsAllowed: true,
    generationTransport: 'local-demo',
    detail: 'Local development',
  }),
}));
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

describe('CaptureShare', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('rejects unsupported synthetic attachments before sending a request', () => {
    render(<CaptureShare />);
    const input = screen.getByLabelText('Choose file');
    fireEvent.change(input, {
      target: { files: [new File(['not an image'], 'notes.txt', { type: 'text/plain' })] },
    });

    expect(screen.getByRole('alert').textContent).toMatch(/unsupported attachment/i);
    expect(suggestCapture).not.toHaveBeenCalled();
  });

  it('shows loading and then route suggestions from a synthetic capture', async () => {
    let resolveRequest: (value: unknown) => void = () => undefined;
    suggestCapture.mockReturnValueOnce(new Promise((resolve) => { resolveRequest = resolve; }));
    render(<CaptureShare />);
    fireEvent.change(screen.getByPlaceholderText(/Paste a thought/i), {
      target: { value: 'A useful thought for the team' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Suggest destinations' }));
    expect(screen.getByRole('button', { name: 'Checking capture…' })).toBeTruthy();

    resolveRequest({
      suggestions: [{
        channel: 'linkedin_text', platform: 'linkedin', format_hint: 'text',
        edit_notes: 'Keep it direct', confidence: 0.9, preview_text: 'A draft',
      }],
      personal_delivery_granted: false,
      social_api_reachable: false,
      connected_platforms: [],
    });
    expect(await screen.findByText(/suggested routes/i)).toBeTruthy();
    expect(screen.getByText(/Social API not reachable/i)).toBeTruthy();
  });

  it('offers retry and reset when the backend is unavailable', async () => {
    suggestCapture.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    render(<CaptureShare />);
    fireEvent.change(screen.getByPlaceholderText(/Paste a thought/i), {
      target: { value: 'A useful thought for the team' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Suggest destinations' }));

    expect((await screen.findByRole('alert')).textContent).toMatch(/backend is unavailable/i);
    expect(screen.getByRole('button', { name: 'Try again' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Start over' }));
    expect(screen.getByPlaceholderText(/Paste a thought/i)).toHaveProperty('value', '');
  });
});
