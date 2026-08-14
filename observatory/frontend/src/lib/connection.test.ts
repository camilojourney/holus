import { describe, expect, it } from 'vitest';
import { allowsLiveEventStream, resolveConnection, trajectoryStreamUrl } from './connection';

describe('connection safety', () => {
  it('blocks live events on a public host', () => {
    const state = resolveConnection({
      hostname: 'holus.camilomartinez.co',
      demoMode: false,
      nodeEnv: 'production',
      observatoryUrl: 'http://localhost:8003',
      liveEvents: false,
    });
    expect(state.liveEventsAllowed).toBe(false);
    expect(state.label).toMatch(/Demo data|Connection required/);
    expect(
      trajectoryStreamUrl({
        hostname: 'holus.camilomartinez.co',
        demoMode: false,
        nodeEnv: 'production',
        observatoryUrl: 'http://localhost:8003',
      }),
    ).toBeNull();
    expect(
      allowsLiveEventStream({
        hostname: 'holus.camilomartinez.co',
        demoMode: false,
        nodeEnv: 'production',
      }),
    ).toBe(false);
  });

  it('blocks live events when demo mode is on, even on localhost', () => {
    expect(
      allowsLiveEventStream({
        hostname: 'localhost',
        demoMode: true,
        nodeEnv: 'development',
        observatoryUrl: 'http://localhost:8003',
      }),
    ).toBe(false);
    expect(
      trajectoryStreamUrl({
        hostname: 'localhost',
        demoMode: true,
        nodeEnv: 'development',
        observatoryUrl: 'http://localhost:8003',
      }),
    ).toBeNull();
  });

  it('allows local development streams only on a local host', () => {
    const state = resolveConnection({
      hostname: 'localhost',
      demoMode: false,
      nodeEnv: 'development',
      observatoryUrl: 'http://localhost:8003',
      liveEvents: true,
    });
    expect(state.kind).toBe('local_dev');
    expect(state.liveEventsAllowed).toBe(true);
  });

  it('does not emit a localhost stream URL for a public hostname', () => {
    const url = trajectoryStreamUrl({
      hostname: 'holus.camilomartinez.co',
      demoMode: false,
      nodeEnv: 'development',
      observatoryUrl: 'http://localhost:8001',
      liveEvents: true,
    });
    expect(url).toBeNull();
  });

  it('blocks live events when production still points at a localhost API', () => {
    const state = resolveConnection({
      hostname: 'localhost',
      demoMode: false,
      nodeEnv: 'production',
      observatoryUrl: 'http://localhost:8003',
      liveEvents: true,
    });
    expect(state.kind).toBe('demo');
    expect(state.liveEventsAllowed).toBe(false);
    expect(
      trajectoryStreamUrl({
        hostname: 'localhost',
        demoMode: false,
        nodeEnv: 'production',
        observatoryUrl: 'http://localhost:8003',
        liveEvents: true,
      }),
    ).toBeNull();
  });

  it('treats production SSR as a public demo even with a remote API URL', () => {
    const state = resolveConnection({
      hostname: '',
      demoMode: false,
      nodeEnv: 'production',
      observatoryUrl: 'https://observatory.internal.example',
      liveEvents: true,
    });
    expect(state.kind).toBe('demo');
    expect(state.liveEventsAllowed).toBe(false);
    expect(
      trajectoryStreamUrl({
        hostname: '',
        demoMode: false,
        nodeEnv: 'production',
        observatoryUrl: 'https://observatory.internal.example',
        liveEvents: true,
      }),
    ).toBeNull();
  });
});
