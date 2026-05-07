import { getStandings } from '@/lib/api';
import { Kicker } from '@/components/kicker';
import { StandingsTable } from '@/components/standings-table';

export const revalidate = 60;
export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Clasificación',
  description: 'Tabla completa de la Liga Endesa 2025-26.',
};

export default async function ClasificacionPage() {
  const standings = await getStandings();

  return (
    <>
      <section className="border-b border-[var(--rule)]">
        <div className="container-editorial py-14 sm:py-20">
          <Kicker className="mb-4 inline-block">Liga Endesa · Temporada 2025-26</Kicker>
          <h1 className="headline max-w-3xl mb-5">Clasificación</h1>
          <p className="lede max-w-2xl">
            Posición, victorias, derrotas, porcentaje y diferencial. Las primeras cuatro
            plazas marcan el camino al play-off.
          </p>
        </div>
      </section>

      <section>
        <div className="container-editorial py-12">
          <StandingsTable rows={standings} />
          <p className="mt-8 text-xs text-[var(--ink-muted)] italic">
            <span className="text-[var(--accent)] not-italic font-semibold">●</span> Plazas
            de play-off (1-4) destacadas en naranja. <span className="text-[var(--ink)] not-italic font-semibold">●</span> Posiciones 5-8 con tinta plena.
          </p>
        </div>
      </section>
    </>
  );
}
