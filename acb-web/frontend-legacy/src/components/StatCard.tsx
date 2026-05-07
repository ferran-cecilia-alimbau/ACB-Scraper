interface StatCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  accentColor?: string;
}

export function StatCard({ label, value, subtitle, accentColor = 'var(--color-accent)' }: StatCardProps) {
  return (
    <div
      className="rounded-lg bg-bg-card border border-border p-4 transition-colors duration-150 hover:bg-bg-hover"
      style={{ borderLeftWidth: 3, borderLeftColor: accentColor }}
    >
      <p className="text-xs font-medium uppercase tracking-wider text-text-secondary">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
      {subtitle && <p className="mt-0.5 text-xs text-text-secondary">{subtitle}</p>}
    </div>
  );
}
