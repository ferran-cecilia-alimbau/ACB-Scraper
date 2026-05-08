'use client';

/**
 * Cliente de la página /jugadores.
 *
 * Pilares:
 *  - Vistas no negociables (cada una ≤10 columnas) que cambian las columnas
 *    visibles de golpe, evitando dashboards de 25 columnas.
 *  - Filtros: búsqueda libre, equipo, posición, mínimo de partidos y minutos.
 *  - Mobile (<768px): la tabla se renderiza como tarjetas apiladas con la
 *    métrica destacada de la vista actual.
 */

import { useMemo, useState } from 'react';
import Link from 'next/link';
import type { PlayerSummary } from '@/lib/api';
import { MetricTable, type MetricColumn } from '@/components/metric-table';
import { PlayerLink } from '@/components/player-link';
import { teamMeta } from '@/lib/teams';
import { cn } from '@/lib/cn';

type ViewKey = 'medias' | 'eficiencia' | 'per36' | 'totales';

interface View {
  key: ViewKey;
  label: string;
  description: string;
  /** Columna que se muestra como métrica grande en mobile cards. */
  highlight: { key: keyof PlayerSummary; label: string; suffix?: string };
}

const VIEWS: View[] = [
  {
    key: 'medias',
    label: 'Medias',
    description: 'Promedios por partido — el lenguaje natural del aficionado.',
    highlight: { key: 'puntos_avg', label: 'PTS' },
  },
  {
    key: 'eficiencia',
    label: 'Eficiencia',
    description: 'Tiro y eficiencia — qué bien tiran los jugadores.',
    highlight: { key: 'ts_pct', label: 'TS%', suffix: '%' },
  },
  {
    key: 'per36',
    label: 'Per 36',
    description: 'Producción extrapolada a 36 minutos — útil para contextualizar a sextos hombres.',
    highlight: { key: 'puntos_per36', label: 'PTS/36' },
  },
  {
    key: 'totales',
    label: 'Totales',
    description: 'Acumulado de la temporada.',
    highlight: { key: 'puntos_total', label: 'PTS' },
  },
];

const POSITIONS = [
  { code: 'B', label: 'Base' },
  { code: 'E', label: 'Escolta' },
  { code: 'A', label: 'Alero' },
  { code: 'AP', label: 'Ala-Pívot' },
  { code: 'P', label: 'Pívot' },
];

interface Props {
  players: PlayerSummary[];
  teamOptions: string[];
  initialTeam?: string;
}

