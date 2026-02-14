"""Funciones reutilizables de gráficos Plotly para el dashboard."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import streamlit as st

from .constants import TEAM_COLORS, RADAR_CATEGORIES


def get_team_color(team: str, secondary: bool = False) -> str:
    """Obtiene color de equipo."""
    colors = TEAM_COLORS.get(team, ("#1f77b4", "#aec7e8"))
    return colors[1] if secondary else colors[0]


# --- Radar Charts ---

def player_radar_chart(
    player_data: dict,
    player_name: str,
    categories: list[str] = None,
) -> go.Figure:
    """Crea radar chart para un jugador.

    Args:
        player_data: Dict con valores normalizados (0-100) para cada categoría
        player_name: Nombre del jugador
        categories: Lista de nombres de ejes (default: RADAR_CATEGORIES)
    """
    if categories is None:
        categories = RADAR_CATEGORIES

    values = [player_data.get(cat, 0) for cat in categories]
    values.append(values[0])  # Cerrar el polígono
    cats = categories + [categories[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=cats,
        fill="toself",
        name=player_name,
        fillcolor="rgba(31, 119, 180, 0.3)",
        line=dict(color="#1f77b4", width=2),
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        title=f"Perfil de {player_name}",
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def comparison_radar_chart(
    player1_data: dict,
    player1_name: str,
    player2_data: dict,
    player2_name: str,
    team1: str = "",
    team2: str = "",
    categories: list[str] = None,
) -> go.Figure:
    """Radar chart con dos jugadores superpuestos."""
    if categories is None:
        categories = RADAR_CATEGORIES

    color1 = get_team_color(team1) if team1 else "#1f77b4"
    color2 = get_team_color(team2) if team2 else "#ff7f0e"

    fig = go.Figure()

    for data, name, color in [
        (player1_data, player1_name, color1),
        (player2_data, player2_name, color2),
    ]:
        values = [data.get(cat, 0) for cat in categories]
        values.append(values[0])
        cats = categories + [categories[0]]

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=cats,
            fill="toself",
            name=name,
            fillcolor=f"rgba{_hex_to_rgba(color, 0.2)}",
            line=dict(color=color, width=2),
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        title=f"{player1_name} vs {player2_name}",
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


# --- Bar Charts ---

def shooting_breakdown_chart(
    team_data: pd.Series, team_name: str
) -> go.Figure:
    """Barras apiladas de T2/T3/TL para un equipo."""
    fig = go.Figure()

    categories = ["T2", "T3", "TL"]
    made_key = "t2_encestados" if "t2_encestados" in team_data.index else "t2_anotados"
    made = [
        team_data.get(made_key, 0),
        team_data.get("t3_encestados", team_data.get("t3_anotados", 0)),
        team_data.get("tl_encestados", team_data.get("tl_anotados", 0)),
    ]
    attempted = [
        team_data.get("t2_intentados", 0),
        team_data.get("t3_intentados", 0),
        team_data.get("tl_intentados", 0),
    ]
    missed = [a - m for a, m in zip(attempted, made)]

    fig.add_trace(go.Bar(name="Anotados", x=categories, y=made, marker_color="#4CAF50"))
    fig.add_trace(go.Bar(name="Fallados", x=categories, y=missed, marker_color="#F44336"))

    fig.update_layout(
        barmode="stack",
        title=f"{team_name} - Desglose de tiro",
        yaxis_title="Intentos",
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def butterfly_chart(
    data1: dict, name1: str,
    data2: dict, name2: str,
    categories: list[str],
    team1: str = "", team2: str = "",
) -> go.Figure:
    """Butterfly chart (barras divergentes desde 0) para comparar dos entidades."""
    color1 = get_team_color(team1) if team1 else "#1f77b4"
    color2 = get_team_color(team2) if team2 else "#ff7f0e"

    vals1 = [-data1.get(cat, 0) for cat in categories]
    vals2 = [data2.get(cat, 0) for cat in categories]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=categories, x=vals1, orientation="h",
        name=name1, marker_color=color1,
        text=[f"{abs(v):.1f}" for v in vals1],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        y=categories, x=vals2, orientation="h",
        name=name2, marker_color=color2,
        text=[f"{v:.1f}" for v in vals2],
        textposition="outside",
    ))

    max_val = max(max(abs(v) for v in vals1), max(abs(v) for v in vals2)) * 1.3
    fig.update_layout(
        barmode="overlay",
        xaxis=dict(range=[-max_val, max_val], title=""),
        title=f"{name1} vs {name2}",
        height=max(350, len(categories) * 40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


# --- Line Charts ---

def evolution_line_chart(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: str = None,
    title: str = "",
    y_label: str = "",
    invert_y: bool = False,
) -> go.Figure:
    """Gráfico de líneas genérico para evolución temporal."""
    if color_col:
        fig = px.line(
            data, x=x_col, y=y_col, color=color_col,
            title=title, labels={y_col: y_label, x_col: "Jornada"},
        )
        # Aplicar colores de equipo si es posible
        for trace in fig.data:
            color = get_team_color(trace.name)
            trace.line.color = color
    else:
        fig = px.line(data, x=x_col, y=y_col, title=title)

    if invert_y:
        fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(dtick=1),
    )

    return fig


def player_evolution_chart(
    game_log: pd.DataFrame,
    stat_col: str,
    player_name: str,
    rolling_window: int = 5,
) -> go.Figure:
    """Línea temporal de una estadística de jugador con media móvil."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=game_log["jornada_num"],
        y=game_log[stat_col],
        mode="lines+markers",
        name=stat_col.replace("_", " ").title(),
        line=dict(color="#1f77b4", width=1),
        marker=dict(size=6),
        opacity=0.6,
    ))

    if len(game_log) >= rolling_window:
        rolling = game_log[stat_col].rolling(window=rolling_window, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=game_log["jornada_num"],
            y=rolling,
            mode="lines",
            name=f"Media móvil ({rolling_window})",
            line=dict(color="#FF5722", width=3),
        ))

    fig.update_layout(
        title=f"{player_name} - {stat_col.replace('_', ' ').title()}",
        xaxis_title="Jornada",
        yaxis_title=stat_col.replace("_", " ").title(),
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(dtick=1),
    )

    return fig


