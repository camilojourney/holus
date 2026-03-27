import { ShieldAlert, ShieldCheck } from 'lucide-react';
import type { HealthStatus } from '@/lib/types';

interface Props {
  health: HealthStatus | null;
  compact?: boolean;
}

export default function KillSwitchBanner({ health, compact = false }: Props) {
  if (!health) return null;

  if (health.kill_switch_active) {
    return (
      <div
        role="alert"
        aria-live="assertive"
        className={`w-full flex items-center gap-3 ${compact ? 'px-4 py-2' : 'px-6 py-4'}`}
        style={{ background: 'var(--danger)', color: 'var(--text-inverse)' }}
      >
        <ShieldAlert size={compact ? 16 : 20} aria-hidden="true" />
        <span className={`font-bold uppercase tracking-wide ${compact ? 'text-sm' : 'text-base'}`}>
          {compact ? 'KILL SWITCH ON' : 'KILL SWITCH ACTIVE'}
        </span>
        {health.kill_switch_activated_at && (
          <span className="opacity-75 text-sm ml-auto">
            Activated: {new Date(health.kill_switch_activated_at).toLocaleString()}
          </span>
        )}
      </div>
    );
  }

  if (!compact) {
    return (
      <div
        className="w-full flex items-center gap-3 px-6 py-3"
        style={{ background: 'var(--success)', color: 'var(--text-inverse)' }}
      >
        <ShieldCheck size={20} aria-hidden="true" />
        <span className="font-medium">System running normally -- Kill switch INACTIVE</span>
      </div>
    );
  }

  return null;
}
