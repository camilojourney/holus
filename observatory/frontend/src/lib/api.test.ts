import { describe, expect, it, vi } from 'vitest';

vi.mock('./connection', () => ({
  isPublicOrDemoSurface: () => true,
}));

describe('public-surface API safety', () => {
  it('returns a local content-detail fallback without fetch', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('fetch must not run on a public/demo surface');
    });
    const { fetchContentDetail } = await import('./api');
    const detail = await fetchContentDetail('c1');
    expect(detail.id).toBe('c1');
    expect(detail.text).toMatch(/Demonstration draft/i);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it('does not post live drafting mutations', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('fetch must not run on a public/demo surface');
    });
    const { createContentFromThought, patchContent, chooseVisual } = await import('./api');
    await expect(
      createContentFromThought({ thought: 'A recruiter-facing demo thought.' }),
    ).rejects.toThrow(/No request was sent/);
    await expect(patchContent('c1', { status: 'approved' })).rejects.toThrow(/No request was sent/);
    await expect(chooseVisual('c1', 'a')).rejects.toThrow(/No request was sent/);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it('does not invent cost telemetry', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('fetch must not run on a public/demo surface');
    });
    const { fetchCosts } = await import('./api');
    await expect(fetchCosts()).resolves.toEqual([]);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });
});
