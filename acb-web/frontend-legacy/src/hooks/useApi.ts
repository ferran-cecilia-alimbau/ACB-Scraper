import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export function useStandings() {
  return useQuery({ queryKey: ['standings'], queryFn: api.getStandings });
}
export function useStandingsEvolution() {
  return useQuery({ queryKey: ['standings', 'evolution'], queryFn: api.getStandingsEvolution });
}
export function useTeams() {
  return useQuery({ queryKey: ['teams'], queryFn: api.getTeams });
}
export function useTeam(name: string) {
  return useQuery({ queryKey: ['team', name], queryFn: () => api.getTeam(name), enabled: !!name });
}
export function usePlayers() {
  return useQuery({ queryKey: ['players'], queryFn: api.getPlayers });
}
export function usePlayer(id: string) {
  return useQuery({ queryKey: ['player', id], queryFn: () => api.getPlayer(id), enabled: !!id });
}
export function useComparePlayers(ids: string[]) {
  return useQuery({
    queryKey: ['players', 'compare', ids],
    queryFn: () => api.comparePlayers(ids),
    enabled: ids.length >= 2,
  });
}
export function useGames() {
  return useQuery({ queryKey: ['games'], queryFn: api.getGames });
}
export function useGame(id: number) {
  return useQuery({ queryKey: ['game', id], queryFn: () => api.getGame(id), enabled: id > 0 });
}
export function useGameTimeline(id: number) {
  return useQuery({ queryKey: ['game', id, 'timeline'], queryFn: () => api.getGameTimeline(id), enabled: id > 0 });
}
export function useGameLineups(id: number) {
  return useQuery({ queryKey: ['game', id, 'lineups'], queryFn: () => api.getGameLineups(id), enabled: id > 0 });
}
export function useGameClutch(id: number, threshold = 5) {
  return useQuery({
    queryKey: ['game', id, 'clutch', threshold],
    queryFn: () => api.getGameClutch(id, threshold),
    enabled: id > 0,
  });
}
export function usePlayerRankings(stat = 'puntos_avg', minGames = 5, minMinutes = 10) {
  return useQuery({
    queryKey: ['rankings', 'players', stat, minGames, minMinutes],
    queryFn: () => api.getPlayerRankings(stat, minGames, minMinutes),
  });
}
export function useTeamRankings() {
  return useQuery({ queryKey: ['rankings', 'teams'], queryFn: api.getTeamRankings });
}
export function useLeagueAverages() {
  return useQuery({ queryKey: ['league', 'averages'], queryFn: api.getLeagueAverages });
}
