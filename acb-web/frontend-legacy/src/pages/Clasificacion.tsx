import { useMemo, useState } from 'react';
import { useStandings, useStandingsEvolution, useTeamRankings } from '../hooks/useApi';
import { PageHeader } from '../components/PageHeader';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { TeamBadge } from '../components/TeamBadge';
import { LineChart } from '../components/charts/LineChart';
import { ScatterChart } from '../components/charts/ScatterChart';
import { ColoredBarChart } from '../components/charts/BarChart';
import { teamColor } from '../lib/formatters';
import { TEAM_COLORS } from '../lib/constants';
import type { Standing, StandingsEvolution, TeamRanking } from '../types';

export default function Clasificacion() {
  const { data: standings, isLoading: sl, isError: serr } = useStandings();
  const { data: evolution, isLoading: el, isError: eerr } = useStandingsEvolution();
  const { data: teamRankings, isLoading: rl, isError: rerr } = useTeamRankings();
  const [tab, setTab] = useState<'tabla' | 'evolution' | 'scatter' | 'diff'>('tabla');

  const typedStandings = (standings || []) as Standing[];
  const typedEvolution = (evolution || []) as StandingsEvolution[];
  const typedRankings = (teamRankings || []) as TeamRanking[];

  // Evolution chart data: pivot to {jornada, team1: pos, team2: pos, ...}
  const evolutionData = useMemo(() => {
    const jornadas = [...new Set(typedEvolution.map((e) => e.jornada_num))].sort((a, b) => a - b);
    return jornadas.map((j) => {
      const row: Record<string, unknown> = { jornada: j };
      typedEvolution
        .filter((e) => e.jornada_num === j)
        .forEach((e) => { row[e.equipo] = e.posicion; });
      return row;
    });
  }, [typedEvolution]);

  const teams = [...new Set(typedEvolution.map((e) => e.equipo))];

  if (sl || el || rl) return <Loading />;
  if (serr || eerr || rerr) return <ErrorMessage />;

  return (
    <div>
      <PageHeader title="Clasificación" subtitle="Liga Endesa 2024-25" />

      {/* Tabs */}
      <div className="flex gap-1 mb-6 rounded-lg bg-bg-card p-1 w-fit">
        {[
          { id: 'tabla', label: 'Tabla' },
          { id: 'evolution', label: 'Evolución' },
          { id: 'scatter', label: 'ORtg vs DRtg' },
          { id: 'diff', label: 'Diferencial' },
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

      {tab === 'tabla' && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-bg-card text-xs font-semibold uppercase text-text-secondary">
                <th className="px-3 py-2.5 text-left">#</th>
                <th className="px-3 py-2.5 text-left">Equipo</th>
                <th className="px-3 py-2.5 text-center">J</th>
                <th className="px-3 py-2.5 text-center">G</th>
                <th className="px-3 py-2.5 text-center">P</th>
                <th className="px-3 py-2.5 text-center">%</th>
                <th className="px-3 py-2.5 text-center">PF</th>
                <th className="px-3 py-2.5 text-center">PC</th>
                <th className="px-3 py-2.5 text-center">Dif</th>
                <th className="px-3 py-2.5 text-center">Casa</th>
                <th className="px-3 py-2.5 text-center">Fuera</th>
              </tr>
            </thead>
            <tbody>
              {typedStandings.map((s) => {
                const colors = TEAM_COLORS[s.equipo] || ['#666', '#999'];
                return (
                  <tr key={s.equipo} className="border-b border-border hover:bg-bg-hover transition-colors">
                    <td className="px-3 py-2 font-medium text-text-secondary">{s.pos}</td>
                    <td className="px-3 py-2">
                      <TeamBadge name={s.equipo} color={colors[0]} size="md" />
                    </td>
                    <td className="px-3 py-2 text-center tabular-nums">{s.J}</td>
                    <td className="px-3 py-2 text-center tabular-nums font-medium text-success">{s.G}</td>
                    <td className="px-3 py-2 text-center tabular-nums text-danger">{s.P}</td>
                    <td className="px-3 py-2 text-center tabular-nums">{s.pct.toFixed(1)}</td>
                    <td className="px-3 py-2 text-center tabular-nums">{s.PF}</td>
                    <td className="px-3 py-2 text-center tabular-nums">{s.PC}</td>
                    <td className={`px-3 py-2 text-center tabular-nums font-medium ${s.Dif > 0 ? 'text-success' : 'text-danger'}`}>
                      {s.Dif > 0 ? '+' : ''}{s.Dif}
                    </td>
                    <td className="px-3 py-2 text-center tabular-nums text-xs">{s.G_casa}-{s.P_casa}</td>
                    <td className="px-3 py-2 text-center tabular-nums text-xs">{s.G_fuera}-{s.P_fuera}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'evolution' && (
        <div className="rounded-lg border border-border bg-bg-card p-4">
          <h3 className="text-sm font-medium mb-3 text-text-secondary">Posición por jornada</h3>
          <LineChart
            data={evolutionData}
            xKey="jornada"
            lines={teams.map((t) => ({
              key: t,
              color: TEAM_COLORS[t]?.[0] || '#666',
              name: t,
            }))}
            height={500}
            invertY
          />
        </div>
      )}

      {tab === 'scatter' && (
        <div className="rounded-lg border border-border bg-bg-card p-4">
          <h3 className="text-sm font-medium mb-3 text-text-secondary">Rating Ofensivo vs Defensivo</h3>
          <ScatterChart
            data={typedRankings.map((t) => ({
              name: t.equipo,
              x: t.ortg,
              y: t.drtg,
              color: t.color,
            }))}
            xLabel="ORtg (mejor →)"
            yLabel="DRtg (← mejor)"
            height={450}
          />
        </div>
      )}

      {tab === 'diff' && (
        <div className="rounded-lg border border-border bg-bg-card p-4">
          <h3 className="text-sm font-medium mb-3 text-text-secondary">Net Rating por equipo</h3>
          <ColoredBarChart
            data={typedRankings.map((t) => ({
              name: t.equipo,
              value: t.net_rtg,
              color: t.net_rtg > 0 ? '#10b981' : '#ef4444',
            }))}
            height={500}
            layout="horizontal"
          />
        </div>
      )}
    </div>
  );
}
