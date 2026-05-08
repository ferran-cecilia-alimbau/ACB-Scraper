'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { teamMeta } from '@/lib/teams';
import type { PlayerSearchResult } from '@/lib/api';
import { cn } from '@/lib/cn';

interface TeamHit {
  type: 'team';
  slug: string;
  name: string;
}
interface PlayerHit {
  type: 'player';
  data: PlayerSearchResult;
}
type Hit = TeamHit | PlayerHit;

interface Props {
  /** Equipos disponibles para sugerir cuando el query coincide. */
  teams: { name: string; slug: string }[];
}

/**
 * Cmd-K / Ctrl-K para búsqueda global.
 * - Atajos: Cmd-K (Mac) / Ctrl-K (Win/Linux), también "/" si no hay foco en input.
 * - Esc: cerrar.
 * - Flechas + Enter: navegar y abrir.
 */
export function CommandPalette({ teams }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<Hit[]>([]);
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  // Atajos globales
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const isInput =
        document.activeElement instanceof HTMLInputElement ||
        document.activeElement instanceof HTMLTextAreaElement ||
        (document.activeElement as HTMLElement | null)?.isContentEditable;
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
        return;
      }
      if (e.key === '/' && !isInput && !open) {
        e.preventDefault();
        setOpen(true);
        return;
      }
      if (e.key === 'Escape' && open) setOpen(false);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  // Foco al abrir
  useEffect(() => {
    if (open) {
      setQuery('');
      setHits([]);
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Búsqueda con debounce ligero
  useEffect(() => {
    if (!open) return;
    const q = query.trim();
    if (!q) {
      setHits([]);
      return;
    }
    const lower = q.toLowerCase();
    const teamHits: TeamHit[] = teams
      .filter((t) => t.name.toLowerCase().includes(lower))
      .slice(0, 5)
      .map((t) => ({ type: 'team', slug: t.slug, name: t.name }));

    const handle = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/players/search?q=${encodeURIComponent(q)}`);
        const data: PlayerSearchResult[] = res.ok ? await res.json() : [];
        const playerHits: PlayerHit[] = data.map((p) => ({ type: 'player', data: p }));
        setHits([...teamHits, ...playerHits]);
        setActive(0);
      } catch {
        setHits(teamHits);
      } finally {
        setLoading(false);
      }
    }, 120);
    return () => clearTimeout(handle);
  }, [query, open, teams]);

  const navigate = useCallback(
    (hit: Hit) => {
      if (hit.type === 'player') router.push(`/jugador/${hit.data.player_id}`);
      // Equipos aún no tienen página propia: redirigir a /jugadores filtrado.
      else router.push(`/jugadores?team=${encodeURIComponent(hit.name)}`);
      setOpen(false);
    },
    [router],
  );

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, hits.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const hit = hits[active];
      if (hit) navigate(hit);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)] border border-[var(--rule)] hover:border-[var(--rule-strong)] hover:text-[var(--ink)] transition-colors"
        aria-label="Buscar jugador o equipo"
      >
        <span aria-hidden>⌕</span>
        <span>Buscar</span>
        <kbd className="font-mono text-[0.65rem] px-1 py-0.5 border border-[var(--rule)] ml-2">
          ⌘ K
        </kbd>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4"
          onClick={() => setOpen(false)}
        >
          <div className="absolute inset-0 bg-[var(--ink)] opacity-30" aria-hidden />
          <div
            className="relative w-full max-w-xl bg-[var(--bg-elev)] border border-[var(--rule-strong)] shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-[var(--rule)] px-4 py-3">
              <span className="text-[var(--ink-muted)]" aria-hidden>
                ⌕
              </span>
              <input
                ref={inputRef}
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Buscar jugador o equipo…"
                className="flex-1 bg-transparent text-[var(--ink)] placeholder:text-[var(--ink-soft)] outline-none text-base"
              />
              <kbd className="font-mono text-[0.65rem] px-1 py-0.5 border border-[var(--rule)] text-[var(--ink-muted)]">
                ESC
              </kbd>
            </div>
            <div className="max-h-[50vh] overflow-y-auto">
              {!query.trim() && (
                <p className="px-4 py-6 text-sm text-[var(--ink-muted)] italic">
                  Escribe el nombre de un jugador o equipo. Atajo: ⌘K / Ctrl-K.
                </p>
              )}
              {query.trim() && !loading && hits.length === 0 && (
                <p className="px-4 py-6 text-sm text-[var(--ink-muted)] italic">
                  Sin resultados.
                </p>
              )}
              <ul role="listbox">
                {hits.map((hit, i) => {
                  const isActive = i === active;
                  if (hit.type === 'team') {
                    return (
                      <li
                        key={`team-${hit.slug}`}
                        role="option"
                        aria-selected={isActive}
                        onMouseEnter={() => setActive(i)}
                        onClick={() => navigate(hit)}
                        className={cn(
                          'cursor-pointer px-4 py-2.5 flex items-baseline gap-3 border-t border-[var(--rule)]',
                          isActive && 'bg-[color-mix(in_srgb,var(--accent)_8%,transparent)]',
                        )}
                      >
                        <span className="text-[0.65rem] uppercase tracking-[0.18em] text-[var(--ink-muted)] w-12 shrink-0">
                          equipo
                        </span>
                        <span className="text-sm">{hit.name}</span>
                      </li>
                    );
                  }
                  const meta = teamMeta(hit.data.equipo);
                  return (
                    <li
                      key={`player-${hit.data.player_id}`}
                      role="option"
                      aria-selected={isActive}
                      onMouseEnter={() => setActive(i)}
                      onClick={() => navigate(hit)}
                      className={cn(
                        'cursor-pointer px-4 py-2.5 flex items-baseline justify-between gap-3 border-t border-[var(--rule)]',
                        isActive && 'bg-[color-mix(in_srgb,var(--accent)_8%,transparent)]',
                      )}
                    >
                      <div className="flex items-baseline gap-3 min-w-0">
                        <span className="text-[0.65rem] uppercase tracking-[0.18em] text-[var(--ink-muted)] w-12 shrink-0">
                          jugador
                        </span>
                        <span className="text-sm truncate">{hit.data.nombre}</span>
                        <span className="text-[0.7rem] uppercase tracking-wider text-[var(--ink-muted)] truncate">
                          {meta.short}
                        </span>
                      </div>
                      <span className="font-mono tabular-nums text-xs text-[var(--ink-muted)] shrink-0">
                        {hit.data.valoracion_avg.toFixed(1)} VAL
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
