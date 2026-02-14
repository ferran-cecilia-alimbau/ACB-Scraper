"""Timeline de diferencia de puntos + rachas para un partido."""

import plotly.graph_objects as go
import pandas as pd
import numpy as np


def create_score_diff_timeline(
    game_pbp: pd.DataFrame,
    local_name: str,
    visitante_name: str,
    runs: list[dict] = None,
) -> go.Figure:
    """Crea timeline de diferencia de puntos a lo largo del partido.

    Args:
        game_pbp: PBP del partido con abs_seconds
        local_name: Nombre del equipo local
        visitante_name: Nombre del equipo visitante
        runs: Rachas detectadas (opcional, para resaltar)

    Returns:
        Figura Plotly
    """
    # Calcular diferencia en cada evento
    df = game_pbp.copy()
    df["score_diff"] = df["marcador_local"].astype(int) - df["marcador_visitante"].astype(int)

    # Eliminar duplicados consecutivos de score_diff para suavizar
    df = df.drop_duplicates(subset=["abs_seconds", "score_diff"])

    fig = go.Figure()

    # Línea de diferencia de marcador
    fig.add_trace(go.Scatter(
        x=df["abs_seconds"] / 60,
        y=df["score_diff"],
        mode="lines",
        name="Diferencia",
        line=dict(color="#1f77b4", width=2),
        fill="tozeroy",
        fillcolor="rgba(31, 119, 180, 0.1)",
    ))

    # Línea del 0
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    # Marcadores de cuartos
    for q in [1, 2, 3]:
        fig.add_vline(
            x=q * 10, line_dash="dot", line_color="lightgray",
            annotation_text=f"Fin {q}C", annotation_position="top"
        )

    # Resaltar rachas si se proporcionan
    if runs:
        for run in runs:
            color = "rgba(255, 0, 0, 0.15)" if run["team"] == "VISITANTE" else "rgba(0, 128, 0, 0.15)"
            label = f"{run['points']}-0"
            fig.add_vrect(
                x0=run["start_sec"] / 60,
                x1=run["end_sec"] / 60,
                fillcolor=color,
                opacity=0.5,
                line_width=0,
                annotation_text=label,
                annotation_position="top left",
            )

    max_time = df["abs_seconds"].max() / 60

    fig.update_layout(
        title=f"{local_name} vs {visitante_name} - Evolución del marcador",
        xaxis_title="Minutos",
        yaxis_title=f"← {visitante_name}    Diferencia    {local_name} →",
        xaxis=dict(range=[0, max_time]),
        height=400,
        showlegend=False,
        template="plotly_white",
    )

    return fig


def create_score_evolution(
    game_pbp: pd.DataFrame,
    local_name: str,
    visitante_name: str,
) -> go.Figure:
    """Crea gráfico con la evolución del marcador de ambos equipos.

    Returns:
        Figura Plotly con dos líneas (local y visitante)
    """
    df = game_pbp.copy()
    df = df.drop_duplicates(subset=["abs_seconds", "marcador_local", "marcador_visitante"])

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["abs_seconds"] / 60,
        y=df["marcador_local"].astype(int),
        mode="lines",
        name=local_name,
        line=dict(color="#2196F3", width=2),
    ))

    fig.add_trace(go.Scatter(
        x=df["abs_seconds"] / 60,
        y=df["marcador_visitante"].astype(int),
        mode="lines",
        name=visitante_name,
        line=dict(color="#F44336", width=2),
    ))

    for q in [1, 2, 3]:
        fig.add_vline(x=q * 10, line_dash="dot", line_color="lightgray")

    fig.update_layout(
        title=f"{local_name} vs {visitante_name} - Marcador",
        xaxis_title="Minutos",
        yaxis_title="Puntos",
        height=400,
        template="plotly_white",
    )

    return fig
