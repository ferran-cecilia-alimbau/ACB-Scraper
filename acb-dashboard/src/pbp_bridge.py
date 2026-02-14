"""Puente centralizado entre el dashboard y acb-pbp-analytics.

Elimina sys.path.insert dispersos — todo acceso PBP pasa por aquí.
Usa importlib para evitar colisión de namespace entre 'src/' del dashboard
y 'src/' de acb-pbp-analytics.
"""

import os
import sys
import types
import importlib.util
import streamlit as st
import pandas as pd

# Root de acb-pbp-analytics
_PBP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "acb-pbp-analytics"))

_module_cache = {}


def _import_pbp(rel_path: str, package_name: str = None):
    """Importa un módulo desde acb-pbp-analytics dado su path relativo.

    Args:
        rel_path: e.g. 'src/pbp_loader', 'analysis/momentum'
        package_name: nombre del paquete padre para relative imports
    """
    if rel_path in _module_cache:
        return _module_cache[rel_path]
    full_path = os.path.join(_PBP_ROOT, rel_path.replace("/", os.sep) + ".py")
    module_name = f"_pbp_{rel_path.replace('/', '_')}"
    spec = importlib.util.spec_from_file_location(
        module_name, full_path,
        submodule_search_locations=[] if package_name else None,
    )
    mod = importlib.util.module_from_spec(spec)
    if package_name:
        mod.__package__ = package_name
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    _module_cache[rel_path] = mod
    return mod


# --- Create fake 'pbp_src' package to handle relative imports within PBP src/ ---
_pbp_src_pkg = types.ModuleType("_pbp_src")
_pbp_src_pkg.__path__ = [os.path.join(_PBP_ROOT, "src")]
_pbp_src_pkg.__package__ = "_pbp_src"
sys.modules["_pbp_src"] = _pbp_src_pkg

# First import time_utils (needed by pbp_loader via relative import)
_time_utils = _import_pbp("src/time_utils")
sys.modules["_pbp_src.time_utils"] = _time_utils
_time_utils.__package__ = "_pbp_src"

# Now pbp_loader can do 'from .time_utils import ...'
_pbp_loader_path = os.path.join(_PBP_ROOT, "src", "pbp_loader.py")
_pbp_loader_spec = importlib.util.spec_from_file_location(
    "_pbp_src.pbp_loader", _pbp_loader_path,
)
_pbp_loader = importlib.util.module_from_spec(_pbp_loader_spec)
_pbp_loader.__package__ = "_pbp_src"
sys.modules["_pbp_src.pbp_loader"] = _pbp_loader
_pbp_loader_spec.loader.exec_module(_pbp_loader)
_module_cache["src/pbp_loader"] = _pbp_loader

# Remaining PBP src modules (no relative imports)
_lineup_tracker = _import_pbp("src/lineup_tracker")
_possession_engine = _import_pbp("src/possession_engine")

# Analysis modules (no relative imports)
_momentum = _import_pbp("analysis/momentum")
_clutch = _import_pbp("analysis/clutch")
_lineup_combos = _import_pbp("analysis/lineup_combos")
_shooting_patterns = _import_pbp("analysis/shooting_patterns")
_fouls = _import_pbp("analysis/fouls")
_substitutions = _import_pbp("analysis/substitutions")
_game_state = _import_pbp("analysis/game_state_performance")

# Visualization modules (no relative imports)
_game_flow = _import_pbp("visualizations/game_flow")
_lineup_matrix = _import_pbp("visualizations/lineup_matrix")

# --- Re-export all public functions ---
# Loader
load_single_game = _pbp_loader.load_single_game
_build_team_lookup = _pbp_loader._build_team_lookup
get_game_pbp = _pbp_loader.get_game_pbp

# Lineup tracker
track_lineups_for_game = _lineup_tracker.track_lineups_for_game
stints_to_dataframe = _lineup_tracker.stints_to_dataframe
player_minutes = _lineup_tracker.player_minutes

# Possession engine
detect_possessions = _possession_engine.detect_possessions
possessions_to_dataframe = _possession_engine.possessions_to_dataframe
count_possessions_by_team = _possession_engine.count_possessions_by_team

# Analysis modules
detect_scoring_runs = _momentum.detect_scoring_runs
filter_clutch_events = _clutch.filter_clutch_events
clutch_shooting_stats = _clutch.clutch_shooting_stats
lineup_net_rating = _lineup_combos.lineup_net_rating
shared_minutes_matrix = _lineup_combos.shared_minutes_matrix
shooting_by_game_state = _shooting_patterns.shooting_by_game_state
shooting_by_quarter = _shooting_patterns.shooting_by_quarter
foul_distribution_by_time = _fouls.foul_distribution_by_time
fouls_by_team_and_quarter = _fouls.fouls_by_team_and_quarter
substitution_impact = _substitutions.substitution_impact
team_performance_by_margin = _game_state.team_performance_by_margin

# Visualization modules
create_score_diff_timeline = _game_flow.create_score_diff_timeline
create_score_evolution = _game_flow.create_score_evolution
create_shared_minutes_heatmap = _lineup_matrix.create_shared_minutes_heatmap
_original_lineup_ratings_table = _lineup_matrix.create_lineup_ratings_table

import plotly.graph_objects as _go


def create_lineup_ratings_table(lineup_df, top_n: int = 10):
    """Tabla de quintetos por net rating, compatible con tema oscuro de Streamlit."""
    if lineup_df.empty:
        return _go.Figure()

    best = lineup_df.head(top_n)
    worst = lineup_df.tail(top_n).iloc[::-1]
    combined = pd.concat([best, worst])

    # Colores de fondo con texto explícito para legibilidad en ambos temas
    bg_colors = [
        "rgba(76,175,80,0.25)" if nr > 0 else "rgba(244,67,54,0.25)"
        for nr in combined["net_rating"]
    ]
    text_colors = [
        "#4CAF50" if nr > 0 else "#F44336"
        for nr in combined["net_rating"]
    ]

    fig = _go.Figure(data=[_go.Table(
        header=dict(
            values=["Quinteto", "Min", "ORtg", "DRtg", "NetRtg", "Stints"],
            fill_color="#1976D2",
            font=dict(color="white", size=12),
            align="left",
        ),
        cells=dict(
            values=[
                combined["lineup_str"],
                combined["minutes"].round(1),
                combined["off_rating"].round(1),
                combined["def_rating"].round(1),
                combined["net_rating"].round(1),
                combined["n_stints"],
            ],
            fill_color=[bg_colors] * 6,
            font=dict(size=11, color=[text_colors] * 6),
            align="left",
        ),
    )])

    fig.update_layout(
        title=f"Top/Bottom {top_n} quintetos por Net Rating",
        height=max(400, len(combined) * 30 + 100),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


from .constants import PBP_DIR


def _resolve_pbp_file(game_id: int) -> str | None:
    """Devuelve el path al fichero PBP de game_id, o None si no existe."""
    filepath = os.path.join(PBP_DIR, f"play_by_play_{game_id}.csv")
    return filepath if os.path.exists(filepath) else None


@st.cache_data(ttl=3600)
def load_and_analyze_game(game_id: int) -> dict:
    """Carga PBP de un partido y ejecuta todos los análisis. Cacheado por game_id.

    Returns:
        dict con claves: pbp, stints, stints_df, possessions, possessions_df, runs
        Devuelve None si no hay fichero PBP.
    """
    filepath = _resolve_pbp_file(game_id)
    if filepath is None:
        return None

    team_lookup = _build_team_lookup()
    pbp = load_single_game(filepath, team_lookup)
    if pbp.empty:
        return None

    stints = track_lineups_for_game(pbp)
    stints_df = stints_to_dataframe(stints)
    possessions = detect_possessions(pbp)
    possessions_df = possessions_to_dataframe(possessions)
    runs = detect_scoring_runs(pbp, min_run=6)

    return {
        "pbp": pbp,
        "stints": stints,
        "stints_df": stints_df,
        "possessions": possessions,
        "possessions_df": possessions_df,
        "runs": runs,
    }
