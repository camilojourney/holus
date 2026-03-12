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
    <div className="px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Agents</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          All registered agents and their current status
        </p>
      </div>

      {error && <ErrorBanner message="Could not load agents from Observatory API" />}

      {!error && agents.length === 0 && (
        <p className="text-sm text-gray-400 dark:text-gray-600">
          No agents found. Ensure Observatory API is running and agents/AGENTS.yaml is populated.
        </p>
      )}

      {/* Status summary */}
      {agents.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {Object.entries(byStatus).map(([status, list]) => (
            <div
              key={status}
              className="border border-gray-200 dark:border-gray-800 rounded-lg px-3 py-2 text-sm"
            >
              <span className="font-medium text-gray-700 dark:text-gray-300">{list.length}</span>
              <span className="ml-1.5 text-gray-500 dark:text-gray-400">{status}</span>
            </div>
          ))}
        </div>
      )}

      {/* Agent grid */}
      {agents.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}
