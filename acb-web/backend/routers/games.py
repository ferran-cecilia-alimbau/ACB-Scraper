"""Games API routes."""

from fastapi import APIRouter, Query

from ..services.data_loader import data
from ..services.metrics import four_factors
from ..services.constants import TEAM_COLORS
from ..services.pbp_service import (
    load_and_analyze_game,
    lineup_net_rating,
    shared_minutes_matrix,
    clutch_shooting_stats,
    filter_clutch_events,
)

from ..services.json_utils import safe, safe_str

router = APIRouter(prefix="/api/games", tags=["games"])


@router.get("")
def list_games():
    gi = data.game_info.sort_values("jornada_num", ascending=False)
    result = []
    for _, g in gi.iterrows():
        lc = TEAM_COLORS.get(g["local"], ("#666", "#999"))
        vc = TEAM_COLORS.get(g["visitante"], ("#666", "#999"))
        result.append({
            "id_partido": safe(g["id_partido"]),
            "jornada_num": safe(g["jornada_num"]),
            "fecha": g["fecha"],
            "local": g["local"],
            "visitante": g["visitante"],
            "resultado_local": safe(g["resultado_local"]),
            "resultado_visitante": safe(g["resultado_visitante"]),
            "local_color": lc[0],
            "visitante_color": vc[0],
            "pabellon": g.get("pabellon", ""),
            "publico": safe(g.get("publico", 0)),
        })
    return result


@router.get("/{game_id}")
def get_game(game_id: int):
    gi = data.game_info[data.game_info["id_partido"] == game_id]
    if gi.empty:
        return {"error": "Game not found"}

    g = gi.iloc[0]
    local = g["local"]
    visitante = g["visitante"]

    # Box score
    ps = data.player_stats[data.player_stats["id_partido"] == game_id]
    local_players = ps[ps["equipo"] == local]
    visit_players = ps[ps["equipo"] == visitante]

    def player_box(df):
        result = []
        for _, p in df.iterrows():
            result.append({
                "player_id": safe(p["player_id"]),
                "nombre": p["nombre"],
                "es_titular": bool(p["es_titular"]),
                "minutos": p["minutos"],
                "puntos": safe(p["puntos"]),
                "t2": f"{safe(p['t2_anotados'])}/{safe(p['t2_intentados'])}",
                "t3": f"{safe(p['t3_anotados'])}/{safe(p['t3_intentados'])}",
                "tl": f"{safe(p['tl_anotados'])}/{safe(p['tl_intentados'])}",
                "rebotes": safe(p["rebotes_totales"]),
                "reb_of": safe(p["rebotes_ofensivos"]),
                "reb_def": safe(p["rebotes_defensivos"]),
                "asistencias": safe(p["asistencias"]),
                "robos": safe(p["robos"]),
                "perdidas": safe(p["perdidas"]),
                "tapones_favor": safe(p["tapones_favor"]),
                "tapones_contra": safe(p["tapones_contra"]),
                "faltas": safe(p["faltas_cometidas"]),
                "plus_minus": safe(p["plus_minus"]),
                "valoracion": safe(p["valoracion"]),
            })
        return result

    # Team stats for four factors
    ts = data.team_stats[data.team_stats["id_partido"] == game_id]
    local_ts = ts[ts["equipo"] == local]
    visit_ts = ts[ts["equipo"] == visitante]

    local_ff = four_factors(local_ts.iloc[0].to_dict()) if len(local_ts) > 0 else {}
    visit_ff = four_factors(visit_ts.iloc[0].to_dict()) if len(visit_ts) > 0 else {}

    parciales_local = g.get("parciales_local", "")
    parciales_visitante = g.get("parciales_visitante", "")

    lc = TEAM_COLORS.get(local, ("#666", "#999"))
    vc = TEAM_COLORS.get(visitante, ("#666", "#999"))

    return {
        "id_partido": safe(g["id_partido"]),
        "jornada_num": safe(g["jornada_num"]),
        "fecha": g["fecha"],
        "local": local,
        "visitante": visitante,
        "resultado_local": safe(g["resultado_local"]),
        "resultado_visitante": safe(g["resultado_visitante"]),
        "local_color": lc[0],
        "visitante_color": vc[0],
        "pabellon": g.get("pabellon", ""),
        "publico": safe(g.get("publico", 0)),
        "parciales_local": parciales_local,
        "parciales_visitante": parciales_visitante,
        "box_score": {
            "local": player_box(local_players),
            "visitante": player_box(visit_players),
        },
        "four_factors": {
            "local": {k: round(v, 1) for k, v in local_ff.items()},
            "visitante": {k: round(v, 1) for k, v in visit_ff.items()},
        },
    }


