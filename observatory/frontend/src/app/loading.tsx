export default function Loading() {
  return (
    <div className="px-6 py-6 space-y-6 animate-pulse">
      {/* Page heading skeleton */}
      <div>
        <div className="h-7 bg-gray-200 dark:bg-gray-800 rounded w-40" />
        <div className="h-4 bg-gray-100 dark:bg-gray-850 rounded w-72 mt-2" />
      </div>

      {/* Health banner skeleton */}
      <div className="h-12 bg-gray-100 dark:bg-gray-800 rounded-xl" />

      {/* KPI cards skeleton */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="border border-gray-200 dark:border-gray-800 rounded-xl p-5 bg-white dark:bg-gray-950">
            <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-24 mb-3" />
            <div className="h-7 bg-gray-200 dark:bg-gray-800 rounded w-16" />
          </div>
        ))}
      </div>

      {/* Agent grid skeleton */}
      <div>
        <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-28 mb-3" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="border border-gray-200 dark:border-gray-800 rounded-xl p-4 bg-white dark:bg-gray-950">
              <div className="flex justify-between mb-3">
                <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-28" />
                <div className="h-5 bg-gray-100 dark:bg-gray-800 rounded-full w-14" />
              </div>
              <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-36 mb-2" />
              <div className="h-5 bg-gray-100 dark:bg-gray-800 rounded w-16 mt-3" />
            </div>
          ))}
        </div>
      </div>

      {/* Trajectory skeleton */}
      <div className="border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-32" />
        </div>
        <div className="space-y-0">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="px-5 py-3 flex gap-3">
              <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-16 mt-1" />
              <div className="flex-1">
                <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded w-48" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
