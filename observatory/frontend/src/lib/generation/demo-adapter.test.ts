import { describe, expect, it, vi } from 'vitest';
import { DEMO_REQUEST } from './contract';
import { DemoGenerationAdapter } from './demo-adapter';

describe('DemoGenerationAdapter', () => {
  it('runs a local ready lifecycle without fetch or EventSource', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const EventSourceStub = vi.fn();
    vi.stubGlobal('EventSource', EventSourceStub);

    const adapter = new DemoGenerationAdapter({ intervalMs: 0, idFactory: () => 'fixed' });
    const created = adapter.create(DEMO_REQUEST, 'ready');
    expect(created.request_id).toBe('holus-demo-fixed');
    expect(created.source).toBe('demo');

    const frames: string[] = [];
    adapter.subscribe(created.request_id, (status) => {
      frames.push(status.status);
      expect(status.preview).not.toHaveProperty('url');
    });

    expect(frames).toEqual(['queued', 'generating', 'ready']);
    expect(adapter.get(created.request_id)?.preview.availability).toBe('local_placeholder');
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(EventSourceStub).not.toHaveBeenCalled();
    adapter.dispose();
  });

  it('exposes a bounded error state without implying a live job', () => {
    const adapter = new DemoGenerationAdapter({ intervalMs: 0, idFactory: () => 'err' });
    const created = adapter.create(DEMO_REQUEST, 'error');
    const messages: string[] = [];
    adapter.subscribe(created.request_id, (status) => {
      if (status.user_message) messages.push(status.user_message);
    });
    expect(adapter.get(created.request_id)?.status).toBe('error');
    expect(messages.at(-1)).toMatch(/No live job was created/);
    adapter.dispose();
  });
});
