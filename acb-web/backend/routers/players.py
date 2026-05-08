"""Players API routes.

Endpoints:
  GET /api/players                  → listado con filtros server-side
  GET /api/players/compare?ids=...  → comparador (legacy)
  GET /api/players/search?q=...     → búsqueda fuzzy para Cmd-K
  GET /api/players/{id}             → ficha completa con percentiles
"""

from typing import Optional

import numpy as np
from fastapi import APIRouter, Query

from ..services.data_loader import data
from ..services.preprocessing import (
    aggregate_player_season, compute_home_away_splits, player_game_log,
    get_player_season, get_player_percentiles, player_last_n_games,
    player_best_game, PERCENTILE_STATS,
)
from ..services.constants import TEAM_COLORS, POSITION_MAP
from ..services.json_utils import safe, safe_str

router = APIRouter(prefix="/api/players", tags=["players"])


def _row_to_summary(row, profile_row=None) -> dict:
    """Construye el shape público de un jugador (lista + comparador)."""
    colors = TEAM_COLORS.get(row["equipo"], ("#666", "#999"))
    posicion = ""
    edad = 0
    altura = 0
    if profile_row is not None and len(profile_row) > 0:
        p = profile_row.iloc[0]
        posicion = safe_str(p.get("posicion"))
        edad = safe(p.get("edad", 0))
        altura = safe(p.get("altura", 0))

    return {
        "player_id": safe(row["player_id"]),
        "nombre": row["nombre"],
        "equipo": row["equipo"],
        "color": colors[0],
        "posicion": posicion,
        "posicion_full": POSITION_MAP.get(posicion, ""),
        "edad": edad,
        "altura": altura,
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
        "plus_minus_avg": round(float(row.get("plus_minus_avg", 0) or 0), 1),
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
        # Totales (para vista "Totales")
        "puntos_total": int(row["puntos"]),
        "rebotes_total": int(row["rebotes_totales"]),
        "asistencias_total": int(row["asistencias"]),
        "valoracion_total": int(row["valoracion"]),
    }


@router.get("")
def list_players(
    team: Optional[str] = Query(None, description="Filtra por equipo (forma corta)"),
    position: Optional[str] = Query(None, description="Filtra por posición (B/E/A/AP/P)"),
    min_games: int = Query(0, ge=0),
    min_minutes: float = Query(0, ge=0),
    sort: str = Query("valoracion_avg", description="Columna de orden"),
    direction: str = Query("desc", regex="^(asc|desc)$"),
    limit: int = Query(500, ge=1, le=1000),
):
    season = get_player_season()
    profiles = data.player_profiles[
        ["player_id", "posicion", "altura", "edad", "nacionalidad"]
    ].drop_duplicates("player_id")
    merged = season.merge(profiles, on="player_id", how="left")

    # Filtros
    if team:
        merged = merged[merged["equipo"] == team]
    if position:
        merged = merged[merged["posicion"].astype(str) == position]
    if min_games > 0:
        merged = merged[merged["partidos"] >= min_games]
    if min_minutes > 0:
        merged = merged[merged["minutos_decimal_avg"] >= min_minutes]

    # Sort
    sort_col = sort if sort in merged.columns else "valoracion_avg"
    ascending = direction == "asc"
    merged = merged.sort_values(sort_col, ascending=ascending, na_position="last")
    merged = merged.head(limit)

    result = []
    for _, row in merged.iterrows():
        prof = profiles[profiles["player_id"] == row["player_id"]]
        result.append(_row_to_summary(row, prof))
    return result


@router.get("/search")
def search_players(q: str = Query(..., min_length=1)):
    """Búsqueda case-insensitive por subcadena en el nombre, para Cmd-K."""
    season = get_player_season()
    needle = q.strip().lower()
    if not needle:
        return []
    matched = season[season["nombre"].str.lower().str.contains(needle, na=False)]
    matched = matched.sort_values("valoracion_avg", ascending=False).head(20)

    result = []
    for _, row in matched.iterrows():
        colors = TEAM_COLORS.get(row["equipo"], ("#666", "#999"))
        result.append({
            "player_id": safe(row["player_id"]),
            "nombre": row["nombre"],
            "equipo": row["equipo"],
            "color": colors[0],
            "puntos_avg": round(float(row["puntos_avg"]), 1),
            "valoracion_avg": round(float(row["valoracion_avg"]), 1),
        })
    return result


@router.get("/compare")
def compare_players(ids: str = Query(..., description="Comma-separated player_ids")):
    player_ids = [pid.strip() for pid in ids.split(",")]
    season = get_player_season()
    profiles = data.player_profiles[
        ["player_id", "posicion", "altura", "edad"]
    ].drop_duplicates("player_id")

    result = []
    for pid in player_ids:
        matched = season[season["player_id"].astype(str) == pid]
        if matched.empty:
            continue
        row = matched.iloc[0]
        prof = profiles[profiles["player_id"].astype(str) == pid]
        result.append(_row_to_summary(row, prof))
    return result


@router.get("/{player_id}")
def get_player(player_id: str):
    season = get_player_season()
    matched = season[season["player_id"].astype(str) == player_id]
    if matched.empty:
        return {"error": "Player not found"}

    row = matched.iloc[0]
    pid_int = int(row["player_id"])
    player_name = row["nombre"]

    prof = data.player_profiles[
        data.player_profiles["player_id"].astype(str) == player_id
    ]
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
    last_5 = player_last_n_games(data.player_stats, data.game_info, player_name, n=5)
    best_game = player_best_game(data.player_stats, data.game_info, player_name)

    # Percentiles + ranks precalculados (puede ser None si no cumple mínimos)
    percentiles_all, ranks_all = get_player_percentiles()
    percentiles: dict[str, float | None] = {}
    rankings: dict[str, dict] = {}
    pool_total = (
        len(next(iter(percentiles_all.values()))) if percentiles_all else 0
    )
    for api_key in PERCENTILE_STATS:
        pct_map = percentiles_all.get(api_key, {})
        rank_map = ranks_all.get(api_key, {})
        percentiles[api_key] = pct_map.get(pid_int)
        if pid_int in rank_map:
            rankings[api_key] = {"rank": int(rank_map[pid_int]), "total": pool_total}
        else:
            rankings[api_key] = {"rank": None, "total": pool_total}

    summary = _row_to_summary(row, prof)

    return {
        "player_id": pid_int,
        "nombre": player_name,
        "equipo": row["equipo"],
        "color": colors[0],
        "colorSecondary": colors[1],
        "profile": profile,
        "stats": {k: v for k, v in summary.items() if k not in {"player_id", "nombre", "equipo", "color", "posicion", "posicion_full", "edad", "altura"}},
        "rankings": rankings,
        "percentiles": percentiles,
        "splits": splits,
        "last_5": last_5,
        "best_game": best_game,
        "game_log": game_log,
    }
