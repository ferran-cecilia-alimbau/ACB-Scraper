"""Preprocesamiento de datos: standings, agregaciones, normalización."""

import pandas as pd
import numpy as np


def calculate_standings(game_info: pd.DataFrame) -> pd.DataFrame:
    records = []
    teams = set(game_info["local"].unique()) | set(game_info["visitante"].unique())

    for team in teams:
        home_games = game_info[game_info["local"] == team]
        away_games = game_info[game_info["visitante"] == team]

        home_wins = (home_games["resultado_local"] > home_games["resultado_visitante"]).sum()
        home_losses = (home_games["resultado_local"] < home_games["resultado_visitante"]).sum()
        away_wins = (away_games["resultado_visitante"] > away_games["resultado_local"]).sum()
        away_losses = (away_games["resultado_visitante"] < away_games["resultado_local"]).sum()

        pf_home = home_games["resultado_local"].sum()
        pc_home = home_games["resultado_visitante"].sum()
        pf_away = away_games["resultado_visitante"].sum()
        pc_away = away_games["resultado_local"].sum()

        total_w = home_wins + away_wins
        total_l = home_losses + away_losses
        total_pf = pf_home + pf_away
        total_pc = pc_home + pc_away
        total_games = total_w + total_l

        records.append({
            "equipo": team,
            "J": int(total_games),
            "G": int(total_w),
            "P": int(total_l),
            "PF": int(total_pf),
            "PC": int(total_pc),
            "Dif": int(total_pf - total_pc),
            "G_casa": int(home_wins),
            "P_casa": int(home_losses),
            "G_fuera": int(away_wins),
            "P_fuera": int(away_losses),
            "pct": round(total_w / total_games * 100, 1) if total_games > 0 else 0,
        })

    df = pd.DataFrame(records)
    df = df.sort_values(["G", "Dif"], ascending=[False, False]).reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "Pos"
    return df


def standings_evolution(game_info: pd.DataFrame) -> list[dict]:
    jornadas = sorted(game_info["jornada_num"].unique())
    evolution = []

    for j in jornadas:
        games_up_to_j = game_info[game_info["jornada_num"] <= j]
        standings = calculate_standings(games_up_to_j)
        for pos, row in standings.iterrows():
            evolution.append({
                "jornada_num": int(j),
                "equipo": row["equipo"],
                "posicion": int(pos),
                "G": int(row["G"]),
                "P": int(row["P"]),
                "pct": float(row["pct"]),
            })

    return evolution


# Precalculado en startup vía DataStore
_PLAYER_SEASON_CACHE: pd.DataFrame | None = None
_PLAYER_PERCENTILES_CACHE: dict[str, dict[int, float]] | None = None
_PLAYER_RANKS_CACHE: dict[str, dict[int, int]] | None = None

# Métricas para las que precomputamos percentiles y ranks. La clave es el
# nombre del campo en la API; el valor es la columna interna en el DataFrame.
PERCENTILE_STATS: dict[str, str] = {
    "puntos_avg": "puntos_avg",
    "rebotes_avg": "rebotes_totales_avg",
    "asistencias_avg": "asistencias_avg",
    "robos_avg": "robos_avg",
    "tapones_avg": "tapones_favor_avg",
    "valoracion_avg": "valoracion_avg",
    "minutos_avg": "minutos_decimal_avg",
    "ts_pct": "ts_pct",
    "efg_pct": "efg_pct",
    "puntos_per36": "puntos_per36",
    "rebotes_per36": "rebotes_totales_per36",
    "asistencias_per36": "asistencias_per36",
    "valoracion_per36": "valoracion_per36",
    "plus_minus_avg": "plus_minus_avg",
}

# Default mínimos para el cálculo de percentiles (filtros visibles en /jugadores)
DEFAULT_MIN_GAMES = 5
DEFAULT_MIN_MINUTES = 10.0


