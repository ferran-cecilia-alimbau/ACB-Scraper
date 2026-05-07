"""Players API routes."""

from fastapi import APIRouter, Query

from ..services.data_loader import data
from ..services.preprocessing import (
    aggregate_player_season, compute_home_away_splits, player_game_log,
)
from ..services.constants import TEAM_COLORS, POSITION_MAP
from ..services.json_utils import safe, safe_str

router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("")
def list_players():
    season = aggregate_player_season(data.player_stats)
    profiles = data.player_profiles[["player_id", "posicion", "altura", "edad", "nacionalidad"]].drop_duplicates("player_id")
    merged = season.merge(profiles, on="player_id", how="left")

    result = []
    for _, row in merged.iterrows():
        colors = TEAM_COLORS.get(row["equipo"], ("#666", "#999"))
        result.append({
            "player_id": safe(row["player_id"]),
            "nombre": row["nombre"],
            "equipo": row["equipo"],
            "color": colors[0],
            "posicion": safe_str(row.get("posicion")),
            "posicion_full": POSITION_MAP.get(safe_str(row.get("posicion")), ""),
            "edad": safe(row.get("edad", 0)),
            "altura": safe(row.get("altura", 0)),
            "partidos": safe(row["partidos"]),
            "titularidades": safe(row["titularidades"]),
            "minutos_avg": round(float(row["minutos_decimal_avg"]), 1),
            "puntos_avg": round(float(row["puntos_avg"]), 1),
            "rebotes_avg": round(float(row["rebotes_totales_avg"]), 1),
            "asistencias_avg": round(float(row["asistencias_avg"]), 1),
            "robos_avg": round(float(row["robos_avg"]), 1),
            "perdidas_avg": round(float(row["perdidas_avg"]), 1),
            "tapones_avg": round(float(row["tapones_favor_avg"]), 1),
            "valoracion_avg": round(float(row["valoracion_avg"]), 1),
            "t2_pct": round(float(row["t2_pct"]), 1),
            "t3_pct": round(float(row["t3_pct"]), 1),
            "tl_pct": round(float(row["tl_pct"]), 1),
            "efg_pct": round(float(row["efg_pct"]), 1),
            "ts_pct": round(float(row["ts_pct"]), 1),
        })

    return result


@router.get("/compare")
def compare_players(ids: str = Query(..., description="Comma-separated player_ids")):
    player_ids = [pid.strip() for pid in ids.split(",")]
    season = aggregate_player_season(data.player_stats)
    profiles = data.player_profiles[["player_id", "posicion", "altura", "edad"]].drop_duplicates("player_id")

    result = []
    for pid in player_ids:
        matched = season[season["player_id"].astype(str) == pid]
        if matched.empty:
            continue
        row = matched.iloc[0]
        prof = profiles[profiles["player_id"].astype(str) == pid]
        pos = safe_str(prof.iloc[0]["posicion"]) if len(prof) > 0 else ""

        colors = TEAM_COLORS.get(row["equipo"], ("#666", "#999"))

        player_data = {
            "player_id": safe(row["player_id"]),
            "nombre": row["nombre"],
            "equipo": row["equipo"],
            "color": colors[0],
            "posicion": pos,
            "partidos": safe(row["partidos"]),
            "minutos_avg": round(float(row["minutos_decimal_avg"]), 1),
            "puntos_avg": round(float(row["puntos_avg"]), 1),
            "rebotes_avg": round(float(row["rebotes_totales_avg"]), 1),
            "asistencias_avg": round(float(row["asistencias_avg"]), 1),
            "robos_avg": round(float(row["robos_avg"]), 1),
            "perdidas_avg": round(float(row["perdidas_avg"]), 1),
            "tapones_avg": round(float(row["tapones_favor_avg"]), 1),
            "valoracion_avg": round(float(row["valoracion_avg"]), 1),
            "t2_pct": round(float(row["t2_pct"]), 1),
            "t3_pct": round(float(row["t3_pct"]), 1),
            "tl_pct": round(float(row["tl_pct"]), 1),
            "efg_pct": round(float(row["efg_pct"]), 1),
            "ts_pct": round(float(row["ts_pct"]), 1),
            "puntos_per36": round(float(row.get("puntos_per36", 0)), 1),
            "rebotes_per36": round(float(row.get("rebotes_totales_per36", 0)), 1),
            "asistencias_per36": round(float(row.get("asistencias_per36", 0)), 1),
            "robos_per36": round(float(row.get("robos_per36", 0)), 1),
            "tapones_per36": round(float(row.get("tapones_favor_per36", 0)), 1),
            "perdidas_per36": round(float(row.get("perdidas_per36", 0)), 1),
            "valoracion_per36": round(float(row.get("valoracion_per36", 0)), 1),
        }
        result.append(player_data)

    return result


