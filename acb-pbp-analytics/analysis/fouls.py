"""Análisis de distribución temporal de faltas."""

import pandas as pd

FOUL_ACTIONS = {
    "Falta personal", "Falta personal 1TL", "Falta personal 2TL",
    "Falta personal 3TL", "Falta en ataque", "Falta antideportiva",
    "Falta técnica 1TL", "Falta técnica banquillo",
    "Falta técnica banquillo compensada", "Falta técnica compensada",
    "Falta técnica entrenador", "Falta técnica entrenador compensada",
    "Descalificante de partido",
}

FOUL_CATEGORIES = {
    "Personal": {"Falta personal", "Falta personal 1TL", "Falta personal 2TL", "Falta personal 3TL"},
    "En ataque": {"Falta en ataque"},
    "Antideportiva": {"Falta antideportiva"},
    "Técnica": {"Falta técnica 1TL", "Falta técnica banquillo", "Falta técnica banquillo compensada",
                "Falta técnica compensada", "Falta técnica entrenador", "Falta técnica entrenador compensada"},
    "Descalificante": {"Descalificante de partido"},
}


def foul_distribution_by_time(
    pbp_data: pd.DataFrame, interval_minutes: int = 2
) -> pd.DataFrame:
    """Distribución de faltas por intervalo de tiempo.

    Args:
        pbp_data: PBP unificado con abs_seconds
        interval_minutes: Tamaño del intervalo en minutos

    Returns:
        DataFrame con columnas: interval, equipo, foul_category, count
    """
    fouls = pbp_data[pbp_data["accion"].isin(FOUL_ACTIONS)].copy()
    interval_sec = interval_minutes * 60
    fouls["interval"] = (fouls["abs_seconds"] // interval_sec).astype(int) * interval_minutes

    # Categorizar faltas
    def categorize_foul(action):
        for cat, actions in FOUL_CATEGORIES.items():
            if action in actions:
                return cat
        return "Otra"

    fouls["foul_category"] = fouls["accion"].apply(categorize_foul)

    result = (
        fouls.groupby(["interval", "equipo", "foul_category"])
        .size()
        .reset_index(name="count")
    )

    return result


def fouls_by_team_and_quarter(pbp_data: pd.DataFrame) -> pd.DataFrame:
    """Faltas por equipo y cuarto."""
    fouls = pbp_data[pbp_data["accion"].isin(FOUL_ACTIONS)].copy()
    result = (
        fouls.groupby(["equipo_nombre", "periodo"])
        .size()
        .reset_index(name="fouls")
    )
    return result


def fouls_local_vs_visitante(pbp_data: pd.DataFrame) -> pd.DataFrame:
    """Comparación de faltas local vs visitante."""
    fouls = pbp_data[pbp_data["accion"].isin(FOUL_ACTIONS)].copy()
    result = (
        fouls.groupby(["equipo", "id_partido"])
        .size()
        .reset_index(name="fouls")
        .groupby("equipo")["fouls"]
        .agg(["mean", "std", "sum", "count"])
        .reset_index()
    )
    result.columns = ["side", "avg_fouls", "std_fouls", "total_fouls", "n_games"]
    return result
