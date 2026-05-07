import { useState } from 'react';
import { useGames, useGameClutch, useGameTimeline } from '../hooks/useApi';
import { PageHeader } from '../components/PageHeader';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { TimelineChart } from '../components/charts/TimelineChart';
import { teamColor } from '../lib/formatters';
import type { GameSummary, ClutchData } from '../types';

export default function Clutch() {
  const { data: games, isLoading: gl, isError: gerr } = useGames();
  const [gameId, setGameId] = useState(0);
  const [threshold, setThreshold] = useState(5);
  const { data: clutchData, isLoading: cl, isError: cerr } = useGameClutch(gameId, threshold);
  const { data: timeline } = useGameTimeline(gameId);
  const [tab, setTab] = useState<'timeline' | 'stats' | 'events'>('timeline');

  const typedGames = (games || []) as GameSummary[];
  const data = clutchData as ClutchData | undefined;
  const hasError = data && 'error' in data;
  const typedTimeline = (timeline || []) as Array<{ diff: number }>;
  const game = typedGames.find((g) => g.id_partido === gameId);

  if (gl) return <Loading />;
  if (gerr) return <ErrorMessage />;

  return (
    <div>
      <PageHeader title="Clutch" subtitle="Análisis de momentos decisivos" />

      <div className="flex flex-wrap gap-4 mb-6">
        <select
          value={gameId || ''}
          onChange={(e) => setGameId(Number(e.target.value))}
          className="max-w-md rounded-lg border border-border bg-bg-card px-3 py-2 text-sm outline-none focus:border-accent"
        >
          <option value="">Seleccionar partido...</option>
          {typedGames.map((g) => (
            <option key={g.id_partido} value={g.id_partido}>
              J{g.jornada_num} — {g.local} {g.resultado_local}-{g.resultado_visitante} {g.visitante}
            </option>
          ))}
        </select>
        <div className="flex items-center gap-2">
          <label className="text-xs text-text-secondary">Umbral:</label>
          <select
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="rounded-lg border border-border bg-bg-card px-2 py-2 text-sm outline-none"
          >
            {[3, 5, 7, 10].map((t) => (
              <option key={t} value={t}>±{t} pts</option>
            ))}
          </select>
        </div>
      </div>

      {/* Empty state: no game selected */}
      {!gameId && (
        <div className="rounded-lg border-2 border-dashed border-border p-12 text-center text-text-secondary">
          <p className="text-lg font-medium">Selecciona un partido</p>
          <p className="text-sm mt-1">Elige un partido del desplegable para ver el análisis clutch</p>
        </div>
      )}

      {gameId > 0 && cl && <Loading />}
      {gameId > 0 && cerr && <ErrorMessage />}

      {/* Error state: PBP not available */}
      {gameId > 0 && !cl && hasError && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 p-8 text-center">
          <p className="text-lg font-medium text-danger">No hay datos PBP disponibles</p>
          <p className="text-sm mt-1 text-text-secondary">Este partido no tiene datos de play-by-play para analizar momentos clutch</p>
        </div>
      )}

      {data && !hasError && game && (
        <div>
          <div className="flex gap-1 mb-4 rounded-lg bg-bg-card p-1 w-fit">
            {[
              { id: 'timeline', label: 'Timeline' },
              { id: 'stats', label: 'Stats Clutch' },
              { id: 'events', label: 'Eventos' },
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

          {tab === 'timeline' && typedTimeline.length > 0 && (
            <div className="rounded-lg border border-border bg-bg-card p-4">
              <h3 className="text-sm font-medium mb-3 text-text-secondary">
                Score diferencia (zona clutch: ±{threshold} pts)
              </h3>
              <TimelineChart
                data={typedTimeline.map((t, i) => ({ index: i, diff: t.diff }))}
                localColor={teamColor(game.local_color)}
                visitanteColor={teamColor(game.visitante_color)}
                height={350}
              />
            </div>
          )}

          {tab === 'stats' && data.stats.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-bg-card text-xs text-text-secondary">
                    {Object.keys(data.stats[0]).map((key) => (
                      <th key={key} className="px-3 py-2 text-center">{key}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.stats.map((row, i) => (
                    <tr key={i} className="border-b border-border hover:bg-bg-hover transition-colors">
                      {Object.values(row).map((val, j) => (
                        <td key={j} className="px-3 py-2 text-center tabular-nums">
                          {typeof val === 'number' ? (Number.isInteger(val) ? val : Number(val).toFixed(1)) : String(val)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tab === 'events' && (
            <div className="space-y-1 max-h-[600px] overflow-y-auto">
              {data.events.map((e, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-3 rounded border px-3 py-2 text-xs border-border bg-bg-card ${
                    e.equipo === 'LOCAL' ? 'border-l-2' : 'border-r-2'
                  }`}
                  style={
                    e.equipo === 'LOCAL'
                      ? { borderLeftColor: teamColor(game.local_color) }
                      : { borderRightColor: teamColor(game.visitante_color) }
                  }
                >
                  <span className="text-text-secondary w-12">{e.periodo} {e.tiempo}</span>
                  <span className="tabular-nums w-16 text-center font-medium">{e.marcador_local}-{e.marcador_visitante}</span>
                  <span className="text-text-secondary w-16">{e.equipo}</span>
                  <span className="font-medium">{e.jugador}</span>
                  <span className="text-text-secondary">{e.accion}</span>
                </div>
              ))}
              {data.events.length === 0 && (
                <p className="text-text-secondary text-sm py-4">No hay eventos clutch en este partido con umbral ±{threshold}</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
