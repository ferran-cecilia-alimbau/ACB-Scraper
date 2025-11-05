"""
Clustering de jugadores y equipos para identificar estilos de juego y arquetipos.

Usa K-Means y otros algoritmos de ML para agrupar jugadores/equipos similares.
"""
from pyspark.sql import DataFrame
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans, BisectingKMeans
from pyspark.ml import Pipeline
from pyspark.sql.functions import col, when, lit
import logging

logger = logging.getLogger(__name__)


def prepare_features_for_clustering(df: DataFrame, feature_cols: list) -> DataFrame:
    """
    Prepara features para clustering: vectorización y normalización.

    Args:
        df: DataFrame con las columnas de features
        feature_cols: Lista de nombres de columnas a usar como features

    Returns:
        DataFrame con columna 'scaled_features' lista para clustering
    """
    logger.info(f"Preparando {len(feature_cols)} features para clustering...")

    # Eliminar nulos
    df_clean = df.na.fill(0, subset=feature_cols)

    # Vectorizar features
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")

    # Normalizar (StandardScaler)
    scaler = StandardScaler(inputCol="features", outputCol="scaled_features",
                            withStd=True, withMean=True)

    # Pipeline
    pipeline = Pipeline(stages=[assembler, scaler])
    model = pipeline.fit(df_clean)
    df_prepared = model.transform(df_clean)

    logger.info("✅ Features preparadas")
    return df_prepared


def cluster_players_by_style(df: DataFrame, n_clusters: int = 5, min_minutes: float = 100.0) -> tuple:
    """
    Agrupa jugadores por estilo de juego usando K-Means.

    Features usadas:
    - Puntos promedio
    - Rebotes promedio
    - Asistencias promedio
    - TS% (eficiencia de tiro)
    - Usage Rate
    - Three Point Rate
    - AST/TOV ratio

    Args:
        df: DataFrame con métricas de jugadores agregadas
        n_clusters: Número de clusters a crear
        min_minutes: Minutos mínimos para incluir jugador

    Returns:
        Tupla (df_with_clusters, model, cluster_centers)
    """
    logger.info(f"Clustering de jugadores en {n_clusters} grupos...")

    # Filtrar jugadores con mínimo de minutos
    df_filtered = df.filter(col("minutos_totales") >= min_minutes)

    # Features para clustering
    feature_cols = [
        "puntos_promedio",
        "rebotes_promedio",
        "asistencias_promedio",
        "ts_percentage_avg",
        "usage_rate_simple",
        "three_point_rate",
        "ast_to_tov_avg"
    ]

    # Preparar features
    df_prepared = prepare_features_for_clustering(df_filtered, feature_cols)

    # K-Means clustering
    kmeans = KMeans(
        k=n_clusters,
        seed=42,
        featuresCol="scaled_features",
        predictionCol="cluster"
    )

    model = kmeans.fit(df_prepared)
    df_clustered = model.transform(df_prepared)

    # Obtener centros de clusters
    centers = model.clusterCenters()

    logger.info(f"✅ Clustering completado. {df_clustered.count()} jugadores agrupados")

    return df_clustered, model, centers


def interpret_player_clusters(df_clustered: DataFrame) -> DataFrame:
    """
    Interpreta y etiqueta los clusters de jugadores basándose en características.

    Args:
        df_clustered: DataFrame con columna 'cluster'

    Returns:
        DataFrame con etiquetas interpretables
    """
    logger.info("Interpretando clusters de jugadores...")

    # Calcular promedios por cluster
    cluster_profiles = (df_clustered
                        .groupBy("cluster")
                        .agg({
                            "puntos_promedio": "avg",
                            "rebotes_promedio": "avg",
                            "asistencias_promedio": "avg",
                            "ts_percentage_avg": "avg",
                            "three_point_rate": "avg"
                        }))

    cluster_profiles.show()

    # Añadir etiquetas interpretables (esto es un ejemplo, ajustar según resultados)
    df_labeled = (df_clustered
                  .withColumn(
                      "cluster_label",
                      when(col("cluster") == 0, "Scorers")
                      .when(col("cluster") == 1, "Playmakers")
                      .when(col("cluster") == 2, "Big Men")
                      .when(col("cluster") == 3, "3&D Wings")
                      .when(col("cluster") == 4, "Role Players")
                      .otherwise("Unknown")
                  ))

    return df_labeled


def cluster_teams_by_style(df_team_avg: DataFrame, n_clusters: int = 3) -> tuple:
    """
    Agrupa equipos por estilo de juego.

    Features usadas:
    - Pace (velocidad)
    - 3PA per game (dependencia del triple)
    - Assist rate (ball movement)
    - eFG% (eficiencia)
    - TOV% (cuidado del balón)

    Args:
        df_team_avg: DataFrame con promedios de equipo
        n_clusters: Número de clusters

    Returns:
        Tupla (df_with_clusters, model)
    """
    logger.info(f"Clustering de equipos en {n_clusters} estilos...")

    feature_cols = [
        "pace_avg",
        "t3pa_per_game",
        "ast_per_game",
        "efg_percent_avg",
        "tov_percent_avg"
    ]

    # Preparar features
    df_prepared = prepare_features_for_clustering(df_team_avg, feature_cols)

    # K-Means
    kmeans = KMeans(
        k=n_clusters,
        seed=42,
        featuresCol="scaled_features",
        predictionCol="style_cluster"
    )

    model = kmeans.fit(df_prepared)
    df_clustered = model.transform(df_prepared)

    logger.info(f"✅ Equipos agrupados en {n_clusters} estilos")

    return df_clustered, model


