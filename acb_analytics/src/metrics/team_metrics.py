"""
Métricas avanzadas de equipos para análisis de basketball.

Incluye Four Factors, Net Rating, Pace, etc.
"""
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, sum as spark_sum, avg, count, when, lit, coalesce, round as spark_round
from pyspark.sql.window import Window
import logging

logger = logging.getLogger(__name__)


def calculate_team_totals_per_game(df: DataFrame) -> DataFrame:
    """
    Calcula totales de equipo por partido.

    Args:
        df: DataFrame con estadísticas de jugadores

    Returns:
        DataFrame con totales agregados por equipo y partido
    """
    logger.info("Calculando totales de equipo por partido...")

    team_totals = (df
                   .groupBy("id_partido", "equipo")
                   .agg(
                       spark_sum("puntos").alias("team_points"),
                       spark_sum("fga").alias("team_fga"),
                       spark_sum("fgm").alias("team_fgm"),
                       spark_sum("t3_intentados").alias("team_3pa"),
                       spark_sum("t3_anotados").alias("team_3pm"),
                       spark_sum("tl_intentados").alias("team_fta"),
                       spark_sum("tl_anotados").alias("team_ftm"),
                       spark_sum("rebotes_ofensivos").alias("team_oreb"),
                       spark_sum("rebotes_defensivos").alias("team_dreb"),
                       spark_sum("rebotes_totales").alias("team_reb"),
                       spark_sum("asistencias").alias("team_ast"),
                       spark_sum("robos").alias("team_stl"),
                       spark_sum("perdidas").alias("team_tov"),
                       spark_sum("tapones_favor").alias("team_blk"),
                       spark_sum("faltas_cometidas").alias("team_pf"),
                       count("player_id").alias("players_used"),
                   ))

    return team_totals


def calculate_four_factors(df_team_totals: DataFrame) -> DataFrame:
    """
    Calcula los Four Factors de Dean Oliver para cada equipo por partido.

    Los Four Factors son los 4 factores más importantes que determinan quién gana:
    1. Shooting (eFG%) - Eficiencia de tiro
    2. Turnovers (TOV%) - Cuidado del balón
    3. Rebounding (OREB%) - Rebote ofensivo
    4. Free Throws (FT Rate) - Tiros libres

    Args:
        df_team_totals: DataFrame con totales de equipo por partido

    Returns:
        DataFrame con Four Factors calculados
    """
    logger.info("Calculando Four Factors...")

    return (df_team_totals
            .withColumn(
                "efg_percent",
                when(col("team_fga") > 0,
                     spark_round(
                         ((col("team_fgm") + 0.5 * col("team_3pm")) / col("team_fga")) * 100,
                         2
                     )
                ).otherwise(None)
            )
            .withColumn(
                "tov_percent",
                when((col("team_fga") + 0.44 * col("team_fta") + col("team_tov")) > 0,
                     spark_round(
                         (col("team_tov") / (col("team_fga") + 0.44 * col("team_fta") + col("team_tov"))) * 100,
                         2
                     )
                ).otherwise(None)
            )
            .withColumn(
                "ft_rate",
                when(col("team_fga") > 0,
                     spark_round(col("team_fta") / col("team_fga"), 2)
                ).otherwise(None)
            ))


def calculate_pace(df_team_totals: DataFrame, minutes_per_game: float = 40.0) -> DataFrame:
    """
    Calcula el Pace (posesiones por partido) para cada equipo.

    Fórmula estimada: Pace ≈ FGA + 0.44 * FTA + TOV - OREB

    El pace real requiere datos del oponente, esta es una aproximación.

    Args:
        df_team_totals: DataFrame con totales de equipo
        minutes_per_game: Minutos por partido (40 para ACB)

    Returns:
        DataFrame con pace calculado
    """
    logger.info("Calculando Pace...")

    return df_team_totals.withColumn(
        "pace_estimated",
        spark_round(
            col("team_fga") + 0.44 * col("team_fta") + col("team_tov") - col("team_oreb"),
            2
        )
    )


def calculate_offensive_rating(df_team_totals: DataFrame) -> DataFrame:
    """
    Offensive Rating: Puntos anotados por 100 posesiones.

    Fórmula simplificada: Off Rating = (Points / Possessions) * 100

    Args:
        df_team_totals: DataFrame con totales y pace

    Returns:
        DataFrame con offensive rating
    """
    return df_team_totals.withColumn(
        "offensive_rating",
        when(col("pace_estimated") > 0,
             spark_round((col("team_points") / col("pace_estimated")) * 100, 2)
        ).otherwise(None)
    )


