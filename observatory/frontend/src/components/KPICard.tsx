interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  tooltip?: string;
  color?: 'default' | 'green' | 'yellow' | 'red' | 'blue';
  staggerIndex?: number;
}

const accentMap = {
  default: 'var(--text-primary)',
  green: 'var(--success)',
  yellow: 'var(--warning)',
  red: 'var(--danger)',
  blue: 'var(--info)',
};

const borderMap = {
  default: 'var(--border-default)',
  green: 'var(--success)',
  yellow: 'var(--warning)',
  red: 'var(--danger)',
  blue: 'var(--info)',
};

export default function KPICard({ title, value, subtitle, tooltip, color = 'default', staggerIndex }: Props) {
  const staggerClass = staggerIndex !== undefined ? `stagger-${staggerIndex}` : '';
  return (
    <div
      className={`card animate-fade-in ${staggerClass} ${tooltip ? 'kpi-tooltip' : ''}`}
      style={{
        borderTop: `3px solid ${borderMap[color]}`,
      }}
    >
      {tooltip && (
        <div className="kpi-tooltip-content">
          {tooltip}
        </div>
      )}
      <h3
        className="text-[0.625rem] font-medium uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-tertiary)', letterSpacing: '0.08em' }}
      >
        {title}
      </h3>
      <p
        className="text-3xl font-extrabold tracking-tight leading-none"
        style={{ color: accentMap[color] }}
      >
        {value}
      </p>
      {subtitle && (
        <p className="text-[0.6875rem] mt-1.5 font-medium" style={{ color: 'var(--text-tertiary)' }}>{subtitle}</p>
      )}
    </div>
  );
}