export function PlayersExplorer({ players, teamOptions, initialTeam = '' }: Props) {
  const [view, setView] = useState<ViewKey>('medias');
  const [search, setSearch] = useState('');
  const [team, setTeam] = useState<string>(initialTeam);
  const [position, setPosition] = useState<string>('');
  const [minGames, setMinGames] = useState(5);
  const [minMinutes, setMinMinutes] = useState(10);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return players.filter((p) => {
      if (needle && !p.nombre.toLowerCase().includes(needle)) return false;
      if (team && p.equipo !== team) return false;
      if (position && p.posicion !== position) return false;
      if (p.partidos < minGames) return false;
      if (p.minutos_avg < minMinutes) return false;
      return true;
    });
  }, [players, search, team, position, minGames, minMinutes]);

  const currentView = VIEWS.find((v) => v.key === view)!;
  const columns = buildColumns(view);

  return (
    <div className="space-y-8">
      {/* Vistas */}
      <nav aria-label="Vista de estadísticas" className="border-b border-[var(--rule)]">
        <ul className="flex flex-wrap items-end gap-x-8 gap-y-2">
          {VIEWS.map((v) => (
            <li key={v.key}>
              <button
                type="button"
                onClick={() => setView(v.key)}
                className={cn(
                  'pb-3 -mb-px border-b-2 text-sm uppercase tracking-[0.16em] transition-colors',
                  view === v.key
                    ? 'border-[var(--accent)] text-[var(--ink)]'
                    : 'border-transparent text-[var(--ink-muted)] hover:text-[var(--ink)]',
                )}
              >
                {v.label}
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-3 mb-4 text-sm text-[var(--ink-muted)]">{currentView.description}</p>
      </nav>

      {/* Filtros */}
      <section
        aria-label="Filtros"
        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4"
      >
        <Field label="Buscar">
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Jugador..."
            className="input-editorial"
          />
        </Field>
        <Field label="Equipo">
          <select
            value={team}
            onChange={(e) => setTeam(e.target.value)}
            className="input-editorial"
          >
            <option value="">Todos</option>
            {teamOptions.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Posición">
          <select
            value={position}
            onChange={(e) => setPosition(e.target.value)}
            className="input-editorial"
          >
            <option value="">Todas</option>
            {POSITIONS.map((p) => (
              <option key={p.code} value={p.code}>
                {p.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Mín partidos">
          <input
            type="number"
            min={0}
            value={minGames}
            onChange={(e) => setMinGames(Number(e.target.value) || 0)}
            className="input-editorial"
          />
        </Field>
        <Field label="Mín minutos">
          <input
            type="number"
            min={0}
            value={minMinutes}
            onChange={(e) => setMinMinutes(Number(e.target.value) || 0)}
            className="input-editorial"
          />
        </Field>
      </section>

      {/* Resumen del filtro */}
      <p className="text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
        {filtered.length} jugadores · mín {minGames} partidos · mín {minMinutes} min
      </p>

      {/* Tabla — desktop */}
      <div className="hidden md:block">
        <MetricTable
          columns={columns}
          rows={filtered}
          rowKey={(p) => p.player_id}
          rowHref={(p) => `/jugador/${p.player_id}`}
          defaultSort={{ key: defaultSortFor(view), direction: 'desc' }}
          emptyText="Ningún jugador cumple los filtros."
        />
      </div>

      {/* Cards — mobile */}
      <ul className="md:hidden grid grid-cols-1 gap-3">
        {filtered.length === 0 && (
          <li className="text-center py-8 italic text-[var(--ink-muted)]">
            Ningún jugador cumple los filtros.
          </li>
        )}
        {filtered.slice(0, 50).map((p) => (
          <li key={p.player_id}>
            <PlayerCard player={p} highlight={currentView.highlight} />
          </li>
        ))}
        {filtered.length > 50 && (
          <li className="text-center pt-4 text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
            Mostrando 50 de {filtered.length}. Refina los filtros para ver más.
          </li>
        )}
      </ul>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[0.65rem] uppercase tracking-[0.16em] text-[var(--ink-muted)]">
        {label}
      </span>
      {children}
    </label>
  );
}

function PlayerCard({
  player,
  highlight,
}: {
  player: PlayerSummary;
  highlight: View['highlight'];
}) {
  const meta = teamMeta(player.equipo);
  const hValue = player[highlight.key];
  return (
    <Link
      href={`/jugador/${player.player_id}`}
      className="block bg-[var(--bg-elev)] border border-[var(--rule)] p-4 hover:border-[var(--rule-strong)] transition-colors"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium truncate">{player.nombre}</p>
          <p className="text-[0.7rem] uppercase tracking-wider text-[var(--ink-muted)] mt-0.5">
            {meta.short} · {player.posicion_full || player.posicion} · {player.partidos}{' '}
            PJ
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className="font-mono tabular-nums text-2xl leading-none">
            {hValue}
            <span className="text-sm text-[var(--ink-muted)] ml-0.5">
              {highlight.suffix ?? ''}
            </span>
          </p>
          <p className="text-[0.65rem] uppercase tracking-[0.16em] text-[var(--ink-muted)] mt-1">
            {highlight.label}
          </p>
        </div>
      </div>
      <dl className="grid grid-cols-4 gap-x-2 gap-y-2 mt-4 pt-3 border-t border-[var(--rule)] text-[0.72rem] font-mono tabular-nums">
        <Stat label="MIN" value={player.minutos_avg} />
        <Stat label="PTS" value={player.puntos_avg} />
        <Stat label="REB" value={player.rebotes_avg} />
        <Stat label="AST" value={player.asistencias_avg} />
      </dl>
    </Link>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[var(--ink-muted)] uppercase tracking-wider text-[0.6rem]">
        {label}
      </span>
      <span className="text-[var(--ink)]">{value}</span>
    </div>
  );
}

// ────────── Definición de columnas por vista ──────────

function defaultSortFor(view: ViewKey): string {
  return view === 'totales' ? 'puntos_total' : view === 'eficiencia' ? 'ts_pct' : `${view === 'per36' ? 'puntos_per36' : 'puntos_avg'}`;
}

function num(p: PlayerSummary, k: keyof PlayerSummary): number {
  const v = p[k];
  return typeof v === 'number' ? v : 0;
}

function buildColumns(view: ViewKey): MetricColumn<PlayerSummary>[] {
  const playerCol: MetricColumn<PlayerSummary> = {
    key: 'jugador',
    label: 'Jugador',
    align: 'left',
    minWidth: '14rem',
    sortValue: (p) => p.nombre,
    render: (p) => (
      <PlayerLink id={p.player_id} nombre={p.nombre} equipo={p.equipo} posicion={p.posicion} asText />
    ),
  };
  const pj: MetricColumn<PlayerSummary> = {
    key: 'partidos',
    label: 'PJ',
    align: 'right',
    sortValue: (p) => p.partidos,
    render: (p) => p.partidos,
    hint: 'Partidos jugados',
  };
  const min: MetricColumn<PlayerSummary> = {
    key: 'minutos_avg',
    label: 'MIN',
    align: 'right',
    sortValue: (p) => p.minutos_avg,
    render: (p) => p.minutos_avg.toFixed(1),
    hint: 'Minutos por partido',
  };

  switch (view) {
    case 'medias':
      return [
        playerCol,
        pj,
        min,
        statCol('puntos_avg', 'PTS', 1),
        statCol('rebotes_avg', 'REB', 1),
        statCol('asistencias_avg', 'AST', 1),
        statCol('robos_avg', 'ROB', 1),
        statCol('tapones_avg', 'TAP', 1),
        statCol('valoracion_avg', 'VAL', 1),
      ];
    case 'eficiencia':
      return [
        playerCol,
        pj,
        min,
        pctCol('t2_pct', 'T2%', 1),
        pctCol('t3_pct', 'T3%', 1),
        pctCol('tl_pct', 'TL%', 1),
        pctCol('efg_pct', 'eFG%', 1, 'Effective Field Goal: corrige el bonus del triple.'),
        pctCol('ts_pct', 'TS%', 1, 'True Shooting: incluye tiros libres y triples ponderados.'),
      ];
    case 'per36':
      return [
        playerCol,
        pj,
        min,
        statCol('puntos_per36', 'PTS', 1),
        statCol('rebotes_per36', 'REB', 1),
        statCol('asistencias_per36', 'AST', 1),
        statCol('robos_per36', 'ROB', 1),
        statCol('tapones_per36', 'TAP', 1),
        statCol('valoracion_per36', 'VAL', 1),
      ];
    case 'totales':
      return [
        playerCol,
        pj,
        min,
        statCol('puntos_total', 'PTS', 0),
        statCol('rebotes_total', 'REB', 0),
        statCol('asistencias_total', 'AST', 0),
        statCol('valoracion_total', 'VAL', 0),
      ];
  }
}

function statCol(
  key: keyof PlayerSummary,
  label: string,
  decimals: number,
): MetricColumn<PlayerSummary> {
  return {
    key: String(key),
    label,
    align: 'right',
    sortValue: (p) => num(p, key),
    render: (p) => num(p, key).toFixed(decimals),
  };
}

function pctCol(
  key: keyof PlayerSummary,
  label: string,
  decimals: number,
  hint?: string,
): MetricColumn<PlayerSummary> {
  return {
    key: String(key),
    label,
    align: 'right',
    sortValue: (p) => num(p, key),
    render: (p) => `${num(p, key).toFixed(decimals)}`,
    hint,
  };
}
