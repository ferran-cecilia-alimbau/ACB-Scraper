import {
  LineChart as RechartsLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { teamColor } from '../../lib/formatters';

interface LineChartProps {
  data: Record<string, unknown>[];
  xKey: string;
  lines: Array<{ key: string; color: string; name?: string }>;
  height?: number;
  invertY?: boolean;
  showLegend?: boolean;
}

export function LineChart({ data, xKey, lines, height = 350, invertY = false, showLegend = false }: LineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsLineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey={xKey} tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis reversed={invertY} tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1a1d28', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, color: '#f0f0f5' }}
        />
        {showLegend && <Legend wrapperStyle={{ color: '#8b8fa3', fontSize: 12 }} />}
        {lines.map((l) => (
          <Line
            key={l.key}
            type="monotone"
            dataKey={l.key}
            name={l.name || l.key}
            stroke={teamColor(l.color)}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </RechartsLineChart>
    </ResponsiveContainer>
  );
}
