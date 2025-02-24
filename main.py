import json
import pandas as pd
import asyncio
import aiohttp
from typing import Dict, Any, List, Set, Tuple, TypeAlias
from scraper import get_game_data
from logger import setup_logger
from dataclasses import dataclass
import logging
from pathlib import Path

logger = setup_logger()

DataFrameDict: TypeAlias = Dict[str, pd.DataFrame]
IdSetDict: TypeAlias = Dict[str, Set[int]]

@dataclass
class FileConfig:
    id_column: str
    columns_key: str

FILE_CONFIGS = {
    'output_file': FileConfig('player_id', 'columns_players'),
    'output_file_game': FileConfig('id_partido', 'columns_games'),
    'output_file_team_totals': FileConfig('id_partido', 'columns_team_totals'),
    'output_file_player_profiles': FileConfig('player_id', 'columns_player_profiles')
}

def load_config(filename: str = 'config.json') -> Dict[str, Any]:
    try:
        with open(filename, 'r') as file:
            config = json.load(file)
        logger.info(f"Configuración cargada exitosamente desde {filename}")
        return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error al cargar la configuración desde {filename}: {str(e)}")
        raise

def load_match_ids(filename: str = 'match_ids.json') -> List[int]:
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
        match_ids = data.get('match_ids', [])
        logger.info(f"Cargados {len(match_ids)} IDs de partidos desde {filename}")
        return match_ids
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error al cargar los IDs de partidos desde {filename}: {str(e)}")
        raise

def ensure_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = ''
    return df[columns]

def load_single_file(filename: str, id_column: str, columns: list | None) -> Tuple[pd.DataFrame, Set[int]]:
    try:
        df = pd.read_csv(filename)
        if columns:
            df = ensure_columns(df, columns)
        ids = set(pd.to_numeric(df[id_column], errors='coerce').dropna().astype(int))
        logger.info(f"Loaded {len(ids)} IDs from {filename}")
        return df, ids
    except FileNotFoundError:
        logger.info(f"File {filename} not found. Creating new one.")
        return pd.DataFrame(columns=columns if columns else None), set()
    except pd.errors.EmptyDataError:
        logger.warning(f"File {filename} is empty")
        return pd.DataFrame(columns=columns if columns else None), set()
    except Exception as e:
        logger.error(f"Error loading {filename}: {str(e)}")
        return pd.DataFrame(columns=columns if columns else None), set()

def load_existing_data(config: Dict[str, Any]) -> Tuple[DataFrameDict, IdSetDict]:
    dataframes: DataFrameDict = {}
    existing_ids: IdSetDict = {}
    
    for file_key, file_config in FILE_CONFIGS.items():
        filename = config.get(file_key)
        if not filename:
            logger.warning(f"Key '{file_key}' not found in configuration")
            continue
            
        columns = config.get(file_config.columns_key)
        df, ids = load_single_file(filename, file_config.id_column, columns)
        dataframes[file_key] = df
        existing_ids[file_key] = ids
    
    return dataframes, existing_ids

async def process_games(match_ids: List[int], base_url: str, config: Dict[str, Any], existing_ids: Set[int], existing_profile_ids: Set[str]) -> List[Dict[str, Any]]:
    async with aiohttp.ClientSession() as session:
        tasks = [get_game_data(session, f"{base_url}{game_id}", game_id, config, existing_profile_ids) 
                 for game_id in match_ids if game_id not in existing_ids]
        results = await asyncio.gather(*tasks)
        return [result for result in results if result]

def save_to_csv(data: pd.DataFrame, output_file: str) -> None:
    if data.empty:
        logger.warning(f"DataFrame vacío. No se guardará el archivo {output_file}")
        return
    logger.info(f"Guardando datos en {output_file}. Shape del DataFrame: {data.shape}")
    data.to_csv(output_file, index=False)
    logger.info(f'Datos guardados en {output_file}')

def process_and_save_data(config: Dict[str, Any], results: List[Dict[str, Any]], dataframes: Dict[str, pd.DataFrame]) -> None:
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
            if profile['player_id'] not in dataframes['output_file_player_profiles']['player_id'].values
        ])

    for key in new_data:
        if new_data[key]:
            new_df = pd.DataFrame(new_data[key])
            columns_key = f'columns_{key.split("_")[-1]}'
            if columns_key in config:
                new_df = ensure_columns(new_df, config[columns_key])
            dataframes[key] = pd.concat([dataframes[key], new_df], ignore_index=True)
            dataframes[key].drop_duplicates(subset=config['id_columns'][key], keep='last', inplace=True)
            save_to_csv(dataframes[key], config[key])

    logger.info(f"Procesamiento y guardado de datos completado")

async def main():
    config = load_config()
    match_ids = load_match_ids()
    dataframes, existing_ids = load_existing_data(config)

    # Obtener los IDs de perfiles existentes
    existing_profile_ids = set(dataframes['output_file_player_profiles']['player_id'].astype(int))

    all_existing_ids = set().union(*existing_ids.values())

    new_match_ids = [id for id in match_ids if id not in all_existing_ids]
    logger.info(f"Iniciando proceso de scraping para {len(new_match_ids)} nuevos partidos")

    results = await process_games(new_match_ids, config['base_url'], config, all_existing_ids, existing_profile_ids)

    if not results:
        logger.info("No hay nuevos datos para procesar.")
        return

    process_and_save_data(config, results, dataframes)

if __name__ == "__main__":
    asyncio.run(main())