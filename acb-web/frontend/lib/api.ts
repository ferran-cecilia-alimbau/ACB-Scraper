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

// ───────── Tipos: Jugadores ─────────

export interface PlayerSummary {
  player_id: number;
  nombre: string;
  equipo: string;
  color: string;
  posicion: string;
  posicion_full: string;
  edad: number;
  altura: number;
  partidos: number;
  titularidades: number;
  minutos_avg: number;
  puntos_avg: number;
  rebotes_avg: number;
  asistencias_avg: number;
  robos_avg: number;
  perdidas_avg: number;
  tapones_avg: number;
  valoracion_avg: number;
  plus_minus_avg: number;
  t2_pct: number;
  t3_pct: number;
  tl_pct: number;
  efg_pct: number;
  ts_pct: number;
  puntos_per36: number;
  rebotes_per36: number;
  asistencias_per36: number;
  robos_per36: number;
  tapones_per36: number;
  perdidas_per36: number;
  valoracion_per36: number;
  puntos_total: number;
  rebotes_total: number;
  asistencias_total: number;
  valoracion_total: number;
}

export interface PlayerSearchResult {
  player_id: number;
  nombre: string;
  equipo: string;
  color: string;
  puntos_avg: number;
  valoracion_avg: number;
}

export interface PlayerSplit {
  sede: 'Casa' | 'Fuera';
  PJ: number;
  puntos: number;
  rebotes_totales: number;
  asistencias: number;
  robos: number;
  perdidas: number;
  valoracion: number;
  minutos_decimal: number;
}

export interface PlayerGameLogRow {
  id_partido: number;
  jornada_num: number;
  fecha: string;
  oponente: string;
  es_local: boolean;
  minutos: string;
  minutos_decimal: number;
  puntos: number;
  t2_anotados: number;
  t2_intentados: number;
  t3_anotados: number;
  t3_intentados: number;
  tl_anotados: number;
  tl_intentados: number;
  rebotes_totales: number;
  rebotes_ofensivos: number;
  rebotes_defensivos: number;
  asistencias: number;
  robos: number;
  perdidas: number;
  tapones_favor: number;
  tapones_contra: number;
  faltas_cometidas: number;
  faltas_recibidas: number;
  plus_minus: number;
  valoracion: number;
  es_titular: boolean;
}

export interface PlayerLastN {
  games: number;
  stats: {
    puntos: number;
    rebotes_totales: number;
    asistencias: number;
    valoracion: number;
    minutos_decimal: number;
  };
  diff_vs_season: {
    puntos: number;
    rebotes_totales: number;
    asistencias: number;
    valoracion: number;
    minutos_decimal: number;
  };
}

export interface PlayerBestGame {
  id_partido: number;
  jornada_num: number;
  fecha: string;
  rival: string;
  puntos: number;
  rebotes: number;
  asistencias: number;
  valoracion: number;
}

export interface RankInfo {
  rank: number | null;
  total: number;
}

export interface PlayerDetail {
  player_id: number;
  nombre: string;
  equipo: string;
  color: string;
  colorSecondary: string;
  profile: {
    posicion: string;
    posicion_full: string;
    altura: number;
    edad: number;
    nacionalidad: string;
    dorsal: number | string;
  };
  stats: Omit<
    PlayerSummary,
    'player_id' | 'nombre' | 'equipo' | 'color' | 'posicion' | 'posicion_full' | 'edad' | 'altura'
  >;
  /** Percentil (0–100) para cada métrica. null si el jugador no cumple mínimos. */
  percentiles: Record<string, number | null>;
  rankings: Record<string, RankInfo>;
  splits: PlayerSplit[];
  last_5: PlayerLastN;
  best_game: PlayerBestGame | Record<string, never>;
  game_log: PlayerGameLogRow[];
}

export interface PlayerRankingRow {
  rank: number;
  player_id: number;
  nombre: string;
  equipo: string;
  color: string;
  posicion: string;
  partidos: number;
  minutos_avg: number;
  value: number;
  puntos_avg: number;
  rebotes_avg: number;
  asistencias_avg: number;
  valoracion_avg: number;
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

export interface PlayersQuery {
  team?: string;
  position?: string;
  min_games?: number;
  min_minutes?: number;
  sort?: string;
  direction?: 'asc' | 'desc';
  limit?: number;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== '');
  if (!entries.length) return '';
  const usp = new URLSearchParams();
  for (const [k, v] of entries) usp.set(k, String(v));
  return `?${usp.toString()}`;
}

export function getPlayers(query: PlayersQuery = {}) {
  return backendFetch<PlayerSummary[]>(`/api/players${buildQuery(query)}`);
}

export function getPlayer(id: number | string) {
  return backendFetch<PlayerDetail>(`/api/players/${id}`);
}

export function searchPlayers(q: string) {
  return backendFetch<PlayerSearchResult[]>(`/api/players/search?q=${encodeURIComponent(q)}`);
}

export interface PlayerRankingsQuery {
  stat?: string;
  min_games?: number;
  min_minutes?: number;
  team?: string;
  position?: string;
  limit?: number;
}

export function getPlayerRankings(query: PlayerRankingsQuery = {}) {
  return backendFetch<PlayerRankingRow[]>(`/api/rankings/players${buildQuery(query)}`);
}
