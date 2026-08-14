'use client';

import { useTrajectoryStream } from '@/lib/sse';
import { Radio } from 'lucide-react';

export default function TrajectoryTimeline() {
  const { events, connected, liveEventsAllowed } = useTrajectoryStream();

  const statusLabel = !liveEventsAllowed
    ? 'Connection required'
    : connected
      ? 'Live'
      : 'Disconnected';
  const statusColor = connected && liveEventsAllowed ? 'var(--success)' : 'var(--warning)';

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'var(--surface-raised)',
        border: '1px solid var(--border-default)',
      }}
    >
      <div
        className="flex items-center justify-between px-5 py-4"
        style={{ borderBottom: '1px solid var(--border-subtle)' }}
      >
        <h2 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
          Agent event stream
        </h2>
        <span
          className="flex items-center gap-1.5 text-xs font-medium"
          style={{ color: statusColor }}
        >
          <Radio
            size={14}
            aria-hidden="true"
          />
          {statusLabel}
        </span>
      </div>
      <div className="max-h-80 overflow-y-auto">
        {!liveEventsAllowed ? (
          <p
            className="text-sm px-5 py-8 text-center leading-6"
            style={{ color: 'var(--text-secondary)' }}
          >
            Live events require an authenticated backend connection. This public demo does not
            open a localhost event stream or display production telemetry.
          </p>
        ) : events.length === 0 ? (
          <p
            className="text-sm px-5 py-8 text-center"
            style={{ color: 'var(--text-tertiary)' }}
          >
            {connected ? 'Awaiting agent activity...' : 'Disconnected from the Observatory event stream.'}
          </p>
        ) : (
          events.map((ev) => (
            <div
              key={ev.id}
              className="px-5 py-3 flex items-start gap-3 transition-colors"
              style={{ borderBottom: '1px solid var(--border-subtle)' }}
            >
              <div className="shrink-0 mt-0.5">
                <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
                  {new Date(ev.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="min-w-0">
                <span
                  className="text-xs font-semibold mr-2"
                  style={{ color: 'var(--brand)' }}
                >
                  {ev.agent_name}
                </span>
                <span
                  className="text-xs px-1.5 py-0.5 rounded mr-2"
                  style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}
                >
                  {ev.event_type}
                </span>
                <span className="text-xs" style={{ color: 'var(--text-primary)' }}>
                  {ev.description}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
