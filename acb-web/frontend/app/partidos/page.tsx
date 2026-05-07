import Link from 'next/link';
import { getGames } from '@/lib/api';
import { Kicker } from '@/components/kicker';
import { MatchCard } from '@/components/match-card';

export const revalidate = 60;
export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Partidos',
  description: 'Listado de partidos por jornada de la Liga Endesa 2025-26.',
};

export default async function PartidosPage() {
  const games = await getGames();
  const jornadas = Array.from(
    new Set(games.map((g) => g.jornada_num).filter((n): n is number => n != null)),
  ).sort((a, b) => b - a);

  const latest = jornadas[0];

  return (
    <>
      <section className="border-b border-[var(--rule)]">
        <div className="container-editorial py-14 sm:py-20">
          <Kicker className="mb-4 inline-block">Calendario</Kicker>
          <h1 className="headline max-w-3xl mb-5">Partidos por jornada</h1>
          <p className="lede max-w-2xl">
            Toda la temporada en orden inverso, jornada a jornada. Cada tarjeta abre
            el boxscore íntegro del encuentro.
          </p>
        </div>
      </section>

      <section>
        <div className="container-editorial py-10">
          <nav
            aria-label="Saltar a jornada"
            className="flex flex-wrap gap-2 mb-12 text-sm"
          >
            {jornadas.map((j) => (
              <Link
                key={j}
                href={`/jornada/${j}`}
                className="border border-[var(--rule)] px-3 py-1.5 hover:border-[var(--rule-strong)] transition-colors text-[var(--ink-muted)] hover:text-[var(--ink)]"
              >
                J{j}
              </Link>
            ))}
          </nav>

          {jornadas.map((j) => {
            const slate = games.filter((g) => g.jornada_num === j);
            return (
              <article key={j} id={`jornada-${j}`} className="mb-16">
                <header className="flex items-baseline justify-between gap-4 mb-6 pb-3 border-b border-[var(--rule-strong)]">
                  <div>
                    <Kicker className="block mb-1">{j === latest ? 'Última' : 'Jornada'}</Kicker>
                    <h2 className="font-serif text-2xl sm:text-3xl">Jornada {j}</h2>
                  </div>
                  <Link
                    href={`/jornada/${j}`}
                    className="text-sm link-underline text-[var(--ink-muted)]"
                  >
                    Ver jornada →
                  </Link>
                </header>
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {slate.map((g) => (
                    <MatchCard key={g.id_partido} game={g} />
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </>
  );
}
