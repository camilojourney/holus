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

      <div className="px-6 py-6 space-y-6">
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
              className={`border rounded-xl px-5 py-4 flex items-center gap-4 ${
                health.status === 'healthy'
                  ? 'border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950'
                  : health.status === 'degraded'
                  ? 'border-yellow-200 bg-yellow-50 dark:border-yellow-900 dark:bg-yellow-950'
                  : 'border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950'
              }`}
            >
              <div
                className={`w-3 h-3 rounded-full ${
                  health.status === 'healthy'
                    ? 'bg-green-500'
                    : health.status === 'degraded'
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
                }`}
              />
              <div>
                <p
                  className={`font-semibold capitalize ${
                    health.status === 'healthy'
                      ? 'text-green-700 dark:text-green-300'
                      : health.status === 'degraded'
                      ? 'text-yellow-700 dark:text-yellow-300'
                      : 'text-red-700 dark:text-red-300'
                  }`}
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
