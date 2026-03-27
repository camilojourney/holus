'use client';

import { useRef, useCallback } from 'react';
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
  const gridRef = useRef<HTMLDivElement>(null);

  // Build lookup: agent+date -> score
  const lookup: Record<string, number> = {};
  for (const ev of evaluations) {
    const key = `${ev.agent_id}|${ev.date.slice(0, 10)}`;
    lookup[key] = ev.score;
  }

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      const target = e.target as HTMLElement;
      if (target.getAttribute('role') !== 'gridcell') return;

      const cells = gridRef.current?.querySelectorAll<HTMLElement>('[role="gridcell"]');
      if (!cells) return;

      const cellArray = Array.from(cells);
      const idx = cellArray.indexOf(target);
      if (idx === -1) return;

      const cols = dateRange.length;
      let next = -1;

      switch (e.key) {
        case 'ArrowRight':
          next = idx + 1 < cellArray.length ? idx + 1 : idx;
          break;
        case 'ArrowLeft':
          next = idx - 1 >= 0 ? idx - 1 : idx;
          break;
        case 'ArrowDown':
          next = idx + cols < cellArray.length ? idx + cols : idx;
          break;
        case 'ArrowUp':
          next = idx - cols >= 0 ? idx - cols : idx;
          break;
        case 'Home':
          next = idx - (idx % cols);
          break;
        case 'End':
          next = idx - (idx % cols) + cols - 1;
          break;
        default:
          return;
      }

      e.preventDefault();
      cellArray[next]?.focus();
    },
    [dateRange.length]
  );

  if (agents.length === 0) {
    return (
      <p className="text-sm text-gray-400 dark:text-gray-400 text-center py-8">
        No agent data available
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <div
        ref={gridRef}
        className="min-w-max"
        role="grid"
        aria-label="Agent quality scores heatmap"
        onKeyDown={handleKeyDown}
      >
        {/* Header row: dates */}
        <div className="flex items-center gap-1 mb-2 pl-32" role="row">
          {dateRange.map((d) => (
            <div
              key={d}
              className="w-7 text-center"
              title={d}
              role="columnheader"
            >
              <span className="text-xs text-gray-400 dark:text-gray-400 rotate-90 inline-block">
                {d.slice(5)}
              </span>
            </div>
          ))}
        </div>
        {/* Rows: agents */}
        {agents.map((agentId, rowIdx) => (
          <div key={agentId} className="flex items-center gap-1 mb-1" role="row">
            <div className="w-32 shrink-0 text-xs text-gray-600 dark:text-gray-400 truncate pr-2 text-right" role="rowheader">
              {agentId}
            </div>
            {dateRange.map((d, colIdx) => {
              const score = lookup[`${agentId}|${d}`];
              return (
                <div
                  key={d}
                  role="gridcell"
                  tabIndex={rowIdx === 0 && colIdx === 0 ? 0 : -1}
                  aria-label={score !== undefined ? `${agentId} ${d}: score ${score}` : `${agentId} ${d}: no data`}
                  className={`w-7 h-7 rounded-sm cursor-pointer focus:outline-2 focus:outline-indigo-500 focus:outline-offset-1 ${scoreColor(score)}`}
                  title={score !== undefined ? `${agentId} ${d}: ${score}` : `${agentId} ${d}: no data`}
                />
              );
            })}
          </div>
        ))}
        {/* Legend */}
        <div className="flex items-center gap-4 mt-4 pl-32">
          {[
            { color: 'bg-green-400 dark:bg-green-600', label: '7\u201310 Pass' },
            { color: 'bg-yellow-400 dark:bg-yellow-600', label: '4\u20137 Review' },
            { color: 'bg-red-400 dark:bg-red-600', label: '0\u20134 Fail' },
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
