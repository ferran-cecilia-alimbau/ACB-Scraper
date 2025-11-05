#!/usr/bin/env python3
"""
Script de análisis avanzado COMPLETO para ACB con PySpark.

Incluye:
- Métricas avanzadas de jugadores
- Métricas de equipos (Four Factors, Pace, etc.)
- Análisis de quintetos óptimos
- Clustering de estilos de juego
- Análisis de consistencia y streaks
- Exporta todos los resultados

Uso:
    python analyze_advanced.py
"""
import sys
from pathlib import Path
import logging
from pyspark.sql.functions import col

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.spark_utils import (
    create_spark_session,
    load_csv_to_spark,
    save_to_parquet,
    show_dataframe_info,
    convert_minutes_to_float,
    calculate_field_goal_attempts,
    calculate_field_goals_made
)
from metrics.player_metrics import calculate_all_advanced_metrics, get_player_summary_stats
from metrics.team_metrics import calculate_all_team_metrics
from models.lineup_analysis import (
    identify_lineups_from_starters,
    calculate_lineup_performance,
    get_best_lineups_by_plus_minus
)
from models.clustering import cluster_players_by_style, cluster_teams_by_style
from models.consistency_analysis import (
    calculate_consistency_metrics,
    detect_scoring_streaks,
    identify_hot_hand_players,
    calculate_player_volatility
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Función principal con análisis completo."""
    print("\n" + "="*80)
    print("  🏀 ACB ADVANCED ANALYTICS - Análisis Completo")
    print("="*80 + "\n")

    # Crear sesión Spark
    spark = create_spark_session(app_name="ACB Advanced Analytics", memory="4g")

    try:
        # ==================================================
        # PASO 1: Cargar datos
        # ==================================================
        print("\n📂 PASO 1: Cargando datos...")

        data_path = Path(__file__).parent.parent / "data" / "output" / "estadisticas_todos_partidos.csv"

        if not data_path.exists():
            logger.error(f"❌ No se encontró el archivo de datos: {data_path}")
            logger.info("💡 Ejecuta primero el scraper")
            return 1

        df_players = load_csv_to_spark(spark, str(data_path), header=True)

        # ==================================================
        # PASO 2: Métricas avanzadas de jugadores
        # ==================================================
        print("\n📊 PASO 2: Calculando métricas avanzadas de jugadores...")

        df_with_metrics = calculate_all_advanced_metrics(df_players)
        df_player_summary = get_player_summary_stats(df_with_metrics, min_minutes=50.0)

        print("\n🏆 TOP 10 JUGADORES POR PER:")
        df_player_summary.select(
            "nombre", "equipo", "partidos_jugados",
            "puntos_promedio", "ts_percentage_avg", "per_avg"
        ).show(10, truncate=False)

        # ==================================================
        # PASO 3: Métricas de equipos
        # ==================================================
        print("\n🏛️ PASO 3: Calculando métricas de equipos...")

        df_team_totals, df_team_avg = calculate_all_team_metrics(df_with_metrics)

        print("\n📈 EQUIPOS - FOUR FACTORS:")
        df_team_avg.select(
            "equipo", "games_played", "ppg",
            "efg_percent_avg", "tov_percent_avg", "ft_rate_avg", "pace_avg"
        ).show(truncate=False)

        print("\n🎨 ESTILOS DE JUEGO:")
        df_team_avg.select(
            "equipo", "style_pace", "style_shooting", "style_offense"
        ).show(truncate=False)

        # ==================================================
        # PASO 4: Análisis de quintetos
        # ==================================================
        print("\n👥 PASO 4: Analizando quintetos óptimos...")

        df_lineups = identify_lineups_from_starters(df_with_metrics)
        df_lineup_stats = calculate_lineup_performance(df_lineups)
        df_best_lineups = get_best_lineups_by_plus_minus(df_lineup_stats, top_n=10)

        print("\n🔥 TOP 10 QUINTETOS POR +/-:")
        df_best_lineups.select(
            "equipo", "games_played", "avg_plus_minus", "avg_points", "player_names"
        ).show(10, truncate=False)

        # ==================================================
        # PASO 5: Clustering de jugadores
        # ==================================================
        print("\n🎨 PASO 5: Clustering de jugadores por estilo...")

        df_clustered_players, kmeans_model, centers = cluster_players_by_style(
            df_player_summary, n_clusters=5, min_minutes=100.0
        )

        print("\n📊 DISTRIBUCIÓN DE JUGADORES POR CLUSTER:")
        df_clustered_players.groupBy("cluster").count().show()

        print("\n💡 EJEMPLO DE JUGADORES POR CLUSTER:")
        for cluster_id in range(5):
            print(f"\n--- Cluster {cluster_id} ---")
            (df_clustered_players
             .filter(col("cluster") == cluster_id)
             .select("nombre", "equipo", "puntos_promedio", "rebotes_promedio", "asistencias_promedio")
             .show(5, truncate=False))

        # ==================================================
        # PASO 6: Clustering de equipos
        # ==================================================
        print("\n🏛️ PASO 6: Clustering de equipos por estilo...")

        df_clustered_teams, team_kmeans = cluster_teams_by_style(df_team_avg, n_clusters=3)

        print("\n🎯 EQUIPOS AGRUPADOS POR ESTILO:")
        df_clustered_teams.select("equipo", "style_cluster", "pace_avg", "3pa_per_game", "ast_per_game").show(truncate=False)

        # ==================================================
        # PASO 7: Análisis de consistencia
        # ==================================================
        print("\n📈 PASO 7: Analizando consistencia de jugadores...")

        df_consistency = calculate_consistency_metrics(df_with_metrics)

        print("\n🎯 JUGADORES MÁS CONSISTENTES (menor CV):")
        df_consistency.filter(col("games") >= 10).orderBy("cv_points").select(
            "nombre", "equipo", "avg_points", "std_points", "cv_points", "consistency_score"
        ).show(10, truncate=False)

        print("\n🎲 JUGADORES MÁS VOLÁTILES (mayor CV):")
        df_consistency.filter(col("games") >= 10).orderBy(col("cv_points").desc()).select(
            "nombre", "equipo", "avg_points", "std_points", "cv_points"
        ).show(10, truncate=False)

        # ==================================================
        # PASO 8: Volatilidad
        # ==================================================
        print("\n⚡ PASO 8: Calculando volatilidad...")

        df_volatility = calculate_player_volatility(df_with_metrics)

        print("\n📊 DISTRIBUCIÓN DE VOLATILIDAD:")
        df_volatility.groupBy("player_type").count().show()

        # ==================================================
        # PASO 9: Detección de rachas
        # ==================================================
        print("\n🔥 PASO 9: Detectando rachas (hot hands)...")

        df_streaks = detect_scoring_streaks(df_with_metrics, streak_threshold=1.3)
        df_hot_players = identify_hot_hand_players(df_streaks, min_streak_games=3)

        print(f"\n🌡️ JUGADORES EN RACHA CALIENTE (últimos 3 partidos):")
        df_hot_players.select(
            "nombre", "equipo", "recent_games", "recent_avg_points", "recent_ts"
        ).show(truncate=False)

        # ==================================================
        # PASO 10: Exportar resultados
        # ==================================================
        print("\n💾 PASO 10: Exportando resultados...")

        output_dir = Path(__file__).parent / "outputs"
        output_dir.mkdir(exist_ok=True)

        # Guardar todos los análisis
        outputs = {
            "player_metrics": df_with_metrics,
            "player_summary": df_player_summary,
            "team_totals": df_team_totals,
            "team_averages": df_team_avg,
            "lineup_stats": df_lineup_stats,
            "player_clusters": df_clustered_players,
            "team_clusters": df_clustered_teams,
            "consistency": df_consistency,
            "volatility": df_volatility,
            "hot_hands": df_hot_players
        }

        for name, df_output in outputs.items():
            parquet_path = output_dir / f"{name}.parquet"
            save_to_parquet(df_output, str(parquet_path))
            logger.info(f"✅ Guardado: {parquet_path}")

        # También guardar CSVs de resúmenes clave
        csv_exports = {
            "player_summary": df_player_summary,
            "team_summary": df_team_avg,
            "top_lineups": df_best_lineups,
            "consistency_leaders": df_consistency.filter(col("games") >= 10).orderBy("cv_points").limit(50)
        }

        for name, df_csv in csv_exports.items():
            csv_path = output_dir / f"{name}.csv"
            (df_csv
             .coalesce(1)
             .write
             .mode("overwrite")
             .option("header", "true")
             .csv(str(csv_path)))
            logger.info(f"✅ CSV guardado: {csv_path}")

        # ==================================================
        # Resumen final
        # ==================================================
        print("\n" + "="*80)
        print("  ✅ ANÁLISIS COMPLETO FINALIZADO")
        print("="*80)
        print(f"\n📊 Resumen:")
        print(f"   - {df_player_summary.count()} jugadores analizados")
        print(f"   - {df_team_avg.count()} equipos analizados")
        print(f"   - {df_lineup_stats.count()} quintetos únicos identificados")
        print(f"   - {df_hot_players.count()} jugadores en racha caliente")
        print(f"\n📁 Todos los resultados guardados en: {output_dir}")
        print("\n💡 Archivos generados:")
        print("   - Parquet: player_metrics, team_averages, lineup_stats, etc.")
        print("   - CSV: player_summary.csv, team_summary.csv, top_lineups.csv")
        print("\n🚀 Próximos pasos:")
        print("   - Explorar outputs/ con Jupyter notebooks")
        print("   - Importar CSVs a Excel/Tableau para visualización")
        print("   - Usar datos para modelos predictivos")
        print("\n")

    except Exception as e:
        logger.error(f"❌ Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Cerrar sesión Spark
        spark.stop()
        logger.info("Sesión Spark cerrada")

    return 0


if __name__ == "__main__":
    sys.exit(main())
