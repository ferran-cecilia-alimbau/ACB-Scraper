"""Preprocesamiento de datos: standings, agregaciones, normalización."""

import pandas as pd
import numpy as np
import streamlit as st

from .constants import TEAM_NAME_MAP


def calculate_standings(game_info: pd.DataFrame) -> pd.DataFrame:
    """Calcula clasificación a partir de resultados de partidos.

    Returns:
        DataFrame con: equipo, G, P, PF, PC, Dif, G_casa, P_casa, G_fuera, P_fuera, pct
    """
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
            "J": total_games,
            "G": total_w,
            "P": total_l,
            "PF": total_pf,
            "PC": total_pc,
            "Dif": total_pf - total_pc,
            "G_casa": home_wins,
            "P_casa": home_losses,
            "G_fuera": away_wins,
            "P_fuera": away_losses,
            "pct": total_w / total_games * 100 if total_games > 0 else 0,
        })

    df = pd.DataFrame(records)
    df = df.sort_values(["G", "Dif"], ascending=[False, False]).reset_index(drop=True)
    df.index = df.index + 1  # Posición empezando en 1
    df.index.name = "Pos"
    return df


def standings_evolution(game_info: pd.DataFrame) -> pd.DataFrame:
    """Calcula la posición de cada equipo tras cada jornada.

    Returns:
        DataFrame con: jornada_num, equipo, posicion, G, P
    """
    jornadas = sorted(game_info["jornada_num"].unique())
    evolution = []

    for j in jornadas:
        games_up_to_j = game_info[game_info["jornada_num"] <= j]
        standings = calculate_standings(games_up_to_j)
        for pos, row in standings.iterrows():
            evolution.append({
                "jornada_num": j,
                "equipo": row["equipo"],
                "posicion": pos,
                "G": row["G"],
                "P": row["P"],
                "pct": row["pct"],
            })

    return pd.DataFrame(evolution)


@st.cache_data
def aggregate_player_season(player_stats: pd.DataFrame) -> pd.DataFrame:
    """Agrega estadísticas de jugador a nivel de temporada.

    Returns:
        DataFrame con totales, promedios y per-36 por jugador.
    """
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

    grouped = player_stats.groupby(["player_id", "nombre", "equipo"]).agg(agg_dict).reset_index()
    grouped = grouped.rename(columns={"id_partido": "partidos", "es_titular": "titularidades"})

    # Promedios por partido
    avg_cols = sum_cols + ["minutos_decimal"]
    for col in avg_cols:
        grouped[f"{col}_avg"] = grouped[col] / grouped["partidos"]

    # Porcentajes de tiro (sobre totales)
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

    # eFG% y TS%
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

    # Per-36
    per36_cols = [
        "puntos", "rebotes_totales", "asistencias", "robos",
        "perdidas", "tapones_favor", "valoracion",
    ]
    for col in per36_cols:
        grouped[f"{col}_per36"] = np.where(
            grouped["minutos_decimal"] > 0,
            grouped[col] * 36 / grouped["minutos_decimal"], 0
        )

    return grouped


@st.cache_data
def aggregate_team_season(team_stats: pd.DataFrame) -> pd.DataFrame:
    """Agrega estadísticas de equipo a nivel de temporada."""
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

    # Promedios por partido
    for col in sum_cols:
        grouped[f"{col}_avg"] = grouped[col] / grouped["partidos"]

    # Porcentajes
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


@st.cache_data
def compute_league_averages(team_stats: pd.DataFrame, player_stats: pd.DataFrame) -> dict:
    """Calcula medias de liga para stats clave.

    Returns:
        dict con medias por partido: pts, reb, ast, rob, per, val, efg, ts,
        t2_pct, t3_pct, tl_pct, fga, ortg, drtg, pace, etc.
    """
    from .metrics import effective_fg_pct, true_shooting_pct, estimate_possessions

    n_games = team_stats["id_partido"].nunique()
    ts = team_stats

    total_pts = ts["puntos"].sum()
    total_fga = (ts["t2_intentados"] + ts["t3_intentados"]).sum()
    total_fgm = (ts["t2_encestados"] + ts["t3_encestados"]).sum()
    total_3pm = ts["t3_encestados"].sum()
    total_fta = ts["tl_intentados"].sum()

    # Per-team-game averages
    n_team_games = len(ts)

    avgs = {
        "pts": ts["puntos"].mean(),
        "reb": ts["rebotes_totales"].mean(),
        "ast": ts["asistencias"].mean(),
        "rob": ts["robos"].mean(),
        "per": ts["perdidas"].mean(),
        "val": ts["valoracion"].mean(),
        "efg": effective_fg_pct(total_fgm, total_3pm, total_fga),
        "ts": true_shooting_pct(total_pts, total_fga, total_fta),
        "t2_pct": ts["t2_encestados"].sum() / ts["t2_intentados"].sum() * 100 if ts["t2_intentados"].sum() > 0 else 0,
        "t3_pct": ts["t3_encestados"].sum() / ts["t3_intentados"].sum() * 100 if ts["t3_intentados"].sum() > 0 else 0,
        "tl_pct": ts["tl_encestados"].sum() / ts["tl_intentados"].sum() * 100 if ts["tl_intentados"].sum() > 0 else 0,
    }

    # Player averages (for players with >= 5 games and >= 5 min/game)
    ps = player_stats.copy()
    player_games = ps.groupby("player_id").agg(
        n_games=("id_partido", "count"),
        avg_min=("minutos_decimal", "mean"),
    ).reset_index()
    eligible = player_games[(player_games["n_games"] >= 5) & (player_games["avg_min"] >= 5)]["player_id"]
    ps_eligible = ps[ps["player_id"].isin(eligible)]

    if not ps_eligible.empty:
        avgs["player_pts"] = ps_eligible.groupby("player_id")["puntos"].mean().mean()
        avgs["player_reb"] = ps_eligible.groupby("player_id")["rebotes_totales"].mean().mean()
        avgs["player_ast"] = ps_eligible.groupby("player_id")["asistencias"].mean().mean()
        avgs["player_rob"] = ps_eligible.groupby("player_id")["robos"].mean().mean()
        avgs["player_per"] = ps_eligible.groupby("player_id")["perdidas"].mean().mean()
        avgs["player_val"] = ps_eligible.groupby("player_id")["valoracion"].mean().mean()
        avgs["player_min"] = ps_eligible.groupby("player_id")["minutos_decimal"].mean().mean()

    return avgs


def compute_home_away_splits(
    player_stats: pd.DataFrame, game_info: pd.DataFrame, player_name: str
) -> pd.DataFrame:
    """Calcula splits casa/fuera para un jugador.

    Returns:
        DataFrame con filas 'Casa' y 'Fuera', columnas de stats promedio.
    """
    player = player_stats[player_stats["nombre"] == player_name].copy()
    if player.empty:
        return pd.DataFrame()

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
    return splits


def player_game_log(
    player_stats: pd.DataFrame,
    game_info: pd.DataFrame,
    player_name: str,
) -> pd.DataFrame:
    """Obtiene el historial partido a partido de un jugador."""
    player = player_stats[player_stats["nombre"] == player_name].copy()
    if player.empty:
        return player

    player = player.merge(
        game_info[["id_partido", "jornada_num", "fecha", "local", "visitante"]],
        on="id_partido",
    )
    player["oponente"] = player.apply(
        lambda r: r["visitante"] if r["equipo"] == r["local"] else r["local"], axis=1
    )
    player["es_local"] = player["equipo"] == player["local"]
    player = player.sort_values("jornada_num")
    return player
