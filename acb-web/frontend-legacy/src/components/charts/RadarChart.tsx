import {
  RadarChart as RechartsRadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip,
} from 'recharts';
import { teamColor } from '../../lib/formatters';

interface RadarChartProps {
  data: Array<{ subject: string; [key: string]: string | number }>;
  radars: Array<{ key: string; color: string; name: string }>;
  height?: number;
}

export function RadarChart({ data, radars, height = 350 }: RadarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsRadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="rgba(255,255,255,0.1)" />
        <PolarAngleAxis dataKey="subject" tick={{ fill: '#8b8fa3', fontSize: 11 }} />
        <PolarRadiusAxis tick={false} axisLine={false} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1a1d28', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, color: '#f0f0f5' }}
        />
        {radars.map((r) => (
          <Radar
            key={r.key}
            name={r.name}
            dataKey={r.key}
            stroke={teamColor(r.color)}
            fill={teamColor(r.color)}
            fillOpacity={0.15}
            strokeWidth={2}
          />
        ))}
        {radars.length > 1 && <Legend wrapperStyle={{ color: '#8b8fa3', fontSize: 12 }} />}
      </RechartsRadarChart>
    </ResponsiveContainer>
  );
}
