import { fetchKnowledge, fetchMemoryContent, fetchLessons } from '@/lib/api';
import FreshnessIndicator from '@/components/FreshnessIndicator';
import ErrorBanner from '@/components/ErrorBanner';
import HoverRow from '@/components/HoverRow';
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
    <div className="px-6 py-6 space-y-6 page-transition">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Knowledge Graph</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          Learned patterns, strategy memory, and extracted lessons from evaluation cycles
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
                  className="rounded-xl px-4 py-3"
                  style={{
                    border: '1px solid var(--border-default)',
                    background: 'var(--surface-raised)',
                  }}
                >
                  <p className="text-xs capitalize" style={{ color: 'var(--text-tertiary)' }}>{status}</p>
                  <p className="text-xl font-bold mt-1" style={{ color: 'var(--text-primary)' }}>{count}</p>
                </div>
              ))}
            </div>
          )}

          {/* System Memory (MEMORY.md) */}
          {memory?.content && (
            <div
              className="rounded-xl overflow-hidden"
              style={{
                border: '1px solid var(--border-default)',
                background: 'var(--surface-raised)',
              }}
            >
              <div
                className="px-5 py-4 flex items-center justify-between"
                style={{ borderBottom: '1px solid var(--border-subtle)' }}
              >
                <h2 className="font-semibold text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Strategy Memory (MEMORY.md)
                </h2>
                <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  {new Date(memory.last_modified).toLocaleDateString()}
                </span>
              </div>
              <div className="px-5 py-4">
                <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                  {memory.content}
                </pre>
              </div>
            </div>
          )}

          {/* Recent Lessons */}
          {lessonsData && lessonsData.lessons.length > 0 && (
            <div
              className="rounded-xl overflow-hidden"
              style={{
                border: '1px solid var(--border-default)',
                background: 'var(--surface-raised)',
              }}
            >
              <div
                className="px-5 py-4 flex items-center justify-between"
                style={{ borderBottom: '1px solid var(--border-subtle)' }}
              >
                <h2 className="font-semibold text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Extracted Lessons ({lessonsData.total} total)
                </h2>
              </div>
              <div>
                {lessonsData.lessons.map((lesson, idx) => (
                  <div
                    key={lesson.id}
                    className="px-5 py-3 transition-colors"
                    style={{
                      borderBottom: idx < lessonsData.lessons.length - 1 ? '1px solid var(--border-subtle)' : undefined,
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm" style={{ color: 'var(--text-primary)' }}>
                          {lesson.lesson}
                        </p>
                        <div className="flex items-center gap-3 mt-1.5">
                          {lesson.date && (
                            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                              {lesson.date}
                            </span>
                          )}
                          {lesson.agent_id && (
                            <span
                              className="text-xs px-1.5 py-0.5 rounded"
                              style={{
                                background: 'var(--surface-2)',
                                color: 'var(--text-tertiary)',
                              }}
                            >
                              {lesson.agent_id}
                            </span>
                          )}
                          {lesson.category && (
                            <span className="text-xs px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-950 text-amber-600 dark:text-amber-400">
                              {lesson.category}
                            </span>
                          )}
                          {lesson.source && (
                            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
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
          <div
            className="rounded-xl overflow-hidden"
            style={{
              border: '1px solid var(--border-default)',
              background: 'var(--surface-raised)',
            }}
          >
            <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <h2 className="font-semibold text-sm" style={{ color: 'var(--text-secondary)' }}>
                Files ({files.length})
              </h2>
            </div>

            {files.length === 0 ? (
              <p className="text-sm px-5 py-6 text-center" style={{ color: 'var(--text-tertiary)' }}>
                Awaiting market signals -- no knowledge files indexed yet.
              </p>
            ) : (
              <div>
                {files
                  .slice()
                  .sort(
                    (a, b) =>
                      new Date(b.modified_at).getTime() - new Date(a.modified_at).getTime()
                  )
                  .map((file, idx) => (
                    <div
                      key={file.path}
                      className="flex items-center gap-4 px-5 py-3 transition-colors"
                      style={{
                        borderBottom: idx < files.length - 1 ? '1px solid var(--border-subtle)' : undefined,
                      }}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                          {file.name}
                        </p>
                        <p className="text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>
                          {file.path}
                        </p>
                      </div>
                      <FreshnessIndicator
                        freshness={file.freshness}
                        modifiedAt={file.modified_at}
                      />
                      <span className="text-xs whitespace-nowrap" style={{ color: 'var(--text-tertiary)' }}>
                        {new Date(file.modified_at).toLocaleDateString()}
                      </span>
                      <span className="text-xs whitespace-nowrap" style={{ color: 'var(--text-tertiary)' }}>
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
