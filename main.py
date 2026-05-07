"""
Punto de entrada principal para el ACB Scraper.

Este módulo coordina el proceso de scraping, cargando la configuración,
procesando los partidos y almacenando los resultados.
"""
import json
import pandas as pd
import asyncio
import argparse
import os
import sys
import tempfile
from typing import Dict, Any, List, Set, Tuple, TypeAlias, Optional
from dataclasses import dataclass
import logging

import constants as const
from logger import setup_logger
from scraper import process_games

# Configurar logger
logger = setup_logger(console_level=logging.INFO)

# Tipos personalizados para mejorar la legibilidad
DataFrameDict: TypeAlias = Dict[str, pd.DataFrame]
IdSetDict: TypeAlias = Dict[str, Set[int]]


@dataclass
class FileConfig:
    """Configuración para cada tipo de archivo de datos."""
    id_column: str
    columns_key: str


# Configuración de los archivos de datos
FILE_CONFIGS = {
    'output_file': FileConfig('player_id', 'columns_players'),
    'output_file_game': FileConfig('id_partido', 'columns_games'),
    'output_file_team_totals': FileConfig('id_partido', 'columns_team_totals'),
    'output_file_player_profiles': FileConfig('player_id', 'columns_player_profiles')
}

# Mapeo de claves internas a claves de columnas en config.json
COLUMN_KEYS = {
    'output_file': 'columns_players',
    'output_file_game': 'columns_games',
    'output_file_team_totals': 'columns_team_totals',
    'output_file_player_profiles': 'columns_player_profiles'
}


def load_config(filename: str = const.CONFIG_FILE) -> Dict[str, Any]:
    """
    Carga la configuración desde un archivo JSON.

    Args:
        filename: Ruta del archivo de configuración

    Returns:
        Diccionario con la configuración

    Raises:
        FileNotFoundError: Si no se encuentra el archivo
        json.JSONDecodeError: Si el archivo no es un JSON válido
    """
    if not filename or not isinstance(filename, str):
        error_msg = "El nombre del archivo de configuración debe ser una cadena válida"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        with open(filename, 'r', encoding='utf-8') as file:
            config = json.load(file)

        logger.info(f"Configuración cargada exitosamente desde {filename}")

        # Validar configuración mínima requerida
        required_keys = [
            'base_url', 'output_file', 'output_file_game',
            'output_file_team_totals', 'output_file_player_profiles',
            'id_columns', 'columns_players', 'columns_games',
            'columns_team_totals', 'columns_player_profiles'
        ]
        missing_keys = [key for key in required_keys if key not in config]

        if missing_keys:
            error_msg = f"Faltan claves requeridas en la configuración: {missing_keys}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validar que id_columns tenga las claves necesarias
        required_id_columns = [
            'output_file', 'output_file_game',
            'output_file_team_totals', 'output_file_player_profiles'
        ]
        if 'id_columns' in config:
            missing_id_cols = [key for key in required_id_columns if key not in config['id_columns']]
            if missing_id_cols:
                error_msg = f"Faltan claves en 'id_columns': {missing_id_cols}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error al cargar la configuración desde {filename}: {str(e)}")
        raise


def load_match_ids(filename: str = const.MATCH_IDS_FILE) -> List[int]:
    """
    Carga los IDs de partidos desde un archivo JSON.

    Args:
        filename: Ruta del archivo de IDs

    Returns:
        Lista de IDs de partidos

    Raises:
        FileNotFoundError: Si no se encuentra el archivo
        json.JSONDecodeError: Si el archivo no es un JSON válido
    """
    if not filename or not isinstance(filename, str):
        error_msg = "El nombre del archivo de IDs debe ser una cadena válida"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        with open(filename, 'r', encoding='utf-8') as file:
            data = json.load(file)

        match_ids = data.get('match_ids', [])

        if not match_ids:
            logger.warning(f"No se encontraron IDs de partidos en {filename}")

        # Validar que todos los IDs son enteros
        if not all(isinstance(id, int) for id in match_ids):
            logger.warning("Algunos IDs no son enteros. Convertiendo a enteros.")
            match_ids = [int(id) for id in match_ids if str(id).isdigit()]

        logger.info(f"Cargados {len(match_ids)} IDs de partidos desde {filename}")
        return match_ids
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error al cargar los IDs de partidos desde {filename}: {str(e)}")
        raise


