"""ACB Dashboard - Entry point."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="ACB Dashboard 2025-26",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.data_loader import load_game_info, load_team_stats, load_player_stats
from src.preprocessing import (
    calculate_standings, aggregate_player_season, compute_league_averages,
)
from src.metrics import add_advanced_stats_to_teams
from src.charts import (
    styled_metric_row, get_team_color, inject_custom_css,
    styled_header, styled_game_card, styled_sidebar_header,
)

inject_custom_css()
styled_header("ACB Dashboard 2025-26", "Análisis estadístico de la Liga Endesa")

game_info = load_game_info()
team_stats = load_team_stats()
player_stats = load_player_stats()
league_avgs = compute_league_averages(team_stats, player_stats)

# --- KPIs principales ---
n_jornadas = game_info["jornada_num"].max()
n_partidos = len(game_info)
avg_pts = team_stats["puntos"].mean()

styled_metric_row([
    {"label": "Jornadas", "value": n_jornadas},
    {"label": "Partidos jugados", "value": n_partidos},
    {"label": "Pts/partido (media)", "value": f"{avg_pts:.1f}"},
    {"label": "Equipos", "value": 18},
])

st.markdown("---")

# --- Última jornada ---
st.subheader(f"Resultados - Jornada {n_jornadas}")

last_round = game_info[game_info["jornada_num"] == n_jornadas].sort_values("fecha")

cols_per_row = 3
rows_needed = (len(last_round) + cols_per_row - 1) // cols_per_row

for row_idx in range(rows_needed):
    cols = st.columns(cols_per_row)
    for col_idx in range(cols_per_row):
        game_idx = row_idx * cols_per_row + col_idx
        if game_idx >= len(last_round):
            break
        g = last_round.iloc[game_idx]
        with cols[col_idx]:
            styled_game_card(g, get_team_color(g["local"]), get_team_color(g["visitante"]))

st.markdown("---")

# --- Clasificación resumida (Top 8 + últimos 2) ---
st.subheader("Clasificación")
standings = calculate_standings(game_info)

display_df = standings[
    ["equipo", "J", "G", "P", "PF", "PC", "Dif", "pct"]
].copy()
display_df["% Vic"] = display_df["pct"].round(1)
display_df = display_df.drop(columns=["pct"])
st.dataframe(display_df, use_container_width=True, hide_index=False)

st.caption("Top 8 = Zona Playoff")

st.markdown("---")

# --- Líderes de temporada ---
st.subheader("Líderes de la temporada")

season_stats = aggregate_player_season(player_stats)
eligible = season_stats[
    (season_stats["partidos"] >= 5) & (season_stats["minutos_decimal_avg"] > 5)
]

leaders = {
    "Anotación": ("puntos_avg", "pts/p"),
    "Rebotes": ("rebotes_totales_avg", "reb/p"),
    "Asistencias": ("asistencias_avg", "ast/p"),
    "Valoración": ("valoracion_avg", "val/p"),
}

cols = st.columns(len(leaders))
for i, (title, (col_name, suffix)) in enumerate(leaders.items()):
    with cols[i]:
        st.markdown(f"**{title}**")
        top3 = eligible.nlargest(3, col_name)[["nombre", "equipo", col_name]].copy()
        for rank, (_, row) in enumerate(top3.iterrows(), 1):
            color = get_team_color(row["equipo"])
            st.markdown(
                f"{rank}. <span style='color:{color};font-weight:bold'>{row['nombre']}</span> "
                f"({row['equipo']}) — {row[col_name]:.1f} {suffix}",
                unsafe_allow_html=True,
            )

st.markdown("---")

# --- Métricas avanzadas highlight ---
st.subheader("Métricas avanzadas")

team_adv = add_advanced_stats_to_teams(team_stats, game_info)
team_adv_agg = team_adv.groupby("equipo").agg(
    avg_ortg=("ortg", "mean"),
    avg_drtg=("drtg", "mean"),
    avg_pace=("pace", "mean"),
).reset_index()
team_adv_agg["net_rtg"] = team_adv_agg["avg_ortg"] - team_adv_agg["avg_drtg"]

best_ortg = team_adv_agg.loc[team_adv_agg["avg_ortg"].idxmax()]
best_drtg = team_adv_agg.loc[team_adv_agg["avg_drtg"].idxmin()]
best_net = team_adv_agg.loc[team_adv_agg["net_rtg"].idxmax()]
fastest = team_adv_agg.loc[team_adv_agg["avg_pace"].idxmax()]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Mejor ataque (ORtg)", best_ortg["equipo"], f"{best_ortg['avg_ortg']:.1f}")
col2.metric("Mejor defensa (DRtg)", best_drtg["equipo"], f"{best_drtg['avg_drtg']:.1f}")
col3.metric("Mejor NetRtg", best_net["equipo"], f"{best_net['net_rtg']:+.1f}")
col4.metric("Mayor ritmo (Pace)", fastest["equipo"], f"{fastest['avg_pace']:.1f}")

st.markdown("---")

# --- Navegación ---
st.subheader("Páginas del dashboard")

pages = [
    ("1 - Clasificación", "Tabla de posiciones, ORtg vs DRtg, evolución de posiciones por jornada"),
    ("2 - Equipo", "Ficha completa de equipo: ofensivo, defensivo, resultados y roster"),
    ("3 - Jugador", "Ficha de jugador: radar, evolución, splits, rankings de liga"),
    ("4 - Comparador", "Compara jugadores, equipos o múltiples jugadores con radar superpuesto"),
    ("5 - Partido", "Box score, Four Factors y análisis play-by-play detallado"),
    ("6 - Rankings", "Líderes estadísticos, rankings de equipos y mejores actuaciones"),
    ("7 - Quintetos", "Análisis de quintetos por partido: lineups, minutos compartidos, stints"),
    ("8 - Clutch", "Análisis de situaciones clutch: timeline, shooting, jugadas clave"),
]

for page_name, desc in pages:
    st.markdown(f"**{page_name}** — {desc}")

# Sidebar
styled_sidebar_header("ACB", "Liga Endesa 2025-26")
st.sidebar.markdown(f"**{n_jornadas}** jornadas · **{n_partidos}** partidos · **18** equipos")
st.sidebar.markdown("---")
st.sidebar.markdown("Navega por las páginas del menú lateral.")
