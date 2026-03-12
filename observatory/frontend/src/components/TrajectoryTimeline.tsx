'use client';

import { useTrajectoryStream } from '@/lib/sse';

export default function TrajectoryTimeline() {
  const { events, connected } = useTrajectoryStream();

  return (
    <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
        <h2 className="font-semibold text-gray-900 dark:text-white text-sm">Live Trajectory</h2>
        <span
          className={`flex items-center gap-1.5 text-xs font-medium ${
            connected
              ? 'text-green-600 dark:text-green-400'
              : 'text-gray-400 dark:text-gray-600'
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}
          />
          {connected ? 'Live' : 'Disconnected'}
        </span>
      </div>
      <div className="divide-y divide-gray-50 dark:divide-gray-900 max-h-80 overflow-y-auto">
        {events.length === 0 ? (
          <p className="text-sm text-gray-400 dark:text-gray-600 px-5 py-6 text-center">
            {connected ? 'Waiting for events...' : 'Connecting to event stream...'}
          </p>
        ) : (
          events.map((ev) => (
            <div key={ev.id} className="px-5 py-3 flex items-start gap-3">
              <div className="shrink-0 mt-0.5">
                <span className="text-xs text-gray-400 dark:text-gray-600 font-mono">
                  {new Date(ev.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 mr-2">
                  {ev.agent_name}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded mr-2">
                  {ev.event_type}
                </span>
                <span className="text-xs text-gray-700 dark:text-gray-300">{ev.description}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
