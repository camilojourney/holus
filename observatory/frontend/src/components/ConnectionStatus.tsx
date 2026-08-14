'use client';

import { resolveConnection, type ConnectionState } from '@/lib/connection';

interface Props {
  state?: ConnectionState;
}

export default function ConnectionStatus({ state }: Props) {
  const connection = state ?? resolveConnection();
  const tone =
    connection.kind === 'local_dev'
      ? { bg: 'var(--success-subtle)', fg: 'var(--success)', dot: 'var(--success)' }
      : { bg: 'var(--warning-subtle)', fg: 'var(--warning)', dot: 'var(--warning)' };

  return (
    <div
      role="status"
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
      style={{ background: tone.bg, color: tone.fg }}
      data-connection-kind={connection.kind}
    >
      <span
        className="status-dot"
        style={{ background: tone.dot }}
        aria-hidden="true"
      />
      {connection.label}
    </div>
  );
}
