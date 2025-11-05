"""
Análisis de consistencia, rachas (streaks) y volatilidad de jugadores.

Detecta "hot hands", rachas frías, y mide la predictibilidad del rendimiento.
"""
from pyspark.sql import DataFrame, Window
from pyspark.sql.functions import (
    col, lag, lead, when, count, sum as spark_sum, avg, stddev,
    row_number, dense_rank, lit, round as spark_round
)
import logging

logger = logging.getLogger(__name__)


def calculate_consistency_metrics(df: DataFrame) -> DataFrame:
    """
    Calcula métricas de consistencia para cada jugador.

    Métricas:
    - Coefficient of Variation (CV): stddev / mean (menor = más consistente)
    - Range: max - min
    - Interquartile Range (IQR): Q3 - Q1

    Args:
        df: DataFrame con estadísticas por partido

    Returns:
        DataFrame con métricas de consistencia por jugador
    """
    logger.info("Calculando métricas de consistencia...")

    from pyspark.sql.functions import expr

    consistency = (df
                   .groupBy("player_id", "nombre", "equipo")
                   .agg(
                       count("id_partido").alias("games"),
                       avg("puntos").alias("avg_points"),
                       stddev("puntos").alias("std_points"),
                       expr("percentile_approx(puntos, 0.25)").alias("q1_points"),
                       expr("percentile_approx(puntos, 0.75)").alias("q3_points"),
                       expr("min(puntos)").alias("min_points"),
                       expr("max(puntos)").alias("max_points"),
                       avg("ts_percentage").alias("avg_ts"),
                       stddev("ts_percentage").alias("std_ts"),
                   )
                   .withColumn(
                       "cv_points",
                       when(col("avg_points") > 0,
                            spark_round(col("std_points") / col("avg_points"), 3)
                       ).otherwise(None)
                   )
                   .withColumn(
                       "range_points",
                       col("max_points") - col("min_points")
                   )
                   .withColumn(
                       "iqr_points",
                       col("q3_points") - col("q1_points")
                   )
                   .withColumn(
                       "consistency_score",
                       # Menor CV = más consistente, escala a 0-100
                       when(col("cv_points").isNotNull(),
                            spark_round(100 * (1 - col("cv_points")), 2)
                       ).otherwise(None)
                   ))

    logger.info("✅ Métricas de consistencia calculadas")
    return consistency


def detect_scoring_streaks(df: DataFrame, streak_threshold: float = 1.5) -> DataFrame:
    """
    Detecta rachas de anotación (hot/cold streaks).

    Hot streak: 3+ partidos consecutivos por encima de la media personal
    Cold streak: 3+ partidos consecutivos por debajo de la media personal

    Args:
        df: DataFrame con estadísticas ordenadas cronológicamente
        streak_threshold: Multiplicador para definir "caliente" (ej: 1.5 = 50% sobre media)

    Returns:
        DataFrame con rachas detectadas
    """
    logger.info("Detectando rachas de anotación...")

    # Window por jugador ordenado por fecha/partido
    window_player = Window.partitionBy("player_id").orderBy("id_partido")

    # Calcular media personal
    player_avg = (df
                  .groupBy("player_id")
                  .agg(avg("puntos").alias("personal_avg_points")))

    df_with_avg = df.join(player_avg, on="player_id")

    # Identificar si cada partido está por encima/debajo de la media
    df_streaks = (df_with_avg
                  .withColumn(
                      "above_avg",
                      when(col("puntos") > col("personal_avg_points") * streak_threshold, 1)
                      .when(col("puntos") < col("personal_avg_points") * (2 - streak_threshold), -1)
                      .otherwise(0)
                  )
                  .withColumn("prev_above", lag("above_avg", 1).over(window_player))
                  .withColumn("next_above", lead("above_avg", 1).over(window_player))
                  # Detectar inicio de racha
                  .withColumn(
                      "streak_start",
                      when((col("above_avg") != 0) &
                           ((col("prev_above").isNull()) | (col("prev_above") != col("above_avg"))), 1)
                      .otherwise(0)
                  ))

    logger.info("✅ Rachas detectadas")
    return df_streaks


