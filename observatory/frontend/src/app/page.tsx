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
    <div className="page-transition">
      {health?.kill_switch_active && (
        <KillSwitchBanner health={health} compact />
      )}

      <div style={{ padding: 'var(--page-padding)' }} className="space-y-6">
        {/* Page header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
            Inference Feed
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Live agent activity, quality drift, and system-wide KPIs
          </p>
        </div>

        {error && <ErrorBanner message="Could not reach Observatory API" />}

        {/* System status pill */}
        {health && (
          <div
            className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium"
            style={{
              background: health.status === 'healthy' ? 'var(--success-subtle)'
                : health.status === 'degraded' ? 'var(--warning-subtle)'
                : 'var(--danger-subtle)',
              border: `1px solid ${
                health.status === 'healthy' ? 'var(--success)'
                : health.status === 'degraded' ? 'var(--warning)'
                : 'var(--danger)'
              }`,
              color: health.status === 'healthy' ? 'var(--success)'
                : health.status === 'degraded' ? 'var(--warning)'
                : 'var(--danger)',
            }}
          >
            <span
              className={`status-dot ${health.status === 'healthy' ? 'status-dot-active' : ''}`}
              style={{
                background: health.status === 'healthy' ? 'var(--success)'
                  : health.status === 'degraded' ? 'var(--warning)'
                  : 'var(--danger)',
              }}
            />
            <span className="capitalize">System: {health.status}</span>
            {health.timestamp && (
              <span className="ml-auto text-xs opacity-60">
                As of {new Date(health.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>
        )}

        {/* KPI Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            title="Inference cycles (7d)"
            value={metrics?.cycles_this_week ?? '--'}
            subtitle="observe-reason-act loops"
            color="blue"
            staggerIndex={1}
          />
          <KPICard
            title="Cycle success rate"
            value={metrics ? `${(metrics.success_rate * 100).toFixed(1)}%` : '--'}
            color={
              metrics
                ? metrics.success_rate >= 0.8
                  ? 'green'
                  : metrics.success_rate >= 0.5
                  ? 'yellow'
                  : 'red'
                : 'default'
            }
            staggerIndex={2}
          />
          <KPICard
            title="Mean judge score"
            value={metrics?.avg_quality_score?.toFixed(1) ?? '--'}
            subtitle="7-evaluator weighted avg"
            color={
              metrics
                ? metrics.avg_quality_score >= 7
                  ? 'green'
                  : metrics.avg_quality_score >= 4
                  ? 'yellow'
                  : 'red'
                : 'default'
            }
            staggerIndex={3}
          />
          <KPICard
            title="Inference cost"
            value={metrics ? `$${metrics.total_cost_usd.toFixed(2)}` : '--'}
            subtitle="token spend (7d)"
            staggerIndex={4}
          />
        </div>

        {/* Agents section */}
        <section>
          <h2 className="section-heading">
            Agent Fleet ({agents.length})
          </h2>
          {agents.length === 0 ? (
            <p className="text-sm py-4" style={{ color: 'var(--text-tertiary)' }}>
              {error ? 'Fleet data unavailable -- check API connection.' : 'No agents registered in AGENTS.yaml.'}
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {agents.map((agent, i) => (
                <AgentCard key={agent.id} agent={agent} staggerIndex={Math.min(i + 1, 12)} />
              ))}
            </div>
          )}
        </section>

        <TrajectoryTimeline />
      </div>
    </div>
  );
}
