"""Página de ficha de equipo: ofensivo/defensivo/resultados/jugadores."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from src.data_loader import load_game_info, load_team_stats, load_player_stats
from src.preprocessing import (
    aggregate_team_season, calculate_standings, aggregate_player_season,
    compute_league_averages,
)
from src.metrics import add_advanced_stats_to_teams, four_factors, estimate_possessions, pace
from src.charts import (
    shooting_breakdown_chart, quarter_heatmap, scatter_chart, get_team_color,
    apply_standard_layout, styled_metric_row, inject_custom_css, styled_header,
)
from src.constants import ALL_TEAMS

st.set_page_config(page_title="Equipo - ACB", layout="wide")
inject_custom_css()
styled_header("Ficha de Equipo", "Ofensivo, defensivo, resultados y roster")

game_info = load_game_info()
team_stats = load_team_stats()
player_stats = load_player_stats()

# Selector de equipo
selected_team = st.sidebar.selectbox("Selecciona equipo", ALL_TEAMS)

# Filtrar datos del equipo
team_games = team_stats[team_stats["equipo"] == selected_team]
team_season = aggregate_team_season(team_stats)
team_season_row = team_season[team_season["equipo"] == selected_team]

if team_season_row.empty:
    st.warning(f"No hay datos para {selected_team}")
    st.stop()

team_row = team_season_row.iloc[0]
color = get_team_color(selected_team)
league_avgs = compute_league_averages(team_stats, player_stats)

# --- Header con KPIs + delta vs liga ---
standings = calculate_standings(game_info)
team_standing = standings[standings["equipo"] == selected_team]

st.markdown(f"### {selected_team}")

if not team_standing.empty:
    ts = team_standing.iloc[0]
    pts_avg = team_row["puntos_avg"]
    pts_received = ts["PC"] / ts["J"] if ts["J"] > 0 else 0

    styled_metric_row([
        {"label": "Posición", "value": team_standing.index[0]},
        {"label": "Balance", "value": f"{ts['G']}G - {ts['P']}P"},
        {"label": "Pts/partido", "value": f"{pts_avg:.1f}",
         "delta": pts_avg - league_avgs["pts"], "suffix": ""},
        {"label": "Pts recibidos/p", "value": f"{pts_received:.1f}",
         "delta": -(pts_received - league_avgs["pts"]), "suffix": ""},
        {"label": "Dif total", "value": f"{ts['Dif']:+d}"},
    ])

# Métricas avanzadas de equipo
team_adv = add_advanced_stats_to_teams(team_stats, game_info)
team_adv_sel = team_adv[team_adv["equipo"] == selected_team]

if not team_adv_sel.empty:
    avg_ortg = team_adv_sel["ortg"].mean()
    avg_drtg = team_adv_sel["drtg"].mean()
    avg_net = avg_ortg - avg_drtg
    avg_pace = team_adv_sel["pace"].mean()

    st.markdown("")
    styled_metric_row([
        {"label": "ORtg", "value": f"{avg_ortg:.1f}"},
        {"label": "DRtg", "value": f"{avg_drtg:.1f}"},
        {"label": "NetRtg", "value": f"{avg_net:+.1f}"},
        {"label": "Pace", "value": f"{avg_pace:.1f}"},
    ])

# --- Tabs ---
tab_off, tab_def, tab_results, tab_players = st.tabs([
    "Ofensivo", "Defensivo", "Resultados", "Jugadores"
])

with tab_off:
    col_left, col_right = st.columns(2)

    with col_left:
        # Donut de distribución de tiro
        t2_att = team_row["t2_intentados"]
        t3_att = team_row["t3_intentados"]
        tl_att = team_row["tl_intentados"]
        fig_donut = go.Figure(go.Pie(
            labels=["T2", "T3", "TL"],
            values=[t2_att, t3_att, tl_att],
            hole=0.4,
            marker_colors=[color, get_team_color(selected_team, True), "#FFB300"],
            textinfo="label+percent",
        ))
        fig_donut.update_layout(title="Distribución de intentos de tiro", height=350)
        st.plotly_chart(apply_standard_layout(fig_donut), use_container_width=True)

    with col_right:
        fig = shooting_breakdown_chart(team_row, selected_team)
        st.plotly_chart(apply_standard_layout(fig), use_container_width=True)

    # Evolución puntos por jornada con media móvil
    st.markdown("---")
    st.subheader("Evolución de puntos por jornada")

    team_game_info = game_info[
        (game_info["local"] == selected_team) | (game_info["visitante"] == selected_team)
    ].sort_values("jornada_num")

    pts_by_game = []
    for _, g in team_game_info.iterrows():
        is_local = g["local"] == selected_team
        pts = g["resultado_local"] if is_local else g["resultado_visitante"]
        pts_by_game.append({"jornada_num": g["jornada_num"], "puntos": pts})

    pts_df = pd.DataFrame(pts_by_game)
    if not pts_df.empty:
        pts_df["media_movil"] = pts_df["puntos"].rolling(window=5, min_periods=1).mean()
        fig_evo = go.Figure()
        fig_evo.add_trace(go.Bar(
            x=pts_df["jornada_num"], y=pts_df["puntos"],
            name="Puntos", marker_color=color, opacity=0.5,
        ))
        fig_evo.add_trace(go.Scatter(
            x=pts_df["jornada_num"], y=pts_df["media_movil"],
            name="Media móvil (5)", line=dict(color="#FF5722", width=3),
        ))
        fig_evo.update_layout(
            xaxis_title="Jornada", yaxis_title="Puntos",
            xaxis=dict(dtick=1), height=350,
        )
        st.plotly_chart(apply_standard_layout(fig_evo), use_container_width=True)

    # Four Factors comparativo (equipo vs liga)
    st.markdown("---")
    st.subheader("Four Factors (equipo vs media de liga)")

    ff_team_list = []
    for _, game_row in team_games.iterrows():
        ff = four_factors(game_row.to_dict())
        ff_team_list.append(ff)

    if ff_team_list:
        ff_df = pd.DataFrame(ff_team_list)
        ff_avg = ff_df.mean()

        # Liga averages
        all_ff = []
        for _, game_row in team_stats.iterrows():
            all_ff.append(four_factors(game_row.to_dict()))
        league_ff = pd.DataFrame(all_ff).mean()

        factors = ["eFG%", "TOV%", "OREB%", "FT_rate"]
        fig_ff = go.Figure()
        fig_ff.add_trace(go.Bar(
            name=selected_team, x=factors,
            y=[ff_avg[f] for f in factors],
            marker_color=color,
        ))
        fig_ff.add_trace(go.Bar(
            name="Media Liga", x=factors,
            y=[league_ff[f] for f in factors],
            marker_color="#9E9E9E",
        ))
        fig_ff.update_layout(
            barmode="group", height=350,
            title="Four Factors: Equipo vs Liga",
            yaxis_title="%",
        )
        st.plotly_chart(apply_standard_layout(fig_ff), use_container_width=True)

with tab_def:
    st.subheader("Perfil defensivo")

    styled_metric_row([
        {"label": "Robos/p", "value": f"{team_row['robos_avg']:.1f}",
         "delta": team_row['robos_avg'] - league_avgs['rob']},
        {"label": "Tapones/p", "value": f"{team_row['tapones_favor_avg']:.1f}"},
        {"label": "Reb. def/p", "value": f"{team_row['rebotes_defensivos_avg']:.1f}"},
        {"label": "Faltas/p", "value": f"{team_row['faltas_cometidas_avg']:.1f}"},
    ])

    if not team_adv_sel.empty:
        st.markdown("---")
        st.subheader("DRtg y NetRtg por partido")
        team_adv_sorted = team_adv_sel.merge(
            game_info[["id_partido", "jornada_num"]], on="id_partido"
        ).sort_values("jornada_num")

        fig_ratings = go.Figure()
        fig_ratings.add_trace(go.Scatter(
            x=team_adv_sorted["jornada_num"], y=team_adv_sorted["drtg"],
            name="DRtg", line=dict(color="#F44336", width=2), mode="lines+markers",
        ))
        fig_ratings.add_trace(go.Scatter(
            x=team_adv_sorted["jornada_num"], y=team_adv_sorted["net_rtg"],
            name="NetRtg", line=dict(color=color, width=2), mode="lines+markers",
        ))
        fig_ratings.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig_ratings.update_layout(
            xaxis_title="Jornada", yaxis_title="Rating",
            xaxis=dict(dtick=1), height=400,
        )
        st.plotly_chart(apply_standard_layout(fig_ratings), use_container_width=True)

    # Scatter: Robos vs Tapones (todos los equipos)
    st.markdown("---")
    st.subheader("Robos vs Tapones (todos los equipos)")
    team_avgs = aggregate_team_season(team_stats)
    fig_def = scatter_chart(
        team_avgs,
        x_col="robos_avg", y_col="tapones_favor_avg",
        label_col="equipo",
        title="Robos vs Tapones por partido",
        x_label="Robos/partido", y_label="Tapones/partido",
    )
    st.plotly_chart(apply_standard_layout(fig_def), use_container_width=True)

with tab_results:
    # Rachas
    st.subheader("Rachas y resultados")

    results = []
    for _, g in team_game_info.iterrows():
        is_local = g["local"] == selected_team
        oponente = g["visitante"] if is_local else g["local"]
        pf = g["resultado_local"] if is_local else g["resultado_visitante"]
        pc = g["resultado_visitante"] if is_local else g["resultado_local"]
        w = pf > pc
        results.append({
            "Jornada": g["jornada_num"],
            "Fecha": g["fecha"],
            "Sede": "Casa" if is_local else "Fuera",
            "Oponente": oponente,
            "PF": pf,
            "PC": pc,
            "Resultado": "V" if w else "D",
            "Dif": pf - pc,
        })

    if results:
        results_df = pd.DataFrame(results)

        # Calcular rachas
        results_list = results_df["Resultado"].tolist()
        current_streak = 1
        for i in range(1, len(results_list)):
            if results_list[i] == results_list[i-1]:
                current_streak += 1
            else:
                current_streak = 1

        streak_type = results_list[-1] if results_list else ""
        current_streak_str = f"{current_streak}{streak_type}"

        # Racha más larga de victorias
        max_w_streak = 0
        curr = 0
        for r in results_list:
            if r == "V":
                curr += 1
                max_w_streak = max(max_w_streak, curr)
            else:
                curr = 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Racha actual", current_streak_str)
        col2.metric("Mejor racha de V", f"{max_w_streak}V")

        # Casa vs Fuera
        home = results_df[results_df["Sede"] == "Casa"]
        away = results_df[results_df["Sede"] == "Fuera"]
        home_w = (home["Resultado"] == "V").sum()
        away_w = (away["Resultado"] == "V").sum()
        col3.metric("Casa/Fuera", f"{home_w}-{len(home)-home_w} / {away_w}-{len(away)-away_w}")

        st.markdown("---")

        # Tabla de resultados con color
        st.subheader("Resultados partido a partido")
        st.dataframe(results_df, use_container_width=True, hide_index=True)

        # Histograma de márgenes
        st.markdown("---")
        st.subheader("Distribución de márgenes")
        fig_margins = px.histogram(
            results_df, x="Dif", nbins=15,
            color="Resultado",
            color_discrete_map={"V": "#4CAF50", "D": "#F44336"},
            title="Distribución de diferencia de puntos",
            labels={"Dif": "Diferencia (PF-PC)", "count": "Partidos"},
        )
        fig_margins.update_layout(height=300)
        st.plotly_chart(apply_standard_layout(fig_margins), use_container_width=True)

    # Parciales por cuarto (heatmap)
    st.markdown("---")
    st.subheader("Parciales por cuarto")

    quarter_data = []
    for _, g in team_game_info.iterrows():
        is_local = g["local"] == selected_team
        parciales_str = g["parciales_local"] if is_local else g["parciales_visitante"]
        try:
            parciales = [int(x) for x in str(parciales_str).split(",")]
            row = {"jornada_num": g["jornada_num"]}
            for i, p in enumerate(parciales):
                row[f"{i+1}C"] = p
            quarter_data.append(row)
        except (ValueError, AttributeError):
            continue

    if quarter_data:
        qdf = pd.DataFrame(quarter_data).set_index("jornada_num")
        fig_heatmap = quarter_heatmap(qdf, selected_team)
        st.plotly_chart(apply_standard_layout(fig_heatmap), use_container_width=True)

with tab_players:
    st.subheader(f"Roster - {selected_team}")

    team_player_stats = player_stats[player_stats["equipo"] == selected_team]
    season = aggregate_player_season(team_player_stats)

    if not season.empty:
        display = season[[
            "nombre", "partidos", "titularidades", "minutos_decimal_avg",
            "puntos_avg", "rebotes_totales_avg", "asistencias_avg",
            "robos_avg", "perdidas_avg", "valoracion_avg",
            "t2_pct", "t3_pct", "tl_pct",
        ]].copy()
        display.columns = [
            "Jugador", "PJ", "Tit", "Min", "Pts", "Reb", "Ast",
            "Rob", "Pér", "Val", "T2%", "T3%", "TL%",
        ]
        for col in ["Min", "Pts", "Reb", "Ast", "Rob", "Pér", "Val", "T2%", "T3%", "TL%"]:
            display[col] = display[col].round(1)
        display = display.sort_values("Min", ascending=False)

        # Destacar líderes
        max_scorer = display.loc[display["Pts"].idxmax(), "Jugador"]
        max_rebounder = display.loc[display["Reb"].idxmax(), "Jugador"]
        max_assists = display.loc[display["Ast"].idxmax(), "Jugador"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Máx. anotador", max_scorer, f"{display.loc[display['Pts'].idxmax(), 'Pts']:.1f} pts")
        col2.metric("Máx. reboteador", max_rebounder, f"{display.loc[display['Reb'].idxmax(), 'Reb']:.1f} reb")
        col3.metric("Máx. asistente", max_assists, f"{display.loc[display['Ast'].idxmax(), 'Ast']:.1f} ast")

        st.markdown("")
        st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos de jugadores para este equipo.")
