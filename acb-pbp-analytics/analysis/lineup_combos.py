"""Análisis de rendimiento por combinación de quintetos."""

import pandas as pd
import numpy as np
from collections import defaultdict


def lineup_net_rating(stints_df: pd.DataFrame, min_minutes: float = 5.0) -> pd.DataFrame:
    """Calcula net rating por quinteto.

    Net rating = (puntos anotados - puntos recibidos) / posesiones estimadas * 100

    Args:
        stints_df: DataFrame de stints (de lineup_tracker.stints_to_dataframe)
        min_minutes: Mínimo de minutos juntos para incluir

    Returns:
        DataFrame con: lineup (str), minutes, pts_for, pts_against, net_rating
    """
    records = []

    for side in ["local", "visitante"]:
        lineup_key = f"lineup_{side}"
        pts_for_start = f"score_{side}_start"
        pts_for_end = f"score_{side}_end"
        pts_against_start = f"score_{'visitante' if side == 'local' else 'local'}_start"
        pts_against_end = f"score_{'visitante' if side == 'local' else 'local'}_end"

        for _, stint in stints_df.iterrows():
            lineup_tuple = tuple(sorted(stint[lineup_key]))
            duration = stint["duration_sec"]
            pts_for = stint[pts_for_end] - stint[pts_for_start]
            pts_against = stint[pts_against_end] - stint[pts_against_start]

            records.append({
                "lineup": lineup_tuple,
                "side": side.upper(),
                "duration_sec": duration,
                "pts_for": pts_for,
                "pts_against": pts_against,
            })

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Agrupar por lineup
    grouped = (
        df.groupby("lineup")
        .agg(
            total_sec=("duration_sec", "sum"),
            total_pts_for=("pts_for", "sum"),
            total_pts_against=("pts_against", "sum"),
            n_stints=("duration_sec", "count"),
        )
        .reset_index()
    )

    grouped["minutes"] = grouped["total_sec"] / 60
    grouped = grouped[grouped["minutes"] >= min_minutes]

    # Net rating per 100 posesiones (estimado: ~1 posesión por 15 segundos)
    grouped["est_possessions"] = grouped["total_sec"] / 15
    grouped["off_rating"] = grouped["total_pts_for"] / grouped["est_possessions"] * 100
    grouped["def_rating"] = grouped["total_pts_against"] / grouped["est_possessions"] * 100
    grouped["net_rating"] = grouped["off_rating"] - grouped["def_rating"]

    grouped["lineup_str"] = grouped["lineup"].apply(lambda x: " / ".join(x))

    return grouped.sort_values("net_rating", ascending=False).reset_index(drop=True)


def shared_minutes_matrix(stints_df: pd.DataFrame, side: str = "local") -> pd.DataFrame:
    """Crea matriz de minutos compartidos entre jugadores.

    Args:
        stints_df: DataFrame de stints
        side: "local" o "visitante"

    Returns:
        DataFrame simétrico con jugadores como índice y columnas
    """
    lineup_key = f"lineup_{side}"
    shared = defaultdict(float)
    players = set()

    for _, stint in stints_df.iterrows():
        lineup = list(stint[lineup_key])
        duration = stint["duration_sec"] / 60  # en minutos
        for i, p1 in enumerate(lineup):
            players.add(p1)
            for p2 in lineup[i:]:
                shared[(p1, p2)] += duration
                if p1 != p2:
                    shared[(p2, p1)] += duration

    players = sorted(players)
    matrix = pd.DataFrame(0.0, index=players, columns=players)
    for (p1, p2), mins in shared.items():
        matrix.loc[p1, p2] = mins

    return matrix
