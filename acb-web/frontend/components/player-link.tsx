import Link from 'next/link';
import { cn } from '@/lib/cn';
import { teamMeta } from '@/lib/teams';

interface PlayerLinkProps {
  id: number | string;
  nombre: string;
  equipo: string;
  posicion?: string;
  className?: string;
  /** Renderizar sin link (útil dentro de tablas con TR clickeables). */
  asText?: boolean;
}

/**
 * Componente sobrio que une nombre de jugador + acento de equipo + posición
 * opcional. Naranja sólo en el guión separador para jerarquía visual.
 */
export function PlayerLink({
  id,
  nombre,
  equipo,
  posicion,
  className,
  asText = false,
}: PlayerLinkProps) {
  const meta = teamMeta(equipo);

  const inner = (
    <span className={cn('inline-flex items-baseline gap-2 min-w-0', className)}>
      <span className="font-medium truncate text-[var(--ink)]">{nombre}</span>
      <span className="text-[0.7rem] text-[var(--ink-muted)] uppercase tracking-wider whitespace-nowrap">
        {meta.short}
        {posicion ? ` · ${posicion}` : ''}
      </span>
    </span>
  );

  if (asText) return inner;
  return (
    <Link href={`/jugador/${id}`} className="link-underline">
      {inner}
    </Link>
  );
}
