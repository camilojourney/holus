import type { Agent, AgentStatus } from '@/lib/types';
import Link from 'next/link';

const statusColors: Record<AgentStatus, { bg: string; text: string; dot: string; label: string }> = {
  active: { bg: 'var(--success-subtle)', text: 'var(--success)', dot: 'var(--success)', label: 'observing' },
  idle: { bg: 'var(--surface-2)', text: 'var(--text-tertiary)', dot: 'var(--text-tertiary)', label: 'idle' },
  running: { bg: 'var(--info-subtle)', text: 'var(--info)', dot: 'var(--info)', label: 'reasoning' },
  error: { bg: 'var(--danger-subtle)', text: 'var(--danger)', dot: 'var(--danger)', label: 'fault' },
  disabled: { bg: 'var(--surface-2)', text: 'var(--text-tertiary)', dot: 'var(--border-default)', label: 'offline' },
  planned: { bg: 'var(--warning-subtle)', text: 'var(--warning)', dot: 'var(--warning)', label: 'evaluating' },
};

const typeIcons: Record<string, string> = {
  manager: 'M',
  specialist: 'S',
  evaluator: 'E',
  ops: 'O',
};

interface Props {
  agent: Agent;
  staggerIndex?: number;
}

export default function AgentCard({ agent, staggerIndex }: Props) {
  const status = statusColors[agent.status] ?? statusColors.idle;
  const isActive = agent.status === 'active' || agent.status === 'running';
  const staggerClass = staggerIndex !== undefined ? `stagger-${staggerIndex}` : '';

  return (
    <Link href={`/agents/${agent.id}`} className="focus-ring rounded-xl">
      <div
        className={`card card-interactive animate-fade-in group ${staggerClass}`}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2.5">
            {/* Agent type badge */}
            <div
              className="w-7 h-7 rounded-md flex items-center justify-center text-[0.625rem] font-bold"
              style={{
                background: 'var(--brand-subtle)',
                color: 'var(--brand)',
              }}
            >
              {typeIcons[agent.type] ?? 'A'}
            </div>
            <h3
              className="font-semibold text-sm leading-tight"
              style={{ color: 'var(--text-primary)' }}
            >
              {agent.name}
            </h3>
          </div>
          <span
            className="flex items-center gap-1.5 text-[0.6875rem] px-2 py-0.5 rounded-full font-medium"
            style={{ background: status.bg, color: status.text }}
          >
            <span
              className={`status-dot ${isActive ? 'status-dot-active' : ''}`}
              style={{ background: status.dot }}
            />
            {status.label}
          </span>
        </div>
        <p
          className="text-xs mb-2 line-clamp-1"
          style={{ color: 'var(--text-secondary)' }}
        >
          {agent.role}
        </p>
        <div className="flex items-center gap-2 mt-3">
          <span
            className="text-[0.625rem] px-2 py-0.5 rounded font-medium"
            style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}
            title="Model tier used for inference"
          >
            {agent.model_tier}
          </span>
          {agent.type && (
            <span
              className="text-[0.625rem] px-2 py-0.5 rounded font-medium"
              style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}
              title="Agent category in the fleet"
            >
              {agent.type}
            </span>
          )}
        </div>
        {agent.model && (
          <p className="text-[0.6875rem] mt-2 truncate font-mono" style={{ color: 'var(--text-tertiary)' }} title="Exact model ID used for last inference">
            {agent.model}
          </p>
        )}
      </div>
    </Link>
  );
}
