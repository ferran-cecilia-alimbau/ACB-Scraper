import { Link } from 'react-router-dom';
import { useStandings, useGames, useLeagueAverages } from '../hooks/useApi';
import { StatCard } from '../components/StatCard';
import { TeamBadge } from '../components/TeamBadge';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { teamColor } from '../lib/formatters';
import { SEASON } from '../lib/constants';
import type { Standing, GameSummary } from '../types';

export default function Home() {
  const { data: standings, isLoading: sl, isError: se } = useStandings();
  const { data: games, isLoading: gl, isError: ge } = useGames();
  const { data: avgs, isLoading: al, isError: ae } = useLeagueAverages();

  if (sl || gl || al) return <Loading />;
  if (se || ge || ae) return <ErrorMessage />;

  const typedStandings = (standings || []) as Standing[];
  const typedGames = (games || []) as GameSummary[];
  const typedAvgs = (avgs || {}) as Record<string, number>;

  const maxJornada = typedGames.length > 0 ? Math.max(...typedGames.map((g) => g.jornada_num)) : 0;
  const lastRound = typedGames.filter((g) => g.jornada_num === maxJornada);

  return (
    <div>
      {/* Hero */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-accent">ACB</span> Liga Endesa
        </h1>
        <p className="mt-1 text-text-secondary">Estadísticas avanzadas temporada {SEASON}</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-8">
        <StatCard label="Jornadas" value={maxJornada} />
        <StatCard label="Partidos" value={typedGames.length} />
        <StatCard label="Pts/Partido" value={typedAvgs.pts?.toFixed(1) || '0'} />
        <StatCard label="Equipos" value={typedStandings.length} />
      </div>

      {/* Last round */}
      {lastRound.length > 0 && (
        <>
          <h2 className="text-lg font-semibold mb-3">Jornada {maxJornada}</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 mb-8">
            {lastRound.map((g) => {
              const localWon = g.resultado_local > g.resultado_visitante;
              return (
                <Link
                  key={g.id_partido}
                  to={`/partidos?id=${g.id_partido}`}
                  className="rounded-lg border border-border bg-bg-card p-4 transition-colors duration-150 hover:bg-bg-hover"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className={`flex items-center gap-2 ${localWon ? 'font-bold' : 'text-text-secondary'}`}>
                        <span
                          className="h-2 w-2 rounded-full inline-block"
                          style={{ backgroundColor: teamColor(g.local_color) }}
                        />
                        <span className="text-sm">{g.local}</span>
                        <span className="ml-auto text-sm tabular-nums">{g.resultado_local}</span>
                      </div>
                      <div className={`flex items-center gap-2 mt-1 ${!localWon ? 'font-bold' : 'text-text-secondary'}`}>
                        <span
                          className="h-2 w-2 rounded-full inline-block"
                          style={{ backgroundColor: teamColor(g.visitante_color) }}
                        />
                        <span className="text-sm">{g.visitante}</span>
                        <span className="ml-auto text-sm tabular-nums">{g.resultado_visitante}</span>
                      </div>
                    </div>
                  </div>
                  <p className="mt-2 text-[10px] text-text-secondary">{g.fecha}</p>
                </Link>
              );
            })}
          </div>
        </>
      )}

      {/* Standings preview */}
      <h2 className="text-lg font-semibold mb-3">Clasificación</h2>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-bg-card text-xs text-text-secondary">
              <th className="px-3 py-2 text-left">#</th>
              <th className="px-3 py-2 text-left">Equipo</th>
              <th className="px-3 py-2 text-center">J</th>
              <th className="px-3 py-2 text-center">G</th>
              <th className="px-3 py-2 text-center">P</th>
              <th className="px-3 py-2 text-center">Dif</th>
            </tr>
          </thead>
          <tbody>
            {typedStandings.map((s) => (
              <tr
                key={s.equipo}
                className={`border-b border-border transition-colors hover:bg-bg-hover ${
                  s.pos <= 8 ? '' : s.pos >= 17 ? 'opacity-60' : ''
                }`}
              >
                <td className="px-3 py-2 text-text-secondary">{s.pos}</td>
                <td className="px-3 py-2">
                  <Link to={`/equipos?team=${encodeURIComponent(s.equipo)}`}>
                    <TeamBadge
                      name={s.equipo}
                      color={teamColor(
                        (typedGames.find((g) => g.local === s.equipo)?.local_color) || '#666'
                      )}
                    />
                  </Link>
                </td>
                <td className="px-3 py-2 text-center tabular-nums">{s.J}</td>
                <td className="px-3 py-2 text-center tabular-nums text-success">{s.G}</td>
                <td className="px-3 py-2 text-center tabular-nums text-danger">{s.P}</td>
                <td className={`px-3 py-2 text-center tabular-nums ${s.Dif > 0 ? 'text-success' : 'text-danger'}`}>
                  {s.Dif > 0 ? '+' : ''}{s.Dif}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