def ensure_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """
    Asegura que el DataFrame contiene todas las columnas especificadas.

    Args:
        df: DataFrame a modificar
        columns: Lista de columnas que debe contener

    Returns:
        DataFrame con las columnas especificadas
    """
    if df is None or columns is None:
        logger.error("DataFrame o lista de columnas es None")
        return pd.DataFrame(columns=columns if columns else None)

    # Añadir columnas que falten
    for col in columns:
        if col not in df.columns:
            df[col] = ''

    # Reordenar y seleccionar solo las columnas especificadas
    return df[columns]


def load_single_file(
    filename: str,
    id_column: str,
    columns: Optional[List[str]]
) -> Tuple[pd.DataFrame, Set[int]]:
    """
    Carga un archivo CSV y extrae los IDs únicos.

    Args:
        filename: Ruta del archivo CSV
        id_column: Nombre de la columna de ID
        columns: Lista de columnas que debe contener

    Returns:
        Tupla con DataFrame y conjunto de IDs
    """
    if not filename or not id_column:
        logger.error("Nombre de archivo o columna de ID vacíos")
        return pd.DataFrame(columns=columns if columns else None), set()

    try:
        # Verificar si el archivo existe
        if not os.path.exists(filename):
            logger.info(f"Archivo {filename} no encontrado. Creando uno nuevo.")
            return pd.DataFrame(columns=columns if columns else None), set()

        # Cargar el archivo
        df = pd.read_csv(filename)

        # Si hay columnas especificadas, asegurar que estén en el DataFrame
        if columns:
            df = ensure_columns(df, columns)

        # Extraer IDs únicos
        if id_column in df.columns:
            ids = set(pd.to_numeric(df[id_column], errors='coerce').dropna().astype(int))
            logger.info(f"Cargados {len(ids)} IDs desde {filename}")
        else:
            logger.warning(f"Columna {id_column} no encontrada en {filename}")
            ids = set()

        return df, ids
    except pd.errors.EmptyDataError:
        logger.warning(f"Archivo {filename} está vacío")
        return pd.DataFrame(columns=columns if columns else None), set()
    except (OSError, pd.errors.ParserError):
        logger.exception(f"Error al cargar {filename}")
        return pd.DataFrame(columns=columns if columns else None), set()


def load_existing_data(config: Dict[str, Any]) -> Tuple[DataFrameDict, IdSetDict]:
    """
    Carga los datos existentes de todos los archivos configurados.

    Args:
        config: Configuración del scraper

    Returns:
        Tupla con diccionarios de DataFrames e IDs
    """
    dataframes: DataFrameDict = {}
    existing_ids: IdSetDict = {}

    # Procesar cada configuración de archivo
    for file_key, file_config in FILE_CONFIGS.items():
        filename = config.get(file_key)

        if not filename:
            logger.warning(f"Clave '{file_key}' no encontrada en la configuración")
            continue

        # Obtener la lista de columnas para este tipo de archivo
        columns = config.get(file_config.columns_key)

        # Cargar el archivo y extraer IDs
        df, ids = load_single_file(filename, file_config.id_column, columns)

        # Almacenar resultados
        dataframes[file_key] = df
        existing_ids[file_key] = ids

    return dataframes, existing_ids


def save_to_csv(data: pd.DataFrame, output_file: str) -> bool:
    """
    Guarda un DataFrame en un archivo CSV.

    Args:
        data: DataFrame a guardar
        output_file: Ruta del archivo de salida

    Returns:
        True si se guardó correctamente, False en caso contrario
    """
    if data is None or data.empty:
        logger.warning(f"DataFrame vacío. No se guardará el archivo {output_file}")
        return False

    try:
        # Crear directorio si no existe
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Guardar archivo de forma atomica para no dejar CSVs corruptos si el
        # proceso se corta durante una ejecucion automatizada.
        logger.info(f"Guardando datos en {output_file}. Shape del DataFrame: {data.shape}")
        fd, temp_path = tempfile.mkstemp(
            prefix=f".{os.path.basename(output_file)}.",
            suffix=".tmp",
            dir=output_dir or ".",
        )
        os.close(fd)
        try:
            data.to_csv(temp_path, index=False)
            os.replace(temp_path, output_file)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        logger.info(f"Datos guardados correctamente en {output_file}")
        return True
    except OSError:
        logger.exception(f"Error al guardar datos en {output_file}")
        return False


