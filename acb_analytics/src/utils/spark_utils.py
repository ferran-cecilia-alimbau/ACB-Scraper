"""
Utilidades para configuración y operaciones comunes de PySpark.
"""
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql import DataFrame
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, BooleanType
import logging

logger = logging.getLogger(__name__)


def create_spark_session(app_name: str = "ACB Analytics",
                         memory: str = "4g",
                         cores: str = "*") -> SparkSession:
    """
    Crea y configura una sesión de Spark optimizada para análisis.

    Args:
        app_name: Nombre de la aplicación Spark
        memory: Memoria para el executor (ej: "4g", "8g")
        cores: Número de cores a usar ("*" para todos)

    Returns:
        SparkSession configurada
    """
    spark = (SparkSession.builder
             .appName(app_name)
             .config("spark.driver.memory", memory)
             .config("spark.executor.memory", memory)
             .config("spark.sql.shuffle.partitions", "200")
             .config("spark.default.parallelism", cores)
             .config("spark.sql.adaptive.enabled", "true")
             .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
             .getOrCreate())

    logger.info(f"Spark session creada: {app_name}")
    logger.info(f"Spark version: {spark.version}")

    return spark


def get_schema_player_stats() -> StructType:
    """
    Define el schema para estadísticas de jugadores.

    Returns:
        StructType con el schema completo
    """
    return StructType([
        StructField("id_partido", IntegerType(), False),
        StructField("player_id", IntegerType(), False),
        StructField("equipo", StringType(), False),
        StructField("es_titular", BooleanType(), True),
        StructField("dorsal", StringType(), True),
        StructField("nombre", StringType(), True),
        StructField("minutos", StringType(), True),
        StructField("puntos", IntegerType(), True),
        StructField("t2_intentados", IntegerType(), True),
        StructField("t2_anotados", IntegerType(), True),
        StructField("t2_porcentaje", FloatType(), True),
        StructField("t3_intentados", IntegerType(), True),
        StructField("t3_anotados", IntegerType(), True),
        StructField("t3_porcentaje", FloatType(), True),
        StructField("tl_intentados", IntegerType(), True),
        StructField("tl_anotados", IntegerType(), True),
        StructField("tl_porcentaje", FloatType(), True),
        StructField("rebotes_defensivos", IntegerType(), True),
        StructField("rebotes_ofensivos", IntegerType(), True),
        StructField("rebotes_totales", IntegerType(), True),
        StructField("asistencias", IntegerType(), True),
        StructField("robos", IntegerType(), True),
        StructField("perdidas", IntegerType(), True),
        StructField("tapones_favor", IntegerType(), True),
        StructField("tapones_contra", IntegerType(), True),
        StructField("mates", IntegerType(), True),
        StructField("faltas_cometidas", IntegerType(), True),
        StructField("faltas_recibidas", IntegerType(), True),
        StructField("plus_minus", IntegerType(), True),
        StructField("valoracion", IntegerType(), True),
    ])


def get_schema_game_info() -> StructType:
    """Schema para información de partidos."""
    return StructType([
        StructField("id_partido", IntegerType(), False),
        StructField("jornada", StringType(), True),
        StructField("fecha", StringType(), True),
        StructField("hora", StringType(), True),
        StructField("pabellon", StringType(), True),
        StructField("publico", StringType(), True),
        StructField("arbitro1", StringType(), True),
        StructField("arbitro2", StringType(), True),
        StructField("arbitro3", StringType(), True),
        StructField("resultado_local", StringType(), True),
        StructField("resultado_visitante", StringType(), True),
        StructField("local", StringType(), True),
        StructField("visitante", StringType(), True),
        StructField("parciales_local", StringType(), True),
        StructField("parciales_visitante", StringType(), True),
    ])


def load_csv_to_spark(spark: SparkSession,
                      filepath: str,
                      schema: StructType = None,
                      header: bool = True) -> DataFrame:
    """
    Carga un CSV a DataFrame de Spark con el schema especificado.

    Args:
        spark: Sesión de Spark
        filepath: Ruta del archivo CSV
        schema: Schema opcional (si no se provee, se infiere)
        header: Si el CSV tiene header

    Returns:
        DataFrame de Spark
    """
    if not Path(filepath).exists():
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

    reader = spark.read.format("csv").option("header", str(header).lower())

    if schema:
        reader = reader.schema(schema)
    else:
        reader = reader.option("inferSchema", "true")

    df = reader.load(filepath)
    logger.info(f"Cargado {filepath}: {df.count()} filas, {len(df.columns)} columnas")

    return df


def save_to_parquet(df: DataFrame, output_path: str, mode: str = "overwrite"):
    """
    Guarda un DataFrame en formato Parquet.

    Args:
        df: DataFrame de Spark
        output_path: Ruta de salida
        mode: Modo de escritura (overwrite, append, error, ignore)
    """
    df.write.mode(mode).parquet(output_path)
    logger.info(f"Guardado en Parquet: {output_path}")


def convert_minutes_to_float(df: DataFrame, column: str = "minutos") -> DataFrame:
    """
    Convierte formato de minutos 'MM:SS' a float (minutos decimales).

    Args:
        df: DataFrame con columna de minutos
        column: Nombre de la columna de minutos

    Returns:
        DataFrame con nueva columna '{column}_float'
    """
    from pyspark.sql.functions import col, split, when

    return df.withColumn(
        f"{column}_float",
        when(col(column).isNotNull(),
             split(col(column), ":").getItem(0).cast("int") +
             split(col(column), ":").getItem(1).cast("int") / 60.0
        ).otherwise(0.0)
    )


def calculate_field_goal_attempts(df: DataFrame) -> DataFrame:
    """
    Calcula FGA (Field Goal Attempts) total = t2_intentados + t3_intentados.

    Args:
        df: DataFrame con estadísticas de jugadores

    Returns:
        DataFrame con columna 'fga'
    """
    from pyspark.sql.functions import col, coalesce, lit

    return df.withColumn(
        "fga",
        coalesce(col("t2_intentados"), lit(0)) +
        coalesce(col("t3_intentados"), lit(0))
    )


def calculate_field_goals_made(df: DataFrame) -> DataFrame:
    """
    Calcula FGM (Field Goals Made) total = t2_anotados + t3_anotados.

    Args:
        df: DataFrame con estadísticas de jugadores

    Returns:
        DataFrame con columna 'fgm'
    """
    from pyspark.sql.functions import col, coalesce, lit

    return df.withColumn(
        "fgm",
        coalesce(col("t2_anotados"), lit(0)) +
        coalesce(col("t3_anotados"), lit(0))
    )


def show_dataframe_info(df: DataFrame, name: str = "DataFrame"):
    """
    Muestra información útil sobre un DataFrame.

    Args:
        df: DataFrame de Spark
        name: Nombre descriptivo del DataFrame
    """
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"Filas: {df.count():,}")
    print(f"Columnas: {len(df.columns)}")
    print(f"\nSchema:")
    df.printSchema()
    print(f"\nPrimeras 5 filas:")
    df.show(5, truncate=False)
    print(f"{'='*60}\n")
