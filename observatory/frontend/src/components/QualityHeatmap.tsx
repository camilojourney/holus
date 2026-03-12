import type { EvaluationRecord } from '@/lib/types';

interface Props {
  evaluations: EvaluationRecord[];
  agents: string[];
  days?: number;
}

function scoreColor(score?: number): string {
  if (score === undefined) return 'bg-gray-100 dark:bg-gray-800';
  if (score >= 7) return 'bg-green-400 dark:bg-green-600';
  if (score >= 4) return 'bg-yellow-400 dark:bg-yellow-600';
  return 'bg-red-400 dark:bg-red-600';
}

function getLast30Days(): string[] {
  return Array.from({ length: 30 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (29 - i));
    return d.toISOString().slice(0, 10);
  });
}

export default function QualityHeatmap({ evaluations, agents, days = 30 }: Props) {
  const dateRange = getLast30Days().slice(-days);

  // Build lookup: agent+date -> score
  const lookup: Record<string, number> = {};
  for (const ev of evaluations) {
    const key = `${ev.agent_id}|${ev.date.slice(0, 10)}`;
    lookup[key] = ev.score;
  }

  if (agents.length === 0) {
    return (
      <p className="text-sm text-gray-400 dark:text-gray-600 text-center py-8">
        No agent data available
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <div className="min-w-max">
        {/* Header row: dates */}
        <div className="flex items-center gap-1 mb-2 pl-32">
          {dateRange.map((d) => (
            <div
              key={d}
              className="w-5 text-center"
              title={d}
            >
              <span className="text-xs text-gray-400 dark:text-gray-600 rotate-90 inline-block">
                {d.slice(5)}
              </span>
            </div>
          ))}
        </div>
        {/* Rows: agents */}
        {agents.map((agentId) => (
          <div key={agentId} className="flex items-center gap-1 mb-1">
            <div className="w-32 shrink-0 text-xs text-gray-600 dark:text-gray-400 truncate pr-2 text-right">
              {agentId}
            </div>
            {dateRange.map((d) => {
              const score = lookup[`${agentId}|${d}`];
              return (
                <div
                  key={d}
                  className={`w-5 h-5 rounded-sm ${scoreColor(score)}`}
                  title={score !== undefined ? `${agentId} ${d}: ${score}` : `${agentId} ${d}: no data`}
                />
              );
            })}
          </div>
        ))}
        {/* Legend */}
        <div className="flex items-center gap-4 mt-4 pl-32">
          {[
            { color: 'bg-green-400 dark:bg-green-600', label: '7–10 Pass' },
            { color: 'bg-yellow-400 dark:bg-yellow-600', label: '4–7 Review' },
            { color: 'bg-red-400 dark:bg-red-600', label: '0–4 Fail' },
            { color: 'bg-gray-100 dark:bg-gray-800', label: 'No data' },
          ].map(({ color, label }) => (
            <div key={label} className="flex items-center gap-1.5">
              <div className={`w-3 h-3 rounded-sm ${color}`} />
              <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
