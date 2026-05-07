import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getGames } from '@/lib/api';
import { Kicker } from '@/components/kicker';
import { MatchCard } from '@/components/match-card';
import { formatDate, parseDate } from '@/lib/format';

export const revalidate = 60;
export const dynamic = 'force-dynamic';

export async function generateMetadata({ params }: { params: Promise<{ n: string }> }) {
  const { n } = await params;
  return {
    title: `Jornada ${n}`,
    description: `Resultados y encuentros de la jornada ${n} de la Liga Endesa 2025-26.`,
  };
}

export default async function JornadaPage({
  params,
}: {
  params: Promise<{ n: string }>;
}) {
  const { n } = await params;
  const jornada = parseInt(n, 10);
  if (!Number.isFinite(jornada)) notFound();

  const all = await getGames();
  const slate = all.filter((g) => g.jornada_num === jornada);
  if (slate.length === 0) notFound();

  const dates = slate
    .map((g) => parseDate(g.fecha))
    .filter((d): d is Date => d != null);
  const dateMin = dates.length ? new Date(Math.min(...dates.map((d) => d.getTime()))) : null;
  const dateMax = dates.length ? new Date(Math.max(...dates.map((d) => d.getTime()))) : null;
  const dateRange =
    dateMin && dateMax
      ? dateMin.getTime() === dateMax.getTime()
        ? formatDate(dateMin.toISOString())
        : `${formatDate(dateMin.toISOString())} → ${formatDate(dateMax.toISOString())}`
      : '';

  const allJornadas = Array.from(
    new Set(all.map((g) => g.jornada_num).filter((j): j is number => j != null)),
  ).sort((a, b) => a - b);
  const idx = allJornadas.indexOf(jornada);
  const prev = idx > 0 ? allJornadas[idx - 1] : null;
  const next = idx >= 0 && idx < allJornadas.length - 1 ? allJornadas[idx + 1] : null;

  return (
    <>
      <section className="border-b border-[var(--rule)]">
        <div className="container-editorial py-14 sm:py-20">
          <Kicker className="mb-4 inline-block">Liga Endesa · 2025-26</Kicker>
          <h1 className="headline mb-5">Jornada {jornada}</h1>
          {dateRange && (
            <p className="lede">
              {dateRange} · {slate.length} partido{slate.length === 1 ? '' : 's'}
            </p>
          )}
        </div>
      </section>

      <section>
        <div className="container-editorial py-12">
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {slate.map((g) => (
              <MatchCard key={g.id_partido} game={g} />
            ))}
          </div>

          <nav
            aria-label="Navegación entre jornadas"
            className="mt-16 pt-8 border-t border-[var(--rule)] flex items-center justify-between text-sm"
          >
            {prev ? (
              <Link href={`/jornada/${prev}`} className="link-underline">
                ← Jornada {prev}
              </Link>
            ) : (
              <span />
            )}
            <Link href="/partidos" className="text-[var(--ink-muted)] link-underline">
              Todas las jornadas
            </Link>
            {next ? (
              <Link href={`/jornada/${next}`} className="link-underline">
                Jornada {next} →
              </Link>
            ) : (
              <span />
            )}
          </nav>
        </div>
      </section>
    </>
  );
}
