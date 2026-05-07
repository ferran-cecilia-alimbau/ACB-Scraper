import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';

interface TimelineChartProps {
  data: Array<{ index: number; diff: number }>;
  localColor: string;
  visitanteColor: string;
  height?: number;
}

export function TimelineChart({ data, localColor, visitanteColor, height = 300 }: TimelineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="index" tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1a1d28', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, color: '#f0f0f5' }}
          formatter={(value: number) => [value > 0 ? `+${value} Local` : `${value} Visitante`, 'Diferencia']}
        />
        <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" />
        <defs>
          <linearGradient id="splitColor" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={localColor} stopOpacity={0.3} />
            <stop offset="50%" stopColor={localColor} stopOpacity={0.05} />
            <stop offset="50%" stopColor={visitanteColor} stopOpacity={0.05} />
            <stop offset="100%" stopColor={visitanteColor} stopOpacity={0.3} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="diff"
          stroke="var(--color-accent)"
          fill="url(#splitColor)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
