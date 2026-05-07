"""Métricas avanzadas de baloncesto.

Fórmulas:
  - eFG%: (FGM + 0.5 * 3PM) / FGA * 100
  - TS%: PTS / (2 * (FGA + 0.44 * FTA)) * 100
  - Posesiones: FGA + 0.44 * FTA + TOV - OREB
  - Pace: posesiones / (minutos / 5) * 40
  - ORtg: (PTS / posesiones) * 100
  - DRtg: (PTS_oponente / posesiones_oponente) * 100
  - Per-36: stat * 36 / minutos_decimal
"""

import pandas as pd
import numpy as np


def effective_fg_pct(fgm: float, three_pm: float, fga: float) -> float:
    if fga == 0:
        return 0.0
    return (fgm + 0.5 * three_pm) / fga * 100


def true_shooting_pct(pts: float, fga: float, fta: float) -> float:
    denom = 2 * (fga + 0.44 * fta)
    if denom == 0:
        return 0.0
    return pts / denom * 100


def estimate_possessions(fga: float, fta: float, tov: float, oreb: float) -> float:
    return fga + 0.44 * fta + tov - oreb


def pace(possessions: float, minutes: float) -> float:
    if minutes == 0:
        return 0.0
    return possessions / (minutes / 5) * 40


def offensive_rating(pts: float, possessions: float) -> float:
    if possessions == 0:
        return 0.0
    return (pts / possessions) * 100


def usage_rate(fga: float, fta: float, tov: float, player_min: float,
               team_fga: float, team_fta: float, team_tov: float, team_min: float) -> float:
    if player_min == 0 or team_min == 0:
        return 0.0
    numerator = (fga + 0.44 * fta + tov) * (team_min / 5)
    denominator = player_min * (team_fga + 0.44 * team_fta + team_tov)
    if denominator == 0:
        return 0.0
    return 100 * numerator / denominator


def per_36(stat: float, minutes: float) -> float:
    if minutes == 0:
        return 0.0
    return stat * 36 / minutes


def four_factors(team_row: dict) -> dict:
    fga = team_row.get("t2_intentados", 0) + team_row.get("t3_intentados", 0)
    if "t2_encestados" in team_row:
        fgm = team_row.get("t2_encestados", 0) + team_row.get("t3_encestados", 0)
    else:
        fgm = team_row.get("t2_anotados", 0) + team_row.get("t3_anotados", 0)
    three_pm = team_row.get("t3_encestados", team_row.get("t3_anotados", 0))
    fta = team_row.get("tl_intentados", 0)
    tov = team_row.get("perdidas", 0)
    oreb = team_row.get("rebotes_ofensivos", 0)

    poss = estimate_possessions(fga, fta, tov, oreb)

    return {
        "eFG%": effective_fg_pct(fgm, three_pm, fga),
        "TOV%": (tov / poss * 100) if poss > 0 else 0,
        "OREB%": (oreb / (oreb + team_row.get("rebotes_defensivos", 0)) * 100)
                 if (oreb + team_row.get("rebotes_defensivos", 0)) > 0 else 0,
        "FT_rate": (fta / fga * 100) if fga > 0 else 0,
    }


def add_advanced_stats_to_players(player_stats: pd.DataFrame) -> pd.DataFrame:
    df = player_stats.copy()
    df["fga"] = df["t2_intentados"] + df["t3_intentados"]
    df["fgm"] = df["t2_anotados"] + df["t3_anotados"]

    df["efg_pct"] = df.apply(
        lambda r: effective_fg_pct(r["fgm"], r["t3_anotados"], r["fga"]), axis=1
    )
    df["ts_pct"] = df.apply(
        lambda r: true_shooting_pct(r["puntos"], r["fga"], r["tl_intentados"]), axis=1
    )

    per36_cols = [
        "puntos", "rebotes_totales", "asistencias", "robos",
        "perdidas", "tapones_favor", "valoracion",
    ]
    for col in per36_cols:
        df[f"{col}_per36"] = df.apply(
            lambda r, c=col: per_36(r[c], r["minutos_decimal"]), axis=1
        )

    return df


def add_advanced_stats_to_teams(team_stats: pd.DataFrame, game_info: pd.DataFrame) -> pd.DataFrame:
    df = team_stats.copy()
    df["fga"] = df["t2_intentados"] + df["t3_intentados"]
    df["fgm"] = df["t2_encestados"] + df["t3_encestados"]

    df["efg_pct"] = df.apply(
        lambda r: effective_fg_pct(r["fgm"], r["t3_encestados"], r["fga"]), axis=1
    )
    df["ts_pct"] = df.apply(
        lambda r: true_shooting_pct(r["puntos"], r["fga"], r["tl_intentados"]), axis=1
    )

    df["est_possessions"] = df.apply(
        lambda r: estimate_possessions(r["fga"], r["tl_intentados"], r["perdidas"], r["rebotes_ofensivos"]),
        axis=1,
    )
    df["ortg"] = df.apply(
        lambda r: offensive_rating(r["puntos"], r["est_possessions"]), axis=1
    )

    games = game_info[["id_partido", "local", "visitante"]].copy()
    merged = df.merge(games, on="id_partido")
    merged["oponente"] = merged.apply(
        lambda r: r["visitante"] if r["equipo"] == r["local"] else r["local"], axis=1
    )

    opp = df[["id_partido", "equipo", "puntos", "est_possessions"]].rename(
        columns={"equipo": "oponente", "puntos": "pts_oponente", "est_possessions": "poss_oponente"}
    )
    merged = merged.merge(opp, on=["id_partido", "oponente"], how="left")
    merged["drtg"] = merged.apply(
        lambda r: offensive_rating(r["pts_oponente"], r["poss_oponente"])
        if pd.notna(r.get("poss_oponente")) else 0,
        axis=1,
    )
    merged["net_rtg"] = merged["ortg"] - merged["drtg"]
    merged["pace"] = merged.apply(
        lambda r: pace(r["est_possessions"], 40), axis=1
    )

    return merged
