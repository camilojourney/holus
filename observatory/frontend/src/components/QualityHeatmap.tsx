'use client';

import { useRef, useCallback, useState } from 'react';
import type { EvaluationRecord } from '@/lib/types';

interface Props {
  evaluations: EvaluationRecord[];
  agents: string[];
  days?: number;
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  agent: string;
  date: string;
  score?: number;
}

/**
 * Continuous color scale: red (0) -> yellow (5) -> green (10).
 * Uses oklch interpolation for perceptually uniform gradients.
 * Falls back to surface-2 for missing data.
 */
function scoreStyle(score?: number): React.CSSProperties {
  if (score === undefined) return { background: 'var(--surface-2)' };
  // Clamp to 0-10
  const s = Math.max(0, Math.min(10, score));
  // Interpolate hue: 25 (red) -> 85 (yellow) -> 145 (green)
  // Lightness: 0.55 at edges, 0.65 at midpoint (yellow pops more)
  // Chroma: 0.18 throughout
  let hue: number;
  let lightness: number;
  if (s <= 5) {
    // red (25) -> yellow (85)
    const t = s / 5;
    hue = 25 + t * 60;
    lightness = 0.55 + t * 0.10;
  } else {
    // yellow (85) -> green (145)
    const t = (s - 5) / 5;
    hue = 85 + t * 60;
    lightness = 0.65 - t * 0.10;
  }
  return { background: `oklch(${lightness.toFixed(2)} 0.18 ${hue.toFixed(0)})` };
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
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    agent: '',
    date: '',
  });

  // Build lookup: agent+date -> score
  const lookup: Record<string, number> = {};
  for (const ev of evaluations) {
    const key = `${ev.agent_id}|${ev.date.slice(0, 10)}`;
    lookup[key] = ev.score;
  }

  const handleCellHover = useCallback(
    (e: React.MouseEvent<HTMLDivElement>, agent: string, date: string, score?: number) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const containerRect = gridRef.current?.getBoundingClientRect();
      if (!containerRect) return;
      setTooltip({
        visible: true,
        x: rect.left - containerRect.left + rect.width / 2,
        y: rect.top - containerRect.top - 8,
        agent,
        date,
        score,
      });
    },
    [],
  );

  const handleCellLeave = useCallback(() => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  }, []);

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
      <p className="text-sm text-center py-8" style={{ color: 'var(--text-tertiary)' }}>
        No agent data available
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <div
        ref={gridRef}
        className="min-w-max relative"
        role="grid"
        aria-label="Agent quality scores heatmap"
        onKeyDown={handleKeyDown}
      >
        {/* Tooltip */}
        {tooltip.visible && (
          <div
            className="absolute z-50 pointer-events-none"
            style={{
              left: tooltip.x,
              top: tooltip.y,
              transform: 'translate(-50%, -100%)',
            }}
          >
            <div
              className="rounded-lg px-3 py-2 text-xs shadow-lg whitespace-nowrap"
              style={{
                background: 'var(--surface-raised)',
                border: '1px solid var(--border-default)',
                color: 'var(--text-primary)',
              }}
            >
              <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                {tooltip.agent}
              </div>
              <div className="mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                {tooltip.date}
              </div>
              <div className="mt-1 font-mono font-bold" style={{
                color: tooltip.score !== undefined
                  ? tooltip.score >= 7 ? 'var(--success)' : tooltip.score >= 4 ? 'var(--warning)' : 'var(--danger)'
                  : 'var(--text-tertiary)',
              }}>
                {tooltip.score !== undefined ? `${tooltip.score}/10` : 'No data'}
              </div>
            </div>
          </div>
        )}

        {/* Header row: dates */}
        <div className="flex items-center gap-1 mb-2 pl-32" role="row">
          {dateRange.map((d) => (
            <div
              key={d}
              className="w-7 text-center"
              role="columnheader"
            >
              <span className="text-xs rotate-90 inline-block" style={{ color: 'var(--text-tertiary)' }}>
                {d.slice(5)}
              </span>
            </div>
          ))}
        </div>
        {/* Rows: agents */}
        {agents.map((agentId, rowIdx) => (
          <div key={agentId} className="flex items-center gap-1 mb-1" role="row">
            <div
              className="w-32 shrink-0 text-xs truncate pr-2 text-right"
              role="rowheader"
              style={{ color: 'var(--text-secondary)' }}
            >
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
                  className="w-7 h-7 rounded-sm cursor-pointer focus:outline-2 focus:outline-offset-1"
                  style={{
                    ...scoreStyle(score),
                    outlineColor: 'var(--brand)',
                  }}
                  onMouseEnter={(e) => handleCellHover(e, agentId, d, score)}
                  onMouseLeave={handleCellLeave}
                />
              );
            })}
          </div>
        ))}
        {/* Legend — continuous gradient */}
        <div className="flex items-center gap-4 mt-4 pl-32">
          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>0</span>
            <div
              className="h-3 rounded-sm"
              style={{
                width: '120px',
                background: 'linear-gradient(to right, oklch(0.55 0.18 25), oklch(0.65 0.18 85), oklch(0.55 0.18 145))',
              }}
            />
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>10</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm" style={{ background: 'var(--surface-2)' }} />
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>No data</span>
          </div>
        </div>
      </div>
    </div>
  );
}
