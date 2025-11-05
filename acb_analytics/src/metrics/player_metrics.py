"""
Métricas avanzadas de jugadores para análisis de basketball.

Incluye métricas modernas como True Shooting %, eFG%, Usage Rate, PER, etc.
"""
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, when, lit, coalesce, round as spark_round
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def calculate_true_shooting_percentage(df: DataFrame) -> DataFrame:
    """
    True Shooting Percentage (TS%): Mide eficiencia real de tiro.

    Fórmula: TS% = PTS / (2 * (FGA + 0.44 * FTA))

    Es mejor que FG% porque considera:
    - Tiros de 2 (valen 2 puntos)
    - Tiros de 3 (valen 3 puntos)
    - Tiros libres (con factor 0.44 porque no todas las posesiones terminan en FT)

    Args:
        df: DataFrame con puntos, fga, tl_intentados

    Returns:
        DataFrame con columna 'ts_percentage'
    """
    return df.withColumn(
        "ts_percentage",
        when(
            (coalesce(col("fga"), lit(0)) + 0.44 * coalesce(col("tl_intentados"), lit(0))) > 0,
            spark_round(
                (coalesce(col("puntos"), lit(0)) /
                 (2 * (coalesce(col("fga"), lit(0)) + 0.44 * coalesce(col("tl_intentados"), lit(0))))) * 100,
                2
            )
        ).otherwise(None)
    )


def calculate_effective_field_goal_percentage(df: DataFrame) -> DataFrame:
    """
    Effective Field Goal Percentage (eFG%): FG% ajustado por valor de tiros de 3.

    Fórmula: eFG% = (FGM + 0.5 * 3PM) / FGA

    Ajusta el FG% tradicional dando crédito extra a los triples.
    Un 40% en triples equivale a un 60% en tiros de 2 en términos de puntos.

    Args:
        df: DataFrame con fgm, t3_anotados, fga

    Returns:
        DataFrame con columna 'efg_percentage'
    """
    return df.withColumn(
        "efg_percentage",
        when(
            coalesce(col("fga"), lit(0)) > 0,
            spark_round(
                ((coalesce(col("fgm"), lit(0)) + 0.5 * coalesce(col("t3_anotados"), lit(0))) /
                 coalesce(col("fga"), lit(0))) * 100,
                2
            )
        ).otherwise(None)
    )


def calculate_usage_rate(df: DataFrame, team_stats: Optional[DataFrame] = None) -> DataFrame:
    """
    Usage Rate (USG%): Estima el % de posesiones de equipo usadas por el jugador.

    Fórmula simplificada (sin datos de equipo):
    USG% ≈ (FGA + 0.44 * FTA + TOV) / MIN

    Con datos de equipo sería:
    USG% = 100 * ((FGA + 0.44 * FTA + TOV) * (Tm MP / 5)) / (MP * (Tm FGA + 0.44 * Tm FTA + Tm TOV))

    Args:
        df: DataFrame con estadísticas de jugadores
        team_stats: Optional DataFrame con totales de equipo

    Returns:
        DataFrame con columna 'usage_rate'
    """
    # Versión simplificada sin datos de equipo
    return df.withColumn(
        "usage_rate_simple",
        when(
            coalesce(col("minutos_float"), lit(0)) > 0,
            spark_round(
                (coalesce(col("fga"), lit(0)) +
                 0.44 * coalesce(col("tl_intentados"), lit(0)) +
                 coalesce(col("perdidas"), lit(0))) /
                coalesce(col("minutos_float"), lit(1)),
                2
            )
        ).otherwise(None)
    )


def calculate_assist_ratio(df: DataFrame) -> DataFrame:
    """
    Assist Ratio (AST%): Porcentaje de posesiones terminadas en asistencia.

    Fórmula: AST% = AST / (FGA + 0.44 * FTA + AST + TOV)

    Mide qué tan bien un jugador distribuye el balón vs intenta anotar.

    Args:
        df: DataFrame con asistencias, fga, fta, tov

    Returns:
        DataFrame con columna 'assist_ratio'
    """
    return df.withColumn(
        "assist_ratio",
        when(
            (coalesce(col("fga"), lit(0)) +
             0.44 * coalesce(col("tl_intentados"), lit(0)) +
             coalesce(col("asistencias"), lit(0)) +
             coalesce(col("perdidas"), lit(0))) > 0,
            spark_round(
                (coalesce(col("asistencias"), lit(0)) /
                 (coalesce(col("fga"), lit(0)) +
                  0.44 * coalesce(col("tl_intentados"), lit(0)) +
                  coalesce(col("asistencias"), lit(0)) +
                  coalesce(col("perdidas"), lit(0)))) * 100,
                2
            )
        ).otherwise(None)
    )


