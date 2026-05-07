import type { BoxScorePlayer } from '@/lib/api';
import { teamMeta } from '@/lib/teams';

interface BoxScoreProps {
  team: string;
  players: BoxScorePlayer[];
}

export function BoxScore({ team, players }: BoxScoreProps) {
  const meta = teamMeta(team);
  // Titulares primero
  const sorted = [...players].sort(
    (a, b) => Number(b.es_titular) - Number(a.es_titular),
  );

  // Totales
  const total = sumStats(players);

  return (
    <section>
      <header className="flex items-baseline gap-3 mb-4">
        <span className="team-monogram team-monogram--sm" aria-hidden>
          {meta.monogram}
        </span>
        <h3 className="font-serif text-xl tracking-tight m-0">{meta.short}</h3>
      </header>

      <div className="overflow-x-auto -mx-4 sm:mx-0">
        <table className="table-editorial min-w-[640px]">
          <thead>
            <tr>
              <th className="text-left">Jugador</th>
              <th>Min</th>
              <th>PT</th>
              <th>T2</th>
              <th>T3</th>
              <th>TL</th>
              <th>REB</th>
              <th>AST</th>
              <th>PER</th>
              <th>REC</th>
              <th>+/−</th>
              <th>V</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((p) => (
              <tr key={p.player_id}>
                <td className="text-left">
                  <span
                    className={
                      p.es_titular
                        ? 'font-semibold'
                        : 'text-[var(--ink-muted)] font-normal'
                    }
                  >
                    {p.nombre}
                  </span>
                </td>
                <td>{p.minutos}</td>
                <td className="font-semibold text-[var(--ink)]">{p.puntos}</td>
                <td>{p.t2}</td>
                <td>{p.t3}</td>
                <td>{p.tl}</td>
                <td>{p.rebotes}</td>
                <td>{p.asistencias}</td>
                <td>{p.perdidas}</td>
                <td>{p.robos}</td>
                <td
                  style={{
                    color:
                      p.plus_minus > 0
                        ? 'var(--positive)'
                        : p.plus_minus < 0
                        ? 'var(--negative)'
                        : 'var(--ink-muted)',
                  }}
                >
                  {p.plus_minus > 0 ? `+${p.plus_minus}` : p.plus_minus}
                </td>
                <td className="font-semibold">{p.valoracion}</td>
              </tr>
            ))}
            <tr className="border-t-2 border-[var(--rule-strong)]">
              <td className="text-left font-semibold uppercase tracking-wider text-[0.72rem]">
                Totales
              </td>
              <td className="text-[var(--ink-muted)]">—</td>
              <td className="font-semibold">{total.puntos}</td>
              <td>{total.t2_a}/{total.t2_i}</td>
              <td>{total.t3_a}/{total.t3_i}</td>
              <td>{total.tl_a}/{total.tl_i}</td>
              <td>{total.rebotes}</td>
              <td>{total.asistencias}</td>
              <td>{total.perdidas}</td>
              <td>{total.robos}</td>
              <td className="text-[var(--ink-muted)]">—</td>
              <td className="font-semibold">{total.valoracion}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

function parseFraction(s: string): [number, number] {
  const [a, b] = s.split('/').map((n) => parseInt(n, 10));
  return [Number.isFinite(a) ? a : 0, Number.isFinite(b) ? b : 0];
}

function sumStats(players: BoxScorePlayer[]) {
  const acc = {
    puntos: 0,
    t2_a: 0,
    t2_i: 0,
    t3_a: 0,
    t3_i: 0,
    tl_a: 0,
    tl_i: 0,
    rebotes: 0,
    asistencias: 0,
    perdidas: 0,
    robos: 0,
    valoracion: 0,
  };
  for (const p of players) {
    acc.puntos += p.puntos || 0;
    const [t2a, t2i] = parseFraction(p.t2);
    acc.t2_a += t2a;
    acc.t2_i += t2i;
    const [t3a, t3i] = parseFraction(p.t3);
    acc.t3_a += t3a;
    acc.t3_i += t3i;
    const [tla, tli] = parseFraction(p.tl);
    acc.tl_a += tla;
    acc.tl_i += tli;
    acc.rebotes += p.rebotes || 0;
    acc.asistencias += p.asistencias || 0;
    acc.perdidas += p.perdidas || 0;
    acc.robos += p.robos || 0;
    acc.valoracion += p.valoracion || 0;
  }
  return acc;
}
