import { getStandings } from '@/lib/api';
import { Kicker } from '@/components/kicker';
import { RankingsExplorer } from './rankings-explorer';

export const revalidate = 60;
export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Rankings · ACB Editorial',
  description:
    'Líderes de la Liga Endesa 2025-26 por categoría: anotación, rebote, creación, defensa, eficiencia, tiro e impacto. Filtros por equipo, posición y mínimos de juego.',
};

export default async function RankingsPage() {
  const standings = await getStandings();
  const teamOptions = standings.map((s) => s.equipo).sort((a, b) => a.localeCompare(b, 'es'));

  return (
    <>
      <section className="border-b border-[var(--rule)]">
        <div className="container-editorial py-12 sm:py-16">
          <Kicker className="mb-3 inline-block">Liga Endesa · 2025-26</Kicker>
          <h1 className="headline mb-4">Rankings</h1>
          <p className="lede max-w-2xl">
            Quién lidera cada categoría, con filtros visibles para evitar que un jugador con
            uno o dos partidos parezca el mejor de la liga.
          </p>
        </div>
      </section>

      <section>
        <div className="container-editorial py-10">
          <RankingsExplorer teamOptions={teamOptions} />
        </div>
      </section>
    </>
  );
}
