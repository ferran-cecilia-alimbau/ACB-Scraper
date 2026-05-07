"""Teams API routes."""

from fastapi import APIRouter

from ..services.data_loader import data
from ..services.preprocessing import aggregate_team_season, calculate_standings
from ..services.metrics import add_advanced_stats_to_teams, four_factors
from ..services.constants import TEAM_COLORS, POSITION_MAP
from ..services.json_utils import safe, safe_str

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("")
def list_teams():
    team_season = aggregate_team_season(data.team_stats)
    standings = calculate_standings(data.game_info)

    result = []
    for _, row in team_season.iterrows():
        team = row["equipo"]
        colors = TEAM_COLORS.get(team, ("#666", "#999"))
        stand = standings[standings["equipo"] == team]
        wins = int(stand["G"].values[0]) if len(stand) > 0 else 0
        losses = int(stand["P"].values[0]) if len(stand) > 0 else 0
        pos = int(stand.index[0]) if len(stand) > 0 else 0

        result.append({
            "name": team,
            "color": colors[0],
            "colorSecondary": colors[1],
            "pos": pos,
            "wins": wins,
            "losses": losses,
            "games": int(row["partidos"]),
            "ppg": round(float(row["puntos_avg"]), 1),
            "rpg": round(float(row["rebotes_totales_avg"]), 1),
            "apg": round(float(row["asistencias_avg"]), 1),
            "t2_pct": round(float(row["t2_pct"]), 1),
            "t3_pct": round(float(row["t3_pct"]), 1),
            "tl_pct": round(float(row["tl_pct"]), 1),
        })

    result.sort(key=lambda x: x["pos"])
    return result


@router.get("/{name}")
def get_team(name: str):
    team_adv = add_advanced_stats_to_teams(data.team_stats, data.game_info)
    team_data = team_adv[team_adv["equipo"] == name]
    if team_data.empty:
        return {"error": "Team not found"}

    standings = calculate_standings(data.game_info)
    stand = standings[standings["equipo"] == name]
    pos = int(stand.index[0]) if len(stand) > 0 else 0
    stand_row = stand.iloc[0].to_dict() if len(stand) > 0 else {}

    # Season averages
    avg_cols = ["puntos", "rebotes_totales", "asistencias", "robos", "perdidas",
                "tapones_favor", "faltas_cometidas", "valoracion"]
    season_avgs = {}
    for col in avg_cols:
        season_avgs[col] = round(float(team_data[col].mean()), 1)

    # Shooting
    season_avgs["t2_pct"] = round(float(team_data["t2_encestados"].sum() / team_data["t2_intentados"].sum() * 100), 1) if team_data["t2_intentados"].sum() > 0 else 0
    season_avgs["t3_pct"] = round(float(team_data["t3_encestados"].sum() / team_data["t3_intentados"].sum() * 100), 1) if team_data["t3_intentados"].sum() > 0 else 0
    season_avgs["tl_pct"] = round(float(team_data["tl_encestados"].sum() / team_data["tl_intentados"].sum() * 100), 1) if team_data["tl_intentados"].sum() > 0 else 0

    # Advanced
    season_avgs["ortg"] = round(float(team_data["ortg"].mean()), 1)
    season_avgs["drtg"] = round(float(team_data["drtg"].mean()), 1)
    season_avgs["net_rtg"] = round(float(team_data["net_rtg"].mean()), 1)
    season_avgs["pace"] = round(float(team_data["pace"].mean()), 1)
    season_avgs["efg_pct"] = round(float(team_data["efg_pct"].mean()), 1)
    season_avgs["ts_pct"] = round(float(team_data["ts_pct"].mean()), 1)

    # Roster
    roster = data.player_profiles[data.player_profiles["equipo"] == name]
    roster_list = []
    for _, p in roster.iterrows():
        roster_list.append({
            "player_id": safe(p["player_id"]),
            "nombre": p["nombre"],
            "posicion": p.get("posicion", ""),
            "posicion_full": POSITION_MAP.get(p.get("posicion", ""), ""),
            "dorsal": safe(p.get("dorsal", "")),
            "altura": safe(p.get("altura", 0)),
            "edad": safe(p.get("edad", 0)),
            "nacionalidad": p.get("nacionalidad", ""),
        })

    # Game results
    gi = data.game_info
    home_games = gi[gi["local"] == name]
    away_games = gi[gi["visitante"] == name]
    games = []
    for _, g in home_games.iterrows():
        games.append({
            "id_partido": safe(g["id_partido"]),
            "jornada_num": safe(g["jornada_num"]),
            "fecha": g["fecha"],
            "local": g["local"],
            "visitante": g["visitante"],
            "resultado_local": safe(g["resultado_local"]),
            "resultado_visitante": safe(g["resultado_visitante"]),
            "is_home": True,
            "win": g["resultado_local"] > g["resultado_visitante"],
        })
    for _, g in away_games.iterrows():
        games.append({
            "id_partido": safe(g["id_partido"]),
            "jornada_num": safe(g["jornada_num"]),
            "fecha": g["fecha"],
            "local": g["local"],
            "visitante": g["visitante"],
            "resultado_local": safe(g["resultado_local"]),
            "resultado_visitante": safe(g["resultado_visitante"]),
            "is_home": False,
            "win": g["resultado_visitante"] > g["resultado_local"],
        })
    games.sort(key=lambda x: x["jornada_num"])

    colors = TEAM_COLORS.get(name, ("#666", "#999"))

    return {
        "name": name,
        "color": colors[0],
        "colorSecondary": colors[1],
        "pos": pos,
        "standings": {k: safe(v) for k, v in stand_row.items()},
        "season_avgs": season_avgs,
        "roster": roster_list,
        "games": games,
    }
