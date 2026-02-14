"""Cargador unificado de datos play-by-play.

Funciones principales:
  - load_single_game: Carga un fichero PBP individual
  - load_all_games: Carga y unifica los 152 ficheros PBP
  - resolve_teams: Sustituye LOCAL/VISITANTE por nombre de equipo real

Los ficheros PBP vienen en orden cronológico inverso → se invierten.
"""

import os
import glob
import pandas as pd

from .time_utils import to_absolute_seconds

# Ruta base relativa al proyecto ACB-Scraper
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PBP_DIR = os.path.join(_PROJECT_ROOT, "data", "play_by_play")
GAME_INFO_PATH = os.path.join(_PROJECT_ROOT, "data", "output", "estadisticas_partido.csv")

# Normalización de nombres de equipo (sponsor → nombre base)
TEAM_NAME_MAP = {
    "Kosner Baskonia": "Baskonia",
    "Recoletas Salud San Pablo Burgos": "Recoletas Salud",
    "Casademont Zaragoza": "Casademont Zgz",
    "Dreamland Gran Canaria": "Dreamland GC",
    "La Laguna Tenerife": "La Laguna TFE",
    "MoraBanc Andorra": "MoraBanc And",
    "Joventut Badalona": "Joventut",
}


def normalize_team_name(name: str) -> str:
    """Normaliza nombre de equipo al formato corto usado en estadisticas_partido."""
    return TEAM_NAME_MAP.get(name, name)


def _build_team_lookup(game_info_path: str = GAME_INFO_PATH) -> dict:
    """Crea diccionario {id_partido: {'LOCAL': equipo_local, 'VISITANTE': equipo_visitante}}."""
    df = pd.read_csv(game_info_path)
    lookup = {}
    for _, row in df.iterrows():
        lookup[row["id_partido"]] = {
            "LOCAL": row["local"],
            "VISITANTE": row["visitante"],
        }
    return lookup


def load_single_game(filepath: str, team_lookup: dict = None) -> pd.DataFrame:
    """Carga un fichero PBP individual, invierte el orden y resuelve equipos.

    Args:
        filepath: Ruta al fichero CSV de play-by-play
        team_lookup: Diccionario de resolución de equipos (opcional)

    Returns:
        DataFrame con columnas originales + 'equipo_nombre' + 'abs_seconds'
    """
    df = pd.read_csv(filepath)

    # Invertir orden (los datos vienen en cronología inversa)
    df = df.iloc[::-1].reset_index(drop=True)

    # Resolver LOCAL/VISITANTE → nombre de equipo
    if team_lookup is not None:
        game_id = df["id_partido"].iloc[0]
        teams = team_lookup.get(game_id, {})
        df["equipo_nombre"] = df["equipo"].map(teams).fillna(df["equipo"])
    else:
        df["equipo_nombre"] = df["equipo"]

    # Calcular segundos absolutos
    df["abs_seconds"] = df.apply(
        lambda r: to_absolute_seconds(r["periodo"], r["tiempo"]), axis=1
    )

    return df


def load_all_games(
    pbp_dir: str = PBP_DIR,
    game_info_path: str = GAME_INFO_PATH,
) -> pd.DataFrame:
    """Carga y unifica todos los ficheros PBP.

    Returns:
        DataFrame unificado con todos los eventos, ordenado cronológicamente por partido.
    """
    team_lookup = _build_team_lookup(game_info_path)
    files = sorted(glob.glob(os.path.join(pbp_dir, "play_by_play_*.csv")))

    frames = []
    for f in files:
        try:
            df = load_single_game(f, team_lookup)
            frames.append(df)
        except Exception as e:
            print(f"Error cargando {f}: {e}")

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)

    # Normalizar nombres de equipo
    result["equipo_nombre"] = result["equipo_nombre"].map(
        lambda x: normalize_team_name(x) if isinstance(x, str) else x
    )

    return result


def get_game_pbp(game_id: int, pbp_data: pd.DataFrame = None) -> pd.DataFrame:
    """Obtiene el PBP de un partido específico.

    Args:
        game_id: ID del partido
        pbp_data: DataFrame unificado (si None, carga solo ese partido)
    """
    if pbp_data is not None:
        return pbp_data[pbp_data["id_partido"] == game_id].copy()

    filepath = os.path.join(PBP_DIR, f"play_by_play_{game_id}.csv")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No existe fichero PBP para partido {game_id}")

    team_lookup = _build_team_lookup()
    return load_single_game(filepath, team_lookup)
