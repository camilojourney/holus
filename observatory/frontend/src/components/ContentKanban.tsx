import type { ContentItem, ContentState } from '@/lib/types';

const COLUMNS: ContentState[] = ['DRAFT', 'REVIEW', 'PUBLISHED'];

const pillarColors = {
  authority: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  entertainment: 'bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-300',
  education: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  conversion: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
};

const columnColors: Record<ContentState, string> = {
  DRAFT: 'text-gray-600 dark:text-gray-400',
  REVIEW: 'text-yellow-700 dark:text-yellow-400',
  PUBLISHED: 'text-green-700 dark:text-green-400',
};

interface Props {
  items: ContentItem[];
}

export default function ContentKanban({ items }: Props) {
  const grouped: Record<ContentState, ContentItem[]> = {
    DRAFT: [],
    REVIEW: [],
    PUBLISHED: [],
  };
  for (const item of items) {
    if (grouped[item.state]) {
      grouped[item.state].push(item);
    }
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {COLUMNS.map((state) => (
        <div
          key={state}
          className="border border-gray-200 dark:border-gray-800 rounded-xl bg-gray-50 dark:bg-gray-900"
        >
          <div className={`px-4 py-3 border-b border-gray-200 dark:border-gray-800 font-semibold text-sm ${columnColors[state]}`}>
            {state}
            <span className="ml-2 text-xs font-normal text-gray-400 dark:text-gray-600">
              ({grouped[state].length})
            </span>
          </div>
          <div className="p-3 space-y-2 min-h-24">
            {grouped[state].length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-gray-600 text-center py-4">
                Empty
              </p>
            ) : (
              grouped[state].map((item) => (
                <div
                  key={item.id}
                  className="bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-lg p-3"
                >
                  <p className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2">
                    {item.title}
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                        pillarColors[item.pillar] ?? 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {item.pillar}
                    </span>
                    <span className="text-xs text-gray-400 dark:text-gray-600">
                      {item.platform}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
