import json
import pandas as pd
import scraper
from logger import setup_logger
import asyncio
import aiohttp
from tqdm import tqdm
from typing import Dict, Any, List
from concurrent.futures import ProcessPoolExecutor

logger = setup_logger()

def load_config(filename: str = 'config.json') -> Dict[str, Any]:
    """
    Load configuration from a JSON file.

    Args:
        filename (str): The name of the configuration file.

    Returns:
        Dict[str, Any]: A dictionary containing the configuration.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        json.JSONDecodeError: If there's an error decoding the JSON.
    """
    try:
        with open(filename, 'r') as file:
            config = json.load(file)
        logger.info(f"Configuración cargada exitosamente desde {filename}")
        return config
    except FileNotFoundError:
        logger.error(f"Archivo de configuración {filename} no encontrado")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error al decodificar JSON desde {filename}")
        raise

async def process_game(session: aiohttp.ClientSession, game_id: int, base_url: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single game by scraping its data.

    Args:
        session (aiohttp.ClientSession): The aiohttp client session.
        game_id (int): The ID of the game to process.
        base_url (str): The base URL for the game data.
        config (Dict[str, Any]): The configuration dictionary.

    Returns:
        Dict[str, Any]: A dictionary containing the game data, or None if an error occurred.
    """
    url = f"{base_url}{game_id}"
    try:
        return await scraper.get_game_data(session, url, game_id, config)
    except Exception as e:
        logger.error(f'Error al procesar el partido {game_id}: {str(e)}')
        return None

async def process_games(start_id: int, end_id: int, base_url: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process a range of games asynchronously.

    Args:
        start_id (int): The starting game ID.
        end_id (int): The ending game ID.
        base_url (str): The base URL for the game data.
        config (Dict[str, Any]): The configuration dictionary.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the processed game data.
    """
    async with aiohttp.ClientSession() as session:
        tasks = [process_game(session, game_id, base_url, config) for game_id in range(start_id, end_id + 1)]
        results = []
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Procesando partidos"):
            result = await f
            if result:
                results.append(result)
        return results

def save_to_csv(data: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save the processed data to a CSV file.

    Args:
        data (List[Dict[str, Any]]): The data to save.
        output_file (str): The name of the output file.
    """
    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False)
    logger.info(f'Datos guardados en {output_file}')

async def main():
    config = load_config()

    start_id = config.get("start_id")
    end_id = config.get("end_id")
    base_url = config.get("base_url")
    output_file = config.get("output_file")
    output_file_game = config.get("output_file_game")

    if start_id is None or end_id is None or start_id > end_id:
        logger.error("Configuración inválida. Por favor, revise los IDs de inicio y fin.")
        return

    logger.info(f"Iniciando proceso de scraping para los partidos {start_id} a {end_id}")

    results = await process_games(start_id, end_id, base_url, config)

    if not results:
        logger.error("No se recopilaron datos. Los archivos de salida estarán vacíos.")
        return

    all_player_stats = []
    all_game_info = []

    for result in results:
        all_player_stats.extend(result['player_stats'])
        all_game_info.append(result['game_info'])

    logger.info(f"Total de estadísticas de jugadores recopiladas: {len(all_player_stats)}")
    logger.info(f"Total de información de partidos recopilada: {len(all_game_info)}")

    # Convertir los resultados a DataFrames
    df_players = pd.DataFrame(all_player_stats)
    df_games = pd.DataFrame(all_game_info)
    
    # Asegurar que todas las columnas estén presentes, incluso si algunos juegos no tienen todos los datos
    columns = ['id_partido', 'jornada', 'fecha', 'hora', 'pabellon', 'publico', 
               'arbitro1', 'arbitro2', 'arbitro3', 
               'resultado_local', 'resultado_visitante', 
               'parciales_local', 'parciales_visitante']
    
    for col in columns:
        if col not in df_games.columns:
            df_games[col] = ''

    # Reordenar las columnas
    df_games = df_games[columns]

    # Guardar los DataFrames en archivos CSV
    save_to_csv(df_players, output_file)
    save_to_csv(df_games, output_file_game)

if __name__ == "__main__":
    asyncio.run(main())