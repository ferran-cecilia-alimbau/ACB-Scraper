import { cn } from '@/lib/cn';

interface StatItem {
  label: string;
  value: string | number;
  /** Texto pequeño debajo del valor (ej: "+1.4 vs media"). */
  hint?: string;
  /** Tono opcional en `hint`: positivo/negativo/neutro. */
  tone?: 'positive' | 'negative' | 'neutral';
}

interface StatGridProps {
  items: StatItem[];
  /** Columnas en desktop. Mobile siempre 2. Default 4. */
  cols?: 2 | 3 | 4 | 5 | 6;
  className?: string;
}

const COL_CLASS: Record<number, string> = {
  2: 'sm:grid-cols-2',
  3: 'sm:grid-cols-3',
  4: 'sm:grid-cols-4',
  5: 'sm:grid-cols-5',
  6: 'sm:grid-cols-6',
};

const TONE_CLASS = {
  positive: 'text-[var(--positive)]',
  negative: 'text-[var(--negative)]',
  neutral: 'text-[var(--ink-muted)]',
} as const;

/**
 * Grid editorial compacto para mostrar métricas principales. Cada celda:
 * label arriba (kicker), valor en mono grande, hint opcional abajo.
 * Se usa en cabecera de jugador/equipo y en bloques de splits.
 */
export function StatGrid({ items, cols = 4, className }: StatGridProps) {
  return (
    <dl
      className={cn(
        'grid grid-cols-2 gap-x-6 gap-y-5 border-t border-[var(--rule)] pt-5',
        COL_CLASS[cols],
        className,
      )}
    >
      {items.map((it) => (
        <div key={it.label} className="flex flex-col">
          <dt className="kicker text-[0.7rem] text-[var(--ink-muted)] mb-1.5">{it.label}</dt>
          <dd className="font-mono tabular-nums text-2xl text-[var(--ink)] leading-none">
            {it.value}
          </dd>
          {it.hint && (
            <span
              className={cn(
                'mt-1.5 text-[0.7rem] uppercase tracking-wide',
                TONE_CLASS[it.tone ?? 'neutral'],
              )}
            >
              {it.hint}
            </span>
          )}
        </div>
      ))}
    </dl>
  );
}
