"""Carga de datos CSV — sin dependencias de Streamlit."""

import pandas as pd

from .constants import (
    PLAYER_STATS_PATH, GAME_INFO_PATH, TEAM_STATS_PATH,
    PLAYER_PROFILES_PATH, TEAM_NAME_MAP,
)


def _normalize_team(name: str) -> str:
    return TEAM_NAME_MAP.get(name, name)


def parse_minutes(minutes_str) -> float:
    try:
        if pd.isna(minutes_str) or minutes_str == "":
            return 0.0
        if isinstance(minutes_str, (int, float)):
            return float(minutes_str)
        parts = str(minutes_str).split(":")
        if len(parts) == 2:
            return int(parts[0]) + int(parts[1]) / 60
        return float(minutes_str)
    except (ValueError, TypeError):
        return 0.0


def load_player_stats() -> pd.DataFrame:
    df = pd.read_csv(PLAYER_STATS_PATH)
    df["minutos_decimal"] = df["minutos"].apply(parse_minutes)
    df["equipo"] = df["equipo"].apply(_normalize_team)

    int_cols = [
        "puntos", "t2_intentados", "t2_anotados", "t3_intentados",
        "t3_anotados", "tl_intentados", "tl_anotados",
        "rebotes_defensivos", "rebotes_ofensivos", "rebotes_totales",
        "asistencias", "robos", "perdidas", "tapones_favor",
        "tapones_contra", "mates", "faltas_cometidas", "faltas_recibidas",
        "valoracion",
    ]
    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df["plus_minus"] = pd.to_numeric(df["plus_minus"], errors="coerce").fillna(0).astype(int)
    df["es_titular"] = df["es_titular"].astype(bool)

    return df


def load_game_info() -> pd.DataFrame:
    df = pd.read_csv(GAME_INFO_PATH)
    df["resultado_local"] = pd.to_numeric(df["resultado_local"], errors="coerce").fillna(0).astype(int)
    df["resultado_visitante"] = pd.to_numeric(df["resultado_visitante"], errors="coerce").fillna(0).astype(int)
    # `jornada` viene como entero (formato nuevo) o como "Jornada N" (formato
    # antiguo). Normalizamos a int siempre.
    jornada_str = df["jornada"].astype(str)
    df["jornada_num"] = (
        jornada_str.str.extract(r"(\d+)")[0]
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype(int)
    )
    df["local"] = df["local"].apply(_normalize_team)
    df["visitante"] = df["visitante"].apply(_normalize_team)
    df["publico"] = pd.to_numeric(df["publico"], errors="coerce").fillna(0).astype(int)
    return df


def load_team_stats() -> pd.DataFrame:
    df = pd.read_csv(TEAM_STATS_PATH)
    df["equipo"] = df["equipo"].apply(_normalize_team)

    int_cols = [
        "puntos", "t2_encestados", "t2_intentados", "t3_encestados",
        "t3_intentados", "tl_encestados", "tl_intentados",
        "rebotes_totales", "rebotes_defensivos", "rebotes_ofensivos",
        "asistencias", "robos", "perdidas", "tapones_favor",
        "tapones_contra", "mates", "faltas_cometidas", "faltas_recibidas",
        "valoracion",
    ]
    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df["plus_minus"] = pd.to_numeric(df["plus_minus"], errors="coerce").fillna(0).astype(int)
    return df


def load_player_profiles() -> pd.DataFrame:
    df = pd.read_csv(PLAYER_PROFILES_PATH)
    df["equipo"] = df["equipo"].apply(_normalize_team)
    df["altura"] = pd.to_numeric(df["altura"], errors="coerce").fillna(0).astype(int)
    df["edad"] = pd.to_numeric(df["edad"], errors="coerce").fillna(0).astype(int)
    return df


# Singleton data store
class DataStore:
    """Holds all DataFrames loaded at startup."""
    player_stats: pd.DataFrame = None
    game_info: pd.DataFrame = None
    team_stats: pd.DataFrame = None
    player_profiles: pd.DataFrame = None

    @classmethod
    def load_all(cls):
        cls.player_stats = load_player_stats()
        cls.game_info = load_game_info()
        cls.team_stats = load_team_stats()
        cls.player_profiles = load_player_profiles()


data = DataStore()
