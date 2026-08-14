import { renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useTrajectoryStream } from './sse';

vi.mock('./connection', () => ({
  allowsLiveEventStream: () => false,
  trajectoryStreamUrl: () => null,
}));

describe('useTrajectoryStream', () => {
  it('does not construct EventSource in public/demo mode', () => {
    const EventSourceStub = vi.fn();
    vi.stubGlobal('EventSource', EventSourceStub);
    const { result } = renderHook(() => useTrajectoryStream());
    expect(result.current.liveEventsAllowed).toBe(false);
    expect(result.current.connected).toBe(false);
    expect(EventSourceStub).not.toHaveBeenCalled();
  });
});
