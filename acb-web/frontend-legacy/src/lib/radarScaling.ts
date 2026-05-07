interface Stats {
  puntos_avg: number;
  ts_pct: number;
  rebotes_avg: number;
  asistencias_avg: number;
  robos_avg: number;
  tapones_avg: number;
  perdidas_avg: number;
  valoracion_avg: number;
}

const RADAR_SUBJECTS = [
  { subject: 'Puntos', key: 'puntos_avg', multiplier: 4 },
  { subject: 'Eficiencia', key: 'ts_pct', multiplier: 1 },
  { subject: 'Rebotes', key: 'rebotes_avg', multiplier: 8 },
  { subject: 'Asistencias', key: 'asistencias_avg', multiplier: 10 },
  { subject: 'Robos', key: 'robos_avg', multiplier: 30 },
  { subject: 'Tapones', key: 'tapones_avg', multiplier: 40 },
  { subject: 'No Pérdidas', key: 'perdidas_avg', multiplier: -20 },
  { subject: 'Valoración', key: 'valoracion_avg', multiplier: 4 },
] as const;

/** Build radar data for a single player (Jugador page). */
export function buildRadarData(stats: Stats): Array<{ subject: string; value: number }> {
  return RADAR_SUBJECTS.map(({ subject, key, multiplier }) => {
    if (multiplier < 0) {
      return { subject, value: Math.max(100 + multiplier * (stats[key] || 0), 0) };
    }
    return { subject, value: Math.min((stats[key] || 0) * multiplier, 100) };
  });
}

/** Build radar data for multiple players (Comparador page). */
export function buildCompareRadarData(
  players: Array<{ nombre: string; [key: string]: unknown }>,
): Array<Record<string, string | number>> {
  return RADAR_SUBJECTS.map(({ subject, key, multiplier }) => {
    const row: Record<string, string | number> = { subject };
    players.forEach((p) => {
      const v = Number(p[key]) || 0;
      if (multiplier < 0) {
        row[p.nombre] = Math.max(100 + multiplier * v, 0);
      } else {
        row[p.nombre] = Math.min(v * multiplier, 100);
      }
    });
    return row;
  });
}
