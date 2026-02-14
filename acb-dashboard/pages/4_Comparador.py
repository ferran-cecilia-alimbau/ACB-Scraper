"""Página de comparación: jugador vs jugador, equipo vs equipo, multi-jugador."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from src.data_loader import load_player_stats, load_game_info, load_team_stats, load_player_profiles
from src.preprocessing import aggregate_player_season, aggregate_team_season, player_game_log
from src.metrics import add_advanced_stats_to_teams, four_factors
from src.charts import comparison_radar_chart, butterfly_chart, get_team_color, apply_standard_layout, inject_custom_css, hex_to_rgba, styled_header
from src.constants import POSITION_MAP, ALL_TEAMS, RADAR_CATEGORIES

st.set_page_config(page_title="Comparador - ACB", layout="wide")
inject_custom_css()
styled_header("Comparador", "Jugadores, equipos y análisis multi-jugador")

# Tabs: Jugadores vs Equipos vs Multi-jugador
tab_players, tab_teams, tab_multi = st.tabs(["Jugadores", "Equipos", "Multi-jugador"])

# --- Comparador de Jugadores ---
with tab_players:
    player_stats = load_player_stats()
    game_info = load_game_info()
    profiles = load_player_profiles()
    season_stats = aggregate_player_season(player_stats)

    season_with_pos = season_stats.merge(
        profiles[["player_id", "posicion"]], on="player_id", how="left"
    )

    player_list = sorted(season_with_pos["nombre"].unique())

    col1, col2 = st.columns(2)
    with col1:
        player1 = st.selectbox("Jugador 1", player_list, index=0, key="p1")
    with col2:
        player2 = st.selectbox("Jugador 2", player_list,
                               index=min(1, len(player_list) - 1), key="p2")

    if player1 == player2:
        st.warning("Selecciona dos jugadores diferentes")
        st.stop()
    else:
        p1_row = season_with_pos[season_with_pos["nombre"] == player1].iloc[0]
        p2_row = season_with_pos[season_with_pos["nombre"] == player2].iloc[0]

        eligible = season_with_pos[
            (season_with_pos["partidos"] >= 5) & (season_with_pos["minutos_decimal_avg"] > 5)
        ]

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

        def calc_radar(player_data, eligible_df):
            radar = {}
            for cat, col in radar_cols.items():
                values = eligible_df[col].dropna()
                if values.empty:
                    radar[cat] = 50
                    continue
                pval = player_data.get(col, 0)
                if cat == "Pérdidas (inv)":
                    pct = (values >= pval).mean() * 100
                else:
                    pct = (values <= pval).mean() * 100
                radar[cat] = min(pct, 100)
            return radar

        p1_radar = calc_radar(p1_row, eligible)
        p2_radar = calc_radar(p2_row, eligible)

        # Radar charts superpuestos
        st.subheader("Radar chart comparativo")
        fig = comparison_radar_chart(
            p1_radar, player1, p2_radar, player2,
            team1=p1_row["equipo"], team2=p2_row["equipo"],
        )
        st.plotly_chart(apply_standard_layout(fig), use_container_width=True)

        # Advanced metrics row
        st.subheader("Métricas avanzadas")
        adv_metrics = ["efg_pct", "ts_pct", "t2_pct", "t3_pct", "tl_pct"]
        adv_labels = ["eFG%", "TS%", "T2%", "T3%", "TL%"]
        adv_table = pd.DataFrame({
            "Métrica": adv_labels,
            player1: [round(p1_row.get(m, 0), 1) for m in adv_metrics],
            player2: [round(p2_row.get(m, 0), 1) for m in adv_metrics],
        })
        st.dataframe(adv_table, use_container_width=True, hide_index=True)

        # Evolución superpuesta
        st.subheader("Evolución superpuesta")
        stat_options = {
            "Puntos": "puntos", "Rebotes": "rebotes_totales",
            "Asistencias": "asistencias", "Valoración": "valoracion",
        }
        sel_stat = st.selectbox("Estadística", list(stat_options.keys()), key="evo_comp")
        stat_col = stat_options[sel_stat]

        gl1 = player_game_log(player_stats, game_info, player1)
        gl2 = player_game_log(player_stats, game_info, player2)

        if not gl1.empty and not gl2.empty:
            fig_evo = go.Figure()
            for gl, name, team in [(gl1, player1, p1_row["equipo"]), (gl2, player2, p2_row["equipo"])]:
                fig_evo.add_trace(go.Scatter(
                    x=gl["jornada_num"], y=gl[stat_col],
                    mode="lines+markers", name=name,
                    line=dict(color=get_team_color(team), width=2),
                ))
            fig_evo.update_layout(
                title=f"{sel_stat} por jornada",
                xaxis_title="Jornada", xaxis=dict(dtick=1), height=350,
            )
            st.plotly_chart(apply_standard_layout(fig_evo), use_container_width=True)

        # Butterfly chart
        st.subheader("Comparación directa (promedios por partido)")
        compare_cats = [
            "Puntos", "Rebotes", "Asistencias", "Robos",
            "Pérdidas", "Tapones", "Valoración", "Minutos",
        ]
        compare_cols = {
            "Puntos": "puntos_avg", "Rebotes": "rebotes_totales_avg",
            "Asistencias": "asistencias_avg", "Robos": "robos_avg",
            "Pérdidas": "perdidas_avg", "Tapones": "tapones_favor_avg",
            "Valoración": "valoracion_avg", "Minutos": "minutos_decimal_avg",
        }

        p1_data = {cat: p1_row.get(col, 0) for cat, col in compare_cols.items()}
        p2_data = {cat: p2_row.get(col, 0) for cat, col in compare_cols.items()}

        fig_bf = butterfly_chart(
            p1_data, player1, p2_data, player2,
            compare_cats,
            team1=p1_row["equipo"], team2=p2_row["equipo"],
        )
        st.plotly_chart(apply_standard_layout(fig_bf), use_container_width=True)

        # Tabla comparativa completa
        st.subheader("Tabla comparativa")
        comp_table = pd.DataFrame({
            "Estadística": compare_cats + ["T2%", "T3%", "TL%", "TS%", "eFG%"],
            player1: [p1_data[c] for c in compare_cats] + [
                p1_row["t2_pct"], p1_row["t3_pct"],
                p1_row["tl_pct"], p1_row["ts_pct"], p1_row["efg_pct"],
            ],
            player2: [p2_data[c] for c in compare_cats] + [
                p2_row["t2_pct"], p2_row["t3_pct"],
                p2_row["tl_pct"], p2_row["ts_pct"], p2_row["efg_pct"],
            ],
        })
        comp_table[player1] = comp_table[player1].round(1)
        comp_table[player2] = comp_table[player2].round(1)
        st.dataframe(comp_table, use_container_width=True, hide_index=True)

        # Historial directo
        st.subheader("Historial directo")
        p1_games = set(player_stats[player_stats["nombre"] == player1]["id_partido"])
        p2_games = set(player_stats[player_stats["nombre"] == player2]["id_partido"])
        common_games = p1_games & p2_games

        if common_games:
            direct_records = []
            for gid in common_games:
                g1 = player_stats[(player_stats["id_partido"] == gid) & (player_stats["nombre"] == player1)].iloc[0]
                g2 = player_stats[(player_stats["id_partido"] == gid) & (player_stats["nombre"] == player2)].iloc[0]
                ginfo = game_info[game_info["id_partido"] == gid].iloc[0]
                direct_records.append({
                    "Jornada": ginfo["jornada_num"],
                    "Fecha": ginfo["fecha"],
                    f"Pts {player1}": g1["puntos"],
                    f"Pts {player2}": g2["puntos"],
                    f"Val {player1}": g1["valoracion"],
                    f"Val {player2}": g2["valoracion"],
                })

            st.dataframe(
                pd.DataFrame(direct_records).sort_values("Jornada"),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No se han enfrentado esta temporada")

# --- Comparador de Equipos ---
with tab_teams:
    team_stats_data = load_team_stats()
    game_info_data = load_game_info()
    team_season = aggregate_team_season(team_stats_data)

    col1, col2 = st.columns(2)
    with col1:
        team1 = st.selectbox("Equipo 1", ALL_TEAMS, index=0, key="t1")
    with col2:
        team2 = st.selectbox("Equipo 2", ALL_TEAMS,
                             index=min(1, len(ALL_TEAMS) - 1), key="t2")

    if team1 == team2:
        st.warning("Selecciona dos equipos diferentes")
        st.stop()
    else:
        t1_row = team_season[team_season["equipo"] == team1]
        t2_row = team_season[team_season["equipo"] == team2]

        if t1_row.empty or t2_row.empty:
            st.warning("Datos de equipo no disponibles")
        else:
            t1_row = t1_row.iloc[0]
            t2_row = t2_row.iloc[0]

            # Four Factors comparison
            st.subheader("Four Factors")
            t1_games = team_stats_data[team_stats_data["equipo"] == team1]
            t2_games = team_stats_data[team_stats_data["equipo"] == team2]

            t1_ff = pd.DataFrame([four_factors(g.to_dict()) for _, g in t1_games.iterrows()]).mean()
            t2_ff = pd.DataFrame([four_factors(g.to_dict()) for _, g in t2_games.iterrows()]).mean()

            factors = ["eFG%", "TOV%", "OREB%", "FT_rate"]
            fig_ff = go.Figure()
            fig_ff.add_trace(go.Bar(
                name=team1, x=factors, y=[t1_ff[f] for f in factors],
                marker_color=get_team_color(team1),
            ))
            fig_ff.add_trace(go.Bar(
                name=team2, x=factors, y=[t2_ff[f] for f in factors],
                marker_color=get_team_color(team2),
            ))
            fig_ff.update_layout(barmode="group", height=350, yaxis_title="%")
            st.plotly_chart(apply_standard_layout(fig_ff), use_container_width=True)

            # ORtg/DRtg/NetRtg/Pace comparison
            st.subheader("Ratings avanzados")
            team_adv = add_advanced_stats_to_teams(team_stats_data, game_info_data)

            for team, team_name in [(team1, team1), (team2, team2)]:
                t_adv = team_adv[team_adv["equipo"] == team]
                if not t_adv.empty:
                    col_a, col_b, col_c, col_d = st.columns(4)
                    col_a.metric(f"ORtg {team_name}", f"{t_adv['ortg'].mean():.1f}")
                    col_b.metric(f"DRtg {team_name}", f"{t_adv['drtg'].mean():.1f}")
                    col_c.metric(f"NetRtg {team_name}", f"{(t_adv['ortg'].mean() - t_adv['drtg'].mean()):+.1f}")
                    col_d.metric(f"Pace {team_name}", f"{t_adv['pace'].mean():.1f}")

            # Butterfly chart
            st.subheader("Comparación directa (promedios por partido)")
            compare_cats_team = [
                "Puntos", "Rebotes", "Asistencias", "Robos",
                "Pérdidas", "Tapones", "T2%", "T3%", "TL%",
            ]
            compare_cols_team = {
                "Puntos": "puntos_avg", "Rebotes": "rebotes_totales_avg",
                "Asistencias": "asistencias_avg", "Robos": "robos_avg",
                "Pérdidas": "perdidas_avg", "Tapones": "tapones_favor_avg",
                "T2%": "t2_pct", "T3%": "t3_pct", "TL%": "tl_pct",
            }

            t1_data = {cat: t1_row.get(col, 0) for cat, col in compare_cols_team.items()}
            t2_data = {cat: t2_row.get(col, 0) for cat, col in compare_cols_team.items()}

            fig_team_bf = butterfly_chart(
                t1_data, team1, t2_data, team2,
                compare_cats_team,
                team1=team1, team2=team2,
            )
            st.plotly_chart(apply_standard_layout(fig_team_bf), use_container_width=True)

            # Tabla
            comp_table_team = pd.DataFrame({
                "Estadística": compare_cats_team,
                team1: [t1_data[c] for c in compare_cats_team],
                team2: [t2_data[c] for c in compare_cats_team],
            })
            comp_table_team[team1] = comp_table_team[team1].round(1)
            comp_table_team[team2] = comp_table_team[team2].round(1)
            st.dataframe(comp_table_team, use_container_width=True, hide_index=True)

            # Enfrentamientos directos
            st.subheader("Enfrentamientos directos")
            direct = game_info_data[
                ((game_info_data["local"] == team1) & (game_info_data["visitante"] == team2))
                | ((game_info_data["local"] == team2) & (game_info_data["visitante"] == team1))
            ]

            if not direct.empty:
                for _, g in direct.iterrows():
                    st.write(
                        f"J{g['jornada_num']} ({g['fecha']}): "
                        f"**{g['local']}** {g['resultado_local']} - "
                        f"{g['resultado_visitante']} **{g['visitante']}**"
                    )
            else:
                st.info("No se han enfrentado esta temporada")

# --- Multi-jugador ---
with tab_multi:
    st.subheader("Comparación multi-jugador (Radar)")

    player_stats_m = load_player_stats()
    profiles_m = load_player_profiles()
    season_stats_m = aggregate_player_season(player_stats_m)
    season_with_pos_m = season_stats_m.merge(
        profiles_m[["player_id", "posicion"]], on="player_id", how="left"
    )

    player_list_m = sorted(season_with_pos_m["nombre"].unique())
    selected_players = st.multiselect(
        "Selecciona 2-5 jugadores",
        player_list_m,
        default=player_list_m[:3] if len(player_list_m) >= 3 else player_list_m[:2],
        max_selections=5,
    )

    if len(selected_players) >= 2:
        eligible_m = season_with_pos_m[
            (season_with_pos_m["partidos"] >= 5) & (season_with_pos_m["minutos_decimal_avg"] > 5)
        ]

        radar_cols_m = {
            "Puntos": "puntos_per36",
            "Eficiencia": "efg_pct",
            "Rebotes": "rebotes_totales_per36",
            "Asistencias": "asistencias_per36",
            "Robos": "robos_per36",
            "Tapones": "tapones_favor_per36",
            "Pérdidas (inv)": "perdidas_per36",
            "Valoración": "valoracion_per36",
        }

        categories = list(radar_cols_m.keys())
        fig_multi = go.Figure()

        colors_palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

        for idx, player_name in enumerate(selected_players):
            p_row = season_with_pos_m[season_with_pos_m["nombre"] == player_name]
            if p_row.empty:
                continue
            p_row = p_row.iloc[0]

            radar_data = {}
            for cat, col in radar_cols_m.items():
                values = eligible_m[col].dropna()
                if values.empty:
                    radar_data[cat] = 50
                    continue
                pval = p_row.get(col, 0)
                if cat == "Pérdidas (inv)":
                    pct = (values >= pval).mean() * 100
                else:
                    pct = (values <= pval).mean() * 100
                radar_data[cat] = min(pct, 100)

            values = [radar_data[c] for c in categories]
            values.append(values[0])
            cats = categories + [categories[0]]

            team_c = get_team_color(p_row["equipo"])

            fig_multi.add_trace(go.Scatterpolar(
                r=values, theta=cats, fill="toself",
                name=player_name,
                fillcolor=f"rgba{hex_to_rgba(team_c, 0.15)}",
                line=dict(color=team_c, width=2),
            ))

        fig_multi.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            title="Radar comparativo multi-jugador",
            height=550,
        )
        st.plotly_chart(apply_standard_layout(fig_multi), use_container_width=True)

        # Table comparison
        st.subheader("Tabla comparativa")
        table_data = {"Estadística": [
            "Pts/p", "Reb/p", "Ast/p", "Rob/p", "Pér/p", "Val/p",
            "T2%", "T3%", "TL%", "TS%", "eFG%", "Min/p",
        ]}
        cols_map = [
            "puntos_avg", "rebotes_totales_avg", "asistencias_avg",
            "robos_avg", "perdidas_avg", "valoracion_avg",
            "t2_pct", "t3_pct", "tl_pct", "ts_pct", "efg_pct", "minutos_decimal_avg",
        ]
        for player_name in selected_players:
            p_row = season_with_pos_m[season_with_pos_m["nombre"] == player_name]
            if p_row.empty:
                continue
            p_row = p_row.iloc[0]
            table_data[player_name] = [round(p_row.get(c, 0), 1) for c in cols_map]

        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
    else:
        st.info("Selecciona al menos 2 jugadores para comparar.")
