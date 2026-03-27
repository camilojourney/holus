import { fetchEvaluations, fetchAgents } from '@/lib/api';
import QualityHeatmap from '@/components/QualityHeatmap';
import ErrorBanner from '@/components/ErrorBanner';
import type { EvalVerdict, EvaluationRecord, Agent } from '@/lib/types';

export const revalidate = 30;

const verdictColors: Record<EvalVerdict, string> = {
  pass: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  review: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  fail: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
};

export default async function EvaluationsPage() {
  let evaluations: EvaluationRecord[] = [];
  let agents: Agent[] = [];
  let error = false;

  try {
    [evaluations, agents] = await Promise.all([fetchEvaluations({ days: 30 }), fetchAgents()]);
  } catch {
    error = true;
  }

  const agentIds = agents.map((a) => a.id);

  const passCounts = { pass: 0, review: 0, fail: 0 };
  for (const ev of evaluations) {
    if (ev.verdict && ev.verdict in passCounts) {
      passCounts[ev.verdict]++;
    }
  }

  return (
    <div className="px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Evaluations</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Quality scores over the last 30 days
        </p>
      </div>

      {error && <ErrorBanner message="Could not load evaluation data" />}

      {!error && (
        <>
          {/* Gate health summary */}
          <div className="grid grid-cols-3 gap-4">
            {(['pass', 'review', 'fail'] as const).map((v) => (
              <div
                key={v}
                className="border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-4 bg-white dark:bg-gray-950 text-center"
              >
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{passCounts[v]}</p>
                <span
                  className={`inline-block mt-2 text-xs px-2 py-0.5 rounded-full font-medium ${verdictColors[v]}`}
                >
                  {v}
                </span>
              </div>
            ))}
          </div>

          {/* Heatmap */}
          <div className="border border-gray-200 dark:border-gray-800 rounded-xl p-5 bg-white dark:bg-gray-950">
            <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-4">
              Quality Heatmap — Agents × Days
            </h2>
            <QualityHeatmap evaluations={evaluations} agents={agentIds} />
          </div>

          {/* Evaluation table */}
          {evaluations.length > 0 && (
            <div className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-white dark:bg-gray-950">
              <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
                <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm">
                  Evaluation History ({evaluations.length} records)
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-900">
                    <tr>
                      {['Agent', 'Date', 'Score', 'Verdict', 'Evaluator'].map((h) => (
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
                    {evaluations.slice(0, 50).map((ev) => (
                      <tr key={ev.id} className="hover:bg-gray-50 dark:hover:bg-gray-900">
                        <td className="px-4 py-2 text-xs text-gray-700 dark:text-gray-300 font-medium">
                          {ev.agent_name}
                        </td>
                        <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400 font-mono">
                          {ev.date.slice(0, 10)}
                        </td>
                        <td className="px-4 py-2 text-xs text-gray-700 dark:text-gray-300">
                          {ev.score}/10
                        </td>
                        <td className="px-4 py-2">
                          {ev.verdict ? (
                            <span
                              className={`text-xs px-1.5 py-0.5 rounded font-medium ${verdictColors[ev.verdict]}`}
                            >
                              {ev.verdict}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">
                          {ev.evaluator ?? '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {evaluations.length === 0 && (
            <p className="text-sm text-gray-400 dark:text-gray-400 py-4">
              No evaluation data yet.
            </p>
          )}
        </>
      )}
    </div>
  );
}