def aggregate_player_season(player_stats: pd.DataFrame) -> pd.DataFrame:
    sum_cols = [
        "puntos", "t2_intentados", "t2_anotados", "t3_intentados",
        "t3_anotados", "tl_intentados", "tl_anotados",
        "rebotes_defensivos", "rebotes_ofensivos", "rebotes_totales",
        "asistencias", "robos", "perdidas", "tapones_favor",
        "tapones_contra", "mates", "faltas_cometidas", "faltas_recibidas",
        "valoracion",
    ]

    agg_dict = {col: "sum" for col in sum_cols}
    agg_dict["minutos_decimal"] = "sum"
    agg_dict["id_partido"] = "count"
    agg_dict["es_titular"] = "sum"
    if "plus_minus" in player_stats.columns:
        agg_dict["plus_minus"] = "sum"

    grouped = player_stats.groupby(["player_id", "nombre", "equipo"]).agg(agg_dict).reset_index()
    grouped = grouped.rename(columns={"id_partido": "partidos", "es_titular": "titularidades"})

    avg_cols = sum_cols + ["minutos_decimal"]
    if "plus_minus" in grouped.columns:
        avg_cols = avg_cols + ["plus_minus"]
    for col in avg_cols:
        grouped[f"{col}_avg"] = grouped[col] / grouped["partidos"]

    grouped["t2_pct"] = np.where(
        grouped["t2_intentados"] > 0,
        grouped["t2_anotados"] / grouped["t2_intentados"] * 100, 0
    )
    grouped["t3_pct"] = np.where(
        grouped["t3_intentados"] > 0,
        grouped["t3_anotados"] / grouped["t3_intentados"] * 100, 0
    )
    grouped["tl_pct"] = np.where(
        grouped["tl_intentados"] > 0,
        grouped["tl_anotados"] / grouped["tl_intentados"] * 100, 0
    )

    grouped["fga"] = grouped["t2_intentados"] + grouped["t3_intentados"]
    grouped["fgm"] = grouped["t2_anotados"] + grouped["t3_anotados"]
    grouped["efg_pct"] = np.where(
        grouped["fga"] > 0,
        (grouped["fgm"] + 0.5 * grouped["t3_anotados"]) / grouped["fga"] * 100, 0
    )
    grouped["ts_pct"] = np.where(
        (grouped["fga"] + 0.44 * grouped["tl_intentados"]) > 0,
        grouped["puntos"] / (2 * (grouped["fga"] + 0.44 * grouped["tl_intentados"])) * 100, 0
    )

    per36_cols = [
        "puntos", "rebotes_totales", "asistencias", "robos",
        "perdidas", "tapones_favor", "valoracion",
    ]
    for col in per36_cols:
        grouped[f"{col}_per36"] = np.where(
            grouped["minutos_decimal"] > 0,
            grouped[col] * 36 / grouped["minutos_decimal"], 0
        )

    if "plus_minus_avg" not in grouped.columns:
        grouped["plus_minus_avg"] = 0.0

    return grouped


def compute_player_percentiles(
    season: pd.DataFrame,
    min_games: int = DEFAULT_MIN_GAMES,
    min_minutes: float = DEFAULT_MIN_MINUTES,
) -> tuple[dict[str, dict[int, float]], dict[str, dict[int, int]]]:
    """Devuelve (percentiles, ranks) por player_id para cada métrica en PERCENTILE_STATS.

    Solo se calculan sobre jugadores que cumplen los mínimos. Para los jugadores
    fuera del pool, el percentil queda como `None`. Esto evita que un jugador
    con 1 partido y 50 puntos aparezca como "percentil 100" en anotación.
    """
    eligible = season[
        (season["partidos"] >= min_games)
        & (season["minutos_decimal_avg"] >= min_minutes)
    ].copy()

    percentiles: dict[str, dict[int, float]] = {}
    ranks: dict[str, dict[int, int]] = {}

    if eligible.empty:
        return percentiles, ranks

    n = len(eligible)
    for api_key, col in PERCENTILE_STATS.items():
        if col not in eligible.columns:
            continue
        values = eligible[col]
        # Percentil = % de jugadores con valor estrictamente menor (rank "bottom")
        pct = values.rank(method="min", ascending=True).sub(1).div(max(n - 1, 1)).mul(100)
        rank = values.rank(method="min", ascending=False).astype(int)
        percentiles[api_key] = dict(zip(eligible["player_id"].tolist(), pct.round(1).tolist()))
        ranks[api_key] = dict(zip(eligible["player_id"].tolist(), rank.tolist()))

    return percentiles, ranks


def get_player_season() -> pd.DataFrame:
    """Devuelve el DataFrame agregado en cache (lazy-load)."""
    global _PLAYER_SEASON_CACHE
    if _PLAYER_SEASON_CACHE is None:
        from .data_loader import data
        _PLAYER_SEASON_CACHE = aggregate_player_season(data.player_stats)
    return _PLAYER_SEASON_CACHE


def get_player_percentiles() -> tuple[dict[str, dict[int, float]], dict[str, dict[int, int]]]:
    global _PLAYER_PERCENTILES_CACHE, _PLAYER_RANKS_CACHE
    if _PLAYER_PERCENTILES_CACHE is None or _PLAYER_RANKS_CACHE is None:
        season = get_player_season()
        _PLAYER_PERCENTILES_CACHE, _PLAYER_RANKS_CACHE = compute_player_percentiles(season)
    return _PLAYER_PERCENTILES_CACHE, _PLAYER_RANKS_CACHE


