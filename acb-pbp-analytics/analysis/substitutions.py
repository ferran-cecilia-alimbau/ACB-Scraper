"""Análisis del impacto de sustituciones en el marcador."""

import pandas as pd
import numpy as np


def substitution_impact(
    game_pbp: pd.DataFrame, window_sec: int = 120
) -> list[dict]:
    """Calcula el impacto en el marcador de cada sustitución.

    Para cada cambio, compara el +/- en los 'window_sec' segundos antes y después.

    Args:
        game_pbp: PBP de un partido con abs_seconds
        window_sec: Ventana de análisis antes/después del cambio (default 2 min)

    Returns:
        Lista de dicts con: player_in, player_out, team, sub_time,
        pm_before, pm_after, impact
    """
    subs_in = game_pbp[game_pbp["accion"] == "Entra a pista"].copy()
    subs_out = game_pbp[game_pbp["accion"] == "Sale de la pista"].copy()

    # Emparejar: mismo timestamp y equipo
    impacts = []
    for _, sub_in_row in subs_in.iterrows():
        t = sub_in_row["abs_seconds"]
        team = sub_in_row["equipo"]

        # Buscar quién sale al mismo tiempo del mismo equipo
        matching_out = subs_out[
            (subs_out["abs_seconds"] == t)
            & (subs_out["equipo"] == team)
        ]

        player_out = matching_out["jugador"].iloc[0] if len(matching_out) > 0 else ""

        # Calcular marcador antes y después
        before_events = game_pbp[
            (game_pbp["abs_seconds"] >= t - window_sec)
            & (game_pbp["abs_seconds"] < t)
        ]
        after_events = game_pbp[
            (game_pbp["abs_seconds"] > t)
            & (game_pbp["abs_seconds"] <= t + window_sec)
        ]

        def _get_pm(events, team_side):
            if events.empty:
                return 0
            first_local = int(events.iloc[0]["marcador_local"])
            first_visit = int(events.iloc[0]["marcador_visitante"])
            last_local = int(events.iloc[-1]["marcador_local"])
            last_visit = int(events.iloc[-1]["marcador_visitante"])
            local_diff = last_local - first_local
            visit_diff = last_visit - first_visit
            if team_side == "LOCAL":
                return local_diff - visit_diff
            return visit_diff - local_diff

        pm_before = _get_pm(before_events, team)
        pm_after = _get_pm(after_events, team)

        impacts.append({
            "player_in": sub_in_row["jugador"],
            "player_out": player_out,
            "team": team,
            "equipo_nombre": sub_in_row.get("equipo_nombre", team),
            "sub_time": t,
            "id_partido": sub_in_row["id_partido"],
            "pm_before": pm_before,
            "pm_after": pm_after,
            "impact": pm_after - pm_before,
        })

    return impacts


def aggregate_sub_impact(impacts: list[dict], min_subs: int = 3) -> pd.DataFrame:
    """Agrega impacto de sustituciones por jugador.

    Args:
        impacts: Lista de impactos de sustituciones
        min_subs: Mínimo de sustituciones para incluir al jugador

    Returns:
        DataFrame con: player_in, equipo_nombre, n_subs, avg_impact, avg_pm_after
    """
    if not impacts:
        return pd.DataFrame()
    df = pd.DataFrame(impacts)
    result = (
        df.groupby(["player_in", "equipo_nombre"])
        .agg(
            n_subs=("impact", "count"),
            avg_impact=("impact", "mean"),
            avg_pm_before=("pm_before", "mean"),
            avg_pm_after=("pm_after", "mean"),
        )
        .reset_index()
    )
    result = result[result["n_subs"] >= min_subs].sort_values(
        "avg_impact", ascending=False
    )
    return result
