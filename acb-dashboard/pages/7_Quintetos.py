"""Página de análisis de Quintetos: lineups, minutos compartidos, stints."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import streamlit as st
import pandas as pd

from src.data_loader import load_game_info
from src.pbp_bridge import (
    load_and_analyze_game, lineup_net_rating, shared_minutes_matrix,
    player_minutes, substitution_impact,
    create_shared_minutes_heatmap, create_lineup_ratings_table,
)
from src.charts import (
    get_team_color, apply_standard_layout, player_stint_gantt_chart, inject_custom_css,
    game_selector, styled_header,
)

st.set_page_config(page_title="Quintetos - ACB", layout="wide")
inject_custom_css()
styled_header("Análisis de Quintetos", "Lineups, minutos compartidos y stints")

game_info = load_game_info()

# Selector de partido
game_id, game = game_selector(game_info, key="quintetos_selector")
local = game["local"]
visitante = game["visitante"]

st.markdown(f"### {local} {game['resultado_local']} - {game['resultado_visitante']} {visitante}")

# Cargar PBP
with st.spinner("Cargando datos play-by-play..."):
    analysis = load_and_analyze_game(game_id)

if analysis is None:
    st.info("No hay datos play-by-play disponibles para este partido.")
    st.stop()

stints = analysis["stints"]
stints_df = analysis["stints_df"]

# Tabs por equipo
tab_local, tab_visit = st.tabs([local, visitante])

for tab, side, team_name in [(tab_local, "local", local), (tab_visit, "visitante", visitante)]:
    with tab:
        # 1. Top quintetos por Net Rating
        st.subheader("Top Quintetos por Net Rating")
        lineup_df = lineup_net_rating(stints_df, min_minutes=2.0)

        if not lineup_df.empty:
            # Filtrar por lado (los lineups del equipo local contienen 5 jugadores del local)
            lineup_key = f"lineup_{side}"
            team_players = set()
            for s in stints:
                for p in s[lineup_key]:
                    team_players.add(p)

            team_lineups = lineup_df[lineup_df["lineup"].apply(
                lambda x: len(set(x) & team_players) >= 3
            )]

            if not team_lineups.empty:
                fig_table = create_lineup_ratings_table(team_lineups, top_n=5)
                st.plotly_chart(apply_standard_layout(fig_table), use_container_width=True)
            else:
                st.info("No hay suficientes datos de quintetos para este equipo.")
        else:
            st.info("No hay suficientes datos de quintetos.")

        st.markdown("---")

        # 2. Heatmap de minutos compartidos
        st.subheader("Minutos compartidos")
        shared_matrix = shared_minutes_matrix(stints_df, side=side)
        if not shared_matrix.empty:
            fig_heatmap = create_shared_minutes_heatmap(shared_matrix, team_name)
            st.plotly_chart(apply_standard_layout(fig_heatmap), use_container_width=True)

        st.markdown("---")

        # 3. Minutos por jugador
        st.subheader("Minutos por jugador")
        mins = player_minutes(stints, team_side=side.upper())
        if mins:
            mins_df = pd.DataFrame(
                sorted(mins.items(), key=lambda x: -x[1]),
                columns=["Jugador", "Minutos"]
            )
            mins_df["Minutos"] = mins_df["Minutos"].round(1)

            import plotly.graph_objects as go
            color = get_team_color(team_name)
            fig_mins = go.Figure(go.Bar(
                y=mins_df["Jugador"],
                x=mins_df["Minutos"],
                orientation="h",
                marker_color=color,
                text=mins_df["Minutos"],
                textposition="outside",
            ))
            fig_mins.update_layout(
                title=f"{team_name} - Minutos por jugador",
                xaxis_title="Minutos",
                height=max(300, len(mins_df) * 35 + 80),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(apply_standard_layout(fig_mins), use_container_width=True)

        st.markdown("---")

        # 4. Gantt de stints
        st.subheader("Timeline de stints")
        fig_gantt = player_stint_gantt_chart(stints_df, side, team_name)
        if fig_gantt.data:
            st.plotly_chart(fig_gantt, use_container_width=True)

        st.markdown("---")

        # 5. Impacto de sustituciones
        st.subheader("Impacto de sustituciones")
        pbp = analysis["pbp"]
        impacts = substitution_impact(pbp)
        if impacts:
            impacts_df = pd.DataFrame(impacts)
            team_impacts = impacts_df[impacts_df["team"] == side.upper()]
            if not team_impacts.empty:
                display = team_impacts[[
                    "player_in", "player_out", "sub_time",
                    "pm_before", "pm_after", "impact"
                ]].copy()
                display["sub_time"] = (display["sub_time"] / 60).round(1)
                display = display.rename(columns={
                    "player_in": "Entra", "player_out": "Sale",
                    "sub_time": "Minuto", "pm_before": "+/- antes",
                    "pm_after": "+/- después", "impact": "Impacto",
                })
                display = display.sort_values("Minuto")
                st.dataframe(display, use_container_width=True, hide_index=True)
            else:
                st.info("No hay sustituciones registradas para este equipo.")
        else:
            st.info("No hay datos de sustituciones.")
