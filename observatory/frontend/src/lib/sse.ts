'use client';

import { useEffect, useRef, useState } from 'react';
import type { TrajectoryEvent } from './types';
import { allowsLiveEventStream, trajectoryStreamUrl } from './connection';

const MAX_EVENTS = 100;
const MAX_RETRY_INTERVAL_MS = 30_000;

export function useTrajectoryStream(): {
  events: TrajectoryEvent[];
  connected: boolean;
  liveEventsAllowed: boolean;
} {
  const liveEventsAllowed = allowsLiveEventStream();
  const [events, setEvents] = useState<TrajectoryEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const retryDelay = useRef(1_000);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Public/demo surfaces must not open EventSource, including localhost targets.
    if (!liveEventsAllowed) return;

    const url = trajectoryStreamUrl();
    if (!url) return;
    if (typeof window !== 'undefined' && /localhost|127\.0\.0\.1|\[::1\]/i.test(url)) {
      const host = window.location.hostname;
      if (host !== 'localhost' && host !== '127.0.0.1' && host !== '::1') return;
    }

    let cancelled = false;

    function connect() {
      if (cancelled) return;
      const streamUrl = trajectoryStreamUrl();
      if (!streamUrl) return;

      const source = new EventSource(streamUrl);
      sourceRef.current = source;

      source.onopen = () => {
        if (cancelled) { source.close(); return; }
        setConnected(true);
        retryDelay.current = 1_000;
      };

      source.onmessage = (ev) => {
        if (cancelled) return;
        try {
          const event = JSON.parse(ev.data) as TrajectoryEvent;
          setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));
        } catch {
          // Ignore malformed frames rather than retrying against a bad payload.
        }
      };

      source.onerror = () => {
        if (cancelled) return;
        setConnected(false);
        source.close();
        sourceRef.current = null;

        timerRef.current = setTimeout(() => {
          retryDelay.current = Math.min(retryDelay.current * 2, MAX_RETRY_INTERVAL_MS);
          connect();
        }, retryDelay.current);
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      if (sourceRef.current) {
        sourceRef.current.close();
        sourceRef.current = null;
      }
    };
  }, [liveEventsAllowed]);

  return { events, connected, liveEventsAllowed };
}
