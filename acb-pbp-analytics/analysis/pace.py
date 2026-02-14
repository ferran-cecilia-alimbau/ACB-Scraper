"""Cálculo de pace (posesiones por 40 minutos) por equipo."""

import pandas as pd


def calculate_pace_from_possessions(
    possessions_df: pd.DataFrame, game_info: pd.DataFrame
) -> pd.DataFrame:
    """Calcula pace por equipo a partir de posesiones detectadas por PBP.

    Args:
        possessions_df: DataFrame de posesiones con 'team', 'id_partido', 'end_sec'
        game_info: estadisticas_partido.csv con 'id_partido', 'local', 'visitante'

    Returns:
        DataFrame con equipo, n_games, total_possessions, avg_pace
    """
    # Determinar duración de cada partido (max abs_seconds)
    game_durations = possessions_df.groupby("id_partido")["end_sec"].max().reset_index()
    game_durations.columns = ["id_partido", "game_duration_sec"]

    # Contar posesiones por equipo por partido
    poss_counts = (
        possessions_df.groupby(["id_partido", "team"])
        .size()
        .reset_index(name="possessions")
    )

    # Merge con duración del partido
    poss_counts = poss_counts.merge(game_durations, on="id_partido")

    # Calcular pace: (posesiones / minutos_jugados) * 40
    poss_counts["minutes_played"] = poss_counts["game_duration_sec"] / 60
    poss_counts["pace"] = poss_counts["possessions"] / poss_counts["minutes_played"] * 40

    # Resolver LOCAL/VISITANTE a nombre de equipo
    team_map = {}
    for _, row in game_info.iterrows():
        team_map[(row["id_partido"], "LOCAL")] = row["local"]
        team_map[(row["id_partido"], "VISITANTE")] = row["visitante"]

    poss_counts["equipo"] = poss_counts.apply(
        lambda r: team_map.get((r["id_partido"], r["team"]), r["team"]), axis=1
    )

    # Agregar por equipo
    result = (
        poss_counts.groupby("equipo")
        .agg(
            n_games=("id_partido", "nunique"),
            total_possessions=("possessions", "sum"),
            avg_pace=("pace", "mean"),
        )
        .reset_index()
        .sort_values("avg_pace", ascending=False)
    )

    return result


def calculate_pace_from_box_score(team_stats: pd.DataFrame) -> pd.DataFrame:
    """Estima pace a partir de box score (fórmula clásica).

    Posesiones ≈ FGA + 0.44 * FTA + TOV - OREB
    Pace = posesiones / (minutos / 5) * 40
    """
    df = team_stats.copy()
    df["est_possessions"] = (
        df["t2_intentados"] + df["t3_intentados"]
        + 0.44 * df["tl_intentados"]
        + df["perdidas"]
        - df["rebotes_ofensivos"]
    )
    df["est_pace"] = df["est_possessions"] / (200 / 5) * 40  # 200 min = 5 jugadores * 40 min

    result = (
        df.groupby("equipo")
        .agg(
            n_games=("id_partido", "nunique"),
            total_est_possessions=("est_possessions", "sum"),
            avg_est_pace=("est_pace", "mean"),
        )
        .reset_index()
        .sort_values("avg_est_pace", ascending=False)
    )

    return result
