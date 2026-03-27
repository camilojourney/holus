/**
 * Holus Logo Mark
 *
 * A concentric-rings mark representing the federated agent orchestration:
 * outer ring = observe, middle ring = reason, inner core = act.
 * Uses brand-visual.yaml colors via CSS custom properties.
 */

interface Props {
  size?: number;
  className?: string;
}

export default function HolusLogo({ size = 32, className = '' }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Holus logo"
      role="img"
    >
      {/* Outer ring — observe */}
      <circle
        cx="16"
        cy="16"
        r="14"
        stroke="var(--brand-accent, #FBBF24)"
        strokeWidth="1.5"
        strokeDasharray="4 3"
        opacity="0.6"
      />
      {/* Middle ring — reason */}
      <circle
        cx="16"
        cy="16"
        r="10"
        stroke="var(--brand, #F59E0B)"
        strokeWidth="2"
        opacity="0.85"
      />
      {/* Inner core — act */}
      <circle
        cx="16"
        cy="16"
        r="5"
        fill="var(--brand, #F59E0B)"
      />
      {/* Center highlight */}
      <circle
        cx="16"
        cy="16"
        r="2"
        fill="var(--text-inverse, #ffffff)"
        opacity="0.9"
      />
    </svg>
  );
}
