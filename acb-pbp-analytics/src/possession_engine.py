"""Motor de detección de posesiones a partir de eventos play-by-play.

Una posesión termina con:
  - Canasta anotada (T2, T3, Mate) → posesión pasa al otro equipo
  - Rebote defensivo del rival → posesión pasa al rival
  - Pérdida → posesión pasa al rival
  - Fin de periodo → posesión termina
  - Último tiro libre anotado/fallado de una secuencia

Caso especial: secuencias de tiros libres
  - Solo el último TL de la secuencia termina la posesión
  - Las faltas que otorgan TL (ej: "Falta Personal 2TL") indican cuántos TL vendrán
"""

import pandas as pd
import re

# Acciones que anotan canasta de campo
FIELD_GOAL_MADE = {"Tiro de 2 anotado", "Triple anotado", "Mate"}

# Acciones de tiro libre
FREE_THROW_MADE = {"Tiro libre anotado"}
FREE_THROW_MISSED = {"Tiro libre fallado"}
FREE_THROW_ALL = FREE_THROW_MADE | FREE_THROW_MISSED

# Acciones de pérdida
TURNOVER_ACTIONS = {a for a in [
    "Pérdida", "Pérdida  - 3\" zona", "Pérdida  - 5\" saque",
    "Pérdida  - Balón perdido", "Pérdida  - Balón retenido",
    "Pérdida  - Campo atrás", "Pérdida  - Dobles",
    "Pérdida  - Final posesión", "Pérdida  - Infracción 8\"",
    "Pérdida  - Mal pase", "Pérdida  - Pasos",
    "Falta en ataque",
]}

# Acciones de rebote
DEFENSIVE_REBOUND = {"Rebote defensivo"}
OFFENSIVE_REBOUND = {"Rebote ofensivo"}

# Fin de periodo
END_PERIOD = {"Final de Periodo", "Final del Partido"}

# Faltas que otorgan tiros libres (extraer número de TL del nombre)
_FOUL_TL_PATTERN = re.compile(r"(\d)TL")


def _count_ft_from_foul(action: str) -> int:
    """Extrae el número de TL otorgados por una falta.
    Ej: 'Falta Personal 2TL' → 2, 'Falta Personal' → 0
    """
    m = _FOUL_TL_PATTERN.search(action)
    return int(m.group(1)) if m else 0


