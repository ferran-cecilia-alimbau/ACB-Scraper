'use client';

import { useMemo, useState, type ReactNode, type CSSProperties } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/cn';

export interface MetricColumn<T> {
  key: string;
  /** Header text. Si quieres header complejo, usa headerNode. */
  label: string;
  headerNode?: ReactNode;
  align?: 'left' | 'right' | 'center';
  /** Render personalizado de la celda. */
  render?: (row: T, index: number) => ReactNode;
  /** Función que extrae el valor para ordenar (numérico). */
  sortValue?: (row: T) => number | string;
  /** Si true, columna es ordenable (default: true para columnas numéricas con sortValue). */
  sortable?: boolean;
  /** Anchura mínima opcional. */
  minWidth?: string;
  /** Tono atenuado en valores bajos (ej: % de tiro con pocos intentos). */
  dim?: (row: T) => boolean;
  /** Texto en cabecera con tooltip. */
  hint?: string;
}

interface MetricTableProps<T> {
  columns: MetricColumn<T>[];
  rows: T[];
  /** Clave única por fila (para React keys). */
  rowKey: (row: T) => string | number;
  /** Si true, hace toda la fila clickeable (link). */
  rowHref?: (row: T) => string | undefined;
  /** Columna inicial de orden. */
  defaultSort?: { key: string; direction: 'asc' | 'desc' };
  /** Mensaje vacío. */
  emptyText?: string;
  className?: string;
}

const ALIGN_CLASS = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
} as const;

export function MetricTable<T>({
  columns,
  rows,
  rowKey,
  rowHref,
  defaultSort,
  emptyText = 'Sin resultados.',
  className,
}: MetricTableProps<T>) {
  const [sort, setSort] = useState<{ key: string; direction: 'asc' | 'desc' } | undefined>(
    defaultSort,
  );
  const router = useRouter();

  // Si la columna activa de sort ya no existe en `columns` (p.ej. al cambiar
  // de vista), reseteamos al defaultSort. React no propaga cambios del prop
  // inicial de useState, así que lo gestionamos explícitamente aquí.
  const sortKeyExists = sort ? columns.some((c) => c.key === sort.key) : true;
  if (!sortKeyExists) {
    setSort(defaultSort);
  }

  const sortedRows = useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col || !col.sortValue) return rows;
    const sorted = [...rows].sort((a, b) => {
      const va = col.sortValue!(a);
      const vb = col.sortValue!(b);
      if (typeof va === 'number' && typeof vb === 'number') {
        return sort.direction === 'asc' ? va - vb : vb - va;
      }
      const sa = String(va);
      const sb = String(vb);
      return sort.direction === 'asc' ? sa.localeCompare(sb) : sb.localeCompare(sa);
    });
    return sorted;
  }, [rows, sort, columns]);

  function toggleSort(col: MetricColumn<T>) {
    if (col.sortable === false || !col.sortValue) return;
    if (sort?.key === col.key) {
      setSort({ key: col.key, direction: sort.direction === 'asc' ? 'desc' : 'asc' });
    } else {
      setSort({ key: col.key, direction: 'desc' });
    }
  }

  if (!rows.length) {
    return (
      <p className={cn('py-8 text-center text-[var(--ink-muted)] italic', className)}>
        {emptyText}
      </p>
    );
  }

  return (
    <div className={cn('overflow-x-auto -mx-4 sm:mx-0', className)}>
      <table className="w-full table-editorial text-sm">
        <thead>
          <tr className="text-[0.7rem] uppercase tracking-[0.14em] text-[var(--ink-muted)]">
            {columns.map((col) => {
              const isSortable = col.sortable !== false && !!col.sortValue;
              const isActive = sort?.key === col.key;
              const arrow = !isActive ? '' : sort?.direction === 'asc' ? ' ↑' : ' ↓';
              const style: CSSProperties = col.minWidth ? { minWidth: col.minWidth } : {};
              return (
                <th
                  key={col.key}
                  scope="col"
                  className={cn(
                    'pb-2.5 pt-1 px-3 font-medium',
                    ALIGN_CLASS[col.align ?? 'left'],
                    isSortable && 'cursor-pointer select-none hover:text-[var(--ink)]',
                    isActive && 'text-[var(--accent)]',
                  )}
                  style={style}
                  onClick={() => toggleSort(col)}
                  title={col.hint}
                >
                  {col.headerNode ?? col.label}
                  {arrow}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row, idx) => {
            const href = rowHref?.(row);
            return (
              <tr
                key={rowKey(row)}
                className={cn(
                  'border-t border-[var(--rule)] hover:bg-[color-mix(in_srgb,var(--accent)_5%,transparent)] transition-colors',
                  href && 'cursor-pointer',
                )}
                onClick={
                  href
                    ? () => {
                        router.push(href);
                      }
                    : undefined
                }
              >
                {columns.map((col) => {
                  const dimmed = col.dim?.(row);
                  return (
                    <td
                      key={col.key}
                      className={cn(
                        'py-2 px-3 align-middle',
                        ALIGN_CLASS[col.align ?? 'left'],
                        col.align !== 'left' && 'tabular-nums font-mono',
                        dimmed && 'text-[var(--ink-soft)]',
                      )}
                    >
                      {col.render
                        ? col.render(row, idx)
                        : col.sortValue
                          ? String(col.sortValue(row))
                          : ''}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
