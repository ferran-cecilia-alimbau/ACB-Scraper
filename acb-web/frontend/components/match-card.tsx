import Link from 'next/link';
import { TeamMonogram } from '@/components/team-monogram';
import { teamMeta } from '@/lib/teams';
import { formatDateShort, parseParciales } from '@/lib/format';
import type { GameSummary } from '@/lib/api';

interface MatchCardProps {
  game: GameSummary;
  parciales_local?: string;
  parciales_visitante?: string;
}

export function MatchCard({ game, parciales_local, parciales_visitante }: MatchCardProps) {
  const localWon = game.resultado_local > game.resultado_visitante;
  const visitWon = game.resultado_visitante > game.resultado_local;
  const localMeta = teamMeta(game.local);
  const visitMeta = teamMeta(game.visitante);
  const pl = parseParciales(parciales_local || '');
  const pv = parseParciales(parciales_visitante || '');

  return (
    <Link
      href={`/partido/${game.id_partido}`}
      className="block bg-[var(--bg-elev)] border border-[var(--rule)] p-6 hover:border-[var(--rule-strong)] transition-colors group"
    >
      <div className="flex items-center justify-between mb-5 text-xs text-[var(--ink-muted)]">
        <span className="kicker">J{game.jornada_num}</span>
        <span className="font-mono uppercase tracking-wider">
          {formatDateShort(game.fecha)}
        </span>
      </div>

      <div className="grid grid-cols-[1fr_auto] gap-4 items-center">
        <Row
          name={localMeta.short}
          teamName={game.local}
          score={game.resultado_local}
          won={localWon}
        />
        <div />
        <Row
          name={visitMeta.short}
          teamName={game.visitante}
          score={game.resultado_visitante}
          won={visitWon}
        />
        <div />
      </div>

      {pl.length > 0 && pv.length > 0 && (
        <div className="mt-5 pt-4 border-t border-[var(--rule)]">
          <table className="w-full text-[0.72rem] font-mono text-[var(--ink-muted)]">
            <thead>
              <tr>
                <th className="text-left font-medium pb-1">Parciales</th>
                {pl.map((_, i) => (
                  <th key={i} className="text-right font-medium pb-1">
                    Q{i + 1}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="text-left py-0.5 pr-2">L</td>
                {pl.map(([a], i) => (
                  <td key={i} className="text-right tabular-nums">
                    {a}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="text-left py-0.5 pr-2">V</td>
                {pv.map(([a], i) => (
                  <td key={i} className="text-right tabular-nums">
                    {a}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-5 flex items-center gap-1 text-[0.72rem] uppercase tracking-[0.18em] text-[var(--ink-muted)]">
        <span className="link-underline">Ficha</span>
        <span aria-hidden>→</span>
      </div>
    </Link>
  );
}

function Row({
  name,
  teamName,
  score,
  won,
}: {
  name: string;
  teamName: string;
  score: number;
  won: boolean;
}) {
  return (
    <>
      <div className="flex items-center gap-3 min-w-0">
        <TeamMonogram name={teamName} size="sm" />
        <span
          className={`text-[0.95rem] font-sans truncate ${
            won ? 'font-semibold text-[var(--ink)]' : 'text-[var(--ink-muted)]'
          }`}
        >
          {name}
        </span>
      </div>
      <span
        className={`score-md ${won ? 'text-[var(--ink)]' : 'text-[var(--ink-muted)]'}`}
      >
        {score}
      </span>
    </>
  );
}