def extract_new_data(
    results: List[Dict[str, Any]],
    existing_profile_ids_set: Set[int]
) -> Dict[str, List]:
    """
    Extrae los nuevos datos de los resultados del scraping.

    Args:
        results: Resultados del scraping
        existing_profile_ids_set: Conjunto de IDs de perfiles existentes

    Returns:
        Diccionario con los nuevos datos organizados por tipo
    """
    new_data = {
        'output_file': [],
        'output_file_game': [],
        'output_file_team_totals': [],
        'output_file_player_profiles': []
    }

    # Procesar cada resultado
    for result in results:
        # Añadir estadísticas de jugadores
        new_data['output_file'].extend(result.get('player_stats', []))

        # Añadir información del partido
        if 'game_info' in result:
            new_data['output_file_game'].append(result['game_info'])

        # Añadir totales de equipos
        new_data['output_file_team_totals'].extend(result.get('team_totals', []))

        # Añadir perfiles de jugadores. El merge posterior actualiza por player_id.
        new_data['output_file_player_profiles'].extend(result.get('player_profiles', []))

    return new_data


def _profile_id_key(value: Any) -> str:
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value)


def merge_player_profiles(
    existing_df: pd.DataFrame,
    new_df: pd.DataFrame,
    columns: List[str]
) -> pd.DataFrame:
    """Actualiza perfiles por player_id sin borrar campos existentes con valores vacios."""
    existing = ensure_columns(existing_df.copy(), columns)
    updates = ensure_columns(new_df.copy(), columns)

    records = {}
    for _, row in existing.iterrows():
        player_id = row.get('player_id')
        if pd.isna(player_id) or str(player_id) == '':
            continue
        records[_profile_id_key(player_id)] = row.to_dict()

    for _, row in updates.iterrows():
        player_id = row.get('player_id')
        if pd.isna(player_id) or str(player_id) == '':
            continue

        key = _profile_id_key(player_id)
        current = records.get(key, {col: '' for col in columns})
        for col in columns:
            value = row.get(col, '')
            if col == 'player_id' or (pd.notna(value) and str(value) != ''):
                current[col] = value
        records[key] = current

    if not records:
        return pd.DataFrame(columns=columns)

    merged = pd.DataFrame(records.values())
    return ensure_columns(merged, columns).drop_duplicates(subset=['player_id'], keep='last')

def merge_and_deduplicate(
    dataframes: Dict[str, pd.DataFrame],
    new_data: Dict[str, List],
    config: Dict[str, Any]
) -> Dict[str, pd.DataFrame]:
    """
    Combina datos nuevos con existentes y elimina duplicados.

    Args:
        dataframes: DataFrames existentes
        new_data: Nuevos datos a añadir
        config: Configuración del scraper

    Returns:
        Diccionario con DataFrames actualizados
    """
    updated_dataframes = {}

    for key in new_data:
        if not new_data[key]:
            updated_dataframes[key] = dataframes[key]
            continue

        new_df = pd.DataFrame(new_data[key])

        # Asegurar que tiene las columnas requeridas
        columns_key = COLUMN_KEYS.get(key)
        if columns_key and columns_key in config:
            new_df = ensure_columns(new_df, config[columns_key])

        if key == 'output_file_player_profiles':
            updated_dataframes[key] = merge_player_profiles(
                dataframes[key], new_df, config[columns_key]
            )
            continue

        # Combinar con los datos existentes
        combined_df = pd.concat([dataframes[key], new_df], ignore_index=True)

        # Eliminar duplicados eficientemente
        # Solo hacemos drop_duplicates una vez sobre todo el DataFrame
        # pandas es lo suficientemente eficiente para manejar esto directamente
        logger.debug(f"Eliminando duplicados en DataFrame de {len(combined_df)} filas")
        combined_df = combined_df.drop_duplicates(
            subset=config['id_columns'][key],
            keep='last'
        )

        updated_dataframes[key] = combined_df

    return updated_dataframes


