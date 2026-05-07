import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTeams, useTeam } from '../hooks/useApi';
import { PageHeader } from '../components/PageHeader';
import { StatCard } from '../components/StatCard';
import { TeamBadge } from '../components/TeamBadge';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { teamColor } from '../lib/formatters';
import type { TeamSummary, TeamDetail } from '../types';

export default function Equipo() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedTeam = searchParams.get('team') || '';
  const { data: teams, isLoading: tl, isError: te } = useTeams();
  const { data: teamDetail, isLoading: dl, isError: de } = useTeam(selectedTeam);
  const [tab, setTab] = useState<'stats' | 'roster' | 'games'>('stats');

  const typedTeams = (teams || []) as TeamSummary[];
  const detail = teamDetail as TeamDetail | undefined;

  if (tl) return <Loading />;
  if (te) return <ErrorMessage />;

  return (
    <div>
      <PageHeader title="Equipos" subtitle="Selecciona un equipo para ver sus estadísticas" />

      {/* Team selector */}
      <div className="flex flex-wrap gap-2 mb-6">
        {typedTeams.map((t) => (
          <button
            key={t.name}
            onClick={() => setSearchParams({ team: t.name })}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors border ${
              selectedTeam === t.name
                ? 'border-accent bg-accent/15 text-accent'
                : 'border-border bg-bg-card text-text-secondary hover:bg-bg-hover hover:text-text-primary'
            }`}
          >
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: teamColor(t.color) }} />
            {t.name}
          </button>
        ))}
      </div>

      {!selectedTeam && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {typedTeams.map((t) => (
            <button
              key={t.name}
              onClick={() => setSearchParams({ team: t.name })}
              className="rounded-lg border border-border bg-bg-card p-4 text-left transition-colors hover:bg-bg-hover"
            >
              <div className="flex items-center justify-between">
                <TeamBadge name={t.name} color={t.color} size="md" />
                <span className="text-xs text-text-secondary">#{t.pos}</span>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                <div>
                  <p className="text-lg font-bold">{t.wins}-{t.losses}</p>
                  <p className="text-[10px] text-text-secondary">Balance</p>
                </div>
                <div>
                  <p className="text-lg font-bold">{t.ppg}</p>
                  <p className="text-[10px] text-text-secondary">PPG</p>
                </div>
                <div>
                  <p className="text-lg font-bold">{t.rpg}</p>
                  <p className="text-[10px] text-text-secondary">RPG</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {selectedTeam && dl && <Loading />}
      {selectedTeam && de && <ErrorMessage />}

      {selectedTeam && detail && !('error' in detail) && (
        <div>
          {/* Header */}
          <div className="flex items-center gap-4 mb-6">
            <div
              className="h-12 w-1 rounded-full"
              style={{ backgroundColor: teamColor(detail.color) }}
            />
            <div>
              <h2 className="text-xl font-bold">{detail.name}</h2>
              <p className="text-sm text-text-secondary">#{detail.pos} en la clasificación</p>
            </div>
          </div>

          {/* KPIs */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6 mb-6">
            <StatCard label="Record" value={`${detail.standings.G || 0}-${detail.standings.P || 0}`} accentColor={teamColor(detail.color)} />
            <StatCard label="PPG" value={detail.season_avgs.puntos} accentColor={teamColor(detail.color)} />
            <StatCard label="RPG" value={detail.season_avgs.rebotes_totales} accentColor={teamColor(detail.color)} />
            <StatCard label="APG" value={detail.season_avgs.asistencias} accentColor={teamColor(detail.color)} />
            <StatCard label="ORtg" value={detail.season_avgs.ortg} accentColor={teamColor(detail.color)} />
            <StatCard label="DRtg" value={detail.season_avgs.drtg} accentColor={teamColor(detail.color)} />
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mb-4 rounded-lg bg-bg-card p-1 w-fit">
            {[
              { id: 'stats', label: 'Estadísticas' },
              { id: 'roster', label: 'Plantilla' },
              { id: 'games', label: 'Resultados' },
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
                <h3 className="text-sm font-medium mb-3 text-text-secondary">Tiro</h3>
                <div className="space-y-3">
                  {[
                    { label: 'T2%', value: detail.season_avgs.t2_pct },
                    { label: 'T3%', value: detail.season_avgs.t3_pct },
                    { label: 'TL%', value: detail.season_avgs.tl_pct },
                    { label: 'eFG%', value: detail.season_avgs.efg_pct },
                    { label: 'TS%', value: detail.season_avgs.ts_pct },
                  ].map((s) => (
                    <div key={s.label} className="flex items-center gap-3">
                      <span className="w-12 text-xs text-text-secondary">{s.label}</span>
                      <div className="flex-1 h-2 rounded-full bg-bg-hover overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{ width: `${s.value}%`, backgroundColor: teamColor(detail.color) }}
                        />
                      </div>
                      <span className="w-12 text-right text-xs font-medium">{s.value?.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-border bg-bg-card p-4">
                <h3 className="text-sm font-medium mb-3 text-text-secondary">Avanzadas</h3>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: 'ORtg', value: detail.season_avgs.ortg },
                    { label: 'DRtg', value: detail.season_avgs.drtg },
                    { label: 'NetRtg', value: detail.season_avgs.net_rtg },
                    { label: 'Pace', value: detail.season_avgs.pace },
                    { label: 'Robos', value: detail.season_avgs.robos },
                    { label: 'Pérdidas', value: detail.season_avgs.perdidas },
                  ].map((s) => (
                    <div key={s.label} className="text-center">
                      <p className="text-xl font-bold">{s.value?.toFixed(1)}</p>
                      <p className="text-[10px] text-text-secondary">{s.label}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === 'roster' && (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-bg-card text-xs text-text-secondary">
                    <th className="px-3 py-2 text-left">#</th>
                    <th className="px-3 py-2 text-left">Jugador</th>
                    <th className="px-3 py-2 text-center">Pos</th>
                    <th className="px-3 py-2 text-center">Altura</th>
                    <th className="px-3 py-2 text-center">Edad</th>
                    <th className="px-3 py-2 text-left">Nac.</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.roster.map((p) => (
                    <tr key={p.player_id} className="border-b border-border hover:bg-bg-hover transition-colors">
                      <td className="px-3 py-2 text-text-secondary">{p.dorsal}</td>
                      <td className="px-3 py-2 font-medium">{p.nombre}</td>
                      <td className="px-3 py-2 text-center text-text-secondary">{p.posicion_full || p.posicion}</td>
                      <td className="px-3 py-2 text-center">{p.altura ? `${p.altura} cm` : '-'}</td>
                      <td className="px-3 py-2 text-center">{p.edad || '-'}</td>
                      <td className="px-3 py-2 text-text-secondary">{p.nacionalidad}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tab === 'games' && (
            <div className="space-y-2">
              {detail.games.map((g) => (
                <div
                  key={g.id_partido}
                  className={`flex items-center gap-4 rounded-lg border bg-bg-card px-4 py-3 transition-colors hover:bg-bg-hover ${
                    g.win ? 'border-success/20' : 'border-danger/20'
                  }`}
                >
                  <span className="text-xs text-text-secondary w-8">J{g.jornada_num}</span>
                  <span className={`text-xs font-medium ${g.win ? 'text-success' : 'text-danger'}`}>
                    {g.win ? 'V' : 'D'}
                  </span>
                  <div className="flex-1 text-sm">
                    <span className={g.is_home ? 'font-medium' : 'text-text-secondary'}>
                      {g.local}
                    </span>
                    <span className="mx-2 text-text-secondary">
                      {g.resultado_local} - {g.resultado_visitante}
                    </span>
                    <span className={!g.is_home ? 'font-medium' : 'text-text-secondary'}>
                      {g.visitante}
                    </span>
                  </div>
                  <span className="text-xs text-text-secondary">{g.fecha}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
