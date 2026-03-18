import { fetchAgent } from '@/lib/api';
import { notFound } from 'next/navigation';
import type { EvalVerdict } from '@/lib/types';

export const revalidate = 30;

interface Props {
  params: Promise<{ id: string }>;
}

const verdictColors: Record<EvalVerdict, string> = {
  pass: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  review: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  fail: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
};

export default async function AgentDetailPage({ params }: Props) {
  const { id } = await params;
  let agent;

  try {
    agent = await fetchAgent(id);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes('404')) notFound();
    // For other errors, show a minimal error state
    return (
      <div className="px-6 py-6">
        <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950 px-5 py-4">
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Could not load agent data
          </p>
          <p className="text-xs text-red-500 dark:text-red-400 mt-1">{msg}</p>
        </div>
      </div>
    );
  }

  const avgScore =
    agent.recent_scores?.length > 0
      ? (agent.recent_scores.reduce((a, b) => a + b, 0) / agent.recent_scores.length).toFixed(1)
      : null;

  return (
    <div className="px-6 py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{agent.name}</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{agent.role}</p>
      </div>

      {/* Info card */}
      <div className="border border-gray-200 dark:border-gray-800 rounded-xl p-5 bg-white dark:bg-gray-950">
        <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-4">Agent Info</h2>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            { label: 'Status', value: agent.status },
            { label: 'Type', value: agent.type || '—' },
            { label: 'Model tier', value: agent.model_tier },
            { label: 'Model', value: agent.model || '—' },
            { label: 'Version', value: agent.version || '—' },
            { label: 'Avg quality', value: avgScore ? `${avgScore}/10` : '—' },
          ].map(({ label, value }) => (
            <div key={label}>
              <dt className="text-xs text-gray-500 dark:text-gray-400">{label}</dt>
              <dd className="text-sm font-medium text-gray-900 dark:text-white mt-0.5 truncate">
                {value}
              </dd>
            </div>
          ))}
        </dl>
      </div>

      {/* Quality score sparkline (simple visual) */}
      {agent.recent_scores?.length > 0 && (
        <div className="border border-gray-200 dark:border-gray-800 rounded-xl p-5 bg-white dark:bg-gray-950">
          <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-4">
            Recent Quality Scores
          </h2>
          <div className="flex items-end gap-1 h-16">
            {agent.recent_scores.map((score, i) => (
              <div
                key={i}
                className={`flex-1 rounded-t transition-all ${
                  score >= 7
                    ? 'bg-green-400 dark:bg-green-600'
                    : score >= 4
                    ? 'bg-yellow-400 dark:bg-yellow-600'
                    : 'bg-red-400 dark:bg-red-600'
                }`}
                style={{ height: `${(score / 10) * 100}%` }}
                title={`${score}/10`}
              />
            ))}
          </div>
          <div className="flex justify-between text-xs text-gray-400 dark:text-gray-600 mt-1">
            <span>older</span>
            <span>newer</span>
          </div>
        </div>
      )}

      {/* Capability Breakdown — horizontal bar chart of rubric dimensions */}
      {(() => {
        const dims = agent.dimension_averages ?? {};
        const dimEntries = Object.entries(dims);
        if (dimEntries.length === 0) {
          return (
            <div className="border border-gray-200 dark:border-gray-800 rounded-xl p-5 bg-white dark:bg-gray-950">
              <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-4">
                Capability Breakdown
              </h2>
              <p className="text-sm text-gray-400 dark:text-gray-600">No evaluations yet</p>
            </div>
          );
        }
        const maxScore = 10;
        return (
          <div className="border border-gray-200 dark:border-gray-800 rounded-xl p-5 bg-white dark:bg-gray-950">
            <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-4">
              Capability Breakdown
            </h2>
            <div className="space-y-3">
              {dimEntries.map(([dim, score]) => {
                const pct = Math.min((score / maxScore) * 100, 100);
                const barColor =
                  score >= 8
                    ? 'bg-green-500 dark:bg-green-400'
                    : score >= 6
                    ? 'bg-yellow-500 dark:bg-yellow-400'
                    : 'bg-red-500 dark:bg-red-400';
                const label = dim.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
                return (
                  <div key={dim}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                        {label}
                      </span>
                      <span className="text-xs font-mono text-gray-500 dark:text-gray-400">
                        {score.toFixed(1)}
                      </span>
                    </div>
                    <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${barColor}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}

      {/* Cycle history table */}
      {agent.cycles?.length > 0 && (
        <div className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-white dark:bg-gray-950">
          <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
            <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm">
              Cycle History (last {agent.cycles.length})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  {['Timestamp', 'Status', 'Score', 'Cost', 'Duration', 'Verdict'].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-900">
                {agent.cycles.map((cycle) => (
                  <tr key={cycle.id} className="hover:bg-gray-50 dark:hover:bg-gray-900">
                    <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400 font-mono whitespace-nowrap">
                      {new Date(cycle.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                          cycle.status === 'success'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                            : cycle.status === 'failed'
                            ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                            : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                        }`}
                      >
                        {cycle.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-700 dark:text-gray-300">
                      {cycle.quality_score?.toFixed(1) ?? '—'}
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-700 dark:text-gray-300">
                      {cycle.cost_usd !== undefined ? `$${cycle.cost_usd.toFixed(4)}` : '—'}
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-700 dark:text-gray-300">
                      {cycle.duration_seconds !== undefined ? `${cycle.duration_seconds}s` : '—'}
                    </td>
                    <td className="px-4 py-2">
                      {cycle.verdict ? (
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded font-medium ${verdictColors[cycle.verdict]}`}
                        >
                          {cycle.verdict}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {agent.cycles?.length === 0 && (
        <p className="text-sm text-gray-400 dark:text-gray-600">No cycle history yet.</p>
      )}
    </div>
  );
}
