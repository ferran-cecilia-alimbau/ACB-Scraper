"""Página de análisis Clutch: rendimiento en los últimos minutos de partidos igualados."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.data_loader import load_game_info
from src.pbp_bridge import (
    load_and_analyze_game, filter_clutch_events, clutch_shooting_stats,
    create_score_diff_timeline,
)
from src.charts import get_team_color, apply_standard_layout, clutch_player_bars, inject_custom_css, game_selector, styled_header

st.set_page_config(page_title="Clutch - ACB", layout="wide")
inject_custom_css()
styled_header("Análisis Clutch", "Rendimiento en los últimos minutos de partidos igualados")

game_info = load_game_info()

# Selector de partido
game_id, game = game_selector(game_info, key="clutch_selector")
local = game["local"]
visitante = game["visitante"]

# Slider de umbral
max_diff = st.sidebar.slider("Umbral de diferencia (puntos)", 1, 15, 5)

st.markdown(f"### {local} {game['resultado_local']} - {game['resultado_visitante']} {visitante}")

# Cargar PBP
with st.spinner("Cargando datos play-by-play..."):
    analysis = load_and_analyze_game(game_id)

if analysis is None:
    st.info("No hay datos play-by-play disponibles para este partido.")
    st.stop()

pbp = analysis["pbp"]
clutch_events = filter_clutch_events(pbp, max_diff=max_diff)

if clutch_events.empty:
    st.info(f"No hay situaciones clutch en este partido (diferencia <= {max_diff} pts en últimos 5 min del 4C o prórrogas).")
    st.stop()

# --- 1. KPIs Clutch ---
st.subheader("Resumen Clutch")

SCORING_ACTIONS = {"Tiro de 2 anotado", "Triple anotado", "Mate", "Tiro libre anotado"}

clutch_scoring = clutch_events[clutch_events["accion"].isin(SCORING_ACTIONS)]
clutch_local_pts = 0
clutch_visit_pts = 0
for _, row in clutch_scoring.iterrows():
    pts = 3 if row["accion"] == "Triple anotado" else (1 if row["accion"] == "Tiro libre anotado" else 2)
    if row["equipo"] == "LOCAL":
        clutch_local_pts += pts
    else:
        clutch_visit_pts += pts

n_clutch_poss = len(clutch_events[clutch_events["accion"].isin(
    SCORING_ACTIONS | {"Tiro de 2 fallado", "Triple fallado", "Mate fallado",
     "Tiro libre fallado", "Pérdida", "Rebote defensivo"}
)])
clutch_duration = (clutch_events["abs_seconds"].max() - clutch_events["abs_seconds"].min()) / 60

winner_clutch = local if clutch_local_pts > clutch_visit_pts else (
    visitante if clutch_visit_pts > clutch_local_pts else "Empate"
)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Eventos clutch", len(clutch_events))
col2.metric("Minutos clutch", f"{clutch_duration:.1f}")
col3.metric(f"Pts {local}", clutch_local_pts)
col4.metric(f"Pts {visitante}", clutch_visit_pts)
col5.metric("Ganador clutch", winner_clutch)

st.markdown("---")

# --- 2. Timeline zoom: últimos 5 min 4C + prórrogas ---
st.subheader("Timeline Clutch")

clutch_pbp = pbp[pbp["abs_seconds"] >= 2100].copy()
if not clutch_pbp.empty:
    clutch_pbp["score_diff"] = (
        clutch_pbp["marcador_local"].astype(int) - clutch_pbp["marcador_visitante"].astype(int)
    )
    df_plot = clutch_pbp.drop_duplicates(subset=["abs_seconds", "score_diff"])

    fig_timeline = go.Figure()
    fig_timeline.add_trace(go.Scatter(
        x=df_plot["abs_seconds"] / 60,
        y=df_plot["score_diff"],
        mode="lines",
        name="Diferencia",
        line=dict(color="#1f77b4", width=2),
        fill="tozeroy",
        fillcolor="rgba(31, 119, 180, 0.1)",
    ))

    # Marcar anotaciones
    scoring_clutch = clutch_scoring.copy()
    if not scoring_clutch.empty:
        for _, row in scoring_clutch.iterrows():
            diff = int(row["marcador_local"]) - int(row["marcador_visitante"])
            color = get_team_color(local) if row["equipo"] == "LOCAL" else get_team_color(visitante)
            pts = 3 if row["accion"] == "Triple anotado" else (1 if row["accion"] == "Tiro libre anotado" else 2)
            fig_timeline.add_trace(go.Scatter(
                x=[row["abs_seconds"] / 60],
                y=[diff],
                mode="markers",
                marker=dict(color=color, size=pts * 4 + 4, symbol="circle"),
                hovertemplate=(
                    f"<b>{row.get('jugador', '')}</b><br>"
                    f"{row['accion']}<br>"
                    f"Min {row['abs_seconds']/60:.1f}<br>"
                    f"Marcador: {row['marcador_local']}-{row['marcador_visitante']}"
                    f"<extra></extra>"
                ),
                showlegend=False,
            ))

    fig_timeline.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    # Umbral clutch
    fig_timeline.add_hline(y=max_diff, line_dash="dot", line_color="rgba(255,0,0,0.3)")
    fig_timeline.add_hline(y=-max_diff, line_dash="dot", line_color="rgba(255,0,0,0.3)")

    fig_timeline.update_layout(
        title="Diferencia de marcador - Tramo Clutch",
        xaxis_title="Minutos",
        yaxis_title=f"← {visitante}    Diferencia    {local} →",
        height=400,
        showlegend=False,
    )
    st.plotly_chart(apply_standard_layout(fig_timeline), use_container_width=True)

st.markdown("---")

# --- 3. Shooting clutch por jugador ---
st.subheader("Estadísticas de tiro en situación Clutch")

clutch_stats = clutch_shooting_stats(pbp, max_diff=max_diff)
if not clutch_stats.empty:
    clutch_only = clutch_stats[clutch_stats["clutch_fga"] + clutch_stats["clutch_fta"] > 0].copy()
    if not clutch_only.empty:
        clutch_only["clutch_fg_pct"] = (
            clutch_only["clutch_pts"] / (clutch_only["clutch_fga"] + 0.44 * clutch_only["clutch_fta"]).replace(0, 1)
        ).round(1)

        # Resolver nombres de equipo
        game_teams = {
            "LOCAL": local,
            "VISITANTE": visitante,
        }
        clutch_only["equipo_nombre"] = clutch_only["equipo"].map(game_teams).fillna(clutch_only["equipo"])

        display_cols = clutch_only[[
            "jugador", "equipo_nombre", "clutch_fga", "clutch_fta",
            "clutch_pts", "clutch_ts_pct"
        ]].copy()
        display_cols = display_cols.rename(columns={
            "jugador": "Jugador", "equipo_nombre": "Equipo",
            "clutch_fga": "FGA", "clutch_fta": "FTA",
            "clutch_pts": "Pts", "clutch_ts_pct": "TS%",
        })
        display_cols["TS%"] = display_cols["TS%"].round(1)
        display_cols["FGA"] = display_cols["FGA"].astype(int)
        display_cols["FTA"] = display_cols["FTA"].astype(int)
        display_cols["Pts"] = display_cols["Pts"].astype(int)
        display_cols = display_cols.sort_values("Pts", ascending=False)
        st.dataframe(display_cols, use_container_width=True, hide_index=True)

        st.markdown("---")

        # --- 4. Barras de puntos clutch ---
        st.subheader("Puntos Clutch por jugador")
        clutch_only_for_bars = clutch_only.copy()
        clutch_only_for_bars["jugador"] = clutch_only["jugador"]
        clutch_only_for_bars["clutch_pts"] = clutch_only["clutch_pts"]
        fig_bars = clutch_player_bars(clutch_only_for_bars, local, visitante)
        if fig_bars.data:
            st.plotly_chart(fig_bars, use_container_width=True)

st.markdown("---")

# --- 5. Jugadas clave ---
st.subheader("Jugadas clave en situación Clutch")

key_actions = {"Tiro de 2 anotado", "Triple anotado", "Mate", "Tiro libre anotado",
               "Pérdida", "Robo", "Rebote ofensivo", "Tapón"}

key_plays = clutch_events[clutch_events["accion"].isin(key_actions)].copy()
if not key_plays.empty:
    key_plays["minuto"] = (key_plays["abs_seconds"] / 60).round(1)
    key_plays["marcador"] = key_plays["marcador_local"].astype(str) + "-" + key_plays["marcador_visitante"].astype(str)
    key_plays["equipo_nombre"] = key_plays["equipo"].map({"LOCAL": local, "VISITANTE": visitante})

    display_plays = key_plays[["minuto", "equipo_nombre", "jugador", "accion", "marcador"]].rename(
        columns={
            "minuto": "Min", "equipo_nombre": "Equipo", "jugador": "Jugador",
            "accion": "Acción", "marcador": "Marcador",
        }
    )
    st.dataframe(display_plays, use_container_width=True, hide_index=True)
else:
    st.info("No hay jugadas clave registradas en situación clutch.")
