"""Rankings API routes."""

from typing import Optional

from fastapi import APIRouter, Query

from ..services.data_loader import data
from ..services.preprocessing import (
    aggregate_team_season, get_player_season, PERCENTILE_STATS,
)
from ..services.metrics import add_advanced_stats_to_teams
from ..services.constants import TEAM_COLORS

from ..services.json_utils import safe

router = APIRouter(prefix="/api/rankings", tags=["rankings"])


# Alias api_key → columna interna para rankings (mismo set que percentiles + extras)
RANKING_STATS: dict[str, str] = {
    **PERCENTILE_STATS,
    "perdidas_avg": "perdidas_avg",
    "t2_pct": "t2_pct",
    "t3_pct": "t3_pct",
    "tl_pct": "tl_pct",
    "rebotes_of_avg": "rebotes_ofensivos_avg",
    "rebotes_def_avg": "rebotes_defensivos_avg",
}


@router.get("/players")
def player_rankings(
    stat: str = Query("puntos_avg", description="Métrica a rankear"),
    min_games: int = Query(5, ge=0),
    min_minutes: float = Query(10, ge=0),
    team: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    if stat not in RANKING_STATS:
        return {"error": f"Unknown stat: {stat}", "available": list(RANKING_STATS.keys())}
    col = RANKING_STATS[stat]

    season = get_player_season()
    profiles = data.player_profiles[["player_id", "posicion"]].drop_duplicates("player_id")
    merged = season.merge(profiles, on="player_id", how="left")

    filtered = merged[merged["partidos"] >= min_games].copy()
    if min_minutes > 0:
        filtered = filtered[filtered["minutos_decimal_avg"] >= min_minutes]
    if team:
        filtered = filtered[filtered["equipo"] == team]
    if position:
        filtered = filtered[filtered["posicion"].astype(str) == position]

    if col not in filtered.columns:
        return {"error": f"Column not present: {col}"}

    filtered = filtered.sort_values(col, ascending=False).head(limit)

    result = []
    for rank, (_, row) in enumerate(filtered.iterrows(), 1):
        colors = TEAM_COLORS.get(row["equipo"], ("#666", "#999"))
        result.append({
            "rank": rank,
            "player_id": safe(row["player_id"]),
            "nombre": row["nombre"],
            "equipo": row["equipo"],
            "color": colors[0],
            "posicion": str(row.get("posicion", "")) if row.get("posicion") else "",
            "partidos": safe(row["partidos"]),
            "minutos_avg": round(float(row["minutos_decimal_avg"]), 1),
            "value": round(float(row[col]), 2),
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
