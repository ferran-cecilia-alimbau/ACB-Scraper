import { TeamMonogram } from '@/components/team-monogram';
import { teamMeta } from '@/lib/teams';
import { signed } from '@/lib/format';
import type { StandingsRow } from '@/lib/api';

interface StandingsTableProps {
  rows: StandingsRow[];
  /** muestra solo top N (compacto para portada) */
  limit?: number;
  /** versión condensada con menos columnas */
  compact?: boolean;
}

export function StandingsTable({ rows, limit, compact }: StandingsTableProps) {
  const visible = limit ? rows.slice(0, limit) : rows;

  return (
    <table className="table-editorial">
      <thead>
        <tr>
          <th className="text-left w-10">Pos</th>
          <th className="text-left">Equipo</th>
          <th>PJ</th>
          <th>V</th>
          <th>D</th>
          {!compact && <th>%</th>}
          {!compact && <th>PF</th>}
          {!compact && <th>PC</th>}
          <th>±</th>
        </tr>
      </thead>
      <tbody>
        {visible.map((row) => {
          const meta = teamMeta(row.equipo);
          const podium = row.pos <= 4;
          const playoff = row.pos >= 5 && row.pos <= 8;
          return (
            <tr key={row.equipo}>
              <td
                className="text-left"
                style={{
                  color: podium
                    ? 'var(--accent)'
                    : playoff
                    ? 'var(--ink)'
                    : 'var(--ink-muted)',
                  fontWeight: podium ? 600 : 500,
                }}
              >
                {row.pos.toString().padStart(2, '0')}
              </td>
              <td className="text-left">
                <span className="inline-flex items-center gap-3 min-w-0">
                  <TeamMonogram name={row.equipo} size="sm" />
                  <span className="truncate">{meta.short}</span>
                </span>
              </td>
              <td>{row.J}</td>
              <td>{row.G}</td>
              <td>{row.P}</td>
              {!compact && <td>{row.pct.toFixed(1)}</td>}
              {!compact && <td>{row.PF}</td>}
              {!compact && <td>{row.PC}</td>}
              <td
                style={{
                  color:
                    row.Dif > 0
                      ? 'var(--positive)'
                      : row.Dif < 0
                      ? 'var(--negative)'
                      : 'var(--ink-muted)',
                }}
              >
                {signed(row.Dif)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