def detect_possessions(game_pbp: pd.DataFrame) -> list[dict]:
    """Detecta posesiones a partir de eventos PBP ordenados cronológicamente.

    Args:
        game_pbp: DataFrame de PBP de un partido con abs_seconds.

    Returns:
        Lista de posesiones, cada una un dict con:
          - team: equipo con la posesión ("LOCAL" o "VISITANTE")
          - start_sec / end_sec: segundos absolutos
          - start_score_local / start_score_visitante
          - end_score_local / end_score_visitante
          - events: lista de acciones en la posesión
          - points_scored: puntos anotados en la posesión
          - ended_by: motivo de fin ("field_goal", "turnover", "defensive_rebound",
                       "free_throw", "end_period")
          - periodo: periodo
    """
    possessions = []
    current_team = None
    poss_events = []
    poss_start_sec = 0.0
    poss_start_score = (0, 0)
    ft_remaining = 0  # TL pendientes en la secuencia actual

    for _, row in game_pbp.iterrows():
        action = row["accion"]
        team = row["equipo"]
        abs_sec = row["abs_seconds"]
        score = (int(row["marcador_local"]), int(row["marcador_visitante"]))

        # Ignorar eventos sin equipo relevante
        if action in ("Quinteto inicial", "Inicio de Periodo", "Inicio del Partido"):
            if current_team is None:
                poss_start_sec = abs_sec
                poss_start_score = score
            continue

        # Salto inicial: determina primer poseedor
        if action == "Salto ganado":
            if current_team is None:
                current_team = team
                poss_start_sec = abs_sec
                poss_start_score = score
            continue
        if action == "Salto perdido":
            continue

        # Sustituciones, tiempos muertos, IR - no cambian posesión
        if action in ("Entra a pista", "Sale de la pista", "Tiempo Muerto",
                       "Tiempo Muerto de TV") or action.startswith("IR -"):
            continue

        # Si no hay equipo poseedor, inferir del primer evento activo
        if current_team is None:
            current_team = team
            poss_start_sec = abs_sec
            poss_start_score = score

        poss_events.append({
            "action": action,
            "team": team,
            "player": row.get("jugador", ""),
            "abs_seconds": abs_sec,
        })

        # Faltas que otorgan TL: marcar cuántos TL esperar
        ft_count = _count_ft_from_foul(action)
        if ft_count > 0:
            ft_remaining = ft_count
            continue

        # Falta recibida, falta personal sin TL, tapón, tapón recibido,
        # asistencia, recuperación - no terminan posesión por sí solas
        if action in ("Falta recibida", "Falta personal", "Tapón", "Tapón recibido",
                       "Asistencia", "Recuperación", "Falta técnica 1TL",
                       "Falta técnica banquillo", "Falta técnica banquillo compensada",
                       "Falta técnica compensada", "Falta técnica entrenador",
                       "Falta técnica entrenador compensada",
                       "Falta antideportiva", "Descalificante de partido",
                       "IR - Challenge ganado", "IR - Challenge perdido"):
            continue

        # Tiros libres: solo el último de la secuencia termina la posesión
        if action in FREE_THROW_ALL:
            if ft_remaining > 0:
                ft_remaining -= 1
            if ft_remaining > 0:
                continue
            # Último TL o TL suelto: termina posesión
            # (excepto si el TL es "1 de 1" después de canasta → ya terminó con la canasta)
            possessions.append({
                "team": current_team,
                "start_sec": poss_start_sec,
                "end_sec": abs_sec,
                "start_score_local": poss_start_score[0],
                "start_score_visitante": poss_start_score[1],
                "end_score_local": score[0],
                "end_score_visitante": score[1],
                "events": poss_events.copy(),
                "ended_by": "free_throw",
                "periodo": row["periodo"],
            })
            current_team = _other_team(current_team)
            poss_events = []
            poss_start_sec = abs_sec
            poss_start_score = score
            continue

        # Canasta de campo anotada
        if action in FIELD_GOAL_MADE:
            possessions.append({
                "team": current_team,
                "start_sec": poss_start_sec,
                "end_sec": abs_sec,
                "start_score_local": poss_start_score[0],
                "start_score_visitante": poss_start_score[1],
                "end_score_local": score[0],
                "end_score_visitante": score[1],
                "events": poss_events.copy(),
                "ended_by": "field_goal",
                "periodo": row["periodo"],
            })
            current_team = _other_team(team)
            poss_events = []
            poss_start_sec = abs_sec
            poss_start_score = score
            ft_remaining = 0
            continue

        # Tiro fallado: no termina posesión (espera rebote)
        if action in ("Tiro de 2 fallado", "Triple fallado", "Mate fallado"):
            continue

        # Rebote defensivo: cambia posesión
        if action in DEFENSIVE_REBOUND:
            possessions.append({
                "team": current_team,
                "start_sec": poss_start_sec,
                "end_sec": abs_sec,
                "start_score_local": poss_start_score[0],
                "start_score_visitante": poss_start_score[1],
                "end_score_local": score[0],
                "end_score_visitante": score[1],
                "events": poss_events.copy(),
                "ended_by": "defensive_rebound",
                "periodo": row["periodo"],
            })
            # El rebote defensivo lo coge el equipo del reboteador → nueva posesión
            current_team = team
            poss_events = []
            poss_start_sec = abs_sec
            poss_start_score = score
            ft_remaining = 0
            continue

        # Rebote ofensivo: mantiene posesión
        if action in OFFENSIVE_REBOUND:
            continue

        # Pérdida
        if action in TURNOVER_ACTIONS:
            possessions.append({
                "team": current_team,
                "start_sec": poss_start_sec,
                "end_sec": abs_sec,
                "start_score_local": poss_start_score[0],
                "start_score_visitante": poss_start_score[1],
                "end_score_local": score[0],
                "end_score_visitante": score[1],
                "events": poss_events.copy(),
                "ended_by": "turnover",
                "periodo": row["periodo"],
            })
            current_team = _other_team(team)
            poss_events = []
            poss_start_sec = abs_sec
            poss_start_score = score
            ft_remaining = 0
            continue

        # Fin de periodo
        if action in END_PERIOD:
            if poss_events:
                possessions.append({
                    "team": current_team,
                    "start_sec": poss_start_sec,
                    "end_sec": abs_sec,
                    "start_score_local": poss_start_score[0],
                    "start_score_visitante": poss_start_score[1],
                    "end_score_local": score[0],
                    "end_score_visitante": score[1],
                    "events": poss_events.copy(),
                    "ended_by": "end_period",
                    "periodo": row["periodo"],
                })
            current_team = None
            poss_events = []
            ft_remaining = 0
            continue

    return possessions


def _other_team(team: str) -> str:
    """Devuelve el equipo contrario."""
    return "VISITANTE" if team == "LOCAL" else "LOCAL"


def possessions_to_dataframe(possessions: list[dict]) -> pd.DataFrame:
    """Convierte lista de posesiones a DataFrame (sin columna events)."""
    if not possessions:
        return pd.DataFrame()
    records = [{k: v for k, v in p.items() if k != "events"} for p in possessions]
    df = pd.DataFrame(records)
    df["duration_sec"] = df["end_sec"] - df["start_sec"]
    df["points_scored"] = df.apply(
        lambda r: (
            (r["end_score_local"] - r["start_score_local"])
            if r["team"] == "LOCAL"
            else (r["end_score_visitante"] - r["start_score_visitante"])
        ),
        axis=1,
    )
    return df


def count_possessions_by_team(possessions: list[dict]) -> dict[str, int]:
    """Cuenta posesiones por equipo."""
    counts = {"LOCAL": 0, "VISITANTE": 0}
    for p in possessions:
        if p["team"] in counts:
            counts[p["team"]] += 1
    return counts
