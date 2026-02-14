"""Análisis de patrones de tiro según contexto (game state)."""

import pandas as pd
import numpy as np


def _classify_game_state(row) -> str:
    """Clasifica el game state: 'Ganando', 'Perdiendo', 'Empatado'."""
    diff = int(row["marcador_local"]) - int(row["marcador_visitante"])
    if row["equipo"] == "VISITANTE":
        diff = -diff
    if diff > 0:
        return "Ganando"
    elif diff < 0:
        return "Perdiendo"
    return "Empatado"


def shooting_by_game_state(pbp_data: pd.DataFrame) -> pd.DataFrame:
    """Tasa de tiro de 3 vs 2 según game state.

    Returns:
        DataFrame con: equipo_nombre, game_state, t2_attempts, t3_attempts,
        t2_made, t3_made, t3_rate, t2_pct, t3_pct
    """
    SHOT_2_MADE = {"Tiro de 2 anotado", "Mate"}
    SHOT_2_MISSED = {"Tiro de 2 fallado", "Mate fallado"}
    SHOT_3_MADE = {"Triple anotado"}
    SHOT_3_MISSED = {"Triple fallado"}
    ALL_SHOTS = SHOT_2_MADE | SHOT_2_MISSED | SHOT_3_MADE | SHOT_3_MISSED

    shots = pbp_data[pbp_data["accion"].isin(ALL_SHOTS)].copy()
    shots["game_state"] = shots.apply(_classify_game_state, axis=1)
    shots["is_3pt"] = shots["accion"].isin(SHOT_3_MADE | SHOT_3_MISSED)
    shots["is_made"] = shots["accion"].isin(SHOT_2_MADE | SHOT_3_MADE)

    result = (
        shots.groupby(["equipo_nombre", "game_state"])
        .agg(
            t2_attempts=("is_3pt", lambda x: (~x).sum()),
            t3_attempts=("is_3pt", "sum"),
            total_made=("is_made", "sum"),
            total_attempts=("is_made", "count"),
        )
        .reset_index()
    )

    result["t3_rate"] = (
        result["t3_attempts"] / (result["t2_attempts"] + result["t3_attempts"]) * 100
    )

    # También calcular porcentaje por tipo
    shots_3 = shots[shots["is_3pt"]].groupby(["equipo_nombre", "game_state"]).agg(
        t3_made=("is_made", "sum"), t3_att=("is_made", "count")
    ).reset_index()
    shots_3["t3_pct"] = shots_3["t3_made"] / shots_3["t3_att"] * 100

    shots_2 = shots[~shots["is_3pt"]].groupby(["equipo_nombre", "game_state"]).agg(
        t2_made=("is_made", "sum"), t2_att=("is_made", "count")
    ).reset_index()
    shots_2["t2_pct"] = shots_2["t2_made"] / shots_2["t2_att"] * 100

    result = result.merge(
        shots_3[["equipo_nombre", "game_state", "t3_pct"]],
        on=["equipo_nombre", "game_state"], how="left"
    ).merge(
        shots_2[["equipo_nombre", "game_state", "t2_pct"]],
        on=["equipo_nombre", "game_state"], how="left"
    )

    return result


def shooting_by_quarter(pbp_data: pd.DataFrame) -> pd.DataFrame:
    """Selección de tiro por cuarto.

    Returns:
        DataFrame con: equipo_nombre, periodo, t2_attempts, t3_attempts,
        t2_pct, t3_pct, t3_rate
    """
    SHOT_2_MADE = {"Tiro de 2 anotado", "Mate"}
    SHOT_2_MISSED = {"Tiro de 2 fallado", "Mate fallado"}
    SHOT_3_MADE = {"Triple anotado"}
    SHOT_3_MISSED = {"Triple fallado"}
    ALL_SHOTS = SHOT_2_MADE | SHOT_2_MISSED | SHOT_3_MADE | SHOT_3_MISSED

    shots = pbp_data[pbp_data["accion"].isin(ALL_SHOTS)].copy()
    shots["is_3pt"] = shots["accion"].isin(SHOT_3_MADE | SHOT_3_MISSED)
    shots["is_made"] = shots["accion"].isin(SHOT_2_MADE | SHOT_3_MADE)

    result = (
        shots.groupby(["equipo_nombre", "periodo"])
        .agg(
            t2_attempts=("is_3pt", lambda x: (~x).sum()),
            t3_attempts=("is_3pt", "sum"),
            total_made=("is_made", "sum"),
        )
        .reset_index()
    )

    result["t3_rate"] = (
        result["t3_attempts"] / (result["t2_attempts"] + result["t3_attempts"]) * 100
    )

    return result
