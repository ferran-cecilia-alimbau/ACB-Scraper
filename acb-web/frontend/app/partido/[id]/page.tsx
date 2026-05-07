import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getGame } from '@/lib/api';
import { Kicker } from '@/components/kicker';
import { BoxScore } from '@/components/boxscore';
import { TeamMonogram } from '@/components/team-monogram';
import { teamMeta } from '@/lib/teams';
import { formatDate, parseParciales } from '@/lib/format';

export const revalidate = 60;
export const dynamic = 'force-dynamic';

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return {
    title: `Partido #${id}`,
    description: `Boxscore detallado del partido ${id} de la Liga Endesa 2025-26.`,
  };
}

export default async function PartidoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const gameId = parseInt(id, 10);
  if (!Number.isFinite(gameId)) notFound();

  let game;
  try {
    game = await getGame(gameId);
  } catch {
    notFound();
  }
  if (!game || 'error' in game) notFound();

  const localMeta = teamMeta(game.local);
  const visitMeta = teamMeta(game.visitante);
  const localWon = game.resultado_local > game.resultado_visitante;
  const visitWon = game.resultado_visitante > game.resultado_local;
  const pl = parseParciales(game.parciales_local);
  const pv = parseParciales(game.parciales_visitante);

  return (
    <>
      {/* Hero */}
      <section className="border-b border-[var(--rule)]">
        <div className="container-editorial py-12 sm:py-16">
          <div className="flex flex-wrap items-center gap-4 mb-8 text-xs text-[var(--ink-muted)]">
            <Kicker className="inline-flex">
              <Link href={`/jornada/${game.jornada_num}`} className="link-underline">
                Jornada {game.jornada_num}
              </Link>
            </Kicker>
            <span aria-hidden>·</span>
            <span className="font-mono uppercase tracking-wider">
              {formatDate(game.fecha)}
            </span>
            {game.pabellon && (
              <>
                <span aria-hidden>·</span>
                <span>{game.pabellon}</span>
              </>
            )}
            {game.publico > 0 && (
              <>
                <span aria-hidden>·</span>
                <span>{game.publico.toLocaleString('es-ES')} espectadores</span>
              </>
            )}
          </div>

          <div className="grid grid-cols-[1fr_auto_1fr] gap-6 sm:gap-12 items-end">
            <TeamSide
              name={localMeta.short}
              teamName={game.local}
              score={game.resultado_local}
              won={localWon}
              align="right"
            />
            <span className="font-serif italic text-[var(--ink-muted)] text-2xl sm:text-3xl pb-3 select-none">
              vs
            </span>
            <TeamSide
              name={visitMeta.short}
              teamName={game.visitante}
              score={game.resultado_visitante}
              won={visitWon}
              align="left"
            />
          </div>

          {pl.length > 0 && (
            <div className="mt-12 max-w-md mx-auto">
              <table className="w-full text-sm font-mono">
                <thead>
                  <tr className="text-[var(--ink-muted)] text-[0.7rem] uppercase tracking-[0.16em]">
                    <th className="text-left font-medium pb-2">Parciales</th>
                    {pl.map((_, i) => (
                      <th key={i} className="text-right font-medium pb-2">
                        Q{i + 1}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="text-left py-1.5 border-t border-[var(--rule)]">
                      {localMeta.short}
                    </td>
                    {pl.map(([a], i) => (
                      <td key={i} className="text-right tabular-nums py-1.5 border-t border-[var(--rule)]">
                        {a}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="text-left py-1.5 border-t border-[var(--rule)]">
                      {visitMeta.short}
                    </td>
                    {pl.map((_, i) => (
                      <td key={i} className="text-right tabular-nums py-1.5 border-t border-[var(--rule)]">
                        {pv[i]?.[0] ?? '—'}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* Boxscores */}
      <section>
        <div className="container-editorial py-12 grid gap-12 lg:grid-cols-1">
          <BoxScore team={game.local} players={game.box_score.local} />
          <BoxScore team={game.visitante} players={game.box_score.visitante} />
        </div>
      </section>
    </>
  );
}

function TeamSide({
  name,
  teamName,
  score,
  won,
  align,
}: {
  name: string;
  teamName: string;
  score: number;
  won: boolean;
  align: 'left' | 'right';
}) {
  return (
    <div className={align === 'right' ? 'text-right' : 'text-left'}>
      <div className={`flex items-center gap-3 mb-3 ${align === 'right' ? 'justify-end' : ''}`}>
        <TeamMonogram name={teamName} size="lg" />
      </div>
      <p
        className={`font-sans uppercase tracking-[0.14em] text-xs sm:text-sm mb-2 ${
          won ? 'text-[var(--ink)] font-semibold' : 'text-[var(--ink-muted)]'
        }`}
      >
        {name}
      </p>
      <p
        className={`score-xl ${
          won ? 'text-[var(--ink)]' : 'text-[var(--ink-muted)]'
        }`}
      >
        {score}
      </p>
    </div>
  );
}
