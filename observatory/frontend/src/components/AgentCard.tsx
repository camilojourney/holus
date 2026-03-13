import type { Agent, AgentStatus } from '@/lib/types';
import Link from 'next/link';

const statusColors: Record<AgentStatus, string> = {
  active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  idle: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  disabled: 'bg-gray-100 text-gray-400 dark:bg-gray-900 dark:text-gray-600',
  planned: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
};

interface Props {
  agent: Agent;
}

export default function AgentCard({ agent }: Props) {
  return (
    <Link href={`/agents/${agent.id}`}>
      <div className="border border-gray-200 dark:border-gray-800 rounded-xl p-4 bg-white dark:bg-gray-950 hover:border-indigo-300 dark:hover:border-indigo-700 hover:shadow-md transition-all cursor-pointer focus-within:ring-2 focus-within:ring-indigo-500 focus-within:ring-offset-2 dark:focus-within:ring-offset-gray-950">
        <div className="flex items-start justify-between mb-3">
          <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
            {agent.name}
          </h3>
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[agent.status]}`}
          >
            {agent.status}
          </span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{agent.role}</p>
        <div className="flex items-center gap-2 mt-3">
          <span className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded">
            {agent.model_tier}
          </span>
          {agent.type && (
            <span className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded">
              {agent.type}
            </span>
          )}
        </div>
        {agent.model && (
          <p className="text-xs text-gray-400 dark:text-gray-600 mt-2 truncate">{agent.model}</p>
        )}
      </div>
    </Link>
  );
}
