/**
 * Helpers de formato pensados para visualización editorial.
 */

const dateFormatter = new Intl.DateTimeFormat('es-ES', {
  day: '2-digit',
  month: 'long',
  year: 'numeric',
});

const dateFormatterShort = new Intl.DateTimeFormat('es-ES', {
  day: '2-digit',
  month: 'short',
  weekday: 'short',
});

/** Recibe '04/10/2025' o ISO; devuelve "04 de octubre de 2025" */
export function formatDate(input: string): string {
  if (!input) return '';
  const iso = parseToIso(input);
  if (!iso) return input;
  return dateFormatter.format(new Date(iso));
}

export function formatDateShort(input: string): string {
  if (!input) return '';
  const iso = parseToIso(input);
  if (!iso) return input;
  return dateFormatterShort.format(new Date(iso)).replace('.', '');
}

function parseToIso(input: string): string | null {
  // Acepta DD/MM/YYYY o YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}/.test(input)) return input;
  const m = input.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (!m) return null;
  return `${m[3]}-${m[2]}-${m[1]}`;
}

/** "30/12/2025" → Date. Para ordenar. */
export function parseDate(input: string): Date | null {
  const iso = parseToIso(input);
  return iso ? new Date(iso) : null;
}

/** "+12" / "-3" / "0" para diferencial */
export function signed(n: number): string {
  if (n > 0) return `+${n}`;
  if (n < 0) return `${n}`;
  return '0';
}

export function pct(num: number, decimals = 1): string {
  return `${num.toFixed(decimals)}%`;
}

/** "1234" → "1.234" (formato español) */
export function nf(n: number): string {
  return new Intl.NumberFormat('es-ES').format(n);
}

/** "10-15,12-8,20-19,9-22" → array<[local, visit]> */
export function parseParciales(input: string): Array<[number, number]> {
  if (!input) return [];
  return input
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((pair) => {
      const [a, b] = pair.split('-').map((n) => parseInt(n, 10));
      return [Number.isFinite(a) ? a : 0, Number.isFinite(b) ? b : 0] as [number, number];
    });
}
