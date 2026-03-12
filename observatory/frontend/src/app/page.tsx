import { fetchHealth, fetchAgents, fetchMetrics } from '@/lib/api';
import KPICard from '@/components/KPICard';
import AgentCard from '@/components/AgentCard';
import KillSwitchBanner from '@/components/KillSwitchBanner';
import ErrorBanner from '@/components/ErrorBanner';
import TrajectoryTimeline from '@/components/TrajectoryTimeline';

export const revalidate = 30;

async function getData() {
  const [health, agents, metrics] = await Promise.allSettled([
    fetchHealth(),
    fetchAgents(),
    fetchMetrics(),
  ]);
  return {
    health: health.status === 'fulfilled' ? health.value : null,
    agents: agents.status === 'fulfilled' ? agents.value : [],
    metrics: metrics.status === 'fulfilled' ? metrics.value : null,
    error: health.status === 'rejected' && agents.status === 'rejected',
  };
}

export default async function DashboardPage() {
  const { health, agents, metrics, error } = await getData();

  return (
    <div>
      {health?.kill_switch_active && (
        <KillSwitchBanner health={health} compact />
      )}

      <div className="px-6 py-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Holus autonomous marketing system — overview
          </p>
        </div>

        {error && <ErrorBanner message="Could not reach Observatory API" />}

        {health && (
          <div
            className={`flex items-center gap-3 px-4 py-3 rounded-xl border text-sm font-medium ${
              health.status === 'healthy'
                ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-900 dark:bg-green-950 dark:text-green-300'
                : health.status === 'degraded'
                ? 'border-yellow-200 bg-yellow-50 text-yellow-700 dark:border-yellow-900 dark:bg-yellow-950 dark:text-yellow-300'
                : 'border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300'
            }`}
          >
            <span className="capitalize">System: {health.status}</span>
            {health.timestamp && (
              <span className="ml-auto text-xs opacity-60">
                As of {new Date(health.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>
        )}

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            title="Cycles this week"
            value={metrics?.cycles_this_week ?? '—'}
            color="blue"
          />
          <KPICard
            title="Success rate"
            value={metrics ? `${(metrics.success_rate * 100).toFixed(1)}%` : '—'}
            color={
              metrics
                ? metrics.success_rate >= 0.8
                  ? 'green'
                  : metrics.success_rate >= 0.5
                  ? 'yellow'
                  : 'red'
                : 'default'
            }
          />
          <KPICard
            title="Avg quality score"
            value={metrics?.avg_quality_score?.toFixed(1) ?? '—'}
            subtitle="out of 10"
            color={
              metrics
                ? metrics.avg_quality_score >= 7
                  ? 'green'
                  : metrics.avg_quality_score >= 4
                  ? 'yellow'
                  : 'red'
                : 'default'
            }
          />
          <KPICard
            title="Total cost"
            value={metrics ? `$${metrics.total_cost_usd.toFixed(2)}` : '—'}
            subtitle="this week"
          />
        </div>

        <div>
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Agents ({agents.length})
          </h2>
          {agents.length === 0 ? (
            <p className="text-sm text-gray-400 dark:text-gray-600 py-4">
              {error ? 'Unable to load agents.' : 'No agents registered.'}
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {agents.map((agent) => (
                <AgentCard key={agent.id} agent={agent} />
              ))}
            </div>
          )}
        </div>

        <TrajectoryTimeline />
      </div>
    </div>
  );
}
