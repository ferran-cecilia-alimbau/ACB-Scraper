"""Heatmap de minutos compartidos entre jugadores."""

import plotly.graph_objects as go
import pandas as pd


def create_shared_minutes_heatmap(
    shared_matrix: pd.DataFrame,
    team_name: str = "",
) -> go.Figure:
    """Crea heatmap de minutos compartidos entre jugadores de un equipo.

    Args:
        shared_matrix: Matriz simétrica de minutos compartidos
        team_name: Nombre del equipo (para título)

    Returns:
        Figura Plotly
    """
    players = shared_matrix.index.tolist()

    fig = go.Figure(data=go.Heatmap(
        z=shared_matrix.values,
        x=players,
        y=players,
        colorscale="YlOrRd",
        text=shared_matrix.values.round(1),
        texttemplate="%{text}",
        textfont={"size": 10},
        hovertemplate="<b>%{x}</b> con <b>%{y}</b><br>Minutos: %{z:.1f}<extra></extra>",
    ))

    title = "Minutos compartidos"
    if team_name:
        title = f"{team_name} - {title}"

    fig.update_layout(
        title=title,
        xaxis=dict(tickangle=45),
        height=600,
        width=700,
        template="plotly_white",
    )

    return fig


def create_lineup_ratings_table(
    lineup_df: pd.DataFrame, top_n: int = 10
) -> go.Figure:
    """Crea tabla con los mejores/peores quintetos por net rating.

    Args:
        lineup_df: Output de lineup_net_rating
        top_n: Número de quintetos a mostrar

    Returns:
        Figura Plotly con tabla
    """
    if lineup_df.empty:
        return go.Figure()

    best = lineup_df.head(top_n)
    worst = lineup_df.tail(top_n).iloc[::-1]
    combined = pd.concat([best, worst])

    colors = [
        "#e8f5e9" if nr > 0 else "#ffebee"
        for nr in combined["net_rating"]
    ]

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["Quinteto", "Min", "ORtg", "DRtg", "NetRtg", "Stints"],
            fill_color="#1976D2",
            font=dict(color="white", size=12),
            align="left",
        ),
        cells=dict(
            values=[
                combined["lineup_str"],
                combined["minutes"].round(1),
                combined["off_rating"].round(1),
                combined["def_rating"].round(1),
                combined["net_rating"].round(1),
                combined["n_stints"],
            ],
            fill_color=[colors] * 6,
            align="left",
            font=dict(size=11),
        ),
    )])

    fig.update_layout(
        title=f"Top/Bottom {top_n} quintetos por Net Rating",
        height=max(400, len(combined) * 30 + 100),
    )

    return fig
