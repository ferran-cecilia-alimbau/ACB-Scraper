"""Página de rankings: líderes estadísticos + rankings de equipos + mejores actuaciones."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.data_loader import load_player_stats, load_player_profiles, load_team_stats, load_game_info
from src.preprocessing import aggregate_player_season, aggregate_team_season
from src.metrics import add_advanced_stats_to_teams, effective_fg_pct
from src.charts import get_team_color, apply_standard_layout, inject_custom_css, styled_header
from src.constants import POSITION_MAP

st.set_page_config(page_title="Rankings - ACB", layout="wide")
inject_custom_css()
styled_header("Rankings de la Liga", "Líderes estadísticos y mejores actuaciones")

player_stats = load_player_stats()
profiles = load_player_profiles()
team_stats_raw = load_team_stats()
game_info = load_game_info()
season_stats = aggregate_player_season(player_stats)

# Merge con posiciones
season_with_pos = season_stats.merge(
    profiles[["player_id", "posicion"]], on="player_id", how="left"
)

# Tabs
tab_players, tab_teams, tab_performances = st.tabs([
    "Jugadores", "Equipos", "Mejores actuaciones"
])

# ===== TAB JUGADORES =====
with tab_players:
    # --- Filtros ---
    st.sidebar.subheader("Filtros")

    min_games = st.sidebar.slider("Mínimo de partidos", 1, 17, 5)
    min_minutes = st.sidebar.slider("Mínimo de minutos/partido", 0, 30, 5)

    positions = st.sidebar.multiselect(
        "Posiciones",
        list(POSITION_MAP.keys()),
        default=list(POSITION_MAP.keys()),
        format_func=lambda x: POSITION_MAP.get(x, x),
    )

    mode = st.sidebar.radio("Modo", ["Por partido", "Total", "Per-36 min"])

    # Filtrar
    filtered = season_with_pos[
        (season_with_pos["partidos"] >= min_games)
        & (season_with_pos["minutos_decimal_avg"] >= min_minutes)
        & (season_with_pos["posicion"].isin(positions))
    ].copy()

    if filtered.empty:
        st.warning("No hay jugadores con los filtros seleccionados")
        st.stop()

    # --- Definir categorías según modo ---
    if mode == "Por partido":
        categories = {
            "Puntos": "puntos_avg",
            "Rebotes": "rebotes_totales_avg",
            "Asistencias": "asistencias_avg",
            "Robos": "robos_avg",
            "Tapones": "tapones_favor_avg",
            "Valoración": "valoracion_avg",
            "Pérdidas": "perdidas_avg",
            "eFG%": "efg_pct",
            "TS%": "ts_pct",
            "T3%": "t3_pct",
            "TL%": "tl_pct",
            "AST/TO": None,
        }
    elif mode == "Total":
        categories = {
            "Puntos": "puntos",
            "Rebotes": "rebotes_totales",
            "Asistencias": "asistencias",
            "Robos": "robos",
            "Tapones": "tapones_favor",
            "Valoración": "valoracion",
            "Triples anotados": "t3_anotados",
        }
    else:  # Per-36
        categories = {
            "Puntos": "puntos_per36",
            "Rebotes": "rebotes_totales_per36",
            "Asistencias": "asistencias_per36",
            "Robos": "robos_per36",
            "Tapones": "tapones_favor_per36",
            "Valoración": "valoracion_per36",
            "Pérdidas": "perdidas_per36",
        }

    # --- Selector de categoría ---
    selected_cat = st.selectbox("Categoría", list(categories.keys()))

    # Handle AST/TO special case
    if selected_cat == "AST/TO":
        filtered["ast_to"] = np.where(
            filtered["perdidas"] > 0,
            filtered["asistencias"] / filtered["perdidas"],
            0,
        )
        col_name = "ast_to"
    else:
        col_name = categories[selected_cat]

    # Para % de tiro, requerir mínimo de intentos
    if selected_cat == "T3%":
        min_att = st.slider("Mín. intentos T3 totales", 10, 100, 30)
        filtered = filtered[filtered["t3_intentados"] >= min_att]
    elif selected_cat == "TL%":
        min_att = st.slider("Mín. intentos TL totales", 10, 100, 20)
        filtered = filtered[filtered["tl_intentados"] >= min_att]

    # Ordenar
    ascending = selected_cat == "Pérdidas"
    top = filtered.nlargest(20, col_name) if not ascending else filtered.nsmallest(20, col_name)

    # --- Top 20 tabla ---
    st.subheader(f"Top 20 - {selected_cat} ({mode})")

    display_df = top[["nombre", "equipo", "partidos", col_name]].copy()
    display_df.columns = ["Jugador", "Equipo", "PJ", selected_cat]
    display_df[selected_cat] = display_df[selected_cat].round(1)
    display_df = display_df.reset_index(drop=True)
    display_df.index = display_df.index + 1
    display_df.index.name = "#"

    st.dataframe(display_df, use_container_width=True)

    # --- Bar chart con colores de equipo ---
    colors = [get_team_color(eq) for eq in top["equipo"]]
    fig = go.Figure(go.Bar(
        y=top.sort_values(col_name, ascending=not ascending)["nombre"],
        x=top.sort_values(col_name, ascending=not ascending)[col_name],
        orientation="h",
        marker_color=[get_team_color(eq) for eq in top.sort_values(col_name, ascending=not ascending)["equipo"]],
        text=top.sort_values(col_name, ascending=not ascending)[col_name].round(1),
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Top 20 - {selected_cat}",
        height=max(400, len(top) * 25 + 100),
        yaxis=dict(autorange="reversed" if not ascending else True),
    )
    st.plotly_chart(apply_standard_layout(fig), use_container_width=True)

    # --- Histograma de distribución ---
    st.subheader(f"Distribución de {selected_cat}")

    fig_hist = px.histogram(
        filtered, x=col_name, nbins=30,
        title=f"Distribución de {selected_cat} ({mode})",
        labels={col_name: selected_cat},
    )
    mean_val = filtered[col_name].mean()
    fig_hist.add_vline(
        x=mean_val, line_dash="dash", line_color="red",
        annotation_text=f"Media: {mean_val:.1f}",
    )
    fig_hist.update_layout(height=350)
    st.plotly_chart(apply_standard_layout(fig_hist), use_container_width=True)

# ===== TAB EQUIPOS =====
with tab_teams:
    st.subheader("Rankings de equipos")

    team_season = aggregate_team_season(team_stats_raw)
    team_adv = add_advanced_stats_to_teams(team_stats_raw, game_info)

    # Aggregate advanced stats per team
    team_adv_agg = team_adv.groupby("equipo").agg(
        avg_ortg=("ortg", "mean"),
        avg_drtg=("drtg", "mean"),
        avg_pace=("pace", "mean"),
    ).reset_index()
    team_adv_agg["avg_net_rtg"] = team_adv_agg["avg_ortg"] - team_adv_agg["avg_drtg"]

    # Merge with team season
    team_rankings = team_season.merge(team_adv_agg, on="equipo", how="left")

    team_cat = st.selectbox("Categoría de equipo", [
        "ORtg", "DRtg", "NetRtg", "Pace",
        "Puntos/p", "Rebotes/p", "Asistencias/p", "Robos/p",
        "eFG%", "T3%", "TL%",
    ])

    team_col_map = {
        "ORtg": "avg_ortg", "DRtg": "avg_drtg", "NetRtg": "avg_net_rtg",
        "Pace": "avg_pace", "Puntos/p": "puntos_avg", "Rebotes/p": "rebotes_totales_avg",
        "Asistencias/p": "asistencias_avg", "Robos/p": "robos_avg",
        "eFG%": None, "T3%": "t3_pct", "TL%": "tl_pct",
    }

    if team_cat == "eFG%":
        team_rankings["efg_pct"] = team_rankings.apply(
            lambda r: effective_fg_pct(
                r["t2_encestados"] + r["t3_encestados"],
                r["t3_encestados"],
                r["t2_intentados"] + r["t3_intentados"],
            ),
            axis=1,
        )
        team_col = "efg_pct"
    else:
        team_col = team_col_map[team_cat]

    ascending = team_cat == "DRtg"
    sorted_teams = team_rankings.sort_values(team_col, ascending=ascending)

    # Bar chart
    fig_team = go.Figure(go.Bar(
        y=sorted_teams["equipo"],
        x=sorted_teams[team_col],
        orientation="h",
        marker_color=[get_team_color(eq) for eq in sorted_teams["equipo"]],
        text=sorted_teams[team_col].round(1),
        textposition="outside",
    ))
    fig_team.update_layout(
        title=f"Ranking de equipos - {team_cat}",
        height=max(400, len(sorted_teams) * 30 + 80),
    )
    st.plotly_chart(apply_standard_layout(fig_team), use_container_width=True)

    # Table
    display_team = sorted_teams[["equipo", team_col]].copy()
    display_team.columns = ["Equipo", team_cat]
    display_team[team_cat] = display_team[team_cat].round(1)
    display_team = display_team.reset_index(drop=True)
    display_team.index = display_team.index + 1
    display_team.index.name = "#"
    st.dataframe(display_team, use_container_width=True)

# ===== TAB MEJORES ACTUACIONES =====
with tab_performances:
    st.subheader("Mejores actuaciones individuales de la temporada")

    perf_cat = st.selectbox("Categoría", [
        "Valoración", "Puntos", "Rebotes", "Asistencias", "Doble-dobles",
        "Partidos 20+ puntos",
    ], key="perf_cat")

    if perf_cat == "Doble-dobles":
        # Count double-doubles
        ps = player_stats.copy()
        stats_for_dd = ["puntos", "rebotes_totales", "asistencias", "robos", "tapones_favor"]
        ps["dd_count"] = (ps[stats_for_dd] >= 10).sum(axis=1)
        ps["is_dd"] = ps["dd_count"] >= 2

        dd_players = ps[ps["is_dd"]].groupby("nombre").agg(
            double_doubles=("is_dd", "sum"),
            equipo=("equipo", "first"),
        ).reset_index().sort_values("double_doubles", ascending=False).head(15)

        st.dataframe(
            dd_players.rename(columns={
                "nombre": "Jugador", "equipo": "Equipo", "double_doubles": "Doble-dobles"
            }).reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

    elif perf_cat == "Partidos 20+ puntos":
        ps = player_stats.copy()
        games_20 = ps[ps["puntos"] >= 20].groupby("nombre").agg(
            count=("puntos", "count"),
            equipo=("equipo", "first"),
            max_pts=("puntos", "max"),
        ).reset_index().sort_values("count", ascending=False).head(15)

        games_20 = games_20.rename(columns={
            "nombre": "Jugador", "equipo": "Equipo",
            "count": "Partidos 20+", "max_pts": "Máx pts",
        })
        st.dataframe(games_20, use_container_width=True, hide_index=True)

    else:
        perf_col = {
            "Valoración": "valoracion", "Puntos": "puntos",
            "Rebotes": "rebotes_totales", "Asistencias": "asistencias",
        }[perf_cat]

        top_perfs = player_stats.nlargest(10, perf_col)[[
            "nombre", "equipo", perf_col, "id_partido"
        ]].copy()

        # Add game info
        top_perfs = top_perfs.merge(
            game_info[["id_partido", "jornada_num", "fecha", "local", "visitante"]],
            on="id_partido",
        )
        top_perfs["oponente"] = top_perfs.apply(
            lambda r: r["visitante"] if r["equipo"] == r["local"] else r["local"], axis=1
        )

        display_perfs = top_perfs[["nombre", "equipo", perf_col, "jornada_num", "oponente", "fecha"]].copy()
        display_perfs.columns = ["Jugador", "Equipo", perf_cat, "Jornada", "Oponente", "Fecha"]
        display_perfs = display_perfs.reset_index(drop=True)
        display_perfs.index = display_perfs.index + 1
        display_perfs.index.name = "#"

        st.dataframe(display_perfs, use_container_width=True)

        # Bar chart
        fig_perf = go.Figure(go.Bar(
            y=display_perfs["Jugador"] + " (J" + display_perfs["Jornada"].astype(str) + ")",
            x=display_perfs[perf_cat],
            orientation="h",
            marker_color=[get_team_color(eq) for eq in display_perfs["Equipo"]],
            text=display_perfs[perf_cat],
            textposition="outside",
        ))
        fig_perf.update_layout(
            title=f"Top 10 actuaciones - {perf_cat}",
            height=400,
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(apply_standard_layout(fig_perf), use_container_width=True)
