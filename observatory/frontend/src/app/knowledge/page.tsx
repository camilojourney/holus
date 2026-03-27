import { fetchKnowledge, fetchMemoryContent, fetchLessons } from '@/lib/api';
import FreshnessIndicator from '@/components/FreshnessIndicator';
import ErrorBanner from '@/components/ErrorBanner';
import type { KnowledgeFile, MemoryContent, LessonsResponse } from '@/lib/types';

export const revalidate = 30;

export default async function KnowledgePage() {
  let files: KnowledgeFile[] = [];
  let memory: MemoryContent | null = null;
  let lessonsData: LessonsResponse | null = null;
  let error = false;

  try {
    [files, memory, lessonsData] = await Promise.all([
      fetchKnowledge(),
      fetchMemoryContent(),
      fetchLessons(20),
    ]);
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

          {/* System Memory (MEMORY.md) */}
          {memory?.content && (
            <div className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-white dark:bg-gray-950">
              <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
                <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm">
                  System Memory
                </h2>
                <span className="text-xs text-gray-400 dark:text-gray-400">
                  {new Date(memory.last_modified).toLocaleDateString()}
                </span>
              </div>
              <div className="px-5 py-4">
                <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
                  {memory.content}
                </pre>
              </div>
            </div>
          )}

          {/* Recent Lessons */}
          {lessonsData && lessonsData.lessons.length > 0 && (
            <div className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-white dark:bg-gray-950">
              <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
                <h2 className="font-semibold text-gray-800 dark:text-gray-200 text-sm">
                  Recent Lessons ({lessonsData.total} total)
                </h2>
              </div>
              <div className="divide-y divide-gray-50 dark:divide-gray-900">
                {lessonsData.lessons.map((lesson) => (
                  <div
                    key={lesson.id}
                    className="px-5 py-3 hover:bg-gray-50 dark:hover:bg-gray-900"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-900 dark:text-white">
                          {lesson.lesson}
                        </p>
                        <div className="flex items-center gap-3 mt-1.5">
                          {lesson.date && (
                            <span className="text-xs text-gray-400 dark:text-gray-400">
                              {lesson.date}
                            </span>
                          )}
                          {lesson.agent_id && (
                            <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                              {lesson.agent_id}
                            </span>
                          )}
                          {lesson.category && (
                            <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400">
                              {lesson.category}
                            </span>
                          )}
                          {lesson.source && (
                            <span className="text-xs text-gray-400 dark:text-gray-400">
                              via {lesson.source.replace(/_/g, ' ')}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
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
              <p className="text-sm text-gray-400 dark:text-gray-400 px-5 py-6 text-center">
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
                        <p className="text-xs text-gray-400 dark:text-gray-400 truncate">
                          {file.path}
                        </p>
                      </div>
                      <FreshnessIndicator
                        freshness={file.freshness}
                        modifiedAt={file.modified_at}
                      />
                      <span className="text-xs text-gray-400 dark:text-gray-400 whitespace-nowrap">
                        {new Date(file.modified_at).toLocaleDateString()}
                      </span>
                      <span className="text-xs text-gray-400 dark:text-gray-400 whitespace-nowrap">
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
