interface Props {
  message?: string;
}

export default function ErrorBanner({ message }: Props) {
  return (
    <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950 px-5 py-4">
      <p className="text-sm font-medium text-red-700 dark:text-red-300">
        Service unavailable
      </p>
      {message && (
        <p className="text-xs text-red-500 dark:text-red-400 mt-1">{message}</p>
      )}
      <p className="text-xs text-red-400 dark:text-red-600 mt-1">
        Check that the Observatory API is running at{' '}
        {process.env.NEXT_PUBLIC_OBSERVATORY_URL || 'http://localhost:8001'}
      </p>
    </div>
  );
}
