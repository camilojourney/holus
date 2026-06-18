'use client';

import { useEffect, useRef, useState } from 'react';
import type { TrajectoryEvent } from './types';
import { trajectoryStreamUrl, isDemoMode } from './api';
import { demoTrajectoryEvents } from './demo-data';

const MAX_EVENTS = 100;
const MAX_RETRY_INTERVAL_MS = 30_000;

export function useTrajectoryStream(): {
  events: TrajectoryEvent[];
  connected: boolean;
} {
  const demoMode = isDemoMode();
  const [events, setEvents] = useState<TrajectoryEvent[]>(
    () => (demoMode ? demoTrajectoryEvents : []),
  );
  const [connected, setConnected] = useState(demoMode);
  const retryDelay = useRef(1_000);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // In demo mode, return static trajectory events without opening an EventSource
    if (demoMode) return;

    let cancelled = false;

    function connect() {
      if (cancelled) return;

      const url = trajectoryStreamUrl();
      console.log('[SSE] Connecting to', url);

      const source = new EventSource(url);
      sourceRef.current = source;

      source.onopen = () => {
        if (cancelled) { source.close(); return; }
        console.log('[SSE] Connected');
        setConnected(true);
        retryDelay.current = 1_000; // reset backoff on success
      };

      source.onmessage = (ev) => {
        if (cancelled) return;
        try {
          const event = JSON.parse(ev.data) as TrajectoryEvent;
          setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));
        } catch {
          console.warn('[SSE] Failed to parse event', ev.data);
        }
      };

      source.onerror = () => {
        if (cancelled) return;
        console.warn('[SSE] Connection error, retrying in', retryDelay.current, 'ms');
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
  }, [demoMode]);

  return { events, connected };
}
