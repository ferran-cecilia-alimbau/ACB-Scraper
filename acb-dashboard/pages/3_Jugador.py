"""Página de ficha de jugador: radar + evolución + splits + rankings."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from src.data_loader import load_player_stats, load_game_info, load_player_profiles, load_team_stats
from src.preprocessing import (
    aggregate_player_season, player_game_log, compute_league_averages,
    compute_home_away_splits,
)
from src.metrics import usage_rate
from src.charts import (
    player_radar_chart, player_evolution_chart, get_team_color,
    apply_standard_layout, styled_metric_row, inject_custom_css, hex_to_rgba, styled_header,
)
from src.constants import POSITION_MAP, RADAR_CATEGORIES

st.set_page_config(page_title="Jugador - ACB", layout="wide")
inject_custom_css()
styled_header("Ficha de Jugador", "Radar, evolución, splits y rankings de liga")

player_stats = load_player_stats()
game_info = load_game_info()
profiles = load_player_profiles()
team_stats = load_team_stats()

# Agregar estadísticas de temporada
season_stats = aggregate_player_season(player_stats)

# Merge con perfiles para posición
season_with_pos = season_stats.merge(
    profiles[["player_id", "posicion", "altura", "edad", "nacionalidad"]],
    on="player_id",
    how="left",
)

# Selector de jugador
player_list = sorted(season_with_pos["nombre"].unique())
selected_player = st.sidebar.selectbox("Selecciona jugador", player_list)

player_row = season_with_pos[season_with_pos["nombre"] == selected_player]
if player_row.empty:
    st.warning("Jugador no encontrado")
    st.stop()

player_row = player_row.iloc[0]
position = player_row.get("posicion", "")
position_name = POSITION_MAP.get(position, position)
team_color = get_team_color(player_row["equipo"])
league_avgs = compute_league_averages(team_stats, player_stats)

# --- Header ---
st.markdown(f"### {selected_player}")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Equipo", player_row["equipo"])
col2.metric("Posición", position_name)
col3.metric("Partidos", int(player_row["partidos"]))
col4.metric("Minutos/partido", f"{player_row['minutos_decimal_avg']:.1f}")
col5.metric("Titularidades", int(player_row["titularidades"]))

st.markdown("---")

# --- Compute league rankings for context ---
eligible_all = season_with_pos[
    (season_with_pos["partidos"] >= 5) & (season_with_pos["minutos_decimal_avg"] > 5)
].copy()

def _league_rank(col, ascending=False):
    """Returns rank (1-based) of selected player in league."""
    if col not in eligible_all.columns:
        return None
    ranked = eligible_all[col].rank(ascending=ascending, method="min")
    player_idx = eligible_all[eligible_all["nombre"] == selected_player].index
    if len(player_idx) == 0:
        return None
    return int(ranked.loc[player_idx[0]])

n_eligible = len(eligible_all)

# --- Stats principales con ranking de liga ---
st.subheader("Promedios por partido")

stats_info = [
    ("Puntos", "puntos_avg", "player_pts"),
    ("Rebotes", "rebotes_totales_avg", "player_reb"),
    ("Asistencias", "asistencias_avg", "player_ast"),
    ("Robos", "robos_avg", "player_rob"),
    ("Pérdidas", "perdidas_avg", "player_per"),
    ("Valoración", "valoracion_avg", "player_val"),
]

cols = st.columns(6)
for i, (label, col_name, avg_key) in enumerate(stats_info):
    val = player_row[col_name]
    rank = _league_rank(col_name, ascending=(label == "Pérdidas"))
    rank_str = f" ({rank}º)" if rank else ""
    delta = val - league_avgs.get(avg_key, 0) if avg_key in league_avgs else None
    cols[i].metric(
        f"{label}{rank_str}",
        f"{val:.1f}",
        f"{delta:+.1f} vs liga" if delta is not None else None,
    )

# Shooting percentages
cols2 = st.columns(5)
cols2[0].metric("T2%", f"{player_row['t2_pct']:.1f}%")
cols2[1].metric("T3%", f"{player_row['t3_pct']:.1f}%")
cols2[2].metric("TL%", f"{player_row['tl_pct']:.1f}%")
cols2[3].metric("TS%", f"{player_row['ts_pct']:.1f}%")
cols2[4].metric("eFG%", f"{player_row['efg_pct']:.1f}%")

# USG% and AST/TO
st.markdown("")
game_log = player_game_log(player_stats, game_info, selected_player)

if not game_log.empty:
    # Compute USG% per game and average
    usg_values = []
    for _, g in game_log.iterrows():
        team_game = team_stats[
            (team_stats["id_partido"] == g["id_partido"]) & (team_stats["equipo"] == g["equipo"])
        ]
        if team_game.empty or g["minutos_decimal"] == 0:
            continue
        tg = team_game.iloc[0]
        # Sum team minutes from all players in this game
        team_game_minutes = player_stats[
            (player_stats["id_partido"] == g["id_partido"]) & (player_stats["equipo"] == g["equipo"])
        ]["minutos_decimal"].sum()
        u = usage_rate(
            g["t2_intentados"] + g["t3_intentados"], g["tl_intentados"], g["perdidas"],
            g["minutos_decimal"],
            tg["t2_intentados"] + tg["t3_intentados"], tg["tl_intentados"], tg["perdidas"],
            team_game_minutes if team_game_minutes > 0 else 200,
        )
        usg_values.append(u)

    avg_usg = np.mean(usg_values) if usg_values else 0
    ast_to = (player_row["asistencias"] / player_row["perdidas"]
              if player_row["perdidas"] > 0 else 0)

    cols3 = st.columns(4)
    cols3[0].metric("USG%", f"{avg_usg:.1f}%")
    cols3[1].metric("AST/TO", f"{ast_to:.2f}")
    cols3[2].metric("FGA/partido",
                    f"{(player_row['t2_intentados'] + player_row['t3_intentados']) / player_row['partidos']:.1f}")
    cols3[3].metric("FTA/partido",
                    f"{player_row['tl_intentados'] / player_row['partidos']:.1f}")

st.markdown("---")

# --- Splits Casa/Fuera ---
st.subheader("Splits Casa / Fuera")
splits = compute_home_away_splits(player_stats, game_info, selected_player)
if not splits.empty:
    display_splits = splits.rename(columns={
        "puntos": "Pts", "rebotes_totales": "Reb", "asistencias": "Ast",
        "robos": "Rob", "perdidas": "Pér", "valoracion": "Val",
        "minutos_decimal": "Min",
    })
    st.dataframe(display_splits, use_container_width=True)

# Splits Titular/Suplente
st.subheader("Splits Titular / Suplente")
if not game_log.empty:
    stats_split_cols = ["puntos", "rebotes_totales", "asistencias", "robos", "perdidas",
                        "valoracion", "minutos_decimal"]
    starter_splits = game_log.groupby("es_titular")[stats_split_cols].mean().round(1)
    starter_splits.index = starter_splits.index.map({True: "Titular", False: "Suplente"})
    starter_splits["PJ"] = game_log.groupby("es_titular")["id_partido"].count()
    display_starter = starter_splits.rename(columns={
        "puntos": "Pts", "rebotes_totales": "Reb", "asistencias": "Ast",
        "robos": "Rob", "perdidas": "Pér", "valoracion": "Val",
        "minutos_decimal": "Min",
    })
    st.dataframe(display_starter, use_container_width=True)

st.markdown("---")

# --- Season Highs ---
st.subheader("Mejores partidos de la temporada")
if not game_log.empty:
    highs = {
        "Puntos": game_log.loc[game_log["puntos"].idxmax()],
        "Rebotes": game_log.loc[game_log["rebotes_totales"].idxmax()],
        "Asistencias": game_log.loc[game_log["asistencias"].idxmax()],
        "Valoración": game_log.loc[game_log["valoracion"].idxmax()],
    }
    cols_h = st.columns(4)
    for i, (stat_name, row) in enumerate(highs.items()):
        stat_col = {"Puntos": "puntos", "Rebotes": "rebotes_totales",
                    "Asistencias": "asistencias", "Valoración": "valoracion"}[stat_name]
        cols_h[i].metric(
            f"Máx. {stat_name}",
            int(row[stat_col]),
            f"J{row['jornada_num']} vs {row['oponente']}",
        )

st.markdown("---")

# --- Radar chart ---
st.subheader("Perfil del jugador (percentil por posición, per-36 min)")

eligible = season_with_pos[
    (season_with_pos["partidos"] >= 5) & (season_with_pos["minutos_decimal_avg"] > 5)
]

if position and not eligible[eligible["posicion"] == position].empty:
    pos_group = eligible[eligible["posicion"] == position]
else:
    pos_group = eligible

radar_cols = {
    "Puntos": "puntos_per36",
    "Eficiencia": "efg_pct",
    "Rebotes": "rebotes_totales_per36",
    "Asistencias": "asistencias_per36",
    "Robos": "robos_per36",
    "Tapones": "tapones_favor_per36",
    "Pérdidas (inv)": "perdidas_per36",
    "Valoración": "valoracion_per36",
}

player_radar = {}
for cat, col in radar_cols.items():
    if col not in pos_group.columns:
        player_radar[cat] = 50
        continue
    values = pos_group[col].dropna()
    if values.empty:
        player_radar[cat] = 50
        continue
    player_val = player_row.get(col, 0)
    if cat == "Pérdidas (inv)":
        pct = (values >= player_val).mean() * 100
    else:
        pct = (values <= player_val).mean() * 100
    player_radar[cat] = min(pct, 100)

col_radar, col_info = st.columns([2, 1])
with col_radar:
    fig_radar = player_radar_chart(player_radar, selected_player)
    # Use team color
    fig_radar.data[0].fillcolor = f"rgba{hex_to_rgba(team_color, 0.3)}"
    fig_radar.data[0].line.color = team_color
    st.plotly_chart(apply_standard_layout(fig_radar), use_container_width=True)

with col_info:
    st.markdown("**Per-36 minutos**")
    for cat, col in radar_cols.items():
        if cat != "Pérdidas (inv)" and cat != "Eficiencia":
            val = player_row.get(col, 0)
            st.text(f"{cat}: {val:.1f}")
        elif cat == "Eficiencia":
            st.text(f"eFG%: {player_row.get('efg_pct', 0):.1f}%")
        else:
            st.text(f"Pérdidas per36: {player_row.get(col, 0):.1f}")

st.markdown("---")

# --- Evolución jornada a jornada (multi-stat) ---
st.subheader("Evolución por jornada")

if not game_log.empty:
    stat_options = {
        "Puntos": "puntos",
        "Rebotes": "rebotes_totales",
        "Asistencias": "asistencias",
        "Valoración": "valoracion",
        "Minutos": "minutos_decimal",
        "Plus/Minus": "plus_minus",
        "Robos": "robos",
        "Pérdidas": "perdidas",
    }

    selected_stats = st.multiselect(
        "Estadísticas a mostrar",
        list(stat_options.keys()),
        default=["Puntos"],
    )

    if selected_stats:
        fig_multi = go.Figure()
        for stat_name in selected_stats:
            stat_col = stat_options[stat_name]
            fig_multi.add_trace(go.Scatter(
                x=game_log["jornada_num"],
                y=game_log[stat_col],
                mode="lines+markers",
                name=stat_name,
                line=dict(width=2),
                marker=dict(size=6),
            ))
            # Media móvil
            if len(game_log) >= 5:
                rolling = game_log[stat_col].rolling(window=5, min_periods=1).mean()
                fig_multi.add_trace(go.Scatter(
                    x=game_log["jornada_num"],
                    y=rolling,
                    mode="lines",
                    name=f"{stat_name} (media 5)",
                    line=dict(width=1, dash="dot"),
                    opacity=0.6,
                ))

        fig_multi.update_layout(
            title=f"{selected_player} - Evolución",
            xaxis_title="Jornada", xaxis=dict(dtick=1),
            height=400,
        )
        st.plotly_chart(apply_standard_layout(fig_multi), use_container_width=True)

    # Tabla de partidos
    st.markdown("---")
    st.subheader("Registro de partidos")
    display_cols = [
        "jornada_num", "fecha", "oponente", "es_local", "minutos",
        "puntos", "rebotes_totales", "asistencias", "robos", "perdidas",
        "plus_minus", "valoracion",
    ]
    available_cols = [c for c in display_cols if c in game_log.columns]
    st.dataframe(
        game_log[available_cols].rename(columns={
            "jornada_num": "Jornada", "fecha": "Fecha", "oponente": "Oponente",
            "es_local": "Local", "minutos": "Min", "puntos": "Pts",
            "rebotes_totales": "Reb", "asistencias": "Ast",
            "robos": "Rob", "perdidas": "Pér",
            "plus_minus": "+/-", "valoracion": "Val",
        }),
        use_container_width=True,
        hide_index=True,
    )
