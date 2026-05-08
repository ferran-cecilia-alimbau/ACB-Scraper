import { getPlayers } from '@/lib/api';
import { Kicker } from '@/components/kicker';
import { PlayersExplorer } from './players-explorer';

export const revalidate = 60;
export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Jugadores · ACB Editorial',
  description:
    'Estadísticas de todos los jugadores de la Liga Endesa 2025-26: medias, eficiencia, per 36 y totales. Filtros por equipo, posición y mínimo de partidos.',
};

interface JugadoresPageProps {
  searchParams?: Promise<{
    team?: string;
  }>;
}

export default async function JugadoresPage({ searchParams }: JugadoresPageProps) {
  const players = await getPlayers({ limit: 1000 });
  const params = searchParams ? await searchParams : {};
  // Lista de equipos derivada de los datos (orden alfabético).
  const teamOptions = Array.from(new Set(players.map((p) => p.equipo))).sort((a, b) =>
    a.localeCompare(b, 'es'),
  );
  const initialTeam = params.team && teamOptions.includes(params.team) ? params.team : '';

  return (
    <>
      <section className="border-b border-[var(--rule)]">
        <div className="container-editorial py-12 sm:py-16">
          <Kicker className="mb-3 inline-block">Liga Endesa · 2025-26</Kicker>
          <h1 className="headline mb-4">Jugadores</h1>
          <p className="lede max-w-2xl">
            {players.length} jugadores con datos esta temporada. Cambia la vista para ver
            medias, eficiencia, producción por 36 minutos o totales acumulados.
          </p>
        </div>
      </section>

      <section>
        <div className="container-editorial py-10">
          <PlayersExplorer
            players={players}
            teamOptions={teamOptions}
            initialTeam={initialTeam}
          />
        </div>
      </section>
    </>
  );
}