def identify_hot_hand_players(df_streaks: DataFrame, min_streak_games: int = 3) -> DataFrame:
    """
    Identifica jugadores que actualmente están en racha caliente.

    Args:
        df_streaks: DataFrame con rachas detectadas
        min_streak_games: Mínimo de partidos para considerar racha

    Returns:
        DataFrame con jugadores en racha caliente
    """
    logger.info("Identificando jugadores en racha caliente...")

    # Obtener últimos N partidos de cada jugador
    window_last_games = Window.partitionBy("player_id").orderBy(col("id_partido").desc())

    recent_form = (df_streaks
                   .withColumn("game_rank", row_number().over(window_last_games))
                   .filter(col("game_rank") <= min_streak_games)
                   .groupBy("player_id", "nombre", "equipo")
                   .agg(
                       spark_sum("above_avg").alias("hot_streak_sum"),
                       count("id_partido").alias("recent_games"),
                       avg("puntos").alias("recent_avg_points"),
                       avg("ts_percentage").alias("recent_ts")
                   )
                   .filter(col("hot_streak_sum") == min_streak_games)  # Todos los partidos por encima
                   .orderBy(col("recent_avg_points").desc()))

    logger.info(f"✅ {recent_form.count()} jugadores en racha caliente")
    return recent_form


def calculate_player_volatility(df: DataFrame) -> DataFrame:
    """
    Calcula volatilidad del rendimiento (similar a volatilidad financiera).

    Jugadores volátiles: alto riesgo, alto reward
    Jugadores estables: predecibles, confiables

    Args:
        df: DataFrame con estadísticas

    Returns:
        DataFrame con métricas de volatilidad
    """
    logger.info("Calculando volatilidad de jugadores...")

    volatility = (df
                  .groupBy("player_id", "nombre", "equipo")
                  .agg(
                      count("id_partido").alias("games"),
                      avg("puntos").alias("avg_points"),
                      stddev("puntos").alias("volatility_points"),
                      avg("plus_minus").alias("avg_plus_minus"),
                      stddev("plus_minus").alias("volatility_plus_minus"),
                      avg("valoracion").alias("avg_rating"),
                      stddev("valoracion").alias("volatility_rating")
                  )
                  .withColumn(
                      "volatility_score",
                      # Normalizar volatilidad de puntos
                      when(col("avg_points") > 0,
                           spark_round((col("volatility_points") / col("avg_points")) * 100, 2)
                      ).otherwise(None)
                  )
                  .withColumn(
                      "player_type",
                      when(col("volatility_score") < 30, "Stable")
                      .when(col("volatility_score") < 50, "Moderate")
                      .otherwise("Volatile")
                  ))

    return volatility


def find_clutch_performers(df: DataFrame, df_games: DataFrame) -> DataFrame:
    """
    Identifica jugadores "clutch" (rinden mejor en partidos cerrados).

    Partidos cerrados: diferencia de puntos final <= 5

    Args:
        df: DataFrame con estadísticas de jugadores
        df_games: DataFrame con información de partidos (resultados)

    Returns:
        DataFrame con performers clutch
    """
    logger.info("Identificando jugadores clutch...")

    # Identificar partidos cerrados (requiere datos de resultado)
    if "resultado_local" in df_games.columns and "resultado_visitante" in df_games.columns:
        from pyspark.sql.functions import abs as spark_abs

        close_games = (df_games
                       .withColumn("point_diff",
                                   spark_abs(col("resultado_local").cast("int") -
                                             col("resultado_visitante").cast("int")))
                       .filter(col("point_diff") <= 5)
                       .select("id_partido"))

        # Performance en partidos cerrados
        clutch_stats = (df
                        .join(close_games, on="id_partido", how="inner")
                        .groupBy("player_id", "nombre", "equipo")
                        .agg(
                            count("id_partido").alias("close_games"),
                            avg("puntos").alias("clutch_ppg"),
                            avg("ts_percentage").alias("clutch_ts"),
                            avg("plus_minus").alias("clutch_plus_minus"),
                            avg("valoracion").alias("clutch_rating")
                        )
                        .filter(col("close_games") >= 3)
                        .orderBy(col("clutch_plus_minus").desc()))

        logger.info(f"✅ {clutch_stats.count()} jugadores clutch identificados")
        return clutch_stats
    else:
        logger.warning("⚠️ No hay datos de resultados para análisis clutch")
        return df.limit(0)


