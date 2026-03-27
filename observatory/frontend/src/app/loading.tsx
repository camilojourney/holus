export default function Loading() {
  return (
    <div className="px-6 py-6 space-y-6">
      {/* Page heading skeleton */}
      <div>
        <div className="skeleton h-7 w-40" />
        <div className="skeleton h-4 w-72 mt-2" />
      </div>

      {/* Health banner skeleton */}
      <div className="skeleton h-12 rounded-xl" />

      {/* KPI cards skeleton */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="skeleton-card p-5">
            <div className="skeleton h-3 w-24 mb-3" />
            <div className="skeleton h-7 w-16" />
          </div>
        ))}
      </div>

      {/* Agent grid skeleton */}
      <div>
        <div className="skeleton h-4 w-28 mb-3" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton-card p-4">
              <div className="flex justify-between mb-3">
                <div className="skeleton h-4 w-28" />
                <div className="skeleton h-5 w-14 rounded-full" />
              </div>
              <div className="skeleton h-3 w-36 mb-2" />
              <div className="skeleton h-5 w-16 mt-3" />
            </div>
          ))}
        </div>
      </div>

      {/* Trajectory skeleton */}
      <div className="skeleton-card">
        <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="skeleton h-4 w-32" />
        </div>
        <div className="space-y-0">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="px-5 py-3 flex gap-3">
              <div className="skeleton h-3 w-16 mt-1" />
              <div className="flex-1">
                <div className="skeleton h-3 w-48" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
