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
        className={`w-full bg-red-600 text-white ${compact ? 'px-4 py-2 text-sm' : 'px-6 py-4 text-base'} flex items-center gap-3`}
      >
        <span className="font-bold uppercase tracking-wide">
          {compact ? 'KILL SWITCH ON' : 'KILL SWITCH ACTIVE'}
        </span>
        {health.kill_switch_activated_at && (
          <span className="opacity-75 text-sm">
            Activated: {new Date(health.kill_switch_activated_at).toLocaleString()}
          </span>
        )}
      </div>
    );
  }

  if (!compact) {
    return (
      <div className="w-full bg-green-600 text-white px-6 py-3 flex items-center gap-3">
        <span className="font-medium">System running normally — Kill switch INACTIVE</span>
      </div>
    );
  }

  return null;
}
