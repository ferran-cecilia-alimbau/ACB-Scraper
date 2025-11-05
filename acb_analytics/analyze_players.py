#!/usr/bin/env python3
"""
Script principal para análisis avanzado de jugadores ACB con PySpark.

Uso:
    python analyze_players.py

Genera:
    - Métricas avanzadas por jugador (TS%, eFG%, PER, etc.)
    - Top performers en cada categoría
    - Resumen estadístico agregado por jugador
    - Exporta resultados a CSV y Parquet
"""
import sys
from pathlib import Path
import logging

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.spark_utils import (
    create_spark_session,
    load_csv_to_spark,
    save_to_parquet,
    show_dataframe_info,
    get_schema_player_stats
)
from metrics.player_metrics import (
    calculate_all_advanced_metrics,
    get_player_summary_stats
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Función principal del análisis."""
    print("\n" + "="*80)
    print("  🏀 ACB ADVANCED ANALYTICS - Análisis de Jugadores")
    print("="*80 + "\n")

    # Crear sesión Spark
    spark = create_spark_session(app_name="ACB Player Analytics", memory="4g")

    try:
        # ==================================================
        # PASO 1: Cargar datos
        # ==================================================
        print("\n📂 PASO 1: Cargando datos...")

        data_path = Path(__file__).parent.parent / "data" / "output" / "estadisticas_todos_partidos.csv"

        if not data_path.exists():
            logger.error(f"❌ No se encontró el archivo de datos: {data_path}")
            logger.info("💡 Ejecuta primero el scraper para generar datos")
            logger.info("   Comando: python main.py")
            return

        # Cargar datos con schema definido
        df_players = load_csv_to_spark(
            spark,
            str(data_path),
            schema=None,  # Dejar que infiera por ahora
            header=True
        )

        show_dataframe_info(df_players, "Estadísticas de Jugadores")

        # ==================================================
        # PASO 2: Calcular métricas avanzadas
        # ==================================================
        print("\n📊 PASO 2: Calculando métricas avanzadas...")

        df_with_metrics = calculate_all_advanced_metrics(df_players)

        # Mostrar sample con métricas
        print("\n✨ Sample de métricas calculadas:")
        df_with_metrics.select(
            "nombre", "equipo", "puntos", "minutos_float",
            "ts_percentage", "efg_percentage", "per_simple",
            "ast_to_tov", "usage_rate_simple"
        ).show(10, truncate=False)

        # ==================================================
        # PASO 3: Agregar estadísticas por jugador
        # ==================================================
        print("\n📈 PASO 3: Generando resumen por jugador...")

        df_summary = get_player_summary_stats(df_with_metrics, min_minutes=50.0)

        print("\n🏆 TOP 20 JUGADORES POR PER:")
        df_summary.select(
            "nombre", "equipo", "partidos_jugados",
            "puntos_promedio", "rebotes_promedio", "asistencias_promedio",
            "ts_percentage_avg", "per_avg"
        ).show(20, truncate=False)

        # ==================================================
        # PASO 4: Top performers por categoría
        # ==================================================
        print("\n" + "="*80)
        print("  🌟 TOP PERFORMERS POR CATEGORÍA")
        print("="*80)

        categories = [
            ("🎯 SCORING EFFICIENCY (TS%)", "ts_percentage_avg", 10),
            ("🔥 OVERALL PERFORMANCE (PER)", "per_avg", 10),
            ("🏃 USAGE LEADERS", "usage_rate_avg", 10),
            ("🎨 PLAYMAKERS (AST/TOV)", "ast_to_tov_avg", 10),
            ("📊 SCORING VOLUME", "puntos_promedio", 10),
            ("🔄 REBOUNDING", "rebotes_promedio", 10),
        ]

        for title, column, n in categories:
            print(f"\n{title}:")
            (df_summary
             .select("nombre", "equipo", "partidos_jugados", column)
             .orderBy(df_summary[column].desc())
             .show(n, truncate=False))

        # ==================================================
        # PASO 5: Exportar resultados
        # ==================================================
        print("\n💾 PASO 5: Exportando resultados...")

        output_dir = Path(__file__).parent / "outputs"
        output_dir.mkdir(exist_ok=True)

        # Guardar datos completos con métricas
        parquet_path = output_dir / "player_stats_with_metrics.parquet"
        save_to_parquet(df_with_metrics, str(parquet_path))

        # Guardar resumen en CSV para fácil lectura
        csv_path = output_dir / "player_summary.csv"
        (df_summary
         .coalesce(1)  # Un solo archivo
         .write
         .mode("overwrite")
         .option("header", "true")
         .csv(str(csv_path)))

        logger.info(f"✅ Datos guardados en: {output_dir}")
        logger.info(f"   - Parquet: {parquet_path}")
        logger.info(f"   - CSV: {csv_path}")

        # ==================================================
        # Resumen final
        # ==================================================
        print("\n" + "="*80)
        print("  ✅ ANÁLISIS COMPLETADO")
        print("="*80)
        print(f"\n📊 Total de jugadores analizados: {df_summary.count()}")
        print(f"📁 Resultados guardados en: {output_dir}")
        print("\n💡 Próximos pasos:")
        print("   1. Revisar outputs/player_summary.csv")
        print("   2. Explorar notebooks/ para análisis interactivos")
        print("   3. Ver docs de métricas en src/metrics/player_metrics.py")
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
