import { cn } from '@/lib/cn';

interface PercentileBarProps {
  /** Percentil 0–100; null si no aplica (jugador no cumple mínimos). */
  percentile: number | null;
  /** Texto a la izquierda (nombre de la métrica). */
  label: string;
  /** Valor formateado a la derecha (ej: "18.4", "57.2%"). */
  value: string | number;
  /** Posición opcional en la liga (ej: "8º de 223"). */
  rank?: string;
  className?: string;
}

/**
 * Barra horizontal de percentil — el patrón único para visualizar
 * "ranking relativo" en toda la web. Si no hay percentil válido (jugador
 * no llega a mínimos), se muestra atenuado sin barra.
 */
export function PercentileBar({
  percentile,
  label,
  value,
  rank,
  className,
}: PercentileBarProps) {
  const hasPct = percentile != null && Number.isFinite(percentile);
  const pct = hasPct ? Math.max(0, Math.min(100, percentile!)) : 0;
  const tone =
    pct >= 80 ? 'bg-[var(--accent)]' : pct >= 50 ? 'bg-[var(--ink)]' : 'bg-[var(--ink-muted)]';

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="text-[var(--ink-muted)]">{label}</span>
        <span className="font-mono tabular-nums font-medium text-[var(--ink)]">{value}</span>
      </div>
      {hasPct ? (
        <>
          <div className="relative h-1 bg-[var(--rule)] overflow-hidden">
            <div
              className={cn('absolute inset-y-0 left-0 transition-[width]', tone)}
              style={{ width: `${pct}%` }}
              aria-hidden
            />
          </div>
          <div className="flex items-baseline justify-between gap-2 text-[0.7rem] text-[var(--ink-muted)] font-mono uppercase tracking-wider">
            <span>p{Math.round(pct)}</span>
            {rank && <span>{rank}</span>}
          </div>
        </>
      ) : (
        <div className="text-[0.7rem] text-[var(--ink-soft)] italic">
          minutos insuficientes para percentil
        </div>
      )}
    </div>
  );
}
