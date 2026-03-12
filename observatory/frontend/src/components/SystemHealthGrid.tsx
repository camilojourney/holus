import type { ServiceStatus } from '@/lib/types';

interface Props {
  services: ServiceStatus[];
}

const statusColors = {
  up: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  down: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  degraded: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
};

export default function SystemHealthGrid({ services }: Props) {
  if (services.length === 0) {
    return (
      <p className="text-sm text-gray-400 dark:text-gray-600 text-center py-8">
        No service data available
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {services.map((svc) => (
        <div
          key={svc.name}
          className="border border-gray-200 dark:border-gray-800 rounded-xl p-4 bg-white dark:bg-gray-950"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium text-gray-900 dark:text-white text-sm">{svc.name}</h3>
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[svc.status]}`}
            >
              {svc.status}
            </span>
          </div>
          {svc.latency_ms !== undefined && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Latency: {svc.latency_ms}ms
            </p>
          )}
          <p className="text-xs text-gray-400 dark:text-gray-600 mt-1">
            Checked: {new Date(svc.last_checked).toLocaleTimeString()}
          </p>
        </div>
      ))}
    </div>
  );
}