def interpret_team_clusters(df_clustered: DataFrame) -> DataFrame:
    """
    Interpreta clusters de equipos y asigna etiquetas de estilo.

    Estilos típicos:
    - "Pace & Space": Rápido + muchos triples
    - "Grind It Out": Lento + pocos triples + interior
    - "Balanced": Mezcla equilibrada
    - "Run & Gun": Muy rápido
    - "Euro Style": Ball movement alto + triples moderados

    Args:
        df_clustered: DataFrame con clusters

    Returns:
        DataFrame con etiquetas de estilo
    """
    logger.info("Interpretando estilos de equipos...")

    # Analizar características de cada cluster
    cluster_profiles = (df_clustered
                        .groupBy("style_cluster")
                        .agg({
                            "pace_avg": "avg",
                            "t3pa_per_game": "avg",
                            "ast_per_game": "avg",
                            "efg_percent_avg": "avg"
                        }))

    cluster_profiles.show()

    # Etiquetar (ajustar según resultados reales)
    df_labeled = (df_clustered
                  .withColumn(
                      "style_label",
                      when(col("style_cluster") == 0, "Pace & Space")
                      .when(col("style_cluster") == 1, "Traditional")
                      .when(col("style_cluster") == 2, "Balanced")
                      .otherwise("Unknown")
                  ))

    return df_labeled


def find_similar_players(df_clustered: DataFrame, player_id: int, top_n: int = 5) -> DataFrame:
    """
    Encuentra jugadores similares basándose en el cluster.

    Args:
        df_clustered: DataFrame con clusters
        player_id: ID del jugador de referencia
        top_n: Número de jugadores similares a retornar

    Returns:
        DataFrame con jugadores similares
    """
    logger.info(f"Buscando jugadores similares a {player_id}...")

    # Obtener cluster del jugador objetivo
    target_cluster = (df_clustered
                      .filter(col("player_id") == player_id)
                      .select("cluster")
                      .collect()[0][0])

    # Jugadores en el mismo cluster (excluyendo el jugador objetivo)
    similar = (df_clustered
               .filter((col("cluster") == target_cluster) & (col("player_id") != player_id))
               .select("player_id", "nombre", "equipo",
                       "puntos_promedio", "rebotes_promedio", "asistencias_promedio",
                       "ts_percentage_avg", "cluster_label")
               .limit(top_n))

    return similar


def get_cluster_statistics(df_clustered: DataFrame) -> DataFrame:
    """
    Genera estadísticas descriptivas de cada cluster.

    Args:
        df_clustered: DataFrame con clusters

    Returns:
        DataFrame con stats por cluster
    """
    logger.info("Generando estadísticas de clusters...")

    from pyspark.sql.functions import count, avg, stddev, min as spark_min, max as spark_max

    stats = (df_clustered
             .groupBy("cluster", "cluster_label")
             .agg(
                 count("player_id").alias("num_players"),
                 avg("puntos_promedio").alias("avg_points"),
                 stddev("puntos_promedio").alias("std_points"),
                 avg("ts_percentage_avg").alias("avg_ts"),
                 avg("usage_rate_simple").alias("avg_usage"),
                 spark_min("puntos_promedio").alias("min_points"),
                 spark_max("puntos_promedio").alias("max_points")
             )
             .orderBy("cluster"))

    return stats


def hierarchical_clustering_players(df: DataFrame, min_minutes: float = 100.0) -> DataFrame:
    """
    Clustering jerárquico usando BisectingKMeans (más interpretable).

    Args:
        df: DataFrame con métricas de jugadores
        min_minutes: Minutos mínimos

    Returns:
        DataFrame con clusters jerárquicos
    """
    logger.info("Clustering jerárquico de jugadores...")

    df_filtered = df.filter(col("minutos_totales") >= min_minutes)

    feature_cols = [
        "puntos_promedio",
        "rebotes_promedio",
        "asistencias_promedio",
        "ts_percentage_avg"
    ]

    df_prepared = prepare_features_for_clustering(df_filtered, feature_cols)

    # BisectingKMeans (división jerárquica)
    bisect_km = BisectingKMeans(
        k=5,
        seed=42,
        featuresCol="scaled_features",
        predictionCol="hierarchical_cluster"
    )

    model = bisect_km.fit(df_prepared)
    df_clustered = model.transform(df_prepared)

    logger.info("✅ Clustering jerárquico completado")

    return df_clustered