def calculate_turnover_ratio(df: DataFrame) -> DataFrame:
    """
    Turnover Ratio (TOV%): Porcentaje de posesiones terminadas en pérdida.

    Fórmula: TOV% = TOV / (FGA + 0.44 * FTA + TOV)

    Mide cuidado del balón. Menor es mejor.

    Args:
        df: DataFrame con perdidas, fga, fta

    Returns:
        DataFrame con columna 'turnover_ratio'
    """
    return df.withColumn(
        "turnover_ratio",
        when(
            (coalesce(col("fga"), lit(0)) +
             0.44 * coalesce(col("tl_intentados"), lit(0)) +
             coalesce(col("perdidas"), lit(0))) > 0,
            spark_round(
                (coalesce(col("perdidas"), lit(0)) /
                 (coalesce(col("fga"), lit(0)) +
                  0.44 * coalesce(col("tl_intentados"), lit(0)) +
                  coalesce(col("perdidas"), lit(0)))) * 100,
                2
            )
        ).otherwise(None)
    )


def calculate_assist_to_turnover_ratio(df: DataFrame) -> DataFrame:
    """
    Assist to Turnover Ratio (AST/TOV): Ratio puro de asistencias vs pérdidas.

    Fórmula: AST/TOV = AST / TOV

    Métrica clásica para bases. >2.0 es excelente, >3.0 es élite.

    Args:
        df: DataFrame con asistencias y perdidas

    Returns:
        DataFrame con columna 'ast_to_tov'
    """
    return df.withColumn(
        "ast_to_tov",
        when(
            coalesce(col("perdidas"), lit(0)) > 0,
            spark_round(
                coalesce(col("asistencias"), lit(0)) /
                coalesce(col("perdidas"), lit(1)),
                2
            )
        ).otherwise(None)
    )


def calculate_rebounding_percentage(df: DataFrame, team_stats: Optional[DataFrame] = None) -> DataFrame:
    """
    Rebounding Percentage: % de rebotes disponibles capturados.

    Fórmula simplificada (sin datos de oponente):
    REB% ≈ TRB / MIN (rebotes por minuto)

    Con datos completos:
    REB% = (TRB * (Tm MIN / 5)) / (MIN * (Tm REB + Opp REB))

    Args:
        df: DataFrame con rebotes y minutos
        team_stats: Optional DataFrame con totales

    Returns:
        DataFrame con columna 'reb_per_minute'
    """
    # Versión simplificada: rebotes por minuto
    return df.withColumn(
        "reb_per_minute",
        when(
            coalesce(col("minutos_float"), lit(0)) > 0,
            spark_round(
                coalesce(col("rebotes_totales"), lit(0)) /
                coalesce(col("minutos_float"), lit(1)),
                2
            )
        ).otherwise(None)
    )


def calculate_points_per_shot_attempt(df: DataFrame) -> DataFrame:
    """
    Points Per Shot Attempt (PPS): Puntos generados por intento de tiro.

    Fórmula: PPS = PTS / (FGA + 0.44 * FTA)

    Mide eficiencia de scoring. >1.0 es bueno, >1.1 es muy bueno.

    Args:
        df: DataFrame con puntos, fga, fta

    Returns:
        DataFrame con columna 'points_per_shot'
    """
    return df.withColumn(
        "points_per_shot",
        when(
            (coalesce(col("fga"), lit(0)) + 0.44 * coalesce(col("tl_intentados"), lit(0))) > 0,
            spark_round(
                coalesce(col("puntos"), lit(0)) /
                (coalesce(col("fga"), lit(0)) + 0.44 * coalesce(col("tl_intentados"), lit(0))),
                2
            )
        ).otherwise(None)
    )


def calculate_player_efficiency_rating(df: DataFrame) -> DataFrame:
    """
    Player Efficiency Rating (PER): Rating global de performance.

    Fórmula simplificada de PER (sin ajustes de equipo/liga):
    PER = (PTS + REB + AST + STL + BLK - Missed FG - Missed FT - TOV) / MIN

    El PER real de Hollinger es mucho más complejo con factores de liga y pace.

    Args:
        df: DataFrame con todas las estadísticas

    Returns:
        DataFrame con columna 'per_simple'
    """
    return df.withColumn(
        "per_simple",
        when(
            coalesce(col("minutos_float"), lit(0)) > 0,
            spark_round(
                (coalesce(col("puntos"), lit(0)) +
                 coalesce(col("rebotes_totales"), lit(0)) +
                 coalesce(col("asistencias"), lit(0)) +
                 coalesce(col("robos"), lit(0)) +
                 coalesce(col("tapones_favor"), lit(0)) -
                 (coalesce(col("fga"), lit(0)) - coalesce(col("fgm"), lit(0))) -  # Missed FG
                 (coalesce(col("tl_intentados"), lit(0)) - coalesce(col("tl_anotados"), lit(0))) -  # Missed FT
                 coalesce(col("perdidas"), lit(0))) /
                coalesce(col("minutos_float"), lit(1)),
                2
            )
        ).otherwise(None)
    )


