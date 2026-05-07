import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { usePlayers, usePlayer } from '../hooks/useApi';
import { PageHeader } from '../components/PageHeader';
import { StatCard } from '../components/StatCard';
import { TeamBadge } from '../components/TeamBadge';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { DataTable } from '../components/DataTable';
import { RadarChart } from '../components/charts/RadarChart';
import { teamColor } from '../lib/formatters';
import { buildRadarData } from '../lib/radarScaling';
import type { PlayerSummary, PlayerDetail } from '../types';
import type { ColumnDef } from '@tanstack/react-table';

export default function Jugador() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get('id') || '';
  const { data: players, isLoading: pl, isError: pe } = usePlayers();
  const { data: playerDetail, isLoading: pdl, isError: pde } = usePlayer(selectedId);
  const [tab, setTab] = useState<'stats' | 'gamelog' | 'radar'>('stats');

  const typedPlayers = (players || []) as PlayerSummary[];
  const detail = playerDetail as PlayerDetail | undefined;

  const columns: ColumnDef<PlayerSummary, unknown>[] = [
    {
      header: 'Jugador',
      accessorKey: 'nombre',
      cell: ({ row }) => (
        <button
          onClick={() => setSearchParams({ id: String(row.original.player_id) })}
          className="font-medium hover:text-accent transition-colors"
        >
          {row.original.nombre}
        </button>
      ),
    },
    {
      header: 'Equipo',
      accessorKey: 'equipo',
      cell: ({ row }) => <TeamBadge name={row.original.equipo} color={row.original.color} />,
    },
    { header: 'Pos', accessorKey: 'posicion' },
    { header: 'PJ', accessorKey: 'partidos' },
    { header: 'Min', accessorKey: 'minutos_avg' },
    { header: 'Pts', accessorKey: 'puntos_avg' },
    { header: 'Reb', accessorKey: 'rebotes_avg' },
    { header: 'Ast', accessorKey: 'asistencias_avg' },
    { header: 'Val', accessorKey: 'valoracion_avg' },
  ];

  if (pl) return <Loading />;
  if (pe) return <ErrorMessage />;

  if (!selectedId) {
    return (
      <div>
        <PageHeader title="Jugadores" subtitle="Estadísticas por jugador de la temporada" />
        <DataTable data={typedPlayers} columns={columns} searchable searchPlaceholder="Buscar jugador..." />
      </div>
    );
  }

  if (pdl) return <Loading />;
  if (pde) return <ErrorMessage />;
  if (!detail || 'error' in detail) return <p className="text-text-secondary">Jugador no encontrado</p>;

  const radarData = buildRadarData(detail.stats);

  return (
    <div>
      <button onClick={() => setSearchParams({})} className="text-sm text-accent hover:text-accent-hover mb-4 inline-block">
        ← Todos los jugadores
      </button>

      {/* Player header */}
      <div className="flex items-center gap-4 mb-6">
        <div className="h-14 w-1 rounded-full" style={{ backgroundColor: teamColor(detail.color) }} />
        <div>
          <h1 className="text-2xl font-bold">{detail.nombre}</h1>
          <div className="flex items-center gap-3 mt-1">
            <TeamBadge name={detail.equipo} color={detail.color} />
            <span className="text-xs text-text-secondary">
              #{detail.profile.dorsal} · {detail.profile.posicion_full} · {detail.profile.altura} cm · {detail.profile.edad} años
            </span>
          </div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6 mb-6">
        <StatCard label="PPG" value={detail.stats.puntos_avg} accentColor={teamColor(detail.color)} subtitle={`#${detail.rankings.puntos_avg?.rank}`} />
        <StatCard label="RPG" value={detail.stats.rebotes_avg} accentColor={teamColor(detail.color)} subtitle={`#${detail.rankings.rebotes_totales_avg?.rank}`} />
        <StatCard label="APG" value={detail.stats.asistencias_avg} accentColor={teamColor(detail.color)} subtitle={`#${detail.rankings.asistencias_avg?.rank}`} />
        <StatCard label="VAL" value={detail.stats.valoracion_avg} accentColor={teamColor(detail.color)} subtitle={`#${detail.rankings.valoracion_avg?.rank}`} />
        <StatCard label="eFG%" value={detail.stats.efg_pct?.toFixed(1) + '%'} accentColor={teamColor(detail.color)} />
        <StatCard label="TS%" value={detail.stats.ts_pct?.toFixed(1) + '%'} accentColor={teamColor(detail.color)} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 rounded-lg bg-bg-card p-1 w-fit">
        {[
          { id: 'stats', label: 'Tiro' },
          { id: 'radar', label: 'Radar' },
          { id: 'gamelog', label: 'Game Log' },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as typeof tab)}
            className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
              tab === t.id ? 'bg-accent text-white font-medium' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'stats' && (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-border bg-bg-card p-4">
            <h3 className="text-sm font-medium mb-3 text-text-secondary">Porcentajes de tiro</h3>
            <div className="space-y-3">
              {[
                { label: 'T2%', value: detail.stats.t2_pct },
                { label: 'T3%', value: detail.stats.t3_pct },
                { label: 'TL%', value: detail.stats.tl_pct },
                { label: 'eFG%', value: detail.stats.efg_pct },
                { label: 'TS%', value: detail.stats.ts_pct },
              ].map((s) => (
                <div key={s.label} className="flex items-center gap-3">
                  <span className="w-12 text-xs text-text-secondary">{s.label}</span>
                  <div className="flex-1 h-2 rounded-full bg-bg-hover overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${Math.min(s.value, 100)}%`, backgroundColor: teamColor(detail.color) }}
                    />
                  </div>
                  <span className="w-12 text-right text-xs font-medium">{s.value?.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-bg-card p-4">
            <h3 className="text-sm font-medium mb-3 text-text-secondary">Splits Casa/Fuera</h3>
            {detail.splits.length > 0 ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-text-secondary">
                    <th className="text-left pb-2">Sede</th>
                    <th className="text-center pb-2">PJ</th>
                    <th className="text-center pb-2">Pts</th>
                    <th className="text-center pb-2">Reb</th>
                    <th className="text-center pb-2">Ast</th>
                    <th className="text-center pb-2">Val</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.splits.map((s) => (
                    <tr key={String(s.sede)} className="border-t border-border">
                      <td className="py-1.5 font-medium">{String(s.sede)}</td>
                      <td className="py-1.5 text-center">{String(s.PJ)}</td>
                      <td className="py-1.5 text-center">{Number(s.puntos).toFixed(1)}</td>
                      <td className="py-1.5 text-center">{Number(s.rebotes_totales).toFixed(1)}</td>
                      <td className="py-1.5 text-center">{Number(s.asistencias).toFixed(1)}</td>
                      <td className="py-1.5 text-center">{Number(s.valoracion).toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-text-secondary text-sm">Sin datos de splits</p>
            )}
          </div>
        </div>
      )}

      {tab === 'radar' && (
        <div className="rounded-lg border border-border bg-bg-card p-4 max-w-lg">
          <RadarChart
            data={radarData}
            radars={[{ key: 'value', color: detail.color, name: detail.nombre }]}
            height={400}
          />
        </div>
      )}

      {tab === 'gamelog' && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-bg-card text-xs text-text-secondary">
                <th className="px-2 py-2 text-left">J</th>
                <th className="px-2 py-2 text-left">Oponente</th>
                <th className="px-2 py-2 text-center">Min</th>
                <th className="px-2 py-2 text-center">Pts</th>
                <th className="px-2 py-2 text-center">Reb</th>
                <th className="px-2 py-2 text-center">Ast</th>
                <th className="px-2 py-2 text-center">Rob</th>
                <th className="px-2 py-2 text-center">Per</th>
                <th className="px-2 py-2 text-center">+/-</th>
                <th className="px-2 py-2 text-center">Val</th>
              </tr>
            </thead>
            <tbody>
              {detail.game_log.map((g) => (
                <tr key={g.id_partido} className="border-b border-border hover:bg-bg-hover transition-colors">
                  <td className="px-2 py-1.5 text-text-secondary">{g.jornada_num}</td>
                  <td className="px-2 py-1.5">
                    <span className="text-xs text-text-secondary mr-1">{g.es_local ? 'vs' : '@'}</span>
                    {g.oponente}
                  </td>
                  <td className="px-2 py-1.5 text-center tabular-nums">{g.minutos}</td>
                  <td className="px-2 py-1.5 text-center tabular-nums font-medium">{g.puntos}</td>
                  <td className="px-2 py-1.5 text-center tabular-nums">{g.rebotes_totales}</td>
                  <td className="px-2 py-1.5 text-center tabular-nums">{g.asistencias}</td>
                  <td className="px-2 py-1.5 text-center tabular-nums">{g.robos}</td>
                  <td className="px-2 py-1.5 text-center tabular-nums">{g.perdidas}</td>
                  <td className={`px-2 py-1.5 text-center tabular-nums ${g.plus_minus > 0 ? 'text-success' : g.plus_minus < 0 ? 'text-danger' : ''}`}>
                    {g.plus_minus > 0 ? '+' : ''}{g.plus_minus}
                  </td>
                  <td className="px-2 py-1.5 text-center tabular-nums font-medium">{g.valoracion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
