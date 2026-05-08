import Link from 'next/link';
import { cn } from '@/lib/cn';

interface RecentFormGame {
  id_partido: number;
  jornada_num: number;
  oponente: string;
  es_local: boolean;
  resultado_propio: number;
  resultado_rival: number;
}

interface RecentFormStripProps {
  games: RecentFormGame[];
  className?: string;
}

/**
 * Tira horizontal con los últimos N partidos. Cada cuadrado muestra W/L
 * con el diferencial debajo. Hover muestra rival y marcador.
 */
export function RecentFormStrip({ games, className }: RecentFormStripProps) {
  if (!games.length) {
    return (
      <p className={cn('text-sm text-[var(--ink-soft)] italic', className)}>
        Sin partidos recientes.
      </p>
    );
  }
  return (
    <ol className={cn('flex flex-wrap gap-1.5', className)} aria-label="Forma reciente">
      {games.map((g) => {
        const won = g.resultado_propio > g.resultado_rival;
        const diff = g.resultado_propio - g.resultado_rival;
        return (
          <li key={g.id_partido}>
            <Link
              href={`/partido/${g.id_partido}`}
              className={cn(
                'flex flex-col items-center justify-center w-9 h-12 border text-center transition-colors',
                won
                  ? 'border-[var(--accent)] text-[var(--ink)]'
                  : 'border-[var(--rule)] text-[var(--ink-muted)]',
              )}
              title={`J${g.jornada_num} ${g.es_local ? 'vs' : '@'} ${g.oponente} · ${g.resultado_propio}–${g.resultado_rival}`}
            >
              <span className="font-mono text-sm leading-none font-semibold">
                {won ? 'V' : 'D'}
              </span>
              <span
                className={cn(
                  'font-mono text-[0.65rem] mt-0.5',
                  won ? 'text-[var(--positive)]' : 'text-[var(--negative)]',
                )}
              >
                {diff > 0 ? `+${diff}` : diff}
              </span>
            </Link>
          </li>
        );
      })}
    </ol>
  );
}
