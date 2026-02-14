"""Análisis de rendimiento en situaciones clutch.

Definición clutch: últimos 5 minutos del 4C (o prórroga) con diferencia <= 5 puntos.
"""

import pandas as pd
import numpy as np


def filter_clutch_events(game_pbp: pd.DataFrame, max_diff: int = 5) -> pd.DataFrame:
    """Filtra eventos que ocurren en situación clutch.

    Clutch: últimos 5 min del 4C (abs_seconds >= 2100) o en prórrogas,
    con diferencia de marcador <= max_diff.
    """
    df = game_pbp.copy()
    df["score_diff"] = abs(
        df["marcador_local"].astype(int) - df["marcador_visitante"].astype(int)
    )

    # Últimos 5 minutos del 4C: abs_seconds >= 2100 y <= 2400
    is_4q_clutch = (df["abs_seconds"] >= 2100) & (df["abs_seconds"] <= 2400)
    # Prórrogas: abs_seconds > 2400
    is_overtime = df["abs_seconds"] > 2400

    is_clutch_time = is_4q_clutch | is_overtime
    is_close = df["score_diff"] <= max_diff

    return df[is_clutch_time & is_close].copy()


def clutch_shooting_stats(
    all_pbp: pd.DataFrame, max_diff: int = 5
) -> pd.DataFrame:
    """Calcula stats de tiro clutch vs regular para cada jugador.

    Returns:
        DataFrame con columnas: jugador, equipo,
        regular_fga, regular_fgm, regular_ts_pct,
        clutch_fga, clutch_fgm, clutch_ts_pct
    """
    SHOT_MADE = {"Tiro de 2 anotado", "Triple anotado", "Mate"}
    SHOT_MISSED = {"Tiro de 2 fallado", "Triple fallado", "Mate fallado"}
    FT_MADE = {"Tiro libre anotado"}
    FT_MISSED = {"Tiro libre fallado"}

    all_shots = all_pbp[
        all_pbp["accion"].isin(SHOT_MADE | SHOT_MISSED | FT_MADE | FT_MISSED)
    ].copy()

    all_shots["score_diff"] = abs(
        all_shots["marcador_local"].astype(int)
        - all_shots["marcador_visitante"].astype(int)
    )
    all_shots["is_clutch"] = (
        ((all_shots["abs_seconds"] >= 2100) & (all_shots["abs_seconds"] <= 2400))
        | (all_shots["abs_seconds"] > 2400)
    ) & (all_shots["score_diff"] <= max_diff)

    def _calc_ts(group):
        pts = 0
        fga = 0
        fta = 0
        for _, r in group.iterrows():
            if r["accion"] in SHOT_MADE:
                fga += 1
                pts += 3 if r["accion"] == "Triple anotado" else 2
            elif r["accion"] in SHOT_MISSED:
                fga += 1
            elif r["accion"] in FT_MADE:
                fta += 1
                pts += 1
            elif r["accion"] in FT_MISSED:
                fta += 1
        denom = 2 * (fga + 0.44 * fta)
        ts_pct = (pts / denom * 100) if denom > 0 else 0.0
        return pd.Series({"pts": pts, "fga": fga, "fta": fta, "ts_pct": ts_pct})

    # Filtrar filas sin jugador
    player_shots = all_shots[all_shots["jugador"].notna() & (all_shots["jugador"] != "")]

    regular = player_shots[~player_shots["is_clutch"]].groupby(
        ["jugador", "equipo"]
    ).apply(_calc_ts, include_groups=False).reset_index()
    regular.columns = ["jugador", "equipo", "regular_pts", "regular_fga", "regular_fta", "regular_ts_pct"]

    clutch = player_shots[player_shots["is_clutch"]].groupby(
        ["jugador", "equipo"]
    ).apply(_calc_ts, include_groups=False).reset_index()
    clutch.columns = ["jugador", "equipo", "clutch_pts", "clutch_fga", "clutch_fta", "clutch_ts_pct"]

    result = regular.merge(clutch, on=["jugador", "equipo"], how="outer").fillna(0)
    return result