def analyze_performance_trends(df: DataFrame, window_size: int = 5) -> DataFrame:
    """
    Analiza tendencias de performance usando moving average.

    Identifica si jugadores están mejorando o empeorando.

    Args:
        df: DataFrame con estadísticas ordenadas
        window_size: Tamaño de ventana para moving average

    Returns:
        DataFrame con tendencias
    """
    logger.info(f"Analizando tendencias con ventana de {window_size} partidos...")

    window_ma = (Window
                 .partitionBy("player_id")
                 .orderBy("id_partido")
                 .rowsBetween(-window_size + 1, 0))

    df_trends = (df
                 .withColumn("ma_points", avg("puntos").over(window_ma))
                 .withColumn("ma_ts", avg("ts_percentage").over(window_ma))
                 .withColumn("ma_plus_minus", avg("plus_minus").over(window_ma)))

    # Detectar tendencia (últimos 3 vs anteriores 3)
    window_recent = Window.partitionBy("player_id").orderBy(col("id_partido").desc())

    trends = (df_trends
              .withColumn("game_recency", row_number().over(window_recent))
              .filter(col("game_recency") <= window_size * 2)
              .withColumn(
                  "period",
                  when(col("game_recency") <= window_size, "recent")
                  .otherwise("previous")
              )
              .groupBy("player_id", "nombre", "equipo", "period")
              .agg(avg("ma_points").alias("avg_ma_points"))
              .groupBy("player_id", "nombre", "equipo")
              .pivot("period", ["recent", "previous"])
              .agg({"avg_ma_points": "first"})
              .withColumnRenamed("recent", "recent_trend")
              .withColumnRenamed("previous", "previous_trend")
              .withColumn(
                  "trend_direction",
                  when(col("recent_trend") > col("previous_trend") * 1.1, "Improving")
                  .when(col("recent_trend") < col("previous_trend") * 0.9, "Declining")
                  .otherwise("Stable")
              ))

    return trends


def calculate_game_score_variance(df: DataFrame) -> DataFrame:
    """
    Calcula variance del "Game Score" (métrica compuesta de John Hollinger).

    Game Score = PTS + 0.4*FGM - 0.7*FGA - 0.4*(FTA-FTM) + 0.7*OREB + 0.3*DREB + STL + 0.7*AST + 0.7*BLK - 0.4*PF - TOV

    Args:
        df: DataFrame con estadísticas

    Returns:
        DataFrame con game score y su varianza
    """
    logger.info("Calculando Game Score variance...")

    df_gs = (df
             .withColumn(
                 "game_score",
                 col("puntos") +
                 0.4 * col("fgm") -
                 0.7 * col("fga") -
                 0.4 * (col("tl_intentados") - col("tl_anotados")) +
                 0.7 * col("rebotes_ofensivos") +
                 0.3 * col("rebotes_defensivos") +
                 col("robos") +
                 0.7 * col("asistencias") +
                 0.7 * col("tapones_favor") -
                 0.4 * col("faltas_cometidas") -
                 col("perdidas")
             ))

    gs_variance = (df_gs
                   .groupBy("player_id", "nombre", "equipo")
                   .agg(
                       count("id_partido").alias("games"),
                       avg("game_score").alias("avg_game_score"),
                       stddev("game_score").alias("std_game_score")
                   )
                   .withColumn(
                       "game_score_consistency",
                       when(col("avg_game_score") > 0,
                            1 / (1 + col("std_game_score") / col("avg_game_score"))
                       ).otherwise(None)
                   ))

    return gs_variance
