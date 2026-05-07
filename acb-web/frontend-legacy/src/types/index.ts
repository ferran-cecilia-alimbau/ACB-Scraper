export interface Standing {
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

export interface StandingsEvolution {
  jornada_num: number;
  equipo: string;
  posicion: number;
  G: number;
  P: number;
  pct: number;
}

export interface TeamSummary {
  name: string;
  color: string;
  colorSecondary: string;
  pos: number;
  wins: number;
  losses: number;
  games: number;
  ppg: number;
  rpg: number;
  apg: number;
  t2_pct: number;
  t3_pct: number;
  tl_pct: number;
}

export interface TeamDetail {
  name: string;
  color: string;
  colorSecondary: string;
  pos: number;
  standings: Record<string, number>;
  season_avgs: Record<string, number>;
  roster: RosterPlayer[];
  games: GameResult[];
}

export interface RosterPlayer {
  player_id: number;
  nombre: string;
  posicion: string;
  posicion_full: string;
  dorsal: number | string;
  altura: number;
  edad: number;
  nacionalidad: string;
}

export interface GameResult {
  id_partido: number;
  jornada_num: number;
  fecha: string;
  local: string;
  visitante: string;
  resultado_local: number;
  resultado_visitante: number;
  is_home: boolean;
  win: boolean;
}

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
  t2_pct: number;
  t3_pct: number;
  tl_pct: number;
  efg_pct: number;
  ts_pct: number;
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
  stats: Record<string, number>;
  rankings: Record<string, { rank: number; total: number }>;
  splits: Array<Record<string, number | string>>;
  game_log: GameLogEntry[];
}

export interface GameLogEntry {
  id_partido: number;
  jornada_num: number;
  fecha: string;
  oponente: string;
  es_local: boolean;
  minutos: string;
  minutos_decimal: number;
  puntos: number;
  rebotes_totales: number;
  asistencias: number;
  robos: number;
  perdidas: number;
  valoracion: number;
  plus_minus: number;
  [key: string]: unknown;
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

export interface GameDetail {
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

export interface TeamRanking {
  equipo: string;
  color: string;
  ortg: number;
  drtg: number;
  net_rtg: number;
  pace: number;
  efg_pct: number;
  ts_pct: number;
  ppg: number;
  rpg: number;
  apg: number;
  spg: number;
  tpg: number;
  bpg: number;
}

export interface PlayerRanking {
  rank: number;
  player_id: number;
  nombre: string;
  equipo: string;
  color: string;
  partidos: number;
  minutos_avg: number;
  value: number;
  puntos_avg: number;
  rebotes_avg: number;
  asistencias_avg: number;
  valoracion_avg: number;
}

export interface LineupData {
  lineups: Array<{
    lineup_str: string;
    minutes: number;
    off_rating: number;
    def_rating: number;
    net_rating: number;
    n_stints: number;
    side: string;
  }>;
  shared_minutes: Record<string, {
    players: string[];
    values: number[][];
  }>;
  stints: Array<{
    player: string;
    side: string;
    start_time: number;
    end_time: number;
    duration: number;
    plus_minus: number;
  }>;
}

export interface ClutchData {
  threshold: number;
  events: Array<{
    periodo: string;
    tiempo: string;
    equipo: string;
    jugador: string;
    accion: string;
    marcador_local: number;
    marcador_visitante: number;
  }>;
  stats: Array<Record<string, unknown>>;
}
