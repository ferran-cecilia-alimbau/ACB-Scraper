'use client';

import { useEffect, useMemo, useState } from 'react';
import type { PlayerRankingRow } from '@/lib/api';
import { MetricTable, type MetricColumn } from '@/components/metric-table';
import { PlayerLink } from '@/components/player-link';
import { cn } from '@/lib/cn';

type Category =
  | 'anotacion'
  | 'rebote'
  | 'creacion'
  | 'defensa'
  | 'eficiencia'
  | 'tiro'
  | 'impacto';

interface CategoryConfig {
  key: Category;
  label: string;
  description: string;
  /** Stats que ofrecen los sub-tabs dentro de la categoría. */
  stats: { key: string; label: string; suffix?: string; decimals?: number }[];
  defaultStat: string;
  minMinutes?: number;
}

const CATEGORIES: CategoryConfig[] = [
  {
    key: 'anotacion',
    label: 'Anotación',
    description: 'Jugadores que más puntúan, en términos absolutos y por 36 minutos.',
    stats: [
      { key: 'puntos_avg', label: 'Puntos por partido', decimals: 1 },
      { key: 'puntos_per36', label: 'Puntos por 36 min', decimals: 1 },
    ],
    defaultStat: 'puntos_avg',
  },
  {
    key: 'rebote',
    label: 'Rebote',
    description: 'Mejores reboteadores totales, ofensivos y defensivos.',
    stats: [
      { key: 'rebotes_avg', label: 'Rebotes por partido', decimals: 1 },
      { key: 'rebotes_of_avg', label: 'Rebotes ofensivos', decimals: 1 },
      { key: 'rebotes_def_avg', label: 'Rebotes defensivos', decimals: 1 },
    ],
    defaultStat: 'rebotes_avg',
  },
  {
    key: 'creacion',
    label: 'Creación',
    description: 'Pasadores y generadores de juego.',
    stats: [{ key: 'asistencias_avg', label: 'Asistencias por partido', decimals: 1 }],
    defaultStat: 'asistencias_avg',
  },
  {
    key: 'defensa',
    label: 'Defensa',
    description: 'Robos y tapones — el impacto medible en el lado defensivo.',
    stats: [
      { key: 'robos_avg', label: 'Robos por partido', decimals: 1 },
      { key: 'tapones_avg', label: 'Tapones por partido', decimals: 1 },
    ],
    defaultStat: 'robos_avg',
  },
  {
    key: 'eficiencia',
    label: 'Eficiencia',
    description: 'Valoración y métricas avanzadas de eficiencia (TS%, eFG%).',
    stats: [
      { key: 'valoracion_avg', label: 'Valoración por partido', decimals: 1 },
      { key: 'ts_pct', label: 'TS%', suffix: '%', decimals: 1 },
      { key: 'efg_pct', label: 'eFG%', suffix: '%', decimals: 1 },
    ],
    defaultStat: 'valoracion_avg',
  },
  {
    key: 'tiro',
    label: 'Tiro',
    description: 'Porcentajes de tiro — filtramos por mínimos de volumen para no premiar muestras pequeñas.',
    stats: [
      { key: 't3_pct', label: 'Triples %', suffix: '%', decimals: 1 },
      { key: 't2_pct', label: 'Tiros de 2 %', suffix: '%', decimals: 1 },
      { key: 'tl_pct', label: 'Tiros libres %', suffix: '%', decimals: 1 },
    ],
    defaultStat: 't3_pct',
    minMinutes: 15,
  },
  {
    key: 'impacto',
    label: 'Impacto',
    description: 'Plus-minus medio: la diferencia que el jugador hace en el marcador mientras está en pista.',
    stats: [{ key: 'plus_minus_avg', label: '+/- por partido', decimals: 1 }],
    defaultStat: 'plus_minus_avg',
  },
];

interface Props {
  teamOptions: string[];
}

