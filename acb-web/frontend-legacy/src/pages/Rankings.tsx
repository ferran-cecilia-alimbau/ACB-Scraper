import { useState } from 'react';
import { usePlayerRankings, useTeamRankings } from '../hooks/useApi';
import { PageHeader } from '../components/PageHeader';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { TeamBadge } from '../components/TeamBadge';
import { teamColor } from '../lib/formatters';
import type { PlayerRanking, TeamRanking } from '../types';

const PLAYER_STATS = [
  { value: 'puntos_avg', label: 'Puntos' },
  { value: 'rebotes_totales_avg', label: 'Rebotes' },
  { value: 'asistencias_avg', label: 'Asistencias' },
  { value: 'robos_avg', label: 'Robos' },
  { value: 'perdidas_avg', label: 'Pérdidas' },
  { value: 'tapones_favor_avg', label: 'Tapones' },
  { value: 'valoracion_avg', label: 'Valoración' },
  { value: 'efg_pct', label: 'eFG%' },
  { value: 'ts_pct', label: 'TS%' },
  { value: 't3_pct', label: 'T3%' },
];

export default function Rankings() {
  const [tab, setTab] = useState<'players' | 'teams'>('players');
  const [stat, setStat] = useState('puntos_avg');
  const { data: playerRankings, isLoading: prl, isError: pre } = usePlayerRankings(stat);
  const { data: teamRankings, isLoading: trl, isError: tre } = useTeamRankings();

  const typedPR = (playerRankings || []) as PlayerRanking[];
  const typedTR = (teamRankings || []) as TeamRanking[];

  return (
    <div>
      <PageHeader title="Rankings" subtitle="Líderes de la temporada" />

      <div className="flex gap-1 mb-6 rounded-lg bg-bg-card p-1 w-fit">
        <button
          onClick={() => setTab('players')}
          className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
            tab === 'players' ? 'bg-accent text-white font-medium' : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          Jugadores
        </button>
        <button
          onClick={() => setTab('teams')}
          className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
            tab === 'teams' ? 'bg-accent text-white font-medium' : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          Equipos
        </button>
      </div>

      {tab === 'players' && (
        <div>
          <div className="flex flex-wrap gap-2 mb-4">
            {PLAYER_STATS.map((s) => (
              <button
                key={s.value}
                onClick={() => setStat(s.value)}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                  stat === s.value
                    ? 'border-accent bg-accent/15 text-accent'
                    : 'border-border text-text-secondary hover:text-text-primary'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>

          {prl ? (
            <Loading />
          ) : pre ? (
            <ErrorMessage />
          ) : typedPR.length === 0 ? (
            <p className="text-sm text-text-secondary py-4">No hay datos disponibles para esta estadística</p>
          ) : (
            <div className="space-y-1">
              {typedPR.map((p) => {
                const maxVal = typedPR[0]?.value ?? 1;
                return (
                  <div
                    key={p.player_id}
                    className="flex items-center gap-3 rounded-lg border border-border bg-bg-card px-4 py-2.5 hover:bg-bg-hover transition-colors"
                  >
                    <span className="w-8 text-sm font-bold text-text-secondary">{p.rank}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{p.nombre}</p>
                      <TeamBadge name={p.equipo} color={p.color} />
                    </div>
                    <div className="w-48 flex items-center gap-2">
                      <div className="flex-1 h-2 rounded-full bg-bg-hover overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${(p.value / maxVal) * 100}%`,
                            backgroundColor: teamColor(p.color),
                          }}
                        />
                      </div>
                      <span className="w-12 text-right text-sm font-bold tabular-nums">{p.value.toFixed(1)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {tab === 'teams' && (
        <div>
          {trl ? (
            <Loading />
          ) : tre ? (
            <ErrorMessage />
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-bg-card text-xs text-text-secondary">
                    <th className="px-3 py-2.5 text-left">Equipo</th>
                    <th className="px-3 py-2.5 text-center">ORtg</th>
                    <th className="px-3 py-2.5 text-center">DRtg</th>
                    <th className="px-3 py-2.5 text-center">NetRtg</th>
                    <th className="px-3 py-2.5 text-center">Pace</th>
                    <th className="px-3 py-2.5 text-center">eFG%</th>
                    <th className="px-3 py-2.5 text-center">TS%</th>
                    <th className="px-3 py-2.5 text-center">PPG</th>
                    <th className="px-3 py-2.5 text-center">RPG</th>
                    <th className="px-3 py-2.5 text-center">APG</th>
                  </tr>
                </thead>
                <tbody>
                  {typedTR.map((t, i) => (
                    <tr key={t.equipo} className="border-b border-border hover:bg-bg-hover transition-colors">
                      <td className="px-3 py-2">
                        <span className="inline-flex items-center gap-2">
                          <span className="text-xs text-text-secondary">{i + 1}</span>
                          <TeamBadge name={t.equipo} color={t.color} size="md" />
                        </span>
                      </td>
                      <td className="px-3 py-2 text-center tabular-nums">{t.ortg.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center tabular-nums">{t.drtg.toFixed(1)}</td>
                      <td className={`px-3 py-2 text-center tabular-nums font-medium ${t.net_rtg > 0 ? 'text-success' : 'text-danger'}`}>
                        {t.net_rtg > 0 ? '+' : ''}{t.net_rtg.toFixed(1)}
                      </td>
                      <td className="px-3 py-2 text-center tabular-nums">{t.pace.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center tabular-nums">{t.efg_pct.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center tabular-nums">{t.ts_pct.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center tabular-nums">{t.ppg.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center tabular-nums">{t.rpg.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center tabular-nums">{t.apg.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
