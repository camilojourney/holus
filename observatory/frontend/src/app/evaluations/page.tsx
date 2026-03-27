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
    <div className="px-6 py-6 space-y-6 page-transition">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Quality Signals</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          Judge verdicts and quality drift across 7 domain-expert evaluators (30d window)
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
                className="rounded-xl px-4 py-4 text-center"
                style={{
                  border: '1px solid var(--border-default)',
                  background: 'var(--surface-raised)',
                }}
              >
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{passCounts[v]}</p>
                <span
                  className={`inline-block mt-2 text-xs px-2 py-0.5 rounded-full font-medium ${verdictColors[v]}`}
                >
                  {v}
                </span>
              </div>
            ))}
          </div>

          {/* Heatmap */}
          <div
            className="rounded-xl p-5"
            style={{
              border: '1px solid var(--border-default)',
              background: 'var(--surface-raised)',
            }}
          >
            <h2 className="font-semibold text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
              Score Heatmap -- Agents x Days (darker = higher quality)
            </h2>
            <QualityHeatmap evaluations={evaluations} agents={agentIds} />
          </div>

          {/* Evaluation table */}
          {evaluations.length > 0 && (
            <div
              className="rounded-xl overflow-hidden"
              style={{
                border: '1px solid var(--border-default)',
                background: 'var(--surface-raised)',
              }}
            >
              <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <h2 className="font-semibold text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Evaluation Log ({evaluations.length} verdicts)
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead style={{ background: 'var(--surface-2)' }}>
                    <tr>
                      {['Agent', 'Date', 'Score', 'Verdict', 'Evaluator'].map((h) => (
                        <th
                          key={h}
                          scope="col"
                          className="px-4 py-2 text-left text-xs font-medium"
                          style={{ color: 'var(--text-tertiary)' }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {evaluations.slice(0, 50).map((ev, idx) => (
                      <tr
                        key={ev.id}
                        className="transition-colors hover:bg-[var(--surface-2)]"
                        style={{
                          borderBottom: idx < Math.min(evaluations.length, 50) - 1 ? '1px solid var(--border-subtle)' : undefined,
                        }}
                      >
                        <td className="px-4 py-2 text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                          {ev.agent_name}
                        </td>
                        <td className="px-4 py-2 text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
                          {ev.date.slice(0, 10)}
                        </td>
                        <td className="px-4 py-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
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
                            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>—</span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>
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
            <p className="text-sm py-4" style={{ color: 'var(--text-tertiary)' }}>
              No quality signals yet -- run first evaluation cycle to populate.
            </p>
          )}
        </>
      )}
    </div>
  );
}
