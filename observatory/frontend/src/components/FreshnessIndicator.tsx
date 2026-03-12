import type { FreshnessStatus } from '@/lib/types';

interface Props {
  freshness: FreshnessStatus;
  modifiedAt?: string;
}

const dotColor: Record<FreshnessStatus, string> = {
  fresh: 'bg-green-500',
  aging: 'bg-yellow-500',
  stale: 'bg-red-500',
};

const labelColor: Record<FreshnessStatus, string> = {
  fresh: 'text-green-600 dark:text-green-400',
  aging: 'text-yellow-600 dark:text-yellow-400',
  stale: 'text-red-600 dark:text-red-400',
};

export default function FreshnessIndicator({ freshness, modifiedAt }: Props) {
  const tooltip = modifiedAt
    ? `Last modified: ${new Date(modifiedAt).toLocaleString()}`
    : freshness;

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-medium ${labelColor[freshness]}`}
      title={tooltip}
    >
      <span className={`w-2 h-2 rounded-full ${dotColor[freshness]}`} />
      {freshness}
    </span>
  );
}
