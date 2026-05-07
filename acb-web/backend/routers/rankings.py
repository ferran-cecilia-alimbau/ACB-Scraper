"""Rankings API routes."""

from fastapi import APIRouter, Query

from ..services.data_loader import data
from ..services.preprocessing import aggregate_player_season, aggregate_team_season
from ..services.metrics import add_advanced_stats_to_teams
from ..services.constants import TEAM_COLORS

from ..services.json_utils import safe

router = APIRouter(prefix="/api/rankings", tags=["rankings"])


@router.get("/players")
def player_rankings(
    stat: str = Query("puntos_avg", description="Stat column to rank by"),
    min_games: int = Query(5),
    min_minutes: float = Query(10),
):
    season = aggregate_player_season(data.player_stats)

    # Filter
    filtered = season[season["partidos"] >= min_games].copy()
    if min_minutes > 0:
        filtered = filtered[filtered["minutos_decimal_avg"] >= min_minutes]

    if stat not in filtered.columns:
        return {"error": f"Unknown stat: {stat}"}

    filtered = filtered.sort_values(stat, ascending=False).head(50)

    result = []
    for rank, (_, row) in enumerate(filtered.iterrows(), 1):
        colors = TEAM_COLORS.get(row["equipo"], ("#666", "#999"))
        result.append({
            "rank": rank,
            "player_id": safe(row["player_id"]),
            "nombre": row["nombre"],
            "equipo": row["equipo"],
            "color": colors[0],
            "partidos": safe(row["partidos"]),
            "minutos_avg": round(float(row["minutos_decimal_avg"]), 1),
            "value": round(float(row[stat]), 2),
            "puntos_avg": round(float(row["puntos_avg"]), 1),
            "rebotes_avg": round(float(row["rebotes_totales_avg"]), 1),
            "asistencias_avg": round(float(row["asistencias_avg"]), 1),
            "valoracion_avg": round(float(row["valoracion_avg"]), 1),
        })

    return result


@router.get("/teams")
def team_rankings():
    team_adv = add_advanced_stats_to_teams(data.team_stats, data.game_info)

    # Aggregate per team
    team_agg = team_adv.groupby("equipo").agg(
        ortg=("ortg", "mean"),
        drtg=("drtg", "mean"),
        net_rtg=("net_rtg", "mean"),
        pace=("pace", "mean"),
        efg_pct=("efg_pct", "mean"),
        ts_pct=("ts_pct", "mean"),
        puntos=("puntos", "mean"),
        rebotes_totales=("rebotes_totales", "mean"),
        asistencias=("asistencias", "mean"),
        robos=("robos", "mean"),
        perdidas=("perdidas", "mean"),
        tapones_favor=("tapones_favor", "mean"),
    ).reset_index()

    result = []
    for _, row in team_agg.iterrows():
        colors = TEAM_COLORS.get(row["equipo"], ("#666", "#999"))
        result.append({
            "equipo": row["equipo"],
            "color": colors[0],
            "ortg": round(float(row["ortg"]), 1),
            "drtg": round(float(row["drtg"]), 1),
            "net_rtg": round(float(row["net_rtg"]), 1),
            "pace": round(float(row["pace"]), 1),
            "efg_pct": round(float(row["efg_pct"]), 1),
            "ts_pct": round(float(row["ts_pct"]), 1),
            "ppg": round(float(row["puntos"]), 1),
            "rpg": round(float(row["rebotes_totales"]), 1),
            "apg": round(float(row["asistencias"]), 1),
            "spg": round(float(row["robos"]), 1),
            "tpg": round(float(row["perdidas"]), 1),
            "bpg": round(float(row["tapones_favor"]), 1),
        })

    result.sort(key=lambda x: x["net_rtg"], reverse=True)
    return result
