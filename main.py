# main.py

import json
import pandas as pd
import asyncio
import os
import sys
from typing import Dict, Any, List, Set, Tuple, TypeAlias, Optional
from dataclasses import dataclass
import logging
from tqdm import tqdm

import constants as const
from logger import setup_logger
from scraper import process_games, create_client_session
from play_by_play_api import get_play_by_play_from_api 
from api_auth import get_fresh_api_token

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
    """
    if not filename or not isinstance(filename, str):
        error_msg = "El nombre del archivo de configuración debe ser una cadena válida"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            config = json.load(file)
        
        logger.info(f"Configuración cargada exitosamente desde {filename}")
        
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
    """
    if df is None or columns is None:
        logger.error("DataFrame o lista de columnas es None")
        return pd.DataFrame(columns=columns if columns else None)
        
    for col in columns:
        if col not in df.columns:
            df[col] = ''
            
    return df[columns]


def load_single_file(
    filename: str, 
    id_column: str, 
    columns: Optional[List[str]]
) -> Tuple[pd.DataFrame, Set[int]]:
    """
    Carga un archivo CSV y extrae los IDs únicos.
    """
    if not filename or not id_column:
        logger.error("Nombre de archivo o columna de ID vacíos")
        return pd.DataFrame(columns=columns if columns else None), set()
        
    try:
        if not os.path.exists(filename):
            logger.info(f"Archivo {filename} no encontrado. Creando uno nuevo.")
            return pd.DataFrame(columns=columns if columns else None), set()
            
        df = pd.read_csv(filename)
        
        if columns:
            df = ensure_columns(df, columns)
            
        if id_column in df.columns:
            ids = set(pd.to_numeric(df[id_column], errors='coerce').dropna().astype(int))
            logger.info(f"Cargados {len(ids)} IDs desde {filename}")
        else:
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
    """
    dataframes: DataFrameDict = {}
    existing_ids: IdSetDict = {}
    
    for file_key, file_config in FILE_CONFIGS.items():
        filename = config.get(file_key)
        
        if not filename:
            continue
            
        columns = config.get(file_config.columns_key)
        
        df, ids = load_single_file(filename, file_config.id_column, columns)
        
        dataframes[file_key] = df
        existing_ids[file_key] = ids
    
    return dataframes, existing_ids


def save_to_csv(data: pd.DataFrame, output_file: str) -> bool:
    """
    Guarda un DataFrame en un archivo CSV.
    """
    if data is None or data.empty:
        logger.warning(f"DataFrame vacío. No se guardará el archivo {output_file}")
        return False
        
    try:
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        logger.info(f"Guardando datos en {output_file}. Shape del DataFrame: {data.shape}")
        data.to_csv(output_file, index=False)
        logger.info(f"Datos guardados correctamente en {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar datos en {output_file}: {str(e)}")
        return False


def extract_new_data(
    results: List[Dict[str, Any]], 
    existing_profile_ids_set: Set[str]
) -> Dict[str, List]:
    """
    Extrae los nuevos datos de los resultados del scraping.
    """
    new_data = {
        'output_file': [],
        'output_file_game': [],
        'output_file_team_totals': [],
        'output_file_player_profiles': []
    }
    
    for result in results:
        new_data['output_file'].extend(result.get('player_stats', []))
        
        if 'game_info' in result:
            new_data['output_file_game'].append(result['game_info'])
            
        new_data['output_file_team_totals'].extend(result.get('team_totals', []))
        
        new_data['output_file_player_profiles'].extend([
            profile for profile in result.get('player_profiles', [])
            if profile['player_id'] not in existing_profile_ids_set
        ])
    
    return new_data


def merge_and_deduplicate(
    dataframes: Dict[str, pd.DataFrame], 
    new_data: Dict[str, List], 
    config: Dict[str, Any]
) -> Dict[str, pd.DataFrame]:
    """
    Combina datos nuevos con existentes y elimina duplicados.
    """
    updated_dataframes = {}
    
    for key in new_data:
        if not new_data[key]:
            updated_dataframes[key] = dataframes[key]
            continue
            
        new_df = pd.DataFrame(new_data[key])
        
        columns_key = COLUMN_KEYS.get(key)
        if columns_key and columns_key in config:
            new_df = ensure_columns(new_df, config[columns_key])
        
        combined_df = pd.concat([dataframes[key], new_df], ignore_index=True)
        
        chunk_size = const.CHUNK_SIZE
        
        if len(combined_df) > chunk_size:
            chunks = [
                combined_df.iloc[i:i+chunk_size] 
                for i in range(0, len(combined_df), chunk_size)
            ]
            
            processed_chunks = []
            for i, chunk in enumerate(chunks):
                processed_chunks.append(
                    chunk.drop_duplicates(
                        subset=config['id_columns'][key], 
                        keep='last'
                    )
                )
            
            combined_df = pd.concat(processed_chunks, ignore_index=True)
            
            combined_df = combined_df.drop_duplicates(
                subset=config['id_columns'][key], 
                keep='last'
            )
        else:
            combined_df = combined_df.drop_duplicates(
                subset=config['id_columns'][key], 
                keep='last'
            )
        
        updated_dataframes[key] = combined_df
    
    return updated_dataframes


def process_and_save_data(
    config: Dict[str, Any], 
    results: List[Dict[str, Any]], 
    dataframes: Dict[str, pd.DataFrame]
) -> None:
    """
    Procesa los resultados del scraping y los guarda en archivos CSV.
    """
    if not results:
        logger.info("No hay resultados de estadísticas para procesar.")
        return
        
    existing_profile_ids_set = set(
        str(id) for id in dataframes['output_file_player_profiles']['player_id'].values
    )
    
    new_data = extract_new_data(results, existing_profile_ids_set)
    
    updated_dataframes = merge_and_deduplicate(dataframes, new_data, config)
    
    for key, df in updated_dataframes.items():
        dataframes[key] = df
        save_to_csv(df, config[key])
    
    logger.info("Procesamiento y guardado de datos de estadísticas completado.")


async def main():
    """Función principal que coordina el scraping en TRES fases."""
    try:
        config = load_config()
        
        # --- FASE 0: OBTENCIÓN DE TOKEN DE AUTORIZACIÓN ---
        fresh_token = await get_fresh_api_token()
        if not fresh_token:
            logger.error("No se pudo obtener un token de API válido. Abortando.")
            return
        # Inyectamos el token fresco en la configuración para que lo usen las demás funciones
        config['acb_api_token'] = fresh_token

        # --- FASE 1: SCRAPING DE ESTADÍSTICAS ---
        all_match_ids = load_match_ids()
        dataframes, existing_ids = load_existing_data(config)
        
        logger.info("="*50)
        logger.info("Iniciando Fase 1: Scraping Asíncrono de Estadísticas")
        
        existing_stats_ids = set(pd.to_numeric(dataframes['output_file_game']['id_partido'], errors='coerce').dropna().astype(int))
        new_stats_match_ids = [id for id in all_match_ids if id not in existing_stats_ids]
        
        if new_stats_match_ids:
            logger.info(f"Se procesarán {len(new_stats_match_ids)} nuevos partidos para obtener estadísticas.")
            existing_profile_ids = set(int(id) for id in pd.to_numeric(dataframes['output_file_player_profiles']['player_id'], errors='coerce').dropna())
            results = await process_games(new_stats_match_ids, config['base_url'], config, existing_stats_ids, existing_profile_ids)
            if results:
                process_and_save_data(config, results, dataframes)
        else:
            logger.info("No hay nuevas estadísticas de partidos para procesar. Todos los datos están al día.")
        
        logger.info("Fase 1 de estadísticas completada.")

        # --- FASE 2: SCRAPING DE PLAY-BY-PLAY DESDE API ---
        if config.get("scrape_play_by_play", False):
            logger.info("="*50)
            logger.info("Iniciando Fase 2: Scraping de Play-by-Play desde API")
            
            if not all_match_ids:
                logger.warning("No hay IDs de partidos en el fichero de entrada para procesar.")
                return

            logger.info(f"Se verificarán {len(all_match_ids)} partidos para Play-by-Play.")
            
            async with await create_client_session() as session:
                tasks = [get_play_by_play_from_api(session, game_id, config) for game_id in all_match_ids]
                for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Procesando PBP (API)"):
                    await f

            logger.info("Fase 2 de Play-by-Play finalizada.")

    except Exception as e:
        logger.error(f"Error en el proceso principal: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())