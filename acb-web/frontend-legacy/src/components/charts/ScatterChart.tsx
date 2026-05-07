import {
  ScatterChart as RechartsScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Cell, ZAxis,
} from 'recharts';
import { teamColor } from '../../lib/formatters';

interface ScatterChartProps {
  data: Array<{ name: string; x: number; y: number; color: string }>;
  xLabel: string;
  yLabel: string;
  height?: number;
  showMeanLines?: boolean;
}

export function ScatterChart({ data, xLabel, yLabel, height = 350, showMeanLines = true }: ScatterChartProps) {
  if (data.length === 0) return null;

  const xMean = data.reduce((s, d) => s + d.x, 0) / data.length;
  const yMean = data.reduce((s, d) => s + d.y, 0) / data.length;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsScatterChart margin={{ top: 10, right: 20, bottom: 25, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis
          dataKey="x" type="number" name={xLabel}
          tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false}
          label={{ value: xLabel, position: 'bottom', fill: '#8b8fa3', fontSize: 12, offset: 10 }}
        />
        <YAxis
          dataKey="y" type="number" name={yLabel}
          tick={{ fill: '#8b8fa3', fontSize: 11 }} axisLine={false} tickLine={false}
          label={{ value: yLabel, angle: -90, position: 'insideLeft', fill: '#8b8fa3', fontSize: 12 }}
        />
        <ZAxis range={[50, 50]} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1a1d28', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, color: '#f0f0f5' }}
          formatter={(value: number) => value.toFixed(1)}
          labelFormatter={(_, payload) => payload?.[0]?.payload?.name || ''}
        />
        {showMeanLines && (
          <>
            <ReferenceLine x={xMean} stroke="rgba(255,255,255,0.15)" strokeDasharray="3 3" />
            <ReferenceLine y={yMean} stroke="rgba(255,255,255,0.15)" strokeDasharray="3 3" />
          </>
        )}
        <Scatter data={data}>
          {data.map((entry, i) => (
            <Cell key={i} fill={teamColor(entry.color)} />
          ))}
        </Scatter>
      </RechartsScatterChart>
    </ResponsiveContainer>
  );
}
