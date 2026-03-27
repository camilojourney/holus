import { fetchHealth } from '@/lib/api';
import KillSwitchBanner from '@/components/KillSwitchBanner';
import SystemHealthGrid from '@/components/SystemHealthGrid';
import ErrorBanner from '@/components/ErrorBanner';

export const revalidate = 0; // always fresh for health page

export default async function HealthPage() {
  let health = null;
  let error = false;

  try {
    health = await fetchHealth();
  } catch {
    error = true;
  }

  return (
    <div className="page-transition">
      {/* Kill switch banner — full width at top */}
      {health && <KillSwitchBanner health={health} />}

      <div style={{ padding: 'var(--page-padding)' }} className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>System Diagnostics</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Service probes, MCP silo connectivity, and kill switch state
          </p>
        </div>

        {error && <ErrorBanner message="Could not reach Observatory API to fetch health data" />}

        {health && (
          <>
            {/* Overall status */}
            <div
              className="rounded-xl px-5 py-4 flex items-center gap-4"
              style={{
                border: `1px solid ${
                  health.status === 'healthy' ? 'var(--health-ok-border)'
                    : health.status === 'degraded' ? 'var(--health-warn-border)'
                    : 'var(--health-err-border)'
                }`,
                background: health.status === 'healthy' ? 'var(--health-ok-bg)'
                  : health.status === 'degraded' ? 'var(--health-warn-bg)'
                  : 'var(--health-err-bg)',
              }}
            >
              <div
                className="w-3 h-3 rounded-full"
                style={{
                  background: health.status === 'healthy' ? 'var(--health-ok-dot)'
                    : health.status === 'degraded' ? 'var(--health-warn-dot)'
                    : 'var(--health-err-dot)',
                }}
              />
              <div>
                <p
                  className="font-semibold capitalize"
                  style={{
                    color: health.status === 'healthy' ? 'var(--health-ok-text)'
                      : health.status === 'degraded' ? 'var(--health-warn-text)'
                      : 'var(--health-err-text)',
                  }}
                >
                  System {health.status}
                </p>
                {health.timestamp && (
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
                    Last checked: {new Date(health.timestamp).toLocaleString()}
                  </p>
                )}
              </div>
            </div>

            {/* Service grid */}
            <div>
              <h2 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>
                Service Probes
              </h2>
              <SystemHealthGrid services={health.services ?? []} />
            </div>
          </>
        )}

        {!health && !error && (
          <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Awaiting diagnostic probe response...</p>
        )}
      </div>
    </div>
  );
}
