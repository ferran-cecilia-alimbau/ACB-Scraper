export function pct(val: number): string {
  return val.toFixed(1) + '%';
}

export function dec(val: number, digits = 1): string {
  return val.toFixed(digits);
}

export function signedNum(val: number): string {
  if (val > 0) return `+${val.toFixed(1)}`;
  return val.toFixed(1);
}

export function teamColor(color: string): string {
  if (color === '#FFFFFF' || color === '#ffffff') return '#c0c0c8';
  return color;
}
