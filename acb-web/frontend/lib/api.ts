/**
 * Tipados y cliente para la API FastAPI.
 *
 * En desarrollo, Next.js reescribe `/api/*` → `BACKEND_URL` (ver next.config.mjs),
 * así que aquí siempre usamos rutas relativas y desde server components hacemos
 * fetch al puerto del backend directamente.
 */

const BACKEND_URL =
  process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

async function backendFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BACKEND_URL}${path}`;
  const res = await fetch(url, {
    ...init,
    next: { revalidate: 60, ...((init as { next?: object } | undefined)?.next || {}) },
  });
  if (!res.ok) {
    throw new Error(`API ${path} → ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

// ───────── Tipos ─────────

export interface StandingsRow {
  pos: number;
  equipo: string;
  J: number;
  G: number;
  P: number;
  PF: number;
  PC: number;
  Dif: number;
  G_casa: number;
  P_casa: number;
  G_fuera: number;
  P_fuera: number;
  pct: number;
}

export interface GameSummary {
  id_partido: number;
  jornada_num: number;
  fecha: string;
  local: string;
  visitante: string;
  resultado_local: number;
  resultado_visitante: number;
  local_color: string;
  visitante_color: string;
  pabellon: string;
  publico: number;
}

export interface BoxScorePlayer {
  player_id: number;
  nombre: string;
  es_titular: boolean;
  minutos: string;
  puntos: number;
  t2: string;
  t3: string;
  tl: string;
  rebotes: number;
  reb_of: number;
  reb_def: number;
  asistencias: number;
  robos: number;
  perdidas: number;
  tapones_favor: number;
  tapones_contra: number;
  faltas: number;
  plus_minus: number;
  valoracion: number;
}

export interface GameDetail extends GameSummary {
  parciales_local: string;
  parciales_visitante: string;
  box_score: {
    local: BoxScorePlayer[];
    visitante: BoxScorePlayer[];
  };
  four_factors: {
    local: Record<string, number>;
    visitante: Record<string, number>;
  };
}

// ───────── Endpoints ─────────

export function getStandings() {
  return backendFetch<StandingsRow[]>('/api/standings');
}

export function getGames() {
  return backendFetch<GameSummary[]>('/api/games');
}

export function getGame(id: number) {
  return backendFetch<GameDetail>(`/api/games/${id}`);
}
