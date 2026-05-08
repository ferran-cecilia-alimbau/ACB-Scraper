'use client';

import type { PlayerGameLogRow } from '@/lib/api';
import { MetricTable, type MetricColumn } from '@/components/metric-table';
import { teamMeta } from '@/lib/teams';
import { formatDateShort } from '@/lib/format';
import Link from 'next/link';

interface Props {
  rows: PlayerGameLogRow[];
}

export function GameLogTable({ rows }: Props) {
  const columns: MetricColumn<PlayerGameLogRow>[] = [
    {
      key: 'jornada',
      label: 'J',
      align: 'right',
      sortValue: (r) => r.jornada_num,
      render: (r) => r.jornada_num,
    },
    {
      key: 'fecha',
      label: 'Fecha',
      align: 'left',
      sortValue: (r) => r.fecha,
      render: (r) => (
        <span className="font-mono text-[0.75rem] text-[var(--ink-muted)]">
          {formatDateShort(r.fecha)}
        </span>
      ),
    },
    {
      key: 'rival',
      label: 'Rival',
      align: 'left',
      minWidth: '10rem',
      sortValue: (r) => r.oponente,
      render: (r) => (
        <Link
          href={`/partido/${r.id_partido}`}
          className="link-underline inline-flex items-baseline gap-1.5"
        >
          <span className="text-[var(--ink-muted)] text-[0.7rem] uppercase">
            {r.es_local ? 'vs' : '@'}
          </span>
          <span className="truncate">{teamMeta(r.oponente).short}</span>
        </Link>
      ),
    },
    {
      key: 'minutos',
      label: 'MIN',
      align: 'right',
      sortValue: (r) => r.minutos_decimal,
      render: (r) => r.minutos || '—',
    },
    {
      key: 'puntos',
      label: 'PTS',
      align: 'right',
      sortValue: (r) => r.puntos,
      render: (r) => r.puntos,
    },
    {
      key: 't2',
      label: 'T2',
      align: 'right',
      sortValue: (r) => r.t2_anotados,
      render: (r) => `${r.t2_anotados}/${r.t2_intentados}`,
    },
    {
      key: 't3',
      label: 'T3',
      align: 'right',
      sortValue: (r) => r.t3_anotados,
      render: (r) => `${r.t3_anotados}/${r.t3_intentados}`,
    },
    {
      key: 'tl',
      label: 'TL',
      align: 'right',
      sortValue: (r) => r.tl_anotados,
      render: (r) => `${r.tl_anotados}/${r.tl_intentados}`,
    },
    {
      key: 'reb',
      label: 'REB',
      align: 'right',
      sortValue: (r) => r.rebotes_totales,
      render: (r) => r.rebotes_totales,
    },
    {
      key: 'ast',
      label: 'AST',
      align: 'right',
      sortValue: (r) => r.asistencias,
      render: (r) => r.asistencias,
    },
    {
      key: 'rob',
      label: 'ROB',
      align: 'right',
      sortValue: (r) => r.robos,
      render: (r) => r.robos,
    },
    {
      key: 'tap',
      label: 'TAP',
      align: 'right',
      sortValue: (r) => r.tapones_favor,
      render: (r) => r.tapones_favor,
    },
    {
      key: 'plus_minus',
      label: '+/-',
      align: 'right',
      sortValue: (r) => r.plus_minus,
      render: (r) => (r.plus_minus > 0 ? `+${r.plus_minus}` : r.plus_minus),
    },
    {
      key: 'val',
      label: 'VAL',
      align: 'right',
      sortValue: (r) => r.valoracion,
      render: (r) => <span className="font-medium">{r.valoracion}</span>,
    },
  ];

  return (
    <MetricTable
      columns={columns}
      rows={rows}
      rowKey={(r) => r.id_partido}
      defaultSort={{ key: 'jornada', direction: 'asc' }}
      emptyText="Sin partidos registrados."
    />
  );
}
