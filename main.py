"""
Punto de entrada principal para el ACB Scraper.

Este módulo coordina el proceso de scraping, cargando la configuración,
procesando los partidos y almacenando los resultados.
"""
import json
import pandas as pd
import asyncio
import os
import sys
from typing import Dict, Any, List, Set, Tuple, TypeAlias, Optional
from dataclasses import dataclass
import logging
from pathlib import Path

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
        
        # Validar configuración mínima
        required_keys = ['base_url', 'output_file']
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            error_msg = f"Faltan claves requeridas en la configuración: {missing_keys}"
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
    except Exception as e:
        logger.error(f"Error al cargar {filename}: {str(e)}")
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
            
        # Guardar archivo
        logger.info(f"Guardando datos en {output_file}. Shape del DataFrame: {data.shape}")
        data.to_csv(output_file, index=False)
        logger.info(f"Datos guardados correctamente en {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar datos en {output_file}: {str(e)}")
        return False


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
        
    # Inicializar diccionario para los nuevos datos
    new_data = {
        'output_file': [],
        'output_file_game': [],
        'output_file_team_totals': [],
        'output_file_player_profiles': []
    }
    
    # Convertir IDs de perfiles a un conjunto para búsquedas más eficientes
    existing_profile_ids_set = set(
        str(id) for id in dataframes['output_file_player_profiles']['player_id'].values
    )
    
    # Procesar cada resultado
    for result in results:
        # Añadir estadísticas de jugadores
        new_data['output_file'].extend(result.get('player_stats', []))
        
        # Añadir información del partido
        if 'game_info' in result:
            new_data['output_file_game'].append(result['game_info'])
            
        # Añadir totales de equipos
        new_data['output_file_team_totals'].extend(result.get('team_totals', []))
        
        # Añadir perfiles de jugadores (solo los que no existen)
        new_data['output_file_player_profiles'].extend([
            profile for profile in result.get('player_profiles', [])
            if profile['player_id'] not in existing_profile_ids_set
        ])
    
    # Guardar cada tipo de datos
    for key in new_data:
        if new_data[key]:
            # Crear DataFrame con los nuevos datos
            new_df = pd.DataFrame(new_data[key])
            
            # Asegurar que tiene las columnas requeridas
            columns_key = f'columns_{key.split("_")[-1]}'
            if columns_key in config:
                new_df = ensure_columns(new_df, config[columns_key])
                
            # Combinar con los datos existentes
            combined_df = pd.concat([dataframes[key], new_df], ignore_index=True)
            
            # Eliminar duplicados eficientemente
            chunk_size = const.CHUNK_SIZE
            
            if len(combined_df) > chunk_size:
                # Para DataFrames grandes, procesar en fragmentos
                logger.info(f"Procesando DataFrame grande ({len(combined_df)} filas) en fragmentos")
                
                # Dividir en fragmentos
                chunks = [
                    combined_df.iloc[i:i+chunk_size] 
                    for i in range(0, len(combined_df), chunk_size)
                ]
                
                # Procesar cada fragmento
                processed_chunks = []
                for i, chunk in enumerate(chunks):
                    logger.debug(f"Procesando fragmento {i+1}/{len(chunks)}")
                    processed_chunks.append(
                        chunk.drop_duplicates(
                            subset=config['id_columns'][key], 
                            keep='last'
                        )
                    )
                
                # Recombinar fragmentos
                combined_df = pd.concat(processed_chunks, ignore_index=True)
                
                # Eliminar duplicados entre fragmentos
                combined_df = combined_df.drop_duplicates(
                    subset=config['id_columns'][key], 
                    keep='last'
                )
            else:
                # Para DataFrames pequeños, procesar directamente
                combined_df = combined_df.drop_duplicates(
                    subset=config['id_columns'][key], 
                    keep='last'
                )
                
            # Actualizar el DataFrame en el diccionario
            dataframes[key] = combined_df
            
            # Guardar el resultado
            save_to_csv(combined_df, config[key])
    
    logger.info("Procesamiento y guardado de datos completado")


async def main():
    """
    Función principal que coordina el proceso de scraping.
    """
    try:
        # Cargar configuración
        config = load_config()
        
        # Cargar IDs de partidos
        match_ids = load_match_ids()
        
        # Cargar datos existentes
        dataframes, existing_ids = load_existing_data(config)
        
        # Preparar conjunto de IDs de perfiles existentes
        existing_profile_ids = set(
            int(id) for id in pd.to_numeric(
                dataframes['output_file_player_profiles']['player_id'], 
                errors='coerce'
            ).dropna()
        )
        
        # Calcular todos los IDs existentes
        all_existing_ids = set().union(*existing_ids.values())
        
        # Filtrar IDs nuevos
        new_match_ids = [id for id in match_ids if id not in all_existing_ids]
        logger.info(f"Iniciando proceso de scraping para {len(new_match_ids)} nuevos partidos")
        
        # Si no hay partidos nuevos, terminar
        if not new_match_ids:
            logger.info("No hay nuevos partidos para procesar. Terminando.")
            return
            
        # Procesar partidos
        results = await process_games(
            new_match_ids, 
            config['base_url'], 
            config, 
            all_existing_ids, 
            existing_profile_ids
        )
        
        # Si no hay resultados, terminar
        if not results:
            logger.info("No se obtuvieron datos nuevos para procesar. Terminando.")
            return
            
        # Procesar y guardar resultados
        process_and_save_data(config, results, dataframes)
        
    except Exception as e:
        logger.error(f"Error en el proceso principal: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    # Ejecutar el proceso principal
    asyncio.run(main())