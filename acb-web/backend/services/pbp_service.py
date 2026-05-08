"""Puente entre la API y acb-pbp-analytics."""

import os
import sys
import types
import importlib.util
import pandas as pd

# Root de acb-pbp-analytics
_PBP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "acb-pbp-analytics"))

_module_cache = {}


def _import_pbp(rel_path: str, package_name: str = None):
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


# Create fake package for relative imports within PBP src/
_pbp_src_pkg = types.ModuleType("_pbp_src")
_pbp_src_pkg.__path__ = [os.path.join(_PBP_ROOT, "src")]
_pbp_src_pkg.__package__ = "_pbp_src"
sys.modules["_pbp_src"] = _pbp_src_pkg

# Import time_utils first (needed by pbp_loader)
_time_utils = _import_pbp("src/time_utils")
sys.modules["_pbp_src.time_utils"] = _time_utils
_time_utils.__package__ = "_pbp_src"

# pbp_loader with relative import support
_pbp_loader_path = os.path.join(_PBP_ROOT, "src", "pbp_loader.py")
_pbp_loader_spec = importlib.util.spec_from_file_location(
    "_pbp_src.pbp_loader", _pbp_loader_path,
)
_pbp_loader = importlib.util.module_from_spec(_pbp_loader_spec)
_pbp_loader.__package__ = "_pbp_src"
sys.modules["_pbp_src.pbp_loader"] = _pbp_loader
_pbp_loader_spec.loader.exec_module(_pbp_loader)
_module_cache["src/pbp_loader"] = _pbp_loader

# Remaining PBP modules
_lineup_tracker = _import_pbp("src/lineup_tracker")
_possession_engine = _import_pbp("src/possession_engine")

# Analysis modules
_momentum = _import_pbp("analysis/momentum")
_clutch = _import_pbp("analysis/clutch")
_lineup_combos = _import_pbp("analysis/lineup_combos")
_shooting_patterns = _import_pbp("analysis/shooting_patterns")
_fouls = _import_pbp("analysis/fouls")
_substitutions = _import_pbp("analysis/substitutions")
_game_state = _import_pbp("analysis/game_state_performance")

# Re-export functions
load_single_game = _pbp_loader.load_single_game
_build_team_lookup = _pbp_loader._build_team_lookup
get_game_pbp = _pbp_loader.get_game_pbp

track_lineups_for_game = _lineup_tracker.track_lineups_for_game
stints_to_dataframe = _lineup_tracker.stints_to_dataframe
player_minutes = _lineup_tracker.player_minutes

detect_possessions = _possession_engine.detect_possessions
possessions_to_dataframe = _possession_engine.possessions_to_dataframe
count_possessions_by_team = _possession_engine.count_possessions_by_team

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

from .constants import PBP_DIR

# In-memory cache for analyzed games
_game_cache: dict[int, dict] = {}


def _resolve_pbp_file(game_id: int) -> str | None:
    filepath = os.path.join(PBP_DIR, f"play_by_play_{game_id}.csv")
    return filepath if os.path.exists(filepath) else None


def load_and_analyze_game(game_id: int) -> dict | None:
    """Load PBP and run all analyses. Cached in memory."""
    if game_id in _game_cache:
        return _game_cache[game_id]

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

    result = {
        "pbp": pbp,
        "stints": stints,
        "stints_df": stints_df,
        "possessions": possessions,
        "possessions_df": possessions_df,
        "runs": runs,
    }
    _game_cache[game_id] = result
    return result
