import { useState } from 'react';
import { usePlayers, useComparePlayers } from '../hooks/useApi';
import { PageHeader } from '../components/PageHeader';
import { TeamBadge } from '../components/TeamBadge';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { RadarChart } from '../components/charts/RadarChart';
import { teamColor } from '../lib/formatters';
import { buildCompareRadarData } from '../lib/radarScaling';
import type { PlayerSummary } from '../types';

interface ComparePlayer {
  player_id: number;
  nombre: string;
  equipo: string;
  color: string;
  [key: string]: unknown;
}

export default function Comparador() {
  const { data: players, isLoading, isError } = usePlayers();
  const [selected, setSelected] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const { data: compared } = useComparePlayers(selected);

  const typedPlayers = (players || []) as PlayerSummary[];
  const typedCompared = (compared || []) as ComparePlayer[];

  const filtered = typedPlayers.filter(
    (p) => p.nombre.toLowerCase().includes(search.toLowerCase()) && !selected.includes(String(p.player_id))
  );

  if (isLoading) return <Loading />;
  if (isError) return <ErrorMessage />;

  const radarData = buildCompareRadarData(typedCompared);

  const statRows = [
    { label: 'Puntos', key: 'puntos_avg' },
    { label: 'Rebotes', key: 'rebotes_avg' },
    { label: 'Asistencias', key: 'asistencias_avg' },
    { label: 'Robos', key: 'robos_avg' },
    { label: 'Pérdidas', key: 'perdidas_avg' },
    { label: 'Tapones', key: 'tapones_avg' },
    { label: 'Valoración', key: 'valoracion_avg' },
    { label: 'T2%', key: 't2_pct' },
    { label: 'T3%', key: 't3_pct' },
    { label: 'TL%', key: 'tl_pct' },
    { label: 'eFG%', key: 'efg_pct' },
    { label: 'TS%', key: 'ts_pct' },
  ];

  return (
    <div>
      <PageHeader title="Comparador" subtitle="Compara estadísticas entre jugadores" />

      {/* Player selection */}
      <div className="mb-6">
        <div className="flex flex-wrap gap-2 mb-3">
          {selected.map((id) => {
            const p = typedPlayers.find((pl) => String(pl.player_id) === id);
            return p ? (
              <span
                key={id}
                className="inline-flex items-center gap-2 rounded-full bg-bg-card border border-border px-3 py-1 text-sm"
              >
                <TeamBadge name={p.nombre} color={p.color} />
                <button
                  onClick={() => setSelected(selected.filter((s) => s !== id))}
                  className="text-text-secondary hover:text-danger"
                >
                  ×
                </button>
              </span>
            ) : null;
          })}
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar jugador para añadir..."
          className="w-full max-w-sm rounded-lg border border-border bg-bg-card px-3 py-2 text-sm outline-none focus:border-accent placeholder:text-text-secondary"
        />
        {search.length > 1 && (
          <div className="mt-1 max-h-48 overflow-y-auto rounded-lg border border-border bg-bg-card">
            {filtered.slice(0, 10).map((p) => (
              <button
                key={p.player_id}
                onClick={() => {
                  setSelected([...selected, String(p.player_id)]);
                  setSearch('');
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-bg-hover transition-colors"
              >
                <TeamBadge name={p.nombre} color={p.color} />
                <span className="text-xs text-text-secondary">{p.equipo}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {selected.length === 1 && typedCompared.length < 2 && (
        <p className="text-sm text-text-secondary mb-6">Selecciona al menos 2 jugadores para comparar</p>
      )}

      {typedCompared.length >= 2 && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Radar */}
          <div className="rounded-lg border border-border bg-bg-card p-4">
            <h3 className="text-sm font-medium mb-3 text-text-secondary">Radar</h3>
            <RadarChart
              data={radarData}
              radars={typedCompared.map((p) => ({
                key: p.nombre,
                color: p.color,
                name: p.nombre,
              }))}
              height={400}
            />
          </div>

          {/* Stat comparison table */}
          <div className="rounded-lg border border-border bg-bg-card p-4">
            <h3 className="text-sm font-medium mb-3 text-text-secondary">Estadísticas</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-text-secondary border-b border-border">
                  <th className="py-2 text-left">Stat</th>
                  {typedCompared.map((p) => (
                    <th key={p.player_id} className="py-2 text-center">{p.nombre}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {statRows.map((s) => {
                  const vals = typedCompared.map((p) => Number((p as Record<string, unknown>)[s.key]) || 0);
                  const maxVal = Math.max(...vals);
                  return (
                    <tr key={s.key} className="border-b border-border">
                      <td className="py-1.5 text-text-secondary">{s.label}</td>
                      {typedCompared.map((p, i) => (
                        <td
                          key={p.player_id}
                          className={`py-1.5 text-center tabular-nums ${vals[i] === maxVal ? 'font-bold text-accent' : ''}`}
                        >
                          {vals[i].toFixed(1)}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