def reset_player_caches() -> None:
    """Llamar tras recarga de CSVs."""
    global _PLAYER_SEASON_CACHE, _PLAYER_PERCENTILES_CACHE, _PLAYER_RANKS_CACHE
    _PLAYER_SEASON_CACHE = None
    _PLAYER_PERCENTILES_CACHE = None
    _PLAYER_RANKS_CACHE = None


def player_last_n_games(
    player_stats: pd.DataFrame,
    game_info: pd.DataFrame,
    player_name: str,
    n: int = 5,
) -> dict:
    """Medias de los últimos N partidos del jugador y diff vs media de temporada."""
    player = player_stats[player_stats["nombre"] == player_name].copy()
    if player.empty:
        return {"games": 0, "stats": {}, "diff_vs_season": {}}

    player = player.merge(game_info[["id_partido", "jornada_num"]], on="id_partido")
    player = player.sort_values("jornada_num", ascending=False).head(n)
    if player.empty:
        return {"games": 0, "stats": {}, "diff_vs_season": {}}

    cols = ["puntos", "rebotes_totales", "asistencias", "valoracion", "minutos_decimal"]
    stats_recent = {c: float(player[c].mean()) for c in cols}

    season_full = player_stats[player_stats["nombre"] == player_name]
    stats_season = {c: float(season_full[c].mean()) for c in cols}
    diff = {c: round(stats_recent[c] - stats_season[c], 2) for c in cols}

    return {
        "games": int(len(player)),
        "stats": {k: round(v, 1) for k, v in stats_recent.items()},
        "diff_vs_season": diff,
    }


def player_best_game(
    player_stats: pd.DataFrame,
    game_info: pd.DataFrame,
    player_name: str,
) -> dict:
    """Partido con mayor valoración del jugador en la temporada."""
    player = player_stats[player_stats["nombre"] == player_name].copy()
    if player.empty:
        return {}

    idx = player["valoracion"].idxmax()
    if pd.isna(idx):
        return {}
    row = player.loc[idx]
    game = game_info[game_info["id_partido"] == row["id_partido"]]
    if game.empty:
        return {}
    g = game.iloc[0]
    rival = g["visitante"] if row["equipo"] == g["local"] else g["local"]
    return {
        "id_partido": int(row["id_partido"]),
        "jornada_num": int(g.get("jornada_num", 0)),
        "fecha": str(g.get("fecha", "")),
        "rival": rival,
        "puntos": int(row["puntos"]),
        "rebotes": int(row["rebotes_totales"]),
        "asistencias": int(row["asistencias"]),
        "valoracion": int(row["valoracion"]),
    }


def aggregate_team_season(team_stats: pd.DataFrame) -> pd.DataFrame:
    sum_cols = [
        "puntos", "t2_encestados", "t2_intentados", "t3_encestados",
        "t3_intentados", "tl_encestados", "tl_intentados",
        "rebotes_totales", "rebotes_defensivos", "rebotes_ofensivos",
        "asistencias", "robos", "perdidas", "tapones_favor",
        "tapones_contra", "mates", "faltas_cometidas", "faltas_recibidas",
        "valoracion",
    ]

    agg_dict = {col: "sum" for col in sum_cols}
    agg_dict["id_partido"] = "count"

    grouped = team_stats.groupby("equipo").agg(agg_dict).reset_index()
    grouped = grouped.rename(columns={"id_partido": "partidos"})

    for col in sum_cols:
        grouped[f"{col}_avg"] = grouped[col] / grouped["partidos"]

    grouped["t2_pct"] = np.where(
        grouped["t2_intentados"] > 0,
        grouped["t2_encestados"] / grouped["t2_intentados"] * 100, 0
    )
    grouped["t3_pct"] = np.where(
        grouped["t3_intentados"] > 0,
        grouped["t3_encestados"] / grouped["t3_intentados"] * 100, 0
    )
    grouped["tl_pct"] = np.where(
        grouped["tl_intentados"] > 0,
        grouped["tl_encestados"] / grouped["tl_intentados"] * 100, 0
    )

    return grouped


