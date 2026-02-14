"""Detección de rachas de puntos (parciales) en partidos.

Una racha es una secuencia de puntos consecutivos de un equipo sin que
el rival anote (ej: 12-0). Se detectan rachas >= umbral_mínimo.
"""

import pandas as pd


def detect_scoring_runs(
    game_pbp: pd.DataFrame, min_run: int = 6
) -> list[dict]:
    """Detecta rachas de puntos >= min_run en un partido.

    Args:
        game_pbp: PBP de un partido en orden cronológico con abs_seconds
        min_run: Puntos mínimos de la racha (default 6-0)

    Returns:
        Lista de rachas con: team, points, start_sec, end_sec,
        start_score_local, start_score_visitante, end_score_local, end_score_visitante
    """
    SCORING_ACTIONS = {
        "Tiro de 2 anotado", "Triple anotado", "Mate",
        "Tiro libre anotado",
    }

    runs = []
    current_team = None
    current_points = 0
    run_start_sec = 0.0
    run_start_score = (0, 0)
    last_sec = 0.0
    last_score = (0, 0)

    for _, row in game_pbp.iterrows():
        if row["accion"] not in SCORING_ACTIONS:
            continue

        team = row["equipo"]
        abs_sec = row["abs_seconds"]
        score = (int(row["marcador_local"]), int(row["marcador_visitante"]))

        # Calcular puntos de esta acción
        if row["accion"] == "Triple anotado":
            pts = 3
        elif row["accion"] in ("Tiro de 2 anotado", "Mate"):
            pts = 2
        else:
            pts = 1

        if team == current_team:
            current_points += pts
        else:
            # El otro equipo anota: cerrar racha anterior si >= min_run
            if current_points >= min_run and current_team is not None:
                runs.append({
                    "team": current_team,
                    "points": current_points,
                    "start_sec": run_start_sec,
                    "end_sec": last_sec,
                    "start_score_local": run_start_score[0],
                    "start_score_visitante": run_start_score[1],
                    "end_score_local": last_score[0],
                    "end_score_visitante": last_score[1],
                })
            current_team = team
            current_points = pts
            run_start_sec = abs_sec
            run_start_score = score

        last_sec = abs_sec
        last_score = score

    # Cerrar última racha
    if current_points >= min_run and current_team is not None:
        runs.append({
            "team": current_team,
            "points": current_points,
            "start_sec": run_start_sec,
            "end_sec": last_sec,
            "start_score_local": run_start_score[0],
            "start_score_visitante": run_start_score[1],
            "end_score_local": last_score[0],
            "end_score_visitante": last_score[1],
        })

    return runs


def runs_to_dataframe(runs: list[dict]) -> pd.DataFrame:
    """Convierte rachas a DataFrame."""
    if not runs:
        return pd.DataFrame()
    df = pd.DataFrame(runs)
    df["duration_sec"] = df["end_sec"] - df["start_sec"]
    return df
