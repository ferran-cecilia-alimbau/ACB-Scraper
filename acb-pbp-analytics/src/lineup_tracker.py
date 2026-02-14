"""State machine para rastrear qué jugadores están en pista en cada momento.

Lógica:
  1. Al inicio de cada periodo, los eventos "Quinteto inicial" definen los 5 jugadores
     por equipo.
  2. "Entra a pista" / "Sale de la pista" actualizan el lineup.
  3. Se agrupan sustituciones del mismo timestamp antes de cerrar un stint.
  4. Output: lista de stints con lineup, tiempos y marcador.
"""

import pandas as pd
import numpy as np
from collections import defaultdict


def _extract_score(row):
    """Extrae marcador de una fila PBP."""
    return int(row["marcador_local"]), int(row["marcador_visitante"])


def track_lineups_for_game(game_pbp: pd.DataFrame) -> list[dict]:
    """Rastrea lineups a lo largo de un partido completo.

    Args:
        game_pbp: DataFrame de PBP de un partido, ya en orden cronológico,
                  con columna 'abs_seconds'.

    Returns:
        Lista de stints, cada uno un dict con:
          - lineup_local: frozenset de nombres de jugadores locales
          - lineup_visitante: frozenset de nombres de jugadores visitantes
          - start_sec: segundo absoluto de inicio
          - end_sec: segundo absoluto de fin
          - score_local_start / score_local_end
          - score_visitante_start / score_visitante_end
          - periodo: periodo donde empieza el stint
    """
    stints = []
    current_local = set()
    current_visitante = set()
    stint_start = 0.0
    score_start = (0, 0)
    current_period = "1C"

    # Agrupar eventos por (abs_seconds) para procesar sustituciones simultáneas
    grouped = game_pbp.groupby("abs_seconds", sort=True)

    last_score = (0, 0)

    for abs_sec, group in grouped:
        events = group.to_dict("records")

        # Detectar inicio de periodo (Quinteto inicial)
        quintetos = [e for e in events if e["accion"] == "Quinteto inicial"]
        subs_in = [e for e in events if e["accion"] == "Entra a pista"]
        subs_out = [e for e in events if e["accion"] == "Sale de la pista"]

        if quintetos:
            # Cerrar stint anterior si hay lineup activo
            if current_local and current_visitante:
                stints.append({
                    "lineup_local": frozenset(current_local),
                    "lineup_visitante": frozenset(current_visitante),
                    "start_sec": stint_start,
                    "end_sec": abs_sec,
                    "score_local_start": score_start[0],
                    "score_visitante_start": score_start[1],
                    "score_local_end": last_score[0],
                    "score_visitante_end": last_score[1],
                    "periodo": current_period,
                })

            # Resetear lineups con quinteto inicial
            current_local = set()
            current_visitante = set()
            for e in quintetos:
                jugador = e["jugador"]
                if not isinstance(jugador, str) or not jugador.strip():
                    continue
                if e["equipo"] == "LOCAL":
                    current_local.add(jugador)
                else:
                    current_visitante.add(jugador)

            stint_start = abs_sec
            score_start = _extract_score(events[0])
            current_period = events[0]["periodo"]

        elif subs_in or subs_out:
            # Cerrar stint anterior
            if current_local and current_visitante:
                stints.append({
                    "lineup_local": frozenset(current_local),
                    "lineup_visitante": frozenset(current_visitante),
                    "start_sec": stint_start,
                    "end_sec": abs_sec,
                    "score_local_start": score_start[0],
                    "score_visitante_start": score_start[1],
                    "score_local_end": last_score[0],
                    "score_visitante_end": last_score[1],
                    "periodo": current_period,
                })

            # Procesar todas las sustituciones del mismo timestamp
            for e in subs_out:
                jugador = e["jugador"]
                if not isinstance(jugador, str):
                    continue
                if e["equipo"] == "LOCAL":
                    current_local.discard(jugador)
                else:
                    current_visitante.discard(jugador)

            for e in subs_in:
                jugador = e["jugador"]
                if not isinstance(jugador, str):
                    continue
                if e["equipo"] == "LOCAL":
                    current_local.add(jugador)
                else:
                    current_visitante.add(jugador)

            stint_start = abs_sec
            score_start = _extract_score(events[0])
            current_period = events[0]["periodo"]

        # Actualizar último marcador conocido
        for e in events:
            s = _extract_score(e)
            if s[0] + s[1] >= last_score[0] + last_score[1]:
                last_score = s

    # Cerrar último stint
    if current_local and current_visitante:
        last_row = game_pbp.iloc[-1]
        stints.append({
            "lineup_local": frozenset(current_local),
            "lineup_visitante": frozenset(current_visitante),
            "start_sec": stint_start,
            "end_sec": last_row["abs_seconds"],
            "score_local_start": score_start[0],
            "score_visitante_start": score_start[1],
            "score_local_end": int(last_row["marcador_local"]),
            "score_visitante_end": int(last_row["marcador_visitante"]),
            "periodo": current_period,
        })

    return stints


def stints_to_dataframe(stints: list[dict]) -> pd.DataFrame:
    """Convierte lista de stints a DataFrame."""
    if not stints:
        return pd.DataFrame()
    df = pd.DataFrame(stints)
    df["duration_sec"] = df["end_sec"] - df["start_sec"]
    df["plus_minus_local"] = (
        (df["score_local_end"] - df["score_local_start"])
        - (df["score_visitante_end"] - df["score_visitante_start"])
    )
    return df


def player_minutes(stints: list[dict], team_side: str = "LOCAL") -> dict[str, float]:
    """Calcula minutos jugados por cada jugador a partir de stints.

    Args:
        stints: Lista de stints del partido
        team_side: "LOCAL" o "VISITANTE"

    Returns:
        Dict {nombre_jugador: minutos_jugados}
    """
    key = "lineup_local" if team_side == "LOCAL" else "lineup_visitante"
    minutes = defaultdict(float)
    for s in stints:
        duration = (s["end_sec"] - s["start_sec"]) / 60.0
        for player in s[key]:
            minutes[player] += duration
    return dict(minutes)
