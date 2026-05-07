import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useGames, useGame, useGameTimeline } from '../hooks/useApi';
import { PageHeader } from '../components/PageHeader';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { TeamBadge } from '../components/TeamBadge';
import { TimelineChart } from '../components/charts/TimelineChart';
import { teamColor } from '../lib/formatters';
import type { GameSummary, GameDetail, BoxScorePlayer } from '../types';

export default function Partido() {
  const [searchParams, setSearchParams] = useSearchParams();
  const gameId = Number(searchParams.get('id')) || 0;
  const { data: games, isLoading: gl, isError: gerr } = useGames();
  const { data: gameDetail, isLoading: gdl, isError: gderr } = useGame(gameId);
  const { data: timeline } = useGameTimeline(gameId);
  const [tab, setTab] = useState<'boxscore' | 'fourfactors' | 'timeline'>('boxscore');
  const [boxTab, setBoxTab] = useState<'local' | 'visitante'>('local');

  const typedGames = (games || []) as GameSummary[];
  const detail = gameDetail as GameDetail | undefined;
  const typedTimeline = (timeline || []) as Array<{ diff: number; periodo: string; tiempo: string }>;

  if (gl) return <Loading />;
  if (gerr) return <ErrorMessage />;

  return (
    <div>
      <PageHeader title="Partidos" subtitle="Selecciona un partido para ver el detalle" />

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
          <p className="text-sm mt-1">Elige un partido del desplegable para ver el detalle</p>
        </div>
      )}

      {gameId > 0 && gdl && <Loading />}
      {gameId > 0 && gderr && <ErrorMessage />}

      {/* Error state: game not found */}
      {gameId > 0 && !gdl && detail && 'error' in detail && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 p-8 text-center">
          <p className="text-lg font-medium text-danger">Partido no encontrado</p>
          <p className="text-sm mt-1 text-text-secondary">No se han encontrado datos para este partido</p>
        </div>
      )}

      {detail && !('error' in detail) && (
        <div>
          {/* Score header */}
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

          {/* Tabs */}
          <div className="flex gap-1 mb-4 rounded-lg bg-bg-card p-1 w-fit">
            {[
              { id: 'boxscore', label: 'Box Score' },
              { id: 'fourfactors', label: 'Four Factors' },
              { id: 'timeline', label: 'Timeline' },
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

          {tab === 'boxscore' && (
            <div>
              <div className="flex gap-1 mb-3 rounded-lg bg-bg-card p-1 w-fit">
                <button
                  onClick={() => setBoxTab('local')}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${boxTab === 'local' ? 'bg-bg-hover font-medium' : 'text-text-secondary'}`}
                >
                  {detail.local}
                </button>
                <button
                  onClick={() => setBoxTab('visitante')}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${boxTab === 'visitante' ? 'bg-bg-hover font-medium' : 'text-text-secondary'}`}
                >
                  {detail.visitante}
                </button>
              </div>
              <BoxScoreTable players={detail.box_score[boxTab]} />
            </div>
          )}

          {tab === 'fourfactors' && (
            <div className="rounded-lg border border-border bg-bg-card p-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-text-secondary border-b border-border">
                    <th className="py-2 text-left">Factor</th>
                    <th className="py-2 text-center">{detail.local}</th>
                    <th className="py-2 text-center">{detail.visitante}</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.keys(detail.four_factors.local).map((key) => {
                    const lv = detail.four_factors.local[key];
                    const vv = detail.four_factors.visitante[key];
                    const better = key === 'TOV%' ? lv < vv : lv > vv;
                    return (
                      <tr key={key} className="border-b border-border">
                        <td className="py-2 text-text-secondary">{key}</td>
                        <td className={`py-2 text-center tabular-nums ${better ? 'font-bold text-success' : ''}`}>
                          {lv?.toFixed(1)}%
                        </td>
                        <td className={`py-2 text-center tabular-nums ${!better ? 'font-bold text-success' : ''}`}>
                          {vv?.toFixed(1)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {tab === 'timeline' && typedTimeline.length > 0 && (
            <div className="rounded-lg border border-border bg-bg-card p-4">
              <TimelineChart
                data={typedTimeline.map((t, i) => ({ index: i, diff: t.diff }))}
                localColor={teamColor(detail.local_color)}
                visitanteColor={teamColor(detail.visitante_color)}
                height={350}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function BoxScoreTable({ players }: { players: BoxScorePlayer[] }) {
  const starters = players.filter((p) => p.es_titular);
  const bench = players.filter((p) => !p.es_titular);

  const renderRows = (list: BoxScorePlayer[]) =>
    list.map((p) => (
      <tr key={p.player_id} className="border-b border-border hover:bg-bg-hover transition-colors">
        <td className="px-2 py-1.5 font-medium whitespace-nowrap">{p.nombre}</td>
        <td className="px-2 py-1.5 text-center tabular-nums text-text-secondary">{p.minutos}</td>
        <td className="px-2 py-1.5 text-center tabular-nums font-medium">{p.puntos}</td>
        <td className="px-2 py-1.5 text-center tabular-nums text-text-secondary">{p.t2}</td>
        <td className="px-2 py-1.5 text-center tabular-nums text-text-secondary">{p.t3}</td>
        <td className="px-2 py-1.5 text-center tabular-nums text-text-secondary">{p.tl}</td>
        <td className="px-2 py-1.5 text-center tabular-nums">{p.rebotes}</td>
        <td className="px-2 py-1.5 text-center tabular-nums">{p.asistencias}</td>
        <td className="px-2 py-1.5 text-center tabular-nums">{p.robos}</td>
        <td className="px-2 py-1.5 text-center tabular-nums">{p.perdidas}</td>
        <td className={`px-2 py-1.5 text-center tabular-nums ${p.plus_minus > 0 ? 'text-success' : p.plus_minus < 0 ? 'text-danger' : ''}`}>
          {p.plus_minus > 0 ? '+' : ''}{p.plus_minus}
        </td>
        <td className="px-2 py-1.5 text-center tabular-nums font-medium">{p.valoracion}</td>
      </tr>
    ));

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border bg-bg-card text-[10px] uppercase text-text-secondary">
            <th className="px-2 py-2 text-left">Jugador</th>
            <th className="px-2 py-2 text-center">Min</th>
            <th className="px-2 py-2 text-center">Pts</th>
            <th className="px-2 py-2 text-center">T2</th>
            <th className="px-2 py-2 text-center">T3</th>
            <th className="px-2 py-2 text-center">TL</th>
            <th className="px-2 py-2 text-center">Reb</th>
            <th className="px-2 py-2 text-center">Ast</th>
            <th className="px-2 py-2 text-center">Rob</th>
            <th className="px-2 py-2 text-center">Per</th>
            <th className="px-2 py-2 text-center">+/-</th>
            <th className="px-2 py-2 text-center">Val</th>
          </tr>
        </thead>
        <tbody>
          {renderRows(starters)}
          {bench.length > 0 && (
            <tr>
              <td colSpan={12} className="px-2 py-1 text-[10px] font-semibold text-text-secondary bg-bg-card">
                BANQUILLO
              </td>
            </tr>
          )}
          {renderRows(bench)}
        </tbody>
      </table>
    </div>
  );
}
