"""
Análisis de lineups/quintetos para identificar combinaciones óptimas.

Este análisis usa el +/- de jugadores para identificar qué combinaciones funcionan mejor.
"""
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, avg, sum as spark_sum, count, collect_list, array_sort, concat_ws, size
from pyspark.sql.window import Window
import logging

logger = logging.getLogger(__name__)


def identify_lineups_from_starters(df: DataFrame) -> DataFrame:
    """
    Identifica quintetos iniciales (5 titulares) por equipo y partido.

    Args:
        df: DataFrame con es_titular flag

    Returns:
        DataFrame con quintetos identificados
    """
    logger.info("Identificando quintetos iniciales...")

    # Filtrar solo titulares
    starters = df.filter(col("es_titular") == True)

    # Agrupar por partido y equipo, listar jugadores
    lineups = (starters
               .groupBy("id_partido", "equipo")
               .agg(
                   collect_list("player_id").alias("player_ids"),
                   collect_list("nombre").alias("player_names"),
                   avg("plus_minus").alias("avg_plus_minus"),
                   spark_sum("puntos").alias("total_points"),
                   count("player_id").alias("num_players")
               )
               # Filtrar solo si hay exactamente 5 jugadores
               .filter(col("num_players") == 5)
               # Ordenar IDs para consistencia
               .withColumn("player_ids_sorted", array_sort(col("player_ids")))
               .withColumn("lineup_id", concat_ws("_", col("player_ids_sorted"))))

    logger.info(f"✅ Identificados {lineups.count()} quintetos iniciales")
    return lineups


def calculate_lineup_performance(df_lineups: DataFrame) -> DataFrame:
    """
    Calcula performance agregada de cada lineup único.

    Args:
        df_lineups: DataFrame con lineups identificados

    Returns:
        DataFrame con métricas de performance por lineup
    """
    logger.info("Calculando performance de lineups...")

    lineup_stats = (df_lineups
                    .groupBy("lineup_id", "equipo", "player_names")
                    .agg(
                        count("id_partido").alias("games_played"),
                        avg("avg_plus_minus").alias("avg_plus_minus"),
                        avg("total_points").alias("avg_points"),
                        spark_sum("total_points").alias("total_points_all_games"),
                    )
                    .filter(col("games_played") >= 3)  # Mínimo 3 partidos
                    .orderBy(col("avg_plus_minus").desc()))

    return lineup_stats


def get_best_lineups_by_plus_minus(df_lineup_stats: DataFrame, top_n: int = 20) -> DataFrame:
    """
    Obtiene los mejores quintetos por +/-.

    Args:
        df_lineup_stats: DataFrame con stats de lineups
        top_n: Número de lineups a retornar

    Returns:
        DataFrame con top lineups
    """
    logger.info(f"Obteniendo top {top_n} quintetos por +/-...")

    return (df_lineup_stats
            .orderBy(col("avg_plus_minus").desc())
            .limit(top_n))


def get_worst_lineups_by_plus_minus(df_lineup_stats: DataFrame, top_n: int = 10) -> DataFrame:
    """
    Obtiene los peores quintetos por +/-.

    Útil para identificar combinaciones que NO funcionan.

    Args:
        df_lineup_stats: DataFrame con stats de lineups
        top_n: Número de lineups a retornar

    Returns:
        DataFrame con peor lineups
    """
    logger.info(f"Obteniendo peores {top_n} quintetos por +/-...")

    return (df_lineup_stats
            .orderBy(col("avg_plus_minus").asc())
            .limit(top_n))


def analyze_player_synergy(df: DataFrame, player1_id: int, player2_id: int) -> DataFrame:
    """
    Analiza la sinergia entre dos jugadores específicos.

    Compara performance cuando juegan juntos vs separados.

    Args:
        df: DataFrame con estadísticas
        player1_id: ID del primer jugador
        player2_id: ID del segundo jugador

    Returns:
        DataFrame con métricas de sinergia
    """
    logger.info(f"Analizando sinergia entre jugadores {player1_id} y {player2_id}...")

    # Performance jugador 1 cuando juega con jugador 2
    together = (df
                .filter(col("player_id") == player1_id)
                .join(
                    df.filter(col("player_id") == player2_id).select("id_partido", "equipo"),
                    on=["id_partido", "equipo"],
                    how="inner"
                )
                .agg(
                    avg("plus_minus").alias("avg_plus_minus_together"),
                    count("id_partido").alias("games_together")
                ))

    # Performance jugador 1 cuando NO juega con jugador 2
    apart = (df
             .filter(col("player_id") == player1_id)
             .join(
                 df.filter(col("player_id") == player2_id).select("id_partido", "equipo"),
                 on=["id_partido", "equipo"],
                 how="left_anti"
             )
             .agg(
                 avg("plus_minus").alias("avg_plus_minus_apart"),
                 count("id_partido").alias("games_apart")
             ))

    # Combinar resultados
    synergy = together.crossJoin(apart).withColumn(
        "synergy_score",
        col("avg_plus_minus_together") - col("avg_plus_minus_apart")
    )

    return synergy