@router.get("/{player_id}")
def get_player(player_id: str):
    season = aggregate_player_season(data.player_stats)
    matched = season[season["player_id"].astype(str) == player_id]
    if matched.empty:
        return {"error": "Player not found"}

    row = matched.iloc[0]
    player_name = row["nombre"]

    prof = data.player_profiles[data.player_profiles["player_id"].astype(str) == player_id]
    profile = {}
    if len(prof) > 0:
        p = prof.iloc[0]
        profile = {
            "posicion": safe_str(p.get("posicion")),
            "posicion_full": POSITION_MAP.get(safe_str(p.get("posicion")), ""),
            "altura": safe(p.get("altura", 0)),
            "edad": safe(p.get("edad", 0)),
            "nacionalidad": safe_str(p.get("nacionalidad")),
            "dorsal": safe(p.get("dorsal", "")),
        }

    colors = TEAM_COLORS.get(row["equipo"], ("#666", "#999"))
    splits = compute_home_away_splits(data.player_stats, data.game_info, player_name)
    game_log = player_game_log(data.player_stats, data.game_info, player_name)

    # Rankings
    all_season = aggregate_player_season(data.player_stats)
    n_players = len(all_season)
    rankings = {}
    for stat in ["puntos_avg", "rebotes_totales_avg", "asistencias_avg", "valoracion_avg"]:
        rank = int((all_season[stat] > row[stat]).sum() + 1)
        rankings[stat] = {"rank": rank, "total": n_players}

    return {
        "player_id": safe(row["player_id"]),
        "nombre": player_name,
        "equipo": row["equipo"],
        "color": colors[0],
        "colorSecondary": colors[1],
        "profile": profile,
        "stats": {
            "partidos": safe(row["partidos"]),
            "titularidades": safe(row["titularidades"]),
            "minutos_avg": round(float(row["minutos_decimal_avg"]), 1),
            "puntos_avg": round(float(row["puntos_avg"]), 1),
            "rebotes_avg": round(float(row["rebotes_totales_avg"]), 1),
            "asistencias_avg": round(float(row["asistencias_avg"]), 1),
            "robos_avg": round(float(row["robos_avg"]), 1),
            "perdidas_avg": round(float(row["perdidas_avg"]), 1),
            "tapones_avg": round(float(row["tapones_favor_avg"]), 1),
            "valoracion_avg": round(float(row["valoracion_avg"]), 1),
            "t2_pct": round(float(row["t2_pct"]), 1),
            "t3_pct": round(float(row["t3_pct"]), 1),
            "tl_pct": round(float(row["tl_pct"]), 1),
            "efg_pct": round(float(row["efg_pct"]), 1),
            "ts_pct": round(float(row["ts_pct"]), 1),
            "puntos_per36": round(float(row.get("puntos_per36", 0)), 1),
            "rebotes_per36": round(float(row.get("rebotes_totales_per36", 0)), 1),
            "asistencias_per36": round(float(row.get("asistencias_per36", 0)), 1),
            "robos_per36": round(float(row.get("robos_per36", 0)), 1),
            "tapones_per36": round(float(row.get("tapones_favor_per36", 0)), 1),
            "perdidas_per36": round(float(row.get("perdidas_per36", 0)), 1),
            "valoracion_per36": round(float(row.get("valoracion_per36", 0)), 1),
        },
        "rankings": rankings,
        "splits": splits,
        "game_log": game_log,
    }
