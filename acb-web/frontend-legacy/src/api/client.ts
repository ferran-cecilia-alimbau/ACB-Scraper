const BASE = '/api';

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  getStandings: () => fetchApi('/standings'),
  getStandingsEvolution: () => fetchApi('/standings/evolution'),
  getTeams: () => fetchApi('/teams'),
  getTeam: (name: string) => fetchApi(`/teams/${encodeURIComponent(name)}`),
  getPlayers: () => fetchApi('/players'),
  getPlayer: (id: string) => fetchApi(`/players/${id}`),
  comparePlayers: (ids: string[]) => fetchApi(`/players/compare?ids=${ids.join(',')}`),
  getGames: () => fetchApi('/games'),
  getGame: (id: number) => fetchApi(`/games/${id}`),
  getGamePbp: (id: number) => fetchApi(`/games/${id}/pbp`),
  getGameTimeline: (id: number) => fetchApi(`/games/${id}/pbp/timeline`),
  getGameLineups: (id: number) => fetchApi(`/games/${id}/pbp/lineups`),
  getGameClutch: (id: number, threshold = 5) =>
    fetchApi(`/games/${id}/pbp/clutch?threshold=${threshold}`),
  getPlayerRankings: (stat = 'puntos_avg', minGames = 5, minMinutes = 10) =>
    fetchApi(`/rankings/players?stat=${stat}&min_games=${minGames}&min_minutes=${minMinutes}`),
  getTeamRankings: () => fetchApi('/rankings/teams'),
  getLeagueAverages: () => fetchApi('/league/averages'),
};