def calculate_three_point_rate(df: DataFrame) -> DataFrame:
    """
    Three Point Attempt Rate (3PAr): Porcentaje de tiros que son triples.

    Fórmula: 3PAr = 3PA / FGA

    Mide dependencia del triple. ACB moderna ~35-45%.

    Args:
        df: DataFrame con t3_intentados y fga

    Returns:
        DataFrame con columna 'three_point_rate'
    """
    return df.withColumn(
        "three_point_rate",
        when(
            coalesce(col("fga"), lit(0)) > 0,
            spark_round(
                (coalesce(col("t3_intentados"), lit(0)) /
                 coalesce(col("fga"), lit(1))) * 100,
                2
            )
        ).otherwise(None)
    )


def calculate_free_throw_rate(df: DataFrame) -> DataFrame:
    """
    Free Throw Rate (FTr): Ratio de tiros libres vs tiros de campo.

    Fórmula: FTr = FTA / FGA

    Mide capacidad de generar faltas. >0.4 es muy bueno.

    Args:
        df: DataFrame con tl_intentados y fga

    Returns:
        DataFrame con columna 'free_throw_rate'
    """
    return df.withColumn(
        "free_throw_rate",
        when(
            coalesce(col("fga"), lit(0)) > 0,
            spark_round(
                coalesce(col("tl_intentados"), lit(0)) /
                coalesce(col("fga"), lit(1)),
                2
            )
        ).otherwise(None)
    )


def calculate_all_advanced_metrics(df: DataFrame) -> DataFrame:
    """
    Calcula TODAS las métricas avanzadas de una vez.

    Args:
        df: DataFrame con estadísticas básicas de jugadores

    Returns:
        DataFrame con todas las métricas avanzadas añadidas
    """
    logger.info("Calculando métricas avanzadas de jugadores...")

    # Primero asegurar que tenemos las columnas calculadas necesarias
    from utils.spark_utils import (
        convert_minutes_to_float,
        calculate_field_goal_attempts,
        calculate_field_goals_made
    )

    df = convert_minutes_to_float(df, "minutos")
    df = calculate_field_goal_attempts(df)
    df = calculate_field_goals_made(df)

    # Ahora calcular todas las métricas
    df = calculate_true_shooting_percentage(df)
    df = calculate_effective_field_goal_percentage(df)
    df = calculate_usage_rate(df)
    df = calculate_assist_ratio(df)
    df = calculate_turnover_ratio(df)
    df = calculate_assist_to_turnover_ratio(df)
    df = calculate_rebounding_percentage(df)
    df = calculate_points_per_shot_attempt(df)
    df = calculate_player_efficiency_rating(df)
    df = calculate_three_point_rate(df)
    df = calculate_free_throw_rate(df)

    logger.info("✅ Métricas avanzadas calculadas")

    return df


def get_player_summary_stats(df: DataFrame, min_minutes: float = 10.0) -> DataFrame:
    """
    Genera resumen estadístico por jugador (agregado de todos los partidos).

    Args:
        df: DataFrame con estadísticas y métricas
        min_minutes: Minutos mínimos totales para incluir jugador

    Returns:
        DataFrame agregado por jugador con promedios y totales
    """
    from pyspark.sql.functions import avg, sum as spark_sum, count, stddev

    logger.info(f"Generando resumen por jugador (min {min_minutes} minutos)...")

    summary = (df
               .groupBy("player_id", "nombre", "equipo")
               .agg(
                   count("id_partido").alias("partidos_jugados"),
                   spark_sum("minutos_float").alias("minutos_totales"),
                   avg("minutos_float").alias("minutos_promedio"),

                   # Totales
                   spark_sum("puntos").alias("puntos_totales"),
                   spark_sum("rebotes_totales").alias("rebotes_totales"),
                   spark_sum("asistencias").alias("asistencias_totales"),
                   spark_sum("robos").alias("robos_totales"),
                   spark_sum("tapones_favor").alias("tapones_totales"),
                   spark_sum("perdidas").alias("perdidas_totales"),

                   # Promedios
                   avg("puntos").alias("puntos_promedio"),
                   avg("rebotes_totales").alias("rebotes_promedio"),
                   avg("asistencias").alias("asistencias_promedio"),
                   avg("plus_minus").alias("plus_minus_promedio"),

                   # Eficiencia
                   avg("ts_percentage").alias("ts_percentage_avg"),
                   avg("efg_percentage").alias("efg_percentage_avg"),
                   avg("per_simple").alias("per_avg"),
                   avg("ast_to_tov").alias("ast_to_tov_avg"),

                   # Porcentajes de tiro
                   avg("t2_porcentaje").alias("t2_porcentaje_avg"),
                   avg("t3_porcentaje").alias("t3_porcentaje_avg"),
                   avg("tl_porcentaje").alias("tl_porcentaje_avg"),

                   # Consistencia
                   stddev("puntos").alias("puntos_stddev"),
                   stddev("ts_percentage").alias("ts_percentage_stddev"),
               )
               .filter(col("minutos_totales") >= min_minutes)
               .orderBy(col("per_avg").desc())
               )

    logger.info(f"✅ Resumen generado para {summary.count()} jugadores")

    return summary
