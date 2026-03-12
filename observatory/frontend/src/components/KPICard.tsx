interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: 'default' | 'green' | 'yellow' | 'red' | 'blue';
}

const colorMap = {
  default: 'text-gray-900 dark:text-white',
  green: 'text-green-600 dark:text-green-400',
  yellow: 'text-yellow-600 dark:text-yellow-400',
  red: 'text-red-600 dark:text-red-400',
  blue: 'text-blue-600 dark:text-blue-400',
};

export default function KPICard({ title, value, subtitle, color = 'default' }: Props) {
  return (
    <div className="border border-gray-200 dark:border-gray-800 rounded-xl p-5 bg-white dark:bg-gray-950">
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
        {title}
      </p>
      <p className={`text-2xl font-bold ${colorMap[color]}`}>{value}</p>
      {subtitle && (
        <p className="text-xs text-gray-400 dark:text-gray-600 mt-1">{subtitle}</p>
      )}
    </div>
  );
}
