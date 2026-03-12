import { fetchKnowledge } from '@/lib/api';
import FreshnessIndicator from '@/components/FreshnessIndicator';
import ErrorBanner from '@/components/ErrorBanner';
import type { KnowledgeFile } from '@/lib/types';

export const revalidate = 30;

export default async function KnowledgePage() {
  let files: KnowledgeFile[] = [];
  let error = false;

  try {
    files = await fetchKnowledge();
  } catch {
    error = true;
  }

  const byFreshness = {
    fresh: files.filter((f) => f.freshness === 'fresh').length,
    aging: files.filter((f) => f.freshness === 'aging').length,
    stale: files.filter((f) => f.freshness === 'stale').length,
  };

  return (
    <div className="px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Knowledge</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Self-improvement memory, decisions, and lessons
        </p>
      </div>

      {error && <ErrorBanner message="Could not load knowledge files" />}

      {!error && (
        <>
          {/* Freshness summary */}
          {files.length > 0 && (
            <div className="flex gap-4">
              {Object.entries(byFreshness).map(([status, count]) => (
                <div
                  key={status}
                  className="border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-3 bg-white dark:bg-gray-950"
                >
                  <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{status}</p>
                  <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">{count}</p>
                </div>
              ))}
            </div>
          )}

          {/* File browser */}
          <div className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-white dark:bg-gray-950">
            <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
              <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm">
                Files ({files.length})
              </h2>
            </div>

            {files.length === 0 ? (
              <p className="text-sm text-gray-400 dark:text-gray-600 px-5 py-6 text-center">
                No knowledge files indexed.
              </p>
            ) : (
              <div className="divide-y divide-gray-50 dark:divide-gray-900">
                {files
                  .slice()
                  .sort(
                    (a, b) =>
                      new Date(b.modified_at).getTime() - new Date(a.modified_at).getTime()
                  )
                  .map((file) => (
                    <div
                      key={file.path}
                      className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 dark:hover:bg-gray-900"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {file.name}
                        </p>
                        <p className="text-xs text-gray-400 dark:text-gray-600 truncate">
                          {file.path}
                        </p>
                      </div>
                      <FreshnessIndicator
                        freshness={file.freshness}
                        modifiedAt={file.modified_at}
                      />
                      <span className="text-xs text-gray-400 dark:text-gray-600 whitespace-nowrap">
                        {new Date(file.modified_at).toLocaleDateString()}
                      </span>
                      <span className="text-xs text-gray-400 dark:text-gray-600 whitespace-nowrap">
                        {(file.size_bytes / 1024).toFixed(1)}KB
                      </span>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