@router.get("/{game_id}/pbp")
def get_game_pbp(game_id: int):
    result = load_and_analyze_game(game_id)
    if result is None:
        return {"error": "PBP not found"}

    pbp = result["pbp"]
    events = []
    for _, row in pbp.iterrows():
        events.append({
            "periodo": row.get("periodo", ""),
            "tiempo": row.get("tiempo", ""),
            "marcador_local": safe(row.get("marcador_local", 0)),
            "marcador_visitante": safe(row.get("marcador_visitante", 0)),
            "equipo": row.get("equipo", ""),
            "jugador": row.get("jugador", ""),
            "accion": row.get("accion", ""),
        })
    return events


@router.get("/{game_id}/pbp/timeline")
def get_score_timeline(game_id: int):
    result = load_and_analyze_game(game_id)
    if result is None:
        return {"error": "PBP not found"}

    pbp = result["pbp"]
    timeline = []
    for _, row in pbp.iterrows():
        ml = row.get("marcador_local", 0)
        mv = row.get("marcador_visitante", 0)
        if ml > 0 or mv > 0:
            timeline.append({
                "periodo": row.get("periodo", ""),
                "tiempo": row.get("tiempo", ""),
                "marcador_local": safe(ml),
                "marcador_visitante": safe(mv),
                "diff": safe(ml - mv),
            })

    return timeline


@router.get("/{game_id}/pbp/lineups")
def get_game_lineups(game_id: int):
    result = load_and_analyze_game(game_id)
    if result is None:
        return {"error": "PBP not found"}

    stints_df = result["stints_df"]
    if stints_df.empty:
        return {"lineups": [], "shared_minutes": {}, "stints": []}

    # Lineup ratings (use min_minutes=1.0 so single-game lineups show up)
    lr = lineup_net_rating(stints_df, min_minutes=1.0)
    lineups = []
    for _, row in lr.iterrows():
        lineups.append({
            "lineup_str": row.get("lineup_str", ""),
            "side": row.get("side", ""),
            "minutes": safe(row.get("minutes", 0)),
            "off_rating": safe(row.get("off_rating", 0)),
            "def_rating": safe(row.get("def_rating", 0)),
            "net_rating": safe(row.get("net_rating", 0)),
            "n_stints": safe(row.get("n_stints", 0)),
        })

    # Shared minutes matrix — call separately for each side
    shared = {}
    for side in ["local", "visitante"]:
        sm = shared_minutes_matrix(stints_df, side=side)
        if sm is not None and not sm.empty:
            side_key = side.upper()
            shared[side_key] = {
                "players": list(sm.columns),
                "values": [[safe(v) for v in row] for row in sm.values.tolist()],
            }

    # Per-player stints for gantt chart (explode lineup tuples into individual player rows)
    stints_list = []
    for _, stint in stints_df.iterrows():
        start_min = safe(stint["start_sec"]) / 60
        end_min = safe(stint["end_sec"]) / 60
        duration_min = safe(stint["duration_sec"]) / 60
        pm_local = safe(stint["plus_minus_local"])

        for side in ["local", "visitante"]:
            lineup_key = f"lineup_{side}"
            lineup = stint[lineup_key]
            pm = pm_local if side == "local" else -pm_local

            for player in sorted(lineup):
                stints_list.append({
                    "player": player,
                    "side": side.upper(),
                    "start_time": round(start_min, 2),
                    "end_time": round(end_min, 2),
                    "duration": round(duration_min, 2),
                    "plus_minus": pm,
                })

    return {
        "lineups": lineups,
        "shared_minutes": shared,
        "stints": stints_list,
    }


@router.get("/{game_id}/pbp/clutch")
def get_game_clutch(game_id: int, threshold: int = Query(5)):
    result = load_and_analyze_game(game_id)
    if result is None:
        return {"error": "PBP not found"}

    pbp = result["pbp"]

    clutch_events = filter_clutch_events(pbp, threshold=threshold)
    clutch_stats = clutch_shooting_stats(pbp, threshold=threshold)

    events = []
    if clutch_events is not None and not clutch_events.empty:
        for _, row in clutch_events.iterrows():
            events.append({
                "periodo": row.get("periodo", ""),
                "tiempo": row.get("tiempo", ""),
                "equipo": row.get("equipo", ""),
                "jugador": row.get("jugador", ""),
                "accion": row.get("accion", ""),
                "marcador_local": safe(row.get("marcador_local", 0)),
                "marcador_visitante": safe(row.get("marcador_visitante", 0)),
            })

    stats = []
    if clutch_stats is not None and not clutch_stats.empty:
        for _, row in clutch_stats.iterrows():
            stats.append({k: safe(v) for k, v in row.to_dict().items()})

    return {
        "threshold": threshold,
        "events": events,
        "stats": stats,
    }