def compute_league_averages(team_stats: pd.DataFrame, player_stats: pd.DataFrame) -> dict:
    from .metrics import effective_fg_pct, true_shooting_pct

    ts = team_stats

    total_pts = ts["puntos"].sum()
    total_fga = (ts["t2_intentados"] + ts["t3_intentados"]).sum()
    total_fgm = (ts["t2_encestados"] + ts["t3_encestados"]).sum()
    total_3pm = ts["t3_encestados"].sum()
    total_fta = ts["tl_intentados"].sum()

    avgs = {
        "pts": float(ts["puntos"].mean()),
        "reb": float(ts["rebotes_totales"].mean()),
        "ast": float(ts["asistencias"].mean()),
        "rob": float(ts["robos"].mean()),
        "per": float(ts["perdidas"].mean()),
        "val": float(ts["valoracion"].mean()),
        "efg": effective_fg_pct(total_fgm, total_3pm, total_fga),
        "ts": true_shooting_pct(total_pts, total_fga, total_fta),
        "t2_pct": ts["t2_encestados"].sum() / ts["t2_intentados"].sum() * 100 if ts["t2_intentados"].sum() > 0 else 0,
        "t3_pct": ts["t3_encestados"].sum() / ts["t3_intentados"].sum() * 100 if ts["t3_intentados"].sum() > 0 else 0,
        "tl_pct": ts["tl_encestados"].sum() / ts["tl_intentados"].sum() * 100 if ts["tl_intentados"].sum() > 0 else 0,
    }

    ps = player_stats.copy()
    player_games = ps.groupby("player_id").agg(
        n_games=("id_partido", "count"),
        avg_min=("minutos_decimal", "mean"),
    ).reset_index()
    eligible = player_games[(player_games["n_games"] >= 5) & (player_games["avg_min"] >= 5)]["player_id"]
    ps_eligible = ps[ps["player_id"].isin(eligible)]

    if not ps_eligible.empty:
        avgs["player_pts"] = float(ps_eligible.groupby("player_id")["puntos"].mean().mean())
        avgs["player_reb"] = float(ps_eligible.groupby("player_id")["rebotes_totales"].mean().mean())
        avgs["player_ast"] = float(ps_eligible.groupby("player_id")["asistencias"].mean().mean())
        avgs["player_rob"] = float(ps_eligible.groupby("player_id")["robos"].mean().mean())
        avgs["player_per"] = float(ps_eligible.groupby("player_id")["perdidas"].mean().mean())
        avgs["player_val"] = float(ps_eligible.groupby("player_id")["valoracion"].mean().mean())
        avgs["player_min"] = float(ps_eligible.groupby("player_id")["minutos_decimal"].mean().mean())

    return avgs


def compute_home_away_splits(
    player_stats: pd.DataFrame, game_info: pd.DataFrame, player_name: str
) -> list[dict]:
    player = player_stats[player_stats["nombre"] == player_name].copy()
    if player.empty:
        return []

    player = player.merge(
        game_info[["id_partido", "local", "visitante"]], on="id_partido"
    )
    player["sede"] = np.where(player["equipo"] == player["local"], "Casa", "Fuera")

    stats_cols = [
        "puntos", "rebotes_totales", "asistencias", "robos", "perdidas",
        "valoracion", "minutos_decimal",
    ]
    splits = player.groupby("sede")[stats_cols].mean().round(1)
    splits["PJ"] = player.groupby("sede")["id_partido"].count()

    result = []
    for sede, row in splits.iterrows():
        entry = {"sede": sede, "PJ": int(row["PJ"])}
        for col in stats_cols:
            entry[col] = float(row[col])
        result.append(entry)
    return result


def player_game_log(
    player_stats: pd.DataFrame,
    game_info: pd.DataFrame,
    player_name: str,
) -> list[dict]:
    player = player_stats[player_stats["nombre"] == player_name].copy()
    if player.empty:
        return []

    player = player.merge(
        game_info[["id_partido", "jornada_num", "fecha", "local", "visitante"]],
        on="id_partido",
    )
    player["oponente"] = player.apply(
        lambda r: r["visitante"] if r["equipo"] == r["local"] else r["local"], axis=1
    )
    player["es_local"] = player["equipo"] == player["local"]
    player = player.sort_values("jornada_num")

    cols = [
        "id_partido", "jornada_num", "fecha", "oponente", "es_local",
        "minutos", "minutos_decimal", "puntos", "t2_anotados", "t2_intentados",
        "t3_anotados", "t3_intentados", "tl_anotados", "tl_intentados",
        "rebotes_totales", "rebotes_ofensivos", "rebotes_defensivos",
        "asistencias", "robos", "perdidas", "tapones_favor", "tapones_contra",
        "faltas_cometidas", "faltas_recibidas", "plus_minus", "valoracion", "es_titular",
    ]
    available = [c for c in cols if c in player.columns]
    records = player[available].to_dict(orient="records")
    # Clean NaN values for JSON serialization
    clean = []
    for rec in records:
        clean_rec = {}
        for k, v in rec.items():
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                clean_rec[k] = 0
            elif hasattr(v, 'item'):  # numpy scalar
                clean_rec[k] = v.item()
            else:
                clean_rec[k] = v
        clean.append(clean_rec)
    return clean
