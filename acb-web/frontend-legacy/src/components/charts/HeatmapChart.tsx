interface HeatmapChartProps {
  players: string[];
  values: number[][];
  height?: number;
}

function getColor(val: number, max: number): string {
  if (max === 0) return 'rgba(232,121,43,0.05)';
  const intensity = val / max;
  return `rgba(232,121,43,${0.1 + intensity * 0.7})`;
}

export function HeatmapChart({ players, values }: HeatmapChartProps) {
  // Calculate max excluding diagonal (diagonal = total minutes per player, distorts scale)
  const offDiagMax = Math.max(
    ...values.flatMap((row, i) => row.filter((_, j) => i !== j)),
    0
  );

  return (
    <div className="overflow-x-auto">
      <table className="text-xs">
        <thead>
          <tr>
            <th className="px-1 py-1 text-left text-text-secondary" />
            {players.map((p) => (
              <th key={p} className="px-1 py-1 text-center text-text-secondary" style={{ writingMode: 'vertical-lr', minWidth: 32 }}>
                {p.split(' ').pop()}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {players.map((p, i) => (
            <tr key={p}>
              <td className="px-2 py-1 text-right text-text-secondary whitespace-nowrap">{p.split(' ').pop()}</td>
              {values[i].map((v, j) => {
                const isDiag = i === j;
                return (
                  <td
                    key={j}
                    className={`px-1 py-1 text-center tabular-nums ${isDiag ? 'font-bold' : ''}`}
                    style={{
                      backgroundColor: isDiag
                        ? 'var(--color-bg-hover)'
                        : getColor(v, offDiagMax),
                      minWidth: 32,
                    }}
                  >
                    {v > 0 ? v.toFixed(0) : ''}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
