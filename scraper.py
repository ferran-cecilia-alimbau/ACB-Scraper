# scraper.py

import logging
from typing import Dict, List, Optional, Set, Any, Tuple
import asyncio
from aiohttp import ClientSession, ClientError
from bs4 import BeautifulSoup
from tqdm import tqdm
import time

import constants as const
from http_client import fetch, create_client_session
from parsers import (
    extract_team_names, 
    extract_game_info, 
    extract_team_totals,
    parse_table
)

logger = logging.getLogger('basketball_scraper')

async def get_game_data(
    session: ClientSession, 
    url: str, 
    game_id: int, 
    config: Dict[str, Any], 
    existing_profile_ids: Set[int],
    semaphore: asyncio.Semaphore
) -> Optional[Dict[str, Any]]:
    """
    Extrae todos los datos relevantes de un partido con control de concurrencia.
    """
    if not url or not game_id:
        logger.error("URL o ID de partido vacíos")
        return None
    
    async with semaphore:
        try:
            logger.info(f"Obteniendo datos del partido {game_id} desde {url}")
            html = await fetch(session, url, config)
            
            if not html or len(html) < 200:
                logger.error(f"El HTML del partido {game_id} es demasiado corto: {len(html)} bytes")
                return None
                
            soup = BeautifulSoup(html, 'html.parser')
            game_info = extract_game_info(soup, game_id)
            
            try:
                team1, team2 = extract_team_names(soup)
            except ValueError as e:
                logger.error(f"Error al extraer nombres de equipos: {str(e)}")
                return None
            
            tables = soup.select(const.SELECTORS["team_stats_table"])
            if len(tables) < 2:
                logger.error(f"No se encontraron las tablas de estadísticas para el partido {game_id}")
                return None
            
            team1_stats, team1_players = await parse_table(session, tables[0], team1, game_id, config, existing_profile_ids)
            team2_stats, team2_players = await parse_table(session, tables[1], team2, game_id, config, existing_profile_ids)
            
            team1_totals = extract_team_totals(tables[0], team1, game_id)
            team2_totals = extract_team_totals(tables[1], team2, game_id)
            
            has_players = len(team1_stats) > 0 or len(team2_stats) > 0
            has_totals = bool(team1_totals) and bool(team2_totals)
            
            if not has_players and not has_totals:
                logger.warning(f"No se encontraron datos suficientes para el partido {game_id}.")
            
            return {
                'game_id': game_id,
                'player_stats': team1_stats + team2_stats,
                'game_info': game_info,
                'team_totals': [t for t in [team1_totals, team2_totals] if t],
                'player_profiles': team1_players + team2_players
            }
        except ClientError as e:
            logger.error(f"Error de cliente HTTP en partido {game_id}: {str(e)}")
            return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout al obtener datos del partido {game_id}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al obtener datos del partido {game_id}: {str(e)}")
            return None

async def process_batch(
    session: ClientSession,
    batch_ids: List[int],
    base_url: str,
    config: Dict[str, Any],
    existing_profile_ids: Set[int],
    semaphore: asyncio.Semaphore,
    pbar: tqdm
) -> Tuple[List[Dict[str, Any]], Set[int]]:
    """
    Procesa un lote de partidos en paralelo.
    """
    tasks = [get_game_data(session, f"{base_url}{game_id}", game_id, config, existing_profile_ids, semaphore) for game_id in batch_ids]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful_results = []
    new_profile_ids = set()
    
    for game_id, result in zip(batch_ids, results):
        if isinstance(result, Exception):
            logger.error(f"Error procesando partido {game_id}: {result}")
        elif result is None:
            logger.warning(f"No se obtuvieron datos del partido {game_id}")
        else:
            successful_results.append(result)
            logger.info(f"Partido {game_id} procesado correctamente")
            if 'player_profiles' in result:
                for profile in result['player_profiles']:
                    if 'player_id' in profile:
                        try:
                            new_profile_ids.add(int(profile['player_id']))
                        except (ValueError, TypeError):
                            pass
        pbar.update(1)
    
    return successful_results, new_profile_ids

async def process_games(
    match_ids: List[int], 
    base_url: str, 
    config: Dict[str, Any], 
    existing_ids: Set[int], 
    existing_profile_ids: Set[int]
) -> List[Dict[str, Any]]:
    """
    Procesa una lista de partidos de forma paralela con control de concurrencia.
    """
    new_match_ids = [id for id in match_ids if id not in existing_ids]
    
    if not new_match_ids:
        logger.info("No hay nuevos partidos para procesar")
        return []
    
    logger.info(f"Procesando {len(new_match_ids)} partidos nuevos")
    
    MAX_CONCURRENT = min(config.get('max_concurrent', const.MAX_CONCURRENT_REQUESTS), 10)
    BATCH_SIZE = min(config.get('batch_size', 20), 50)
    
    logger.info(f"Configuración: {MAX_CONCURRENT} peticiones concurrentes, lotes de {BATCH_SIZE}")
    
    current_profile_ids = existing_profile_ids.copy()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async with await create_client_session() as session:
        all_successful_results = []
        with tqdm(total=len(new_match_ids), desc="Procesando Estadísticas") as pbar:
            for i in range(0, len(new_match_ids), BATCH_SIZE):
                batch = new_match_ids[i:i + BATCH_SIZE]
                
                batch_results, new_profiles = await process_batch(session, batch, base_url, config, current_profile_ids, semaphore, pbar)
                
                all_successful_results.extend(batch_results)
                
                profiles_added = len(new_profiles - current_profile_ids)
                if profiles_added > 0:
                    current_profile_ids.update(new_profiles)
                    logger.info(f"Añadidos {profiles_added} nuevos perfiles al caché")
                
                if i + BATCH_SIZE < len(new_match_ids):
                    pause_time = config.get('batch_pause', 2)
                    await asyncio.sleep(pause_time)
        
        logger.info(f"Procesamiento de estadísticas completado: {len(all_successful_results)} exitosos.")
        return all_successful_results