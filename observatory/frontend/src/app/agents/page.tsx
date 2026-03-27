import { fetchAgents } from '@/lib/api';
import AgentCard from '@/components/AgentCard';
import ErrorBanner from '@/components/ErrorBanner';
import type { Agent } from '@/lib/types';

export const revalidate = 30;

export default async function AgentsPage() {
  let agents: Agent[] = [];
  let error = false;

  try {
    agents = await fetchAgents();
  } catch {
    error = true;
  }

  const byStatus = agents.reduce<Record<string, typeof agents>>((acc, a) => {
    acc[a.status] = [...(acc[a.status] ?? []), a];
    return acc;
  }, {});

  return (
    <div style={{ padding: 'var(--page-padding)' }} className="space-y-6 page-transition">
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
          Agent Fleet
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          32 registered agents -- model tiers, roles, and operational state
        </p>
      </div>

      {error && <ErrorBanner message="Could not load agents from Observatory API" />}

      {!error && agents.length === 0 && (
        <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
          No agents in registry. Verify AGENTS.yaml is populated and Observatory API is reachable.
        </p>
      )}

      {/* Status summary */}
      {agents.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {Object.entries(byStatus).map(([status, list]) => (
            <div
              key={status}
              className="rounded-lg px-3 py-2 text-sm"
              style={{
                border: '1px solid var(--border-default)',
                background: 'var(--surface-raised)',
              }}
            >
              <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{list.length}</span>
              <span className="ml-1.5" style={{ color: 'var(--text-secondary)' }}>{status}</span>
            </div>
          ))}
        </div>
      )}

      {/* Agent grid */}
      {agents.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {agents.map((agent, i) => (
            <AgentCard key={agent.id} agent={agent} staggerIndex={Math.min(i + 1, 12)} />
          ))}
        </div>
      )}
    </div>
  );
}
