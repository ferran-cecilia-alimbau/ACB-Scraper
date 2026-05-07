import {
  BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, Legend,
} from 'recharts';

interface BarChartProps {
  data: Record<string, unknown>[];
  xKey: string;
  bars: Array<{ key: string; color: string; name?: string }>;
  height?: number;
  layout?: 'horizontal' | 'vertical';
  showLegend?: boolean;
}

export function BarChart({ data, xKey, bars, height = 350, layout = 'vertical', showLegend = false }: BarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart data={data} layout={layout} margin={{ top: 5, right: 20, bottom: 5, left: layout === 'horizontal' ? 80 : 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        {layout === 'vertical' ? (
          <>
            <XAxis dataKey={xKey} tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} />
          </>
        ) : (
          <>
            <XAxis type="number" tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis dataKey={xKey} type="category" tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} width={100} />
          </>
        )}
        <Tooltip
          contentStyle={{ backgroundColor: '#1a1d28', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, color: '#f0f0f5' }}
        />
        {showLegend && <Legend wrapperStyle={{ color: '#8b8fa3', fontSize: 12 }} />}
        {bars.map((b) => (
          <Bar key={b.key} dataKey={b.key} name={b.name || b.key} fill={b.color} radius={[3, 3, 0, 0]} />
        ))}
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}

interface ColoredBarChartProps {
  data: Array<{ name: string; value: number; color: string }>;
  height?: number;
  layout?: 'horizontal' | 'vertical';
}

export function ColoredBarChart({ data, height = 350, layout = 'horizontal' }: ColoredBarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart data={data} layout={layout} margin={{ top: 5, right: 20, bottom: 5, left: layout === 'horizontal' ? 100 : 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        {layout === 'horizontal' ? (
          <>
            <XAxis type="number" tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis dataKey="name" type="category" tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} width={100} />
          </>
        ) : (
          <>
            <XAxis dataKey="name" tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false} />
          </>
        )}
        <Tooltip contentStyle={{ backgroundColor: '#1a1d28', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, color: '#f0f0f5' }} />
        <Bar dataKey="value" radius={[3, 3, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Bar>
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}
