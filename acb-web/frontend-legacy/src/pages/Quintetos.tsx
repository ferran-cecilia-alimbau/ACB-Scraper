import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useGames, useGame, useGameLineups } from '../hooks/useApi';
import { PageHeader } from '../components/PageHeader';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { StatCard } from '../components/StatCard';
import { HeatmapChart } from '../components/charts/HeatmapChart';
import { teamColor } from '../lib/formatters';
import type { GameSummary, GameDetail, LineupData } from '../types';

/** "Alberto Díaz / Chris Duarte / ..." → "Díaz - Duarte - ..." */
function truncateLineup(str: string): string {
  return str
    .split(' / ')
    .map((name) => {
      const parts = name.trim().split(' ');
      return parts.length > 1 ? parts.slice(1).join(' ') : parts[0];
    })
    .join(' - ');
}

/** "Alberto Díaz García" → "A. Díaz García" */
function shortName(fullName: string): string {
  const parts = fullName.trim().split(' ');
  if (parts.length <= 1) return fullName;
  return `${parts[0][0]}. ${parts.slice(1).join(' ')}`;
}

export default function Quintetos() {
  const [searchParams, setSearchParams] = useSearchParams();
  const gameId = Number(searchParams.get('id')) || 0;
  const { data: games, isLoading: gl, isError: gerr } = useGames();
  const { data: gameDetail } = useGame(gameId);
  const { data: lineupData, isLoading: ll, isError: lerr } = useGameLineups(gameId);
  const [tab, setTab] = useState<'lineups' | 'heatmap' | 'stints'>('lineups');
  const [lineupSide, setLineupSide] = useState<'LOCAL' | 'VISITANTE'>('LOCAL');

  const typedGames = (games || []) as GameSummary[];
  const detail = gameDetail as GameDetail | undefined;
  const data = lineupData as LineupData | undefined;
  const hasError = data && 'error' in data;

  if (gl) return <Loading />;
  if (gerr) return <ErrorMessage />;

  const game = typedGames.find((g) => g.id_partido === gameId);

  // KPI calculations
  const localLineups = data && !hasError ? data.lineups.filter((l) => l.side === 'LOCAL') : [];
  const visitLineups = data && !hasError ? data.lineups.filter((l) => l.side === 'VISITANTE') : [];
  const allLineups = [...localLineups, ...visitLineups];
  const bestNet = allLineups.length > 0 ? allLineups.reduce((a, b) => (a.net_rating > b.net_rating ? a : b)) : null;
  const worstNet = allLineups.length > 0 ? allLineups.reduce((a, b) => (a.net_rating < b.net_rating ? a : b)) : null;
  const mostUsed = allLineups.length > 0 ? allLineups.reduce((a, b) => (a.minutes > b.minutes ? a : b)) : null;

  return (
    <div>
      <PageHeader title="Quintetos" subtitle="Análisis de lineups y minutos compartidos" />

      {/* Game selector */}
      <select
        value={gameId || ''}
        onChange={(e) => setSearchParams({ id: e.target.value })}
        className="mb-6 w-full max-w-md rounded-lg border border-border bg-bg-card px-3 py-2 text-sm outline-none focus:border-accent"
      >
        <option value="">Seleccionar partido...</option>
        {typedGames.map((g) => (
          <option key={g.id_partido} value={g.id_partido}>
            J{g.jornada_num} — {g.local} {g.resultado_local}-{g.resultado_visitante} {g.visitante} ({g.fecha})
          </option>
        ))}
      </select>

      {/* Empty state: no game selected */}
      {!gameId && (
        <div className="rounded-lg border-2 border-dashed border-border p-12 text-center text-text-secondary">
          <p className="text-lg font-medium">Selecciona un partido</p>
          <p className="text-sm mt-1">Elige un partido del desplegable para ver el análisis de quintetos</p>
        </div>
      )}

      {gameId > 0 && ll && <Loading />}
      {gameId > 0 && lerr && <ErrorMessage />}

      {/* Error state: PBP not available */}
      {gameId > 0 && hasError && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 p-8 text-center">
          <p className="text-lg font-medium text-danger">No hay datos PBP disponibles</p>
          <p className="text-sm mt-1 text-text-secondary">Este partido no tiene datos de play-by-play para analizar quintetos</p>
        </div>
      )}

      {data && !hasError && (
        <div>
          {/* Score header */}
          {detail && !('error' in detail) && (
            <div className="rounded-lg border border-border bg-bg-card p-6 mb-6">
              <div className="flex items-center justify-center gap-6">
                <div className="text-center flex-1">
                  <div className="flex items-center justify-end gap-2">
                    <span className="text-xl font-bold">{detail.local}</span>
                    <span className="h-4 w-4 rounded-full" style={{ backgroundColor: teamColor(detail.local_color) }} />
                  </div>
                </div>
                <div className="text-center">
                  <p className="text-4xl font-bold tabular-nums">
                    {detail.resultado_local}
                    <span className="mx-2 text-text-secondary">-</span>
                    {detail.resultado_visitante}
                  </p>
                  <p className="text-xs text-text-secondary mt-1">Jornada {detail.jornada_num} · {detail.fecha}</p>
                  {detail.parciales_local && (
                    <p className="text-xs text-text-secondary mt-1">
                      {detail.parciales_local} / {detail.parciales_visitante}
                    </p>
                  )}
                </div>
                <div className="text-center flex-1">
                  <div className="flex items-center justify-start gap-2">
                    <span className="h-4 w-4 rounded-full" style={{ backgroundColor: teamColor(detail.visitante_color) }} />
                    <span className="text-xl font-bold">{detail.visitante}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard
              label="Quintetos usados"
              value={`${localLineups.length} / ${visitLineups.length}`}
              subtitle={`${game?.local ?? 'Local'} / ${game?.visitante ?? 'Visitante'}`}
            />
            {bestNet && (
              <StatCard
                label="Mejor NetRtg"
                value={`${bestNet.net_rating > 0 ? '+' : ''}${bestNet.net_rating.toFixed(1)}`}
                subtitle={truncateLineup(bestNet.lineup_str)}
                accentColor="var(--color-success)"
              />
            )}
            {worstNet && (
              <StatCard
                label="Peor NetRtg"
                value={`${worstNet.net_rating > 0 ? '+' : ''}${worstNet.net_rating.toFixed(1)}`}
                subtitle={truncateLineup(worstNet.lineup_str)}
                accentColor="var(--color-danger)"
              />
            )}
            {mostUsed && (
              <StatCard
                label="Más usado"
                value={`${mostUsed.minutes.toFixed(1)}'`}
                subtitle={truncateLineup(mostUsed.lineup_str)}
              />
            )}
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mb-4 rounded-lg bg-bg-card p-1 w-fit">
            {[
              { id: 'lineups', label: 'Quintetos' },
              { id: 'heatmap', label: 'Min. Compartidos' },
              { id: 'stints', label: 'Stints' },
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

          {tab === 'lineups' && (
            <div>
              {/* Sub-tabs LOCAL / VISITANTE */}
              <div className="flex gap-1 mb-3 rounded-lg bg-bg-card p-1 w-fit">
                <button
                  onClick={() => setLineupSide('LOCAL')}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${lineupSide === 'LOCAL' ? 'bg-bg-hover font-medium' : 'text-text-secondary'}`}
                >
                  {game?.local ?? 'Local'}
                </button>
                <button
                  onClick={() => setLineupSide('VISITANTE')}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${lineupSide === 'VISITANTE' ? 'bg-bg-hover font-medium' : 'text-text-secondary'}`}
                >
                  {game?.visitante ?? 'Visitante'}
                </button>
              </div>

              {(() => {
                const filtered = data.lineups.filter((l) => l.side === lineupSide);
                if (filtered.length === 0) {
                  return (
                    <div className="rounded-lg border border-border bg-bg-card p-8 text-center text-text-secondary">
                      No se encontraron quintetos con suficientes minutos
                    </div>
                  );
                }
                return (
                  <div className="overflow-x-auto rounded-lg border border-border">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-border bg-bg-card text-[10px] uppercase text-text-secondary">
                          <th className="px-3 py-2 text-left">Quinteto</th>
                          <th className="px-3 py-2 text-center">Min</th>
                          <th className="px-3 py-2 text-center">ORtg</th>
                          <th className="px-3 py-2 text-center">DRtg</th>
                          <th className="px-3 py-2 text-center">NetRtg</th>
                          <th className="px-3 py-2 text-center">Stints</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.map((l, i) => (
                          <tr
                            key={i}
                            className={`border-b border-border hover:bg-bg-hover transition-colors ${
                              l.net_rating > 0 ? 'bg-success/5' : 'bg-danger/5'
                            }`}
                          >
                            <td className="px-3 py-2">{l.lineup_str}</td>
                            <td className="px-3 py-2 text-center tabular-nums">{l.minutes.toFixed(1)}</td>
                            <td className="px-3 py-2 text-center tabular-nums">{l.off_rating.toFixed(1)}</td>
                            <td className="px-3 py-2 text-center tabular-nums">{l.def_rating.toFixed(1)}</td>
                            <td className={`px-3 py-2 text-center tabular-nums font-bold ${l.net_rating > 0 ? 'text-success' : 'text-danger'}`}>
                              {l.net_rating > 0 ? '+' : ''}{l.net_rating.toFixed(1)}
                            </td>
                            <td className="px-3 py-2 text-center">{l.n_stints}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              })()}
            </div>
          )}

          {tab === 'heatmap' && (
            <div className="grid gap-6 lg:grid-cols-2">
              {Object.entries(data.shared_minutes).map(([side, matrix]) => (
                <div key={side} className="rounded-lg border border-border bg-bg-card p-4">
                  <h3 className="text-sm font-medium mb-3 text-text-secondary">
                    {side === 'LOCAL' ? game?.local : game?.visitante} — Min. compartidos
                  </h3>
                  <HeatmapChart players={matrix.players} values={matrix.values} />
                </div>
              ))}
            </div>
          )}

          {tab === 'stints' && (
            <div className="grid gap-6">
              {['LOCAL', 'VISITANTE'].map((side) => {
                const sideStints = data.stints.filter((s) => s.side === side);
                const uniquePlayers = [...new Set(sideStints.map((s) => s.player))];
                const maxTime = Math.max(...data.stints.map((s) => s.end_time), 40);
                const teamName = side === 'LOCAL' ? game?.local : game?.visitante;

                // Dynamic labels: quarters + OT periods
                const labels: Array<{ pos: number; label: string }> = [
                  { pos: 0, label: "0'" },
                  { pos: 10, label: 'Q1' },
                  { pos: 20, label: 'Q2' },
                  { pos: 30, label: 'Q3' },
                  { pos: 40, label: 'Q4' },
                ];
                if (maxTime > 40) {
                  for (let i = 1; i <= Math.ceil((maxTime - 40) / 5); i++) {
                    labels.push({ pos: 40 + i * 5, label: `OT${i}` });
                  }
                }

                return (
                  <div key={side} className="rounded-lg border border-border bg-bg-card p-4">
                    <h3 className="text-sm font-medium mb-3 text-text-secondary">
                      {teamName} — Rotaciones
                    </h3>
                    <div className="space-y-1">
                      {uniquePlayers.map((player) => {
                        const playerStints = sideStints.filter((s) => s.player === player);
                        return (
                          <div key={player} className="flex items-center gap-2">
                            <span className="w-36 text-xs text-right text-text-secondary truncate" title={player}>
                              {shortName(player)}
                            </span>
                            <div className="flex-1 h-5 bg-bg-hover rounded relative">
                              {playerStints.map((s, i) => (
                                <div
                                  key={i}
                                  className="absolute h-full rounded"
                                  title={`${s.start_time.toFixed(1)}' - ${s.end_time.toFixed(1)}' (${s.plus_minus >= 0 ? '+' : ''}${s.plus_minus})`}
                                  style={{
                                    left: `${(s.start_time / maxTime) * 100}%`,
                                    width: `${Math.max((s.duration / maxTime) * 100, 0.5)}%`,
                                    backgroundColor: s.plus_minus >= 0 ? '#10b981' : '#ef4444',
                                    opacity: 0.8,
                                  }}
                                />
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    {/* Dynamic time labels */}
                    <div className="flex items-center gap-2 mt-2">
                      <span className="w-36" />
                      <div className="flex-1 relative h-4">
                        {labels.map((l) => (
                          <span
                            key={l.pos}
                            className="absolute text-[10px] text-text-secondary -translate-x-1/2"
                            style={{ left: `${(l.pos / maxTime) * 100}%` }}
                          >
                            {l.label}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
              <div className="flex gap-4 text-xs text-text-secondary">
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-success inline-block opacity-80" /> +/- positivo</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-danger inline-block opacity-80" /> +/- negativo</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
