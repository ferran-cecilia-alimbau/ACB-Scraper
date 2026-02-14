"""Página de Clasificación: Tabla + ORtg/DRtg scatter + diferencial + evolución."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.data_loader import load_game_info, load_team_stats
from src.preprocessing import calculate_standings, standings_evolution, aggregate_team_season
from src.metrics import add_advanced_stats_to_teams
from src.charts import get_team_color, apply_standard_layout, scatter_chart, inject_custom_css, styled_header

st.set_page_config(page_title="Clasificación - ACB", layout="wide")
inject_custom_css()
styled_header("Clasificación ACB 2025-26", "Tabla, ratings y evolución por jornada")

game_info = load_game_info()
team_stats = load_team_stats()

# --- Tabla de clasificación ---
st.subheader("Tabla de posiciones")
standings = calculate_standings(game_info)

# Formatear para mostrar
display_df = standings[
    ["equipo", "J", "G", "P", "PF", "PC", "Dif",
     "G_casa", "P_casa", "G_fuera", "P_fuera", "pct"]
].copy()
display_df["Casa"] = display_df["G_casa"].astype(str) + "-" + display_df["P_casa"].astype(str)
display_df["Fuera"] = display_df["G_fuera"].astype(str) + "-" + display_df["P_fuera"].astype(str)
display_df["% Vic"] = display_df["pct"].round(1)
display_df = display_df[["equipo", "J", "G", "P", "PF", "PC", "Dif", "Casa", "Fuera", "% Vic"]]

# Resaltar zona playoff (top 8)
st.dataframe(display_df, use_container_width=True, hide_index=False)

st.caption("Top 8 = Zona Playoff")

st.markdown("---")

# --- KPIs mejorados ---
leader = standings.iloc[0]
last = standings.iloc[-1]

# Calcular métricas avanzadas para KPIs
team_adv = add_advanced_stats_to_teams(team_stats, game_info)
team_season_adv = team_adv.groupby("equipo").agg(
    avg_ortg=("ortg", "mean"),
    avg_drtg=("drtg", "mean"),
    avg_pace=("pace", "mean"),
).reset_index()

best_attack = team_season_adv.loc[team_season_adv["avg_ortg"].idxmax()]
best_defense = team_season_adv.loc[team_season_adv["avg_drtg"].idxmin()]
fastest_pace = team_season_adv.loc[team_season_adv["avg_pace"].idxmax()]

# Carrera más apretada: diferencia entre pos 8 y 9
if len(standings) >= 9:
    pos8 = standings.iloc[7]
    pos9 = standings.iloc[8]
    race_diff = pos8["G"] - pos9["G"]
else:
    race_diff = None

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Líder", leader["equipo"], f"{leader['G']}G-{leader['P']}P")
col2.metric("Mejor ataque (ORtg)", best_attack["equipo"], f"{best_attack['avg_ortg']:.1f}")
col3.metric("Mejor defensa (DRtg)", best_defense["equipo"], f"{best_defense['avg_drtg']:.1f}")
col4.metric("Más rápido (Pace)", fastest_pace["equipo"], f"{fastest_pace['avg_pace']:.1f}")
if race_diff is not None:
    col5.metric("Playoff race (8ª-9ª)", f"{race_diff:+d} G",
                f"{pos8['equipo']} vs {pos9['equipo']}")

st.markdown("---")

# --- ORtg vs DRtg Scatter ---
st.subheader("Offensive Rating vs Defensive Rating")

scatter_df = team_season_adv.copy()
scatter_df["equipo"] = scatter_df["equipo"]
scatter_df["net_rtg"] = scatter_df["avg_ortg"] - scatter_df["avg_drtg"]

fig_scatter = go.Figure()
for _, row in scatter_df.iterrows():
    color = get_team_color(row["equipo"])
    fig_scatter.add_trace(go.Scatter(
        x=[row["avg_ortg"]],
        y=[row["avg_drtg"]],
        mode="markers+text",
        text=[row["equipo"]],
        textposition="top center",
        textfont=dict(size=9),
        marker=dict(color=color, size=12),
        showlegend=False,
        hovertemplate=(
            f"<b>{row['equipo']}</b><br>"
            f"ORtg: {row['avg_ortg']:.1f}<br>"
            f"DRtg: {row['avg_drtg']:.1f}<br>"
            f"NetRtg: {row['net_rtg']:+.1f}<extra></extra>"
        ),
    ))

# Medias
fig_scatter.add_hline(y=scatter_df["avg_drtg"].mean(), line_dash="dash", line_color="gray", opacity=0.5)
fig_scatter.add_vline(x=scatter_df["avg_ortg"].mean(), line_dash="dash", line_color="gray", opacity=0.5)

# Annotations for quadrants
fig_scatter.add_annotation(
    x=scatter_df["avg_ortg"].max(), y=scatter_df["avg_drtg"].min(),
    text="Elite", showarrow=False, font=dict(color="green", size=10), opacity=0.5)
fig_scatter.add_annotation(
    x=scatter_df["avg_ortg"].min(), y=scatter_df["avg_drtg"].max(),
    text="Peor", showarrow=False, font=dict(color="red", size=10), opacity=0.5)

fig_scatter.update_layout(
    xaxis_title="Offensive Rating (más alto = mejor)",
    yaxis_title="Defensive Rating (más bajo = mejor)",
    yaxis=dict(autorange="reversed"),
    height=500,
)
st.plotly_chart(apply_standard_layout(fig_scatter), use_container_width=True)

st.markdown("---")

# --- Barras de diferencial de puntos ---
st.subheader("Diferencial de puntos por equipo")

diff_df = standings[["equipo", "Dif"]].copy().sort_values("Dif", ascending=True)
colors = [
    "#4CAF50" if d > 0 else "#F44336" for d in diff_df["Dif"]
]

fig_diff = go.Figure(go.Bar(
    y=diff_df["equipo"],
    x=diff_df["Dif"],
    orientation="h",
    marker_color=colors,
    text=diff_df["Dif"].apply(lambda x: f"{x:+d}"),
    textposition="outside",
))
fig_diff.update_layout(
    title="Diferencial total de puntos",
    xaxis_title="Diferencia (PF - PC)",
    height=max(400, len(diff_df) * 30 + 80),
)
st.plotly_chart(apply_standard_layout(fig_diff), use_container_width=True)

st.markdown("---")

# --- Evolución de posiciones ---
st.subheader("Evolución de posiciones por jornada")

evolution = standings_evolution(game_info)

all_teams = sorted(evolution["equipo"].unique())
selected_teams = st.multiselect(
    "Equipos a mostrar",
    all_teams,
    default=all_teams[:6],
)

if selected_teams:
    filtered = evolution[evolution["equipo"].isin(selected_teams)]
    color_map = {team: get_team_color(team) for team in selected_teams}

    fig = px.line(
        filtered,
        x="jornada_num",
        y="posicion",
        color="equipo",
        color_discrete_map=color_map,
        markers=True,
        labels={"jornada_num": "Jornada", "posicion": "Posición", "equipo": "Equipo"},
    )

    fig.update_yaxes(autorange="reversed", dtick=1)
    fig.update_xaxes(dtick=1)
    fig.update_layout(height=500, hovermode="x unified")

    st.plotly_chart(apply_standard_layout(fig), use_container_width=True)

# --- Evolución de victorias ---
st.subheader("Evolución de victorias acumuladas")

if selected_teams:
    fig2 = px.line(
        filtered,
        x="jornada_num",
        y="G",
        color="equipo",
        color_discrete_map=color_map,
        markers=True,
        labels={"jornada_num": "Jornada", "G": "Victorias", "equipo": "Equipo"},
    )

    fig2.update_xaxes(dtick=1)
    fig2.update_layout(height=400)

    st.plotly_chart(apply_standard_layout(fig2), use_container_width=True)