def get_team_season_averages(df_team_totals: DataFrame) -> DataFrame:
    """
    Calcula promedios de temporada por equipo.

    Args:
        df_team_totals: DataFrame con totales de equipo por partido

    Returns:
        DataFrame con promedios de temporada
    """
    logger.info("Calculando promedios de temporada por equipo...")

    return (df_team_totals
            .groupBy("equipo")
            .agg(
                count("id_partido").alias("games_played"),
                avg("team_points").alias("ppg"),
                avg("team_fga").alias("fga_per_game"),
                avg("team_fgm").alias("fgm_per_game"),
                avg("team_3pa").alias("t3pa_per_game"),
                avg("team_3pm").alias("t3pm_per_game"),
                avg("team_reb").alias("reb_per_game"),
                avg("team_ast").alias("ast_per_game"),
                avg("team_tov").alias("tov_per_game"),
                avg("efg_percent").alias("efg_percent_avg"),
                avg("tov_percent").alias("tov_percent_avg"),
                avg("ft_rate").alias("ft_rate_avg"),
                avg("pace_estimated").alias("pace_avg"),
                avg("offensive_rating").alias("off_rating_avg"),
            )
            .orderBy(col("off_rating_avg").desc()))


def calculate_three_point_volume(df_team_totals: DataFrame) -> DataFrame:
    """
    Calcula el % de tiros que son triples (estilo de juego).

    Args:
        df_team_totals: DataFrame con totales de equipo

    Returns:
        DataFrame con 3PA Rate
    """
    return df_team_totals.withColumn(
        "three_point_rate",
        when(col("team_fga") > 0,
             spark_round((col("team_3pa") / col("team_fga")) * 100, 2)
        ).otherwise(None)
    )


def calculate_assist_rate(df_team_totals: DataFrame) -> DataFrame:
    """
    Assist Rate: % de canastas asistidas.

    Fórmula: AST% = AST / FGM

    Mide ball movement. >60% es bueno para equipos modernos.

    Args:
        df_team_totals: DataFrame con totales

    Returns:
        DataFrame con assist rate
    """
    return df_team_totals.withColumn(
        "assist_rate",
        when(col("team_fgm") > 0,
             spark_round((col("team_ast") / col("team_fgm")) * 100, 2)
        ).otherwise(None)
    )


def identify_playing_style(df_team_averages: DataFrame) -> DataFrame:
    """
    Identifica el estilo de juego de cada equipo basado en métricas.

    Estilos:
    - Fast Pace: pace > 75
    - Three Heavy: 3PA rate > 40%
    - Inside Game: 3PA rate < 30%
    - Ball Movement: AST rate > 65%
    - Isolation: AST rate < 55%

    Args:
        df_team_averages: DataFrame con promedios de equipo

    Returns:
        DataFrame con columnas de estilo
    """
    logger.info("Identificando estilos de juego...")

    return (df_team_averages
            .withColumn(
                "style_pace",
                when(col("pace_avg") > 75, "Fast")
                .when(col("pace_avg") < 65, "Slow")
                .otherwise("Medium")
            )
            .withColumn(
                "style_shooting",
                when(col("t3pa_per_game") / col("fga_per_game") > 0.40, "Three Heavy")
                .when(col("t3pa_per_game") / col("fga_per_game") < 0.30, "Inside Game")
                .otherwise("Balanced")
            )
            .withColumn(
                "style_offense",
                when(col("ast_per_game") / col("fgm_per_game") > 0.65, "Ball Movement")
                .when(col("ast_per_game") / col("fgm_per_game") < 0.55, "Isolation")
                .otherwise("Mixed")
            ))


def calculate_all_team_metrics(df_players: DataFrame) -> tuple[DataFrame, DataFrame]:
    """
    Pipeline completo: calcula todas las métricas de equipo.

    Args:
        df_players: DataFrame con estadísticas de jugadores

    Returns:
        Tupla con (totales_por_partido, promedios_temporada)
    """
    logger.info("=== Calculando métricas de equipos ===")

    # Paso 1: Totales por partido
    df_totals = calculate_team_totals_per_game(df_players)

    # Paso 2: Four Factors
    df_totals = calculate_four_factors(df_totals)

    # Paso 3: Pace y ratings
    df_totals = calculate_pace(df_totals)
    df_totals = calculate_offensive_rating(df_totals)

    # Paso 4: Métricas de estilo
    df_totals = calculate_three_point_volume(df_totals)
    df_totals = calculate_assist_rate(df_totals)

    # Paso 5: Promedios de temporada
    df_averages = get_team_season_averages(df_totals)
    df_averages = identify_playing_style(df_averages)

    logger.info("✅ Métricas de equipos completadas")

    return df_totals, df_averages
