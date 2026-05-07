import Link from 'next/link';
import { getStandings, getGames } from '@/lib/api';
import { Kicker } from '@/components/kicker';
import { StandingsTable } from '@/components/standings-table';
import { MatchCard } from '@/components/match-card';
import { formatDate, parseDate } from '@/lib/format';

export const revalidate = 60;
export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const [standings, games] = await Promise.all([getStandings(), getGames()]);

  const lastJornada = Math.max(0, ...games.map((g) => g.jornada_num || 0));
  const featured = games
    .filter((g) => g.jornada_num === lastJornada)
    .sort((a, b) => {
      const da = parseDate(a.fecha)?.getTime() || 0;
      const db = parseDate(b.fecha)?.getTime() || 0;
      return db - da;
    })
    .slice(0, 6);

  const next = games
    .filter((g) => g.jornada_num === lastJornada + 1)
    .slice(0, 9);

  const leader = standings[0];
  const second = standings[1];

  // Frase tipo periódico — dinámica pero modesta
  const headline = leader
    ? `${leader.equipo} mantiene el pulso en lo alto de la Liga Endesa`
    : 'La Liga Endesa, en cifras';

  const lede = leader && second
    ? `Tras ${leader.J} jornadas, ${leader.equipo} suma ${leader.G}-${leader.P} y aventaja a ${second.equipo} (${second.G}-${second.P}) por diferencial: ${leader.Dif > 0 ? '+' : ''}${leader.Dif} frente a ${second.Dif > 0 ? '+' : ''}${second.Dif}.`
    : 'Crónica de partidos, clasificación y estadísticas en un trazo sobrio.';

  return (
    <>
      {/* Hero */}
      <section className="border-b border-[var(--rule)]">
        <div className="container-editorial py-16 sm:py-24">
          <Kicker className="mb-5 inline-block">
            <span className="italic font-normal tracking-[0.2em]">Jornada {lastJornada}</span>
          </Kicker>
          <h1 className="headline max-w-4xl mb-6 text-[clamp(2.6rem,6.4vw,5rem)]">
            {headline}
          </h1>
          <p className="lede max-w-2xl">{lede}</p>
        </div>
      </section>

      {/* Featured games */}
      {featured.length > 0 && (
        <section className="border-b border-[var(--rule)]">
          <div className="container-editorial py-14 sm:py-20">
            <div className="flex items-baseline justify-between gap-4 mb-8">
              <div>
                <Kicker className="block mb-2">Últimos resultados</Kicker>
                <h2 className="font-serif text-2xl sm:text-3xl">Jornada {lastJornada}</h2>
              </div>
              <Link href="/partidos" className="text-sm link-underline text-[var(--ink-muted)]">
                Ver todos →
              </Link>
            </div>
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {featured.map((g) => (
                <MatchCard key={g.id_partido} game={g} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Top 5 standings */}
      <section className="border-b border-[var(--rule)]">
        <div className="container-editorial py-14 sm:py-20 grid gap-12 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <Kicker className="block mb-2">Clasificación</Kicker>
            <h2 className="font-serif text-2xl sm:text-3xl mb-6">
              <Link href="/clasificacion" className="link-underline">Liderato</Link>
            </h2>
            <StandingsTable rows={standings} limit={8} compact />
            <div className="mt-6 text-sm">
              <Link href="/clasificacion" className="link-underline text-[var(--accent)]">
                Tabla completa →
              </Link>
            </div>
          </div>

          {/* Próxima jornada */}
          <aside>
            <Kicker className="block mb-2">Próxima jornada</Kicker>
            <h2 className="font-serif text-2xl sm:text-3xl mb-6">
              {next.length > 0 ? `Jornada ${lastJornada + 1}` : 'Sin partidos previstos'}
            </h2>
            {next.length > 0 ? (
              <ul className="space-y-3 text-sm">
                {next.map((g) => (
                  <li key={g.id_partido} className="border-b border-[var(--rule)] pb-3">
                    <span className="block text-[var(--ink-muted)] font-mono uppercase tracking-wider text-[0.7rem] mb-1">
                      {formatDate(g.fecha)}
                    </span>
                    <Link
                      href={`/partido/${g.id_partido}`}
                      className="font-medium text-[var(--ink)] hover:text-[var(--accent)] transition-colors"
                    >
                      {g.local} <span className="text-[var(--ink-muted)] mx-1.5">·</span> {g.visitante}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-[var(--ink-muted)] italic">
                Cuando se publiquen los próximos partidos aparecerán aquí.
              </p>
            )}
          </aside>
        </div>
      </section>
    </>
  );
}