def _profile_ids_from_df(df: pd.DataFrame) -> Set[int]:
    """Extrae los player_id existentes como set[int]."""
    if df is None or df.empty or 'player_id' not in df.columns:
        return set()
    return set(int(value) for value in pd.to_numeric(df['player_id'], errors='coerce').dropna())


def process_and_save_data(
    config: Dict[str, Any],
    results: List[Dict[str, Any]],
    dataframes: Dict[str, pd.DataFrame]
) -> None:
    """
    Procesa los resultados del scraping y los guarda en archivos CSV.

    Args:
        config: Configuración del scraper
        results: Resultados del scraping
        dataframes: DataFrames existentes
    """
    if not results:
        logger.info("No hay resultados para procesar")
        return

    existing_profile_ids_set = _profile_ids_from_df(dataframes.get('output_file_player_profiles'))

    # Extraer nuevos datos
    new_data = extract_new_data(results, existing_profile_ids_set)

    # Combinar y deduplicar
    updated_dataframes = merge_and_deduplicate(dataframes, new_data, config)

    # Guardar cada tipo de datos
    for key, df in updated_dataframes.items():
        dataframes[key] = df
        save_to_csv(df, config[key])

    logger.info("Procesamiento y guardado de datos completado")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scraper de estadisticas ACB")
    parser.add_argument(
        "--only",
        nargs="+",
        type=int,
        metavar="ID",
        help="Procesar solo estos IDs, manteniendo la configuracion y CSVs actuales.",
    )
    return parser.parse_args()


async def main(match_ids_override: Optional[List[int]] = None):
    """
    Función principal que coordina el proceso de scraping.
    """
    try:
        # Cargar configuración
        config = load_config()

        # Cargar IDs de partidos. El fichero completo se mantiene como fuente
        # de orden/jornada aunque el orquestador pida procesar solo unos IDs.
        configured_match_ids = load_match_ids()
        match_ids = match_ids_override if match_ids_override is not None else configured_match_ids

        # ACB Live ya no expone la jornada en la ficha del partido. El input
        # oficial del scraper esta ordenado por calendario; con 18 equipos son
        # 9 partidos por jornada.
        jornada_match_ids = configured_match_ids + [
            match_id for match_id in match_ids if match_id not in configured_match_ids
        ]
        config['_match_id_to_jornada'] = {
            match_id: (idx // 9) + 1 for idx, match_id in enumerate(jornada_match_ids)
        }

        # Cargar datos existentes
        dataframes, existing_ids = load_existing_data(config)

        # Preparar conjunto de IDs de perfiles existentes
        existing_profile_ids = _profile_ids_from_df(dataframes.get('output_file_player_profiles'))

        # La fila de estadisticas_partido.csv es el marcador canonico de que
        # un partido esta procesado. No mezclamos player_id con id_partido.
        existing_game_ids = existing_ids.get('output_file_game', set())

        # Filtrar IDs nuevos
        new_match_ids = [id for id in match_ids if id not in existing_game_ids]
        logger.info(f"Iniciando proceso de scraping para {len(new_match_ids)} nuevos partidos")

        # Si no hay partidos nuevos, terminar
        if not new_match_ids:
            logger.info("No hay nuevos partidos para procesar. Terminando.")
            return

        # Cada partido se guarda al instante para que una interrupción no
        # pierda lo ya procesado. Reescribir los CSV completos en cada partido
        # es O(N²) en disco, pero a la escala actual (~150 partidos / ~400KB)
        # es despreciable. La optimización real (append/upsert incremental)
        # queda pendiente y no debe hacerse acumulando en memoria.
        def save_single_result(result: Dict[str, Any]) -> None:
            process_and_save_data(config, [result], dataframes)

        results = await process_games(
            new_match_ids,
            config['base_url'],
            config,
            existing_game_ids,
            existing_profile_ids,
            on_result=save_single_result
        )

        # Si no hay resultados, terminar
        if not results:
            logger.info("No se obtuvieron datos nuevos para procesar. Terminando.")
            return

        logger.info(f"{len(results)} partidos procesados y guardados incrementalmente")

    except Exception as e:
        logger.error(f"Error en el proceso principal: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    # Ejecutar el proceso principal
    args = parse_args()
    asyncio.run(main(args.only))