def find_best_teammates_for_player(df: DataFrame, player_id: int, min_games: int = 5) -> DataFrame:
    """
    Encuentra los mejores compañeros para un jugador específico.

    Args:
        df: DataFrame con estadísticas
        player_id: ID del jugador
        min_games: Mínimo de partidos juntos

    Returns:
        DataFrame con mejores compañeros ordenados por impacto
    """
    logger.info(f"Encontrando mejores compañeros para jugador {player_id}...")

    # Partidos del jugador objetivo
    player_games = df.filter(col("player_id") == player_id).select("id_partido", "equipo", "plus_minus")

    # Stats del jugador con cada compañero
    teammates = (df
                 .filter(col("player_id") != player_id)
                 .join(player_games, on=["id_partido", "equipo"], how="inner")
                 .groupBy("player_id", "nombre", "equipo")
                 .agg(
                     count("id_partido").alias("games_together"),
                     avg(player_games["plus_minus"]).alias("avg_plus_minus_with_teammate")
                 )
                 .filter(col("games_together") >= min_games)
                 .orderBy(col("avg_plus_minus_with_teammate").desc()))

    return teammates


def calculate_lineup_efficiency(df_lineups: DataFrame, df_game_results: DataFrame = None) -> DataFrame:
    """
    Calcula eficiencia de lineups incluyendo victorias/derrotas si hay datos disponibles.

    Args:
        df_lineups: DataFrame con lineups
        df_game_results: Optional DataFrame con resultados de partidos

    Returns:
        DataFrame con métricas de eficiencia
    """
    logger.info("Calculando eficiencia de lineups...")

    if df_game_results is not None:
        # Join con resultados para calcular win%
        df_with_results = df_lineups.join(
            df_game_results.select("id_partido", "equipo", "resultado"),
            on=["id_partido", "equipo"],
            how="left"
        )

        lineup_efficiency = (df_with_results
                             .groupBy("lineup_id", "equipo")
                             .agg(
                                 count("id_partido").alias("games"),
                                 spark_sum(
                                     (col("resultado") == "W").cast("int")
                                 ).alias("wins"),
                                 avg("avg_plus_minus").alias("avg_plus_minus")
                             )
                             .withColumn("win_pct",
                                         (col("wins") / col("games")) * 100))

        return lineup_efficiency.orderBy(col("win_pct").desc())

    else:
        # Sin datos de resultados, solo +/-
        return calculate_lineup_performance(df_lineups)


def analyze_position_combinations(df: DataFrame) -> DataFrame:
    """
    Analiza qué combinaciones de posiciones funcionan mejor.

    Requiere datos de posición en player profiles.

    Args:
        df: DataFrame con estadísticas y posiciones

    Returns:
        DataFrame con análisis de combinaciones de posiciones
    """
    logger.info("Analizando combinaciones de posiciones...")

    # Esto requeriría join con player profiles para obtener posiciones
    # Por ahora retornamos placeholder
    logger.warning("⚠️ Análisis de posiciones requiere datos de perfiles de jugadores")

    return df.limit(0)  # DataFrame vacío


def get_lineup_summary(df: DataFrame) -> dict:
    """
    Genera resumen general de análisis de lineups.

    Args:
        df: DataFrame con estadísticas de jugadores

    Returns:
        Diccionario con métricas de resumen
    """
    logger.info("Generando resumen de lineups...")

    # Identificar lineups
    lineups = identify_lineups_from_starters(df)
    lineup_stats = calculate_lineup_performance(lineups)

    summary = {
        "total_unique_lineups": lineup_stats.count(),
        "avg_plus_minus_all": lineup_stats.agg(avg("avg_plus_minus")).collect()[0][0],
        "best_lineup_plus_minus": lineup_stats.agg({"avg_plus_minus": "max"}).collect()[0][0],
        "worst_lineup_plus_minus": lineup_stats.agg({"avg_plus_minus": "min"}).collect()[0][0],
    }

    return summary
