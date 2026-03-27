import { fetchAgent } from '@/lib/api';
import { notFound } from 'next/navigation';
import type { EvalVerdict } from '@/lib/types';
import AgentSparkline from '@/components/AgentSparkline';

export const revalidate = 30;

interface Props {
  params: Promise<{ id: string }>;
}

const verdictStyles: Record<EvalVerdict, { bg: string; text: string }> = {
  pass: { bg: 'var(--success-subtle)', text: 'var(--success)' },
  review: { bg: 'var(--warning-subtle)', text: 'var(--warning)' },
  fail: { bg: 'var(--danger-subtle)', text: 'var(--danger)' },
};

export default async function AgentDetailPage({ params }: Props) {
  const { id } = await params;
  let agent;

  try {
    agent = await fetchAgent(id);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes('404')) notFound();
    return (
      <div style={{ padding: 'var(--page-padding)' }}>
        <ErrorState message={msg} />
      </div>
    );
  }

  const avgScore =
    agent.recent_scores?.length > 0
      ? (agent.recent_scores.reduce((a: number, b: number) => a + b, 0) / agent.recent_scores.length).toFixed(1)
      : null;

  return (
    <div style={{ padding: 'var(--page-padding)' }} className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
          {agent.name}
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{agent.role}</p>
      </div>

      {/* Info card */}
      <div className="card">
        <h2 className="font-semibold text-sm mb-4" style={{ color: 'var(--text-primary)' }}>Agent Configuration</h2>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            { label: 'Status', value: agent.status },
            { label: 'Type', value: agent.type || '--' },
            { label: 'Model tier', value: agent.model_tier },
            { label: 'Model', value: agent.model || '--' },
            { label: 'Version', value: agent.version || '--' },
            { label: 'Mean judge score', value: avgScore ? `${avgScore}/10` : '--' },
          ].map(({ label, value }) => (
            <div key={label}>
              <dt className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</dt>
              <dd className="text-sm font-medium mt-0.5 truncate" style={{ color: 'var(--text-primary)' }}>
                {value}
              </dd>
            </div>
          ))}
        </dl>
      </div>

      {/* Quality score sparkline */}
      {agent.recent_scores?.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
            Quality Trajectory
          </h2>
          <AgentSparkline scores={agent.recent_scores} />
          <div className="flex justify-between text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
            <span>older</span>
            <span>newer</span>
          </div>
        </div>
      )}

      {/* Capability Breakdown */}
      {(() => {
        const dims = agent.dimension_averages ?? {};
        const dimEntries = Object.entries(dims);
        if (dimEntries.length === 0) {
          return (
            <div className="card">
              <h2 className="font-semibold text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
                Capability Breakdown
              </h2>
              <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>No judge evaluations yet -- awaiting first cycle.</p>
            </div>
          );
        }
        const maxScore = 10;
        return (
          <div className="card">
            <h2 className="font-semibold text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
              Capability Breakdown
            </h2>
            <div className="space-y-3">
              {dimEntries.map(([dim, score]) => {
                const pct = Math.min((score / maxScore) * 100, 100);
                const barColor = score >= 8 ? 'var(--success)' : score >= 6 ? 'var(--warning)' : 'var(--danger)';
                const label = dim.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
                return (
                  <div key={dim}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                        {label}
                      </span>
                      <span className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                        {score.toFixed(1)}
                      </span>
                    </div>
                    <div
                      className="h-2 rounded-full overflow-hidden"
                      style={{ background: 'var(--surface-2)' }}
                    >
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${pct}%`, background: barColor }}
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
        <div
          className="rounded-xl overflow-hidden"
          style={{ background: 'var(--surface-raised)', border: '1px solid var(--border-default)' }}
        >
          <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <h2 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
              Cycle History (last {agent.cycles.length})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: 'var(--surface-1)' }}>
                  {['Timestamp', 'Status', 'Score', 'Cost', 'Duration', 'Verdict'].map((h) => (
                    <th
                      key={h}
                      scope="col"
                      className="px-4 py-2 text-left text-xs font-medium sticky top-0"
                      style={{ color: 'var(--text-tertiary)', background: 'var(--surface-1)' }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {agent.cycles.map((cycle) => {
                  const statusStyle = cycle.status === 'success'
                    ? { bg: 'var(--success-subtle)', text: 'var(--success)' }
                    : cycle.status === 'failed'
                    ? { bg: 'var(--danger-subtle)', text: 'var(--danger)' }
                    : { bg: 'var(--surface-2)', text: 'var(--text-tertiary)' };

                  return (
                    <tr
                      key={cycle.id}
                      style={{ borderBottom: '1px solid var(--border-subtle)' }}
                    >
                      <td className="px-4 py-2 text-xs font-mono whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>
                        {new Date(cycle.timestamp).toLocaleString()}
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className="text-xs px-1.5 py-0.5 rounded font-medium"
                          style={{ background: statusStyle.bg, color: statusStyle.text }}
                        >
                          {cycle.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-xs" style={{ color: 'var(--text-primary)' }}>
                        {cycle.quality_score?.toFixed(1) ?? '--'}
                      </td>
                      <td className="px-4 py-2 text-xs" style={{ color: 'var(--text-primary)' }}>
                        {cycle.cost_usd !== undefined ? `$${cycle.cost_usd.toFixed(4)}` : '--'}
                      </td>
                      <td className="px-4 py-2 text-xs" style={{ color: 'var(--text-primary)' }}>
                        {cycle.duration_seconds !== undefined ? `${cycle.duration_seconds}s` : '--'}
                      </td>
                      <td className="px-4 py-2">
                        {cycle.verdict ? (
                          <span
                            className="text-xs px-1.5 py-0.5 rounded font-medium"
                            style={{
                              background: verdictStyles[cycle.verdict].bg,
                              color: verdictStyles[cycle.verdict].text,
                            }}
                          >
                            {cycle.verdict}
                          </span>
                        ) : (
                          <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>--</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {agent.cycles?.length === 0 && (
        <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>No inference cycles recorded -- agent has not been dispatched yet.</p>
      )}
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div
      className="rounded-xl px-5 py-4"
      style={{
        background: 'var(--danger-subtle)',
        border: '1px solid var(--danger)',
      }}
    >
      <p className="text-sm font-medium" style={{ color: 'var(--danger)' }}>
        Could not load agent data
      </p>
      <p className="text-xs mt-1" style={{ color: 'var(--danger)', opacity: 0.8 }}>{message}</p>
    </div>
  );
}