export function RankingsExplorer({ teamOptions }: Props) {
  const [category, setCategory] = useState<Category>('eficiencia');
  const cfg = CATEGORIES.find((c) => c.key === category)!;
  const [stat, setStat] = useState<string>(cfg.defaultStat);
  const [minGames, setMinGames] = useState(5);
  const [minMinutes, setMinMinutes] = useState(cfg.minMinutes ?? 10);
  const [team, setTeam] = useState('');
  const [position, setPosition] = useState('');
  const [topN, setTopN] = useState(25);
  const [rows, setRows] = useState<PlayerRankingRow[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cuando cambia la categoría, ajustar stat y mínimos por defecto.
  useEffect(() => {
    setStat(cfg.defaultStat);
    setMinMinutes(cfg.minMinutes ?? 10);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  // Carga del ranking cada vez que cambian los parámetros.
  useEffect(() => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      stat,
      min_games: String(minGames),
      min_minutes: String(minMinutes),
      limit: String(topN),
    });
    if (team) params.set('team', team);
    if (position) params.set('position', position);
    fetch(`/api/rankings/players?${params.toString()}`)
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d)) setRows(d);
        else {
          setRows([]);
          setError('Error en la consulta de rankings.');
        }
      })
      .catch(() => setError('No se pudo conectar con el backend.'))
      .finally(() => setLoading(false));
  }, [stat, minGames, minMinutes, team, position, topN]);

  const currentStat = cfg.stats.find((s) => s.key === stat) ?? cfg.stats[0];

  const columns: MetricColumn<PlayerRankingRow>[] = useMemo(() => {
    return [
      {
        key: 'rank',
        label: '#',
        align: 'right',
        sortable: false,
        render: (r) => (
          <span
            className={cn(
              'font-mono tabular-nums',
              r.rank <= 3 && 'text-[var(--accent)] font-semibold',
            )}
          >
            {r.rank}
          </span>
        ),
      },
      {
        key: 'jugador',
        label: 'Jugador',
        align: 'left',
        minWidth: '14rem',
        sortValue: (r) => r.nombre,
        render: (r) => (
          <PlayerLink id={r.player_id} nombre={r.nombre} equipo={r.equipo} posicion={r.posicion} asText />
        ),
      },
      {
        key: 'value',
        label: currentStat.label.toUpperCase(),
        align: 'right',
        sortValue: (r) => r.value,
        render: (r) => (
          <span className="font-medium text-[var(--accent)]">
            {r.value.toFixed(currentStat.decimals ?? 1)}
            {currentStat.suffix ?? ''}
          </span>
        ),
      },
      {
        key: 'partidos',
        label: 'PJ',
        align: 'right',
        sortValue: (r) => r.partidos,
        render: (r) => r.partidos,
      },
      {
        key: 'minutos_avg',
        label: 'MIN',
        align: 'right',
        sortValue: (r) => r.minutos_avg,
        render: (r) => r.minutos_avg.toFixed(1),
      },
      {
        key: 'puntos_avg',
        label: 'PTS',
        align: 'right',
        sortValue: (r) => r.puntos_avg,
        render: (r) => r.puntos_avg.toFixed(1),
      },
      {
        key: 'rebotes_avg',
        label: 'REB',
        align: 'right',
        sortValue: (r) => r.rebotes_avg,
        render: (r) => r.rebotes_avg.toFixed(1),
      },
      {
        key: 'asistencias_avg',
        label: 'AST',
        align: 'right',
        sortValue: (r) => r.asistencias_avg,
        render: (r) => r.asistencias_avg.toFixed(1),
      },
      {
        key: 'valoracion_avg',
        label: 'VAL',
        align: 'right',
        sortValue: (r) => r.valoracion_avg,
        render: (r) => r.valoracion_avg.toFixed(1),
      },
    ];
  }, [currentStat]);

  return (
    <div className="space-y-8">
      {/* Tabs principales */}
      <nav aria-label="Categoría de ranking" className="border-b border-[var(--rule)]">
        <ul className="flex flex-wrap items-end gap-x-7 gap-y-2">
          {CATEGORIES.map((c) => (
            <li key={c.key}>
              <button
                type="button"
                onClick={() => setCategory(c.key)}
                className={cn(
                  'pb-3 -mb-px border-b-2 text-sm uppercase tracking-[0.16em] transition-colors',
                  category === c.key
                    ? 'border-[var(--accent)] text-[var(--ink)]'
                    : 'border-transparent text-[var(--ink-muted)] hover:text-[var(--ink)]',
                )}
              >
                {c.label}
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-3 mb-2 text-sm text-[var(--ink-muted)]">{cfg.description}</p>
      </nav>

      {/* Sub-tabs (estadística) */}
      {cfg.stats.length > 1 && (
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          {cfg.stats.map((s) => (
            <button
              key={s.key}
              type="button"
              onClick={() => setStat(s.key)}
              className={cn(
                'transition-colors link-underline',
                stat === s.key ? 'text-[var(--ink)]' : 'text-[var(--ink-muted)]',
              )}
            >
              {s.label}
            </button>
          ))}
        </div>
      )}

      {/* Filtros */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
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
            <option value="B">Base</option>
            <option value="E">Escolta</option>
            <option value="A">Alero</option>
            <option value="AP">Ala-Pívot</option>
            <option value="P">Pívot</option>
          </select>
        </Field>
        <Field label="Top N">
          <select
            value={topN}
            onChange={(e) => setTopN(Number(e.target.value))}
            className="input-editorial"
          >
            <option value="10">10</option>
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </Field>
      </section>

      {/* Filtro activo */}
      <p className="text-xs uppercase tracking-[0.14em] text-[var(--ink-muted)]">
        {currentStat.label} · mín {minGames} partidos · mín {minMinutes} min
        {team ? ` · ${team}` : ''}
        {position ? ` · ${position}` : ''}
      </p>

      {/* Tabla */}
      {error && (
        <p className="text-sm text-[var(--negative)] italic py-4">{error}</p>
      )}
      {loading && !rows && (
        <p className="text-sm text-[var(--ink-muted)] italic py-8 text-center">Cargando…</p>
      )}
      {rows && (
        <MetricTable
          columns={columns}
          rows={rows}
          rowKey={(r) => r.player_id}
          rowHref={(r) => `/jugador/${r.player_id}`}
          emptyText="Ningún jugador cumple los filtros."
        />
      )}
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
