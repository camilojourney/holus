import type { ServiceStatus } from '@/lib/types';

interface Props {
  services: ServiceStatus[];
}

const statusStyles = {
  up: { bg: 'var(--success-subtle)', text: 'var(--success)', dot: 'var(--success)' },
  down: { bg: 'var(--danger-subtle)', text: 'var(--danger)', dot: 'var(--danger)' },
  degraded: { bg: 'var(--warning-subtle)', text: 'var(--warning)', dot: 'var(--warning)' },
};

export default function SystemHealthGrid({ services }: Props) {
  if (services.length === 0) {
    return (
      <p className="text-sm text-center py-8" style={{ color: 'var(--text-tertiary)' }}>
        No service probes returned -- check API connectivity
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {services.map((svc) => {
        const style = statusStyles[svc.status];
        return (
          <div key={svc.name} className="card animate-fade-in">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>
                {svc.name}
              </h3>
              <span
                className="flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full font-medium"
                style={{ background: style.bg, color: style.text }}
              >
                <span
                  className={`status-dot ${svc.status === 'up' ? 'status-dot-active' : ''}`}
                  style={{ background: style.dot }}
                />
                {svc.status}
              </span>
            </div>
            {svc.latency_ms !== undefined && (
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }} title="Round-trip latency to service endpoint">
                RTT: {svc.latency_ms}ms
              </p>
            )}
            <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
              {svc.status === 'down' && svc.latency_ms === undefined
                ? 'Connection required — not production telemetry'
                : `Last probe: ${new Date(svc.last_checked).toLocaleTimeString()}`}
            </p>
          </div>
        );
      })}
    </div>
  );
}
