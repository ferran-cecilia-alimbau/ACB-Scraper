"""Página de partido: box score + Four Factors + PBP análisis completo."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.data_loader import load_game_info, load_team_stats, load_player_stats
from src.metrics import four_factors
from src.charts import get_team_color, apply_standard_layout, inject_custom_css, game_selector, styled_header
from src.pbp_bridge import (
    load_and_analyze_game, shooting_by_game_state, shooting_by_quarter,
    foul_distribution_by_time, fouls_by_team_and_quarter,
    substitution_impact, count_possessions_by_team,
    create_score_diff_timeline, create_score_evolution,
    detect_scoring_runs,
)

st.set_page_config(page_title="Partido - ACB", layout="wide")
inject_custom_css()
styled_header("Análisis de Partido", "Box score, Four Factors y play-by-play")

game_info = load_game_info()
team_stats = load_team_stats()
player_stats = load_player_stats()

# Selector de partido
game_id, game = game_selector(game_info, key="partido_selector")
local = game["local"]
visitante = game["visitante"]

# --- Header ---
st.markdown(f"### {local} {game['resultado_local']} - {game['resultado_visitante']} {visitante}")
col1, col2, col3 = st.columns(3)
col1.metric("Jornada", game["jornada_num"])
col2.metric("Fecha", game["fecha"])
col3.metric("Pabellón", game["pabellon"])

# Parciales
st.markdown("**Parciales:**")
try:
    parc_local = [int(x.strip()) for x in str(game["parciales_local"]).split(",")]
    parc_visit = [int(x.strip()) for x in str(game["parciales_visitante"]).split(",")]
    quarters = [f"{i+1}C" for i in range(len(parc_local))]
    parc_df = pd.DataFrame({
        "Cuarto": quarters + ["Total"],
        local: parc_local + [sum(parc_local)],
        visitante: parc_visit + [sum(parc_visit)],
    })
    st.dataframe(parc_df, use_container_width=True, hide_index=True)
except (ValueError, AttributeError):
    pass

st.markdown("---")

# --- Box Score ---
st.subheader("Box Score")

tab_local, tab_visit = st.tabs([local, visitante])

for tab, team_name in [(tab_local, local), (tab_visit, visitante)]:
    with tab:
        team_players = player_stats[
            (player_stats["id_partido"] == game_id) & (player_stats["equipo"] == team_name)
        ].copy()

        if not team_players.empty:
            team_players = team_players.sort_values(
                ["es_titular", "minutos_decimal"], ascending=[False, False]
            )

            display_cols = [
                "nombre", "minutos", "puntos",
                "t2_anotados", "t2_intentados",
                "t3_anotados", "t3_intentados",
                "tl_anotados", "tl_intentados",
                "rebotes_totales", "asistencias", "robos", "perdidas",
                "tapones_favor", "faltas_cometidas", "plus_minus", "valoracion",
            ]
            available = [c for c in display_cols if c in team_players.columns]

            rename_map = {
                "nombre": "Jugador", "minutos": "Min", "puntos": "Pts",
                "t2_anotados": "T2M", "t2_intentados": "T2A",
                "t3_anotados": "T3M", "t3_intentados": "T3A",
                "tl_anotados": "TLM", "tl_intentados": "TLA",
                "rebotes_totales": "Reb", "asistencias": "Ast",
                "robos": "Rob", "perdidas": "Pér",
                "tapones_favor": "Tap", "faltas_cometidas": "FP",
                "plus_minus": "+/-", "valoracion": "Val",
            }

            st.dataframe(
                team_players[available].rename(columns=rename_map),
                use_container_width=True,
                hide_index=True,
            )

st.markdown("---")

# --- Four Factors ---
st.subheader("Four Factors de Dean Oliver")

game_team_stats = team_stats[team_stats["id_partido"] == game_id]
if len(game_team_stats) == 2:
    local_stats = game_team_stats[game_team_stats["equipo"] == local].iloc[0]
    visit_stats = game_team_stats[game_team_stats["equipo"] == visitante].iloc[0]

    ff_local = four_factors(local_stats.to_dict())
    ff_visit = four_factors(visit_stats.to_dict())

    ff_display = pd.DataFrame({
        "Factor": ["eFG%", "TOV%", "OREB%", "FT Rate"],
        local: [ff_local["eFG%"], ff_local["TOV%"], ff_local["OREB%"], ff_local["FT_rate"]],
        visitante: [ff_visit["eFG%"], ff_visit["TOV%"], ff_visit["OREB%"], ff_visit["FT_rate"]],
    })
    ff_display[local] = ff_display[local].round(1)
    ff_display[visitante] = ff_display[visitante].round(1)
    st.dataframe(ff_display, use_container_width=True, hide_index=True)

st.markdown("---")

# --- PBP Analysis ---
st.subheader("Análisis Play-by-Play")

with st.spinner("Cargando datos play-by-play..."):
    analysis = load_and_analyze_game(game_id)

if analysis is None:
    st.info("No hay datos play-by-play para este partido.")
else:
    pbp = analysis["pbp"]
    runs = analysis["runs"]

    # PBP Tabs
    tab_timeline, tab_shooting, tab_poss, tab_fouls, tab_subs = st.tabs([
        "Timeline", "Tiro por contexto", "Posesiones", "Faltas", "Sustituciones"
    ])

    # --- Tab Timeline ---
    with tab_timeline:
        fig_diff = create_score_diff_timeline(pbp, local, visitante, runs)
        st.plotly_chart(apply_standard_layout(fig_diff), use_container_width=True)

        fig_score = create_score_evolution(pbp, local, visitante)
        st.plotly_chart(apply_standard_layout(fig_score), use_container_width=True)

        if runs:
            st.markdown("**Rachas detectadas (>=6-0):**")
            for run in runs:
                team_name = local if run["team"] == "LOCAL" else visitante
                mins = run["start_sec"] / 60
                st.write(
                    f"- **{run['points']}-0** de {team_name} "
                    f"(min {mins:.1f}, marcador {run['start_score_local']}-{run['start_score_visitante']} "
                    f"→ {run['end_score_local']}-{run['end_score_visitante']})"
                )

    # --- Tab Shooting ---
    with tab_shooting:
        st.markdown("##### Tiro por estado del marcador")
        shot_state = shooting_by_game_state(pbp)
        if not shot_state.empty:
            # Resolve team names
            team_map = {"LOCAL": local, "VISITANTE": visitante}
            shot_state["equipo"] = shot_state["equipo_nombre"].map(
                lambda x: team_map.get(x, x)
            )

            for team in [local, visitante]:
                team_data = shot_state[shot_state["equipo"] == team]
                if team_data.empty:
                    continue

                st.markdown(f"**{team}**")
                fig = go.Figure()
                states = ["Ganando", "Empatado", "Perdiendo"]
                for state in states:
                    row = team_data[team_data["game_state"] == state]
                    if row.empty:
                        continue
                    r = row.iloc[0]
                    t2_pct = r.get("t2_pct", 0)
                    t3_pct = r.get("t3_pct", 0)
                    fig.add_trace(go.Bar(
                        name=f"T2% {state}", x=[state], y=[t2_pct if pd.notna(t2_pct) else 0],
                        marker_color=get_team_color(team),
                        opacity=0.7,
                    ))
                    fig.add_trace(go.Bar(
                        name=f"T3% {state}", x=[state], y=[t3_pct if pd.notna(t3_pct) else 0],
                        marker_color=get_team_color(team, secondary=True),
                        opacity=0.7,
                    ))

                fig.update_layout(
                    barmode="group", height=300,
                    title=f"{team} - % de tiro por game state",
                    yaxis_title="% de tiro",
                )
                st.plotly_chart(apply_standard_layout(fig), use_container_width=True)

        st.markdown("---")
        st.markdown("##### Tiro por cuarto")
        shot_quarter = shooting_by_quarter(pbp)
        if not shot_quarter.empty:
            shot_quarter["equipo"] = shot_quarter["equipo_nombre"].map(
                lambda x: team_map.get(x, x)
            )
            for team in [local, visitante]:
                team_data = shot_quarter[shot_quarter["equipo"] == team]
                if team_data.empty:
                    continue
                fig_q = go.Figure()
                fig_q.add_trace(go.Bar(
                    name="T2", x=team_data["periodo"], y=team_data["t2_attempts"],
                    marker_color=get_team_color(team),
                ))
                fig_q.add_trace(go.Bar(
                    name="T3", x=team_data["periodo"], y=team_data["t3_attempts"],
                    marker_color=get_team_color(team, secondary=True),
                ))
                fig_q.update_layout(
                    barmode="stack", height=300,
                    title=f"{team} - Intentos de tiro por cuarto",
                    yaxis_title="Intentos",
                )
                st.plotly_chart(apply_standard_layout(fig_q), use_container_width=True)

    # --- Tab Posesiones ---
    with tab_poss:
        possessions = analysis["possessions"]
        possessions_df = analysis["possessions_df"]

        if not possessions_df.empty:
            poss_counts = count_possessions_by_team(possessions)
            col1, col2 = st.columns(2)
            col1.metric(f"Posesiones {local}", poss_counts.get("LOCAL", 0))
            col2.metric(f"Posesiones {visitante}", poss_counts.get("VISITANTE", 0))

            # Puntos por posesión
            for side, team in [("LOCAL", local), ("VISITANTE", visitante)]:
                side_poss = possessions_df[possessions_df["team"] == side]
                if not side_poss.empty:
                    ppp = side_poss["points_scored"].sum() / len(side_poss)
                    st.metric(f"Pts/posesión {team}", f"{ppp:.2f}")

            st.markdown("---")
            st.markdown("##### Cómo terminan las posesiones")

            for side, team in [("LOCAL", local), ("VISITANTE", visitante)]:
                side_poss = possessions_df[possessions_df["team"] == side]
                if side_poss.empty:
                    continue

                ended_by = side_poss["ended_by"].value_counts()
                labels_map = {
                    "field_goal": "Canasta", "turnover": "Pérdida",
                    "defensive_rebound": "Reb. Defensivo rival", "free_throw": "Tiros libres",
                    "end_period": "Fin de periodo",
                }
                labels = [labels_map.get(k, k) for k in ended_by.index]

                fig_donut = go.Figure(go.Pie(
                    labels=labels, values=ended_by.values,
                    hole=0.4, textinfo="label+percent",
                ))
                fig_donut.update_layout(
                    title=f"{team} - Fin de posesiones",
                    height=350,
                )
                st.plotly_chart(apply_standard_layout(fig_donut), use_container_width=True)

    # --- Tab Faltas ---
    with tab_fouls:
        st.markdown("##### Distribución temporal de faltas")
        foul_dist = foul_distribution_by_time(pbp)
        if not foul_dist.empty:
            team_map_fouls = {"LOCAL": local, "VISITANTE": visitante}
            foul_dist["equipo_nombre"] = foul_dist["equipo"].map(team_map_fouls).fillna(foul_dist["equipo"])

            fig_fouls = px.bar(
                foul_dist.groupby(["interval", "equipo_nombre"])["count"].sum().reset_index(),
                x="interval", y="count", color="equipo_nombre",
                barmode="group",
                title="Faltas por intervalo de 2 minutos",
                labels={"interval": "Minuto", "count": "Faltas", "equipo_nombre": "Equipo"},
                color_discrete_map={local: get_team_color(local), visitante: get_team_color(visitante)},
            )
            fig_fouls.update_layout(height=350)
            st.plotly_chart(apply_standard_layout(fig_fouls), use_container_width=True)

        st.markdown("---")
        st.markdown("##### Faltas por equipo y cuarto")
        fouls_quarter = fouls_by_team_and_quarter(pbp)
        if not fouls_quarter.empty:
            fig_fq = px.bar(
                fouls_quarter, x="periodo", y="fouls", color="equipo_nombre",
                barmode="group",
                title="Faltas por cuarto",
                labels={"periodo": "Periodo", "fouls": "Faltas", "equipo_nombre": "Equipo"},
            )
            fig_fq.update_layout(height=350)
            st.plotly_chart(apply_standard_layout(fig_fq), use_container_width=True)

    # --- Tab Sustituciones ---
    with tab_subs:
        st.markdown("##### Timeline de cambios")
        impacts = substitution_impact(pbp)
        if impacts:
            impacts_df = pd.DataFrame(impacts)
            team_map_subs = {"LOCAL": local, "VISITANTE": visitante}
            impacts_df["equipo_nombre"] = impacts_df["team"].map(team_map_subs)

            # Timeline scatter
            fig_subs = go.Figure()
            for team_side, team_name in [("LOCAL", local), ("VISITANTE", visitante)]:
                team_subs = impacts_df[impacts_df["team"] == team_side]
                fig_subs.add_trace(go.Scatter(
                    x=team_subs["sub_time"] / 60,
                    y=team_subs["impact"],
                    mode="markers",
                    name=team_name,
                    marker=dict(
                        color=get_team_color(team_name),
                        size=10,
                        symbol="diamond",
                    ),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b> entra<br>"
                        "%{customdata[1]} sale<br>"
                        "Min: %{x:.1f}<br>"
                        "Impacto +/-: %{y:+d}<extra></extra>"
                    ),
                    customdata=list(zip(team_subs["player_in"], team_subs["player_out"])),
                ))

            fig_subs.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig_subs.update_layout(
                title="Impacto de sustituciones (+/- después vs antes)",
                xaxis_title="Minuto", yaxis_title="Impacto +/-",
                height=400,
            )
            st.plotly_chart(apply_standard_layout(fig_subs), use_container_width=True)

            # Tabla de impactos
            display = impacts_df[[
                "equipo_nombre", "player_in", "player_out", "sub_time",
                "pm_before", "pm_after", "impact"
            ]].copy()
            display["sub_time"] = (display["sub_time"] / 60).round(1)
            display = display.rename(columns={
                "equipo_nombre": "Equipo", "player_in": "Entra",
                "player_out": "Sale", "sub_time": "Minuto",
                "pm_before": "+/- antes", "pm_after": "+/- después",
                "impact": "Impacto",
            })
            display = display.sort_values("Minuto")
            st.dataframe(display, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de sustituciones.")
