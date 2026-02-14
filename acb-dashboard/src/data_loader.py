"""Carga de datos CSV con caché de Streamlit."""

import os
import pandas as pd
import streamlit as st

from .constants import (
    PLAYER_STATS_PATH, GAME_INFO_PATH, TEAM_STATS_PATH,
    PLAYER_PROFILES_PATH, PBP_DIR, TEAM_NAME_MAP,
)


def _normalize_team(name: str) -> str:
    """Normaliza nombre de equipo al formato corto."""
    return TEAM_NAME_MAP.get(name, name)


def parse_minutes(minutes_str) -> float:
    """Convierte 'MM:SS' a minutos decimales."""
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


@st.cache_data(ttl=3600)
def load_player_stats() -> pd.DataFrame:
    """Carga estadísticas individuales de todos los partidos."""
    df = pd.read_csv(PLAYER_STATS_PATH)
    df["minutos_decimal"] = df["minutos"].apply(parse_minutes)
    df["equipo"] = df["equipo"].apply(_normalize_team)

    # Convertir tipos
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


@st.cache_data(ttl=3600)
def load_game_info() -> pd.DataFrame:
    """Carga información de partidos."""
    df = pd.read_csv(GAME_INFO_PATH)
    df["resultado_local"] = pd.to_numeric(df["resultado_local"], errors="coerce").fillna(0).astype(int)
    df["resultado_visitante"] = pd.to_numeric(df["resultado_visitante"], errors="coerce").fillna(0).astype(int)
    df["jornada_num"] = df["jornada"].str.extract(r"(\d+)").astype(int)
    df["local"] = df["local"].apply(_normalize_team)
    df["visitante"] = df["visitante"].apply(_normalize_team)
    df["publico"] = pd.to_numeric(df["publico"], errors="coerce").fillna(0).astype(int)
    return df


@st.cache_data(ttl=3600)
def load_team_stats() -> pd.DataFrame:
    """Carga estadísticas de equipos por partido."""
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


@st.cache_data(ttl=3600)
def load_player_profiles() -> pd.DataFrame:
    """Carga perfiles de jugadores."""
    df = pd.read_csv(PLAYER_PROFILES_PATH)
    df["equipo"] = df["equipo"].apply(_normalize_team)
    df["altura"] = pd.to_numeric(df["altura"], errors="coerce").fillna(0).astype(int)
    df["edad"] = pd.to_numeric(df["edad"], errors="coerce").fillna(0).astype(int)
    return df


@st.cache_data(ttl=3600)
def load_pbp_game(game_id: int) -> pd.DataFrame:
    """Carga PBP de un partido específico. Usa pbp_bridge internamente."""
    from .pbp_bridge import load_and_analyze_game
    result = load_and_analyze_game(game_id)
    if result is None:
        return pd.DataFrame()
    return result["pbp"]