# --- Heatmap ---

def quarter_heatmap(data: pd.DataFrame, team_name: str = "") -> go.Figure:
    """Heatmap de parciales por cuarto para un equipo.

    Args:
        data: DataFrame con jornada_num como filas y cuartos como columnas
        team_name: Nombre del equipo
    """
    fig = go.Figure(data=go.Heatmap(
        z=data.values,
        x=data.columns.tolist(),
        y=[f"J{j}" for j in data.index],
        colorscale="RdYlGn",
        text=data.values,
        texttemplate="%{text}",
        textfont={"size": 11},
        hovertemplate="Jornada %{y}<br>%{x}: %{z} pts<extra></extra>",
    ))

    title = "Parciales por cuarto"
    if team_name:
        title = f"{team_name} - {title}"

    fig.update_layout(
        title=title,
        xaxis_title="Cuarto",
        yaxis_title="Jornada",
        height=max(350, len(data) * 25 + 100),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


# --- Scatter ---

def scatter_chart(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    label_col: str = None,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    add_mean_lines: bool = True,
) -> go.Figure:
    """Scatter plot genérico con etiquetas opcionales."""
    fig = go.Figure()

    # Color por equipo si hay columna 'equipo'
    if "equipo" in data.columns:
        for _, row in data.iterrows():
            color = get_team_color(row["equipo"])
            label = row[label_col] if label_col else ""
            fig.add_trace(go.Scatter(
                x=[row[x_col]],
                y=[row[y_col]],
                mode="markers+text",
                text=[label],
                textposition="top center",
                marker=dict(color=color, size=12),
                showlegend=False,
                hovertemplate=f"<b>{label}</b><br>{x_label}: %{{x:.1f}}<br>{y_label}: %{{y:.1f}}<extra></extra>",
            ))
    else:
        fig.add_trace(go.Scatter(
            x=data[x_col],
            y=data[y_col],
            mode="markers+text",
            text=data[label_col] if label_col else None,
            textposition="top center",
            marker=dict(size=10),
        ))

    if add_mean_lines:
        fig.add_hline(y=data[y_col].mean(), line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(x=data[x_col].mean(), line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title=title,
        xaxis_title=x_label or x_col,
        yaxis_title=y_label or y_col,
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


# --- Helpers ---

def inject_custom_css():
    """Inyecta CSS personalizado para el dashboard con tema oscuro premium."""
    st.markdown("""
    <style>
    /* ===== Variables centralizadas ===== */
    :root {
        --acb-accent: #E8792B;
        --acb-accent-muted: rgba(232, 121, 43, 0.25);
        --acb-accent-subtle: rgba(232, 121, 43, 0.10);
        --acb-surface: #1A1D24;
        --acb-surface-hover: #22262E;
        --acb-border: rgba(250, 250, 250, 0.08);
        --acb-border-accent: rgba(232, 121, 43, 0.35);
        --acb-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        --acb-shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.4);
        --acb-radius: 8px;
        --acb-transition: all 0.2s ease;
    }

    /* ===== Metric cards ===== */
    [data-testid="stMetric"] {
        background: var(--acb-surface);
        border-radius: var(--acb-radius);
        padding: 14px 18px;
        border-left: 3px solid var(--acb-accent);
        border: 1px solid var(--acb-border);
        border-left: 3px solid var(--acb-accent);
        box-shadow: var(--acb-shadow);
        transition: var(--acb-transition);
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-1px);
        box-shadow: var(--acb-shadow-hover);
        border-color: var(--acb-border-accent);
    }
    [data-testid="stMetric"] [data-testid="stMetricLabel"] {
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.75rem;
        opacity: 0.7;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.4rem;
        font-weight: 700;
    }
    [data-testid="stMetric"] [data-testid="stMetricDelta"] {
        font-size: 0.8rem;
    }

    /* ===== Tabs ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid var(--acb-border);
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 6px 6px 0 0;
        font-weight: 500;
        transition: var(--acb-transition);
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: var(--acb-surface-hover);
    }
    .stTabs [aria-selected="true"] {
        border-bottom: 2px solid var(--acb-accent) !important;
        font-weight: 600;
    }

    /* ===== Headers ===== */
    h2 {
        border-bottom: 2px solid var(--acb-accent-muted);
        padding-bottom: 8px;
        margin-bottom: 16px;
    }
    h3 {
        color: var(--acb-accent);
    }

    /* ===== DataFrames ===== */
    [data-testid="stDataFrame"] {
        border-radius: var(--acb-radius);
        border: 1px solid var(--acb-border);
        overflow: hidden;
    }

    /* ===== Sidebar ===== */
    [data-testid="stSidebar"] {
        border-right: 1px solid var(--acb-border);
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label {
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 0.78rem;
        opacity: 0.8;
    }

    /* ===== Dividers (st.markdown("---")) ===== */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(
            90deg,
            transparent,
            var(--acb-accent-muted),
            transparent
        );
        margin: 24px 0;
    }

    /* ===== Widgets (selectbox, multiselect) ===== */
    [data-baseweb="select"] > div {
        border-radius: 6px !important;
    }
    [data-baseweb="select"] > div:focus-within {
        border-color: var(--acb-accent) !important;
        box-shadow: 0 0 0 1px var(--acb-accent-muted) !important;
    }

    /* ===== Expanders ===== */
    [data-testid="stExpander"] {
        border: 1px solid var(--acb-border);
        border-radius: var(--acb-radius);
    }
    [data-testid="stExpander"]:hover {
        border-color: var(--acb-border-accent);
    }

    /* ===== Scrollbar ===== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(250, 250, 250, 0.12);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(250, 250, 250, 0.2);
    }

    /* ===== Styled header component ===== */
    .acb-header {
        margin-bottom: 24px;
        padding-bottom: 12px;
        border-bottom: 2px solid var(--acb-accent);
    }
    .acb-header h1 {
        font-weight: 800;
        font-size: 2rem;
        margin: 0;
        padding: 0;
        border: none;
    }
    .acb-header .subtitle {
        color: rgba(250, 250, 250, 0.5);
        font-size: 0.95rem;
        margin-top: 4px;
    }

    /* ===== Game cards ===== */
    .acb-game-card {
        background: var(--acb-surface);
        border-radius: var(--acb-radius);
        padding: 14px 16px;
        border: 1px solid var(--acb-border);
        box-shadow: var(--acb-shadow);
        transition: var(--acb-transition);
        margin-bottom: 6px;
    }
    .acb-game-card:hover {
        box-shadow: var(--acb-shadow-hover);
        border-color: var(--acb-border-accent);
    }
    .acb-game-card .team-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 3px 0;
    }
    .acb-game-card .team-name {
        font-size: 0.92rem;
    }
    .acb-game-card .team-score {
        font-size: 1rem;
        min-width: 30px;
        text-align: right;
    }
    .acb-game-card .winner {
        font-weight: 700;
    }

    /* ===== Sidebar header ===== */
    .acb-sidebar-header {
        text-align: center;
        padding: 10px 0 16px;
        margin-bottom: 16px;
        border-bottom: 1px solid var(--acb-border);
    }
    .acb-sidebar-header .logo-text {
        font-size: 2rem;
        font-weight: 800;
        color: var(--acb-accent);
        letter-spacing: 0.1em;
    }
    .acb-sidebar-header .logo-subtitle {
        font-size: 0.82rem;
        color: rgba(250, 250, 250, 0.5);
        margin-top: 2px;
    }
    </style>
    """, unsafe_allow_html=True)


def apply_standard_layout(fig: go.Figure) -> go.Figure:
    """Aplica layout Plotly dark theme consistente a todas las figuras."""
    fig.update_layout(
        template="plotly_dark",
        font=dict(family="Inter, sans-serif", size=12, color="rgba(250,250,250,0.85)"),
        margin=dict(l=40, r=20, t=50, b=40),
        hoverlabel=dict(
            bgcolor="rgba(26,29,36,0.95)",
            bordercolor="rgba(232,121,43,0.5)",
            font=dict(size=12, color="#FAFAFA"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(250,250,250,0.1)",
            borderwidth=1,
            font=dict(size=11, color="rgba(250,250,250,0.8)"),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis=dict(
            gridcolor="rgba(250,250,250,0.06)",
            zerolinecolor="rgba(250,250,250,0.12)",
        ),
        yaxis=dict(
            gridcolor="rgba(250,250,250,0.06)",
            zerolinecolor="rgba(250,250,250,0.12)",
        ),
        title=dict(
            font=dict(size=14, color="rgba(250,250,250,0.9)"),
            x=0,
            xanchor="left",
        ),
    )
    return fig


def styled_metric_row(metrics: list[dict]):
    """Renderiza una fila de métricas con delta vs media de liga.

    Args:
        metrics: lista de dicts con keys: label, value, delta (opcional), suffix (opcional)
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        delta = m.get("delta")
        suffix = m.get("suffix", "")
        value = f"{m['value']}{suffix}" if suffix else m["value"]
        if delta is not None:
            delta_str = f"{delta:+.1f}{suffix}" if isinstance(delta, float) else str(delta)
            col.metric(m["label"], value, delta_str)
        else:
            col.metric(m["label"], value)


def player_stint_gantt_chart(
    stints_df: pd.DataFrame, side: str, team_name: str = ""
) -> go.Figure:
    """Gantt horizontal de stints por jugador, coloreado por +/- del stint.

    Args:
        stints_df: DataFrame de stints (de lineup_tracker)
        side: 'local' o 'visitante'
        team_name: Nombre del equipo para título
    """
    lineup_key = f"lineup_{side}"
    pm_key = "plus_minus_local" if side == "local" else None

    records = []
    for _, stint in stints_df.iterrows():
        lineup = stint[lineup_key]
        start_min = stint["start_sec"] / 60
        end_min = stint["end_sec"] / 60
        if pm_key and pm_key in stint.index:
            pm = stint[pm_key]
        else:
            if side == "visitante":
                pm = -stint.get("plus_minus_local", 0)
            else:
                pm = stint.get("plus_minus_local", 0)
        for player in lineup:
            records.append({
                "Jugador": player,
                "Inicio": start_min,
                "Fin": end_min,
                "+/-": pm,
            })

    if not records:
        return go.Figure()

    df = pd.DataFrame(records)
    players = sorted(df["Jugador"].unique())

    fig = go.Figure()
    for _, row in df.iterrows():
        color = "#4CAF50" if row["+/-"] >= 0 else "#F44336"
        opacity = min(0.3 + abs(row["+/-"]) * 0.07, 1.0)
        fig.add_trace(go.Bar(
            y=[row["Jugador"]],
            x=[row["Fin"] - row["Inicio"]],
            base=[row["Inicio"]],
            orientation="h",
            marker=dict(color=color, opacity=opacity),
            hovertemplate=(
                f"<b>{row['Jugador']}</b><br>"
                f"Min {row['Inicio']:.1f}-{row['Fin']:.1f}<br>"
                f"+/-: {row['+/-']:+d}<extra></extra>"
            ),
            showlegend=False,
        ))

    # Quarter markers
    for q in [10, 20, 30]:
        fig.add_vline(x=q, line_dash="dot", line_color="lightgray")

    title = "Timeline de minutos por jugador"
    if team_name:
        title = f"{team_name} - {title}"

    fig.update_layout(
        title=title,
        xaxis_title="Minutos",
        yaxis=dict(categoryorder="array", categoryarray=list(reversed(players))),
        height=max(300, len(players) * 45 + 80),
        barmode="overlay",
    )
    return apply_standard_layout(fig)


def clutch_player_bars(clutch_df: pd.DataFrame, local: str, visitante: str) -> go.Figure:
    """Barras horizontales de puntos clutch por jugador, coloreado por equipo."""
    if clutch_df.empty:
        return go.Figure()

    df = clutch_df[clutch_df["clutch_pts"] > 0].sort_values("clutch_pts", ascending=True)
    if df.empty:
        return go.Figure()

    colors = []
    for _, row in df.iterrows():
        team = row.get("equipo_nombre", row.get("equipo", ""))
        if team in ("LOCAL", local):
            colors.append(get_team_color(local))
        else:
            colors.append(get_team_color(visitante))

    fig = go.Figure(go.Bar(
        y=df["jugador"],
        x=df["clutch_pts"],
        orientation="h",
        marker_color=colors,
        text=df["clutch_pts"].astype(int),
        textposition="outside",
    ))

    fig.update_layout(
        title="Puntos en situación Clutch",
        xaxis_title="Puntos",
        height=max(300, len(df) * 30 + 80),
    )
    return apply_standard_layout(fig)


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> tuple:
    """Convierte #RRGGBB a (r, g, b, alpha)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (r, g, b, alpha)


# Alias for backwards compatibility
_hex_to_rgba = hex_to_rgba


def styled_header(title: str, subtitle: str = None):
    """Header de página con tipografía premium y borde accent."""
    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div class="subtitle">{subtitle}</div>'
    st.markdown(
        f'<div class="acb-header"><h1>{title}</h1>{subtitle_html}</div>',
        unsafe_allow_html=True,
    )


def styled_game_card(game_row, local_color: str, visit_color: str):
    """Tarjeta de resultado de partido con flexbox y estilos premium."""
    local_won = game_row["resultado_local"] > game_row["resultado_visitante"]
    local_cls = "winner" if local_won else ""
    visit_cls = "winner" if not local_won else ""

    st.markdown(
        f'<div class="acb-game-card" style="border-left: 3px solid {local_color}">'
        f'<div class="team-row">'
        f'<span class="team-name {local_cls}" style="color:{local_color}">{game_row["local"]}</span>'
        f'<span class="team-score {local_cls}">{int(game_row["resultado_local"])}</span>'
        f'</div>'
        f'<div class="team-row">'
        f'<span class="team-name {visit_cls}" style="color:{visit_color}">{game_row["visitante"]}</span>'
        f'<span class="team-score {visit_cls}">{int(game_row["resultado_visitante"])}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def styled_sidebar_header(title: str, subtitle: str):
    """Logo-header centrado para la sidebar."""
    st.sidebar.markdown(
        f'<div class="acb-sidebar-header">'
        f'<div class="logo-text">{title}</div>'
        f'<div class="logo-subtitle">{subtitle}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def game_selector(game_info: pd.DataFrame, key: str = "game_selector") -> tuple:
    """Selector de partido reutilizable para sidebar.

    Persiste la selección en st.session_state["selected_game_id"] para que
    al navegar entre páginas (Partido, Quintetos, Clutch) se mantenga el
    partido seleccionado.

    Returns:
        (game_id, game_row) - ID del partido y la fila de game_info correspondiente.
    """
    game_info_sorted = game_info.sort_values(["jornada_num", "fecha"])
    labels = []
    ids = []
    for _, g in game_info_sorted.iterrows():
        label = (
            f"J{g['jornada_num']} - {g['local']} {g['resultado_local']}-"
            f"{g['resultado_visitante']} {g['visitante']} ({g['fecha']})"
        )
        labels.append(label)
        ids.append(g["id_partido"])

    # Determinar índice inicial desde session_state compartido
    default_idx = 0
    shared_id = st.session_state.get("selected_game_id")
    if shared_id is not None and shared_id in ids:
        default_idx = ids.index(shared_id)

    selected_label = st.sidebar.selectbox(
        "Selecciona partido", labels, index=default_idx, key=key,
    )
    idx = labels.index(selected_label)
    game_id = ids[idx]

    # Persistir en session_state compartido
    st.session_state["selected_game_id"] = game_id

    game_row = game_info[game_info["id_partido"] == game_id].iloc[0]
    return game_id, game_row
