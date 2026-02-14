"""Rendimiento de equipos/jugadores según el estado del marcador."""

import pandas as pd
import numpy as np


def _get_margin_bucket(diff: int) -> str:
    """Clasifica la diferencia en rangos."""
    if diff >= 16:
        return "+16 o más"
    elif diff >= 11:
        return "+11 a +15"
    elif diff >= 6:
        return "+6 a +10"
    elif diff >= 1:
        return "+1 a +5"
    elif diff == 0:
        return "Empate"
    elif diff >= -5:
        return "-1 a -5"
    elif diff >= -10:
        return "-6 a -10"
    elif diff >= -15:
        return "-11 a -15"
    else:
        return "-16 o menos"


MARGIN_ORDER = [
    "-16 o menos", "-11 a -15", "-6 a -10", "-1 a -5",
    "Empate",
    "+1 a +5", "+6 a +10", "+11 a +15", "+16 o más"
]


def team_performance_by_margin(
    pbp_data: pd.DataFrame,
) -> pd.DataFrame:
    """Eficiencia de tiro por equipo según margen del marcador.

    Returns:
        DataFrame con: equipo_nombre, margin_bucket, fga, fgm, fg_pct, pts
    """
    MADE = {"Tiro de 2 anotado", "Triple anotado", "Mate", "Tiro libre anotado"}
    MISSED = {"Tiro de 2 fallado", "Triple fallado", "Mate fallado", "Tiro libre fallado"}
    ALL = MADE | MISSED

    shots = pbp_data[pbp_data["accion"].isin(ALL)].copy()

    # Calcular margen desde la perspectiva de cada equipo
    shots["diff"] = shots.apply(
        lambda r: (
            int(r["marcador_local"]) - int(r["marcador_visitante"])
            if r["equipo"] == "LOCAL"
            else int(r["marcador_visitante"]) - int(r["marcador_local"])
        ),
        axis=1,
    )
    shots["margin_bucket"] = shots["diff"].apply(_get_margin_bucket)
    shots["is_made"] = shots["accion"].isin(MADE)

    # Puntos por tiro
    def _points(row):
        if not row["is_made"]:
            return 0
        if row["accion"] == "Triple anotado":
            return 3
        elif row["accion"] in ("Tiro de 2 anotado", "Mate"):
            return 2
        return 1

    shots["pts"] = shots.apply(_points, axis=1)

    result = (
        shots.groupby(["equipo_nombre", "margin_bucket"])
        .agg(
            fga=("is_made", "count"),
            fgm=("is_made", "sum"),
            pts=("pts", "sum"),
        )
        .reset_index()
    )
    result["fg_pct"] = result["fgm"] / result["fga"] * 100

    # Ordenar margin_bucket
    result["margin_bucket"] = pd.Categorical(
        result["margin_bucket"], categories=MARGIN_ORDER, ordered=True
    )
    result = result.sort_values(["equipo_nombre", "margin_bucket"])

    return result
