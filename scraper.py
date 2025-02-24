"""
Módulo principal de scraping para recopilar datos de partidos de baloncesto de la ACB.

Este módulo provee funciones para extraer datos de partidos, estadísticas de jugadores
y perfiles de jugadores de la web de la ACB, respetando límites de tasa y reintentos.
"""
import logging
from typing import Dict, List, Optional, Set, Any
import asyncio
from aiohttp import ClientSession, ClientError
from bs4 import BeautifulSoup

import constants as const
from http_client import fetch, create_client_session, concurrency_limiter
from parsers import (
    extract_team_names, 
    extract_game_info, 
    extract_team_totals,
    parse_table
)

# Configurar el logger
logger = logging.getLogger('basketball_scraper')


async def get_game_data(
    session: ClientSession, 
    url: str, 
    game_id: int, 
    config: Dict[str, Any], 
    existing_profile_ids: Set[int]
) -> Optional[Dict[str, Any]]:
    """
    Extrae todos los datos relevantes de un partido.
    
    Args:
        session: Sesión HTTP para realizar peticiones
        url: URL del partido a scrapear
        game_id: ID del partido
        config: Configuración del scraper
        existing_profile_ids: Conjunto de IDs de perfiles ya existentes
        
    Returns:
        Diccionario con todos los datos extraídos del partido o None si hay error
    """
    if not url or not game_id:
        logger.error("URL o ID de partido vacíos")
        return None
        
    try:
        # Obtener el HTML del partido
        logger.info(f"Obteniendo datos del partido {game_id} desde {url}")
        html = await fetch(session, url, config)
        
        # Validar que hay contenido HTML
        if not html or len(html) < 200:
            logger.error(f"El HTML del partido {game_id} es demasiado corto: {len(html)} bytes")
            return None
            
        # Parsear el HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extraer información básica del partido
        game_info = extract_game_info(soup, game_id)
        
        # Extraer nombres de los equipos
        try:
            team1, team2 = extract_team_names(soup)
        except ValueError as e:
            logger.error(f"Error al extraer nombres de equipos: {str(e)}")
            return None
        
        # Buscar las tablas de estadísticas
        tables = soup.select(const.SELECTORS["team_stats_table"])
        if len(tables) < 2:
            logger.error(f"No se encontraron las tablas de estadísticas para el partido {game_id}")
            return None
        
        # Extraer estadísticas de jugadores
        team1_stats, team1_players = await parse_table(
            session, tables[0], team1, game_id, config, existing_profile_ids
        )
        team2_stats, team2_players = await parse_table(
            session, tables[1], team2, game_id, config, existing_profile_ids
        )
        
        # Extraer totales de equipos
        team1_totals = extract_team_totals(tables[0], team1, game_id)
        team2_totals = extract_team_totals(tables[1], team2, game_id)
        
        # Verificar que tenemos suficientes datos para considerar el scrape exitoso
        has_players = len(team1_stats) > 0 or len(team2_stats) > 0
        has_totals = bool(team1_totals) and bool(team2_totals)
        
        if not has_players and not has_totals:
            logger.warning(
                f"No se encontraron datos suficientes para el partido {game_id}. "
                f"Jugadores: {len(team1_stats) + len(team2_stats)}, "
                f"Totales: {1 if team1_totals else 0} + {1 if team2_totals else 0}"
            )
        
        # Devolver los datos extraídos
        return {
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


async def process_games(
    match_ids: List[int], 
    base_url: str, 
    config: Dict[str, Any], 
    existing_ids: Set[int], 
    existing_profile_ids: Set[int]
) -> List[Dict[str, Any]]:
    """
    Procesa una lista de partidos con control de concurrencia.
    
    Args:
        match_ids: Lista de IDs de partidos a procesar
        base_url: URL base para construir las URLs completas
        config: Configuración del scraper
        existing_ids: Conjunto de IDs de partidos ya procesados
        existing_profile_ids: Conjunto de IDs de perfiles ya existentes
        
    Returns:
        Lista de diccionarios con todos los datos extraídos
    """
    # Filtrar IDs ya procesados
    new_match_ids = [id for id in match_ids if id not in existing_ids]
    
    if not new_match_ids:
        logger.info("No hay nuevos partidos para procesar")
        return []
    
    logger.info(f"Procesando {len(new_match_ids)} partidos nuevos")
    
    # Crear sesión HTTP compartida
    async with await create_client_session() as session:
        # Crear tareas asíncronas respetando el límite de concurrencia
        tasks = []
        for game_id in new_match_ids:
            url = f"{base_url}{game_id}"
            task = concurrency_limiter.run(
                get_game_data(session, url, game_id, config, existing_profile_ids)
            )
            tasks.append(task)
        
        # Esperar a que se completen todas las tareas
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar resultados exitosos
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                game_id = new_match_ids[i] if i < len(new_match_ids) else "desconocido"
                logger.error(f"Error en partido {game_id}: {str(result)}")
            elif result is not None:
                successful_results.append(result)
        
        logger.info(
            f"Procesamiento completado: {len(successful_results)} exitosos "
            f"de {len(new_match_ids)} intentados"
        )
        
        return successful_results