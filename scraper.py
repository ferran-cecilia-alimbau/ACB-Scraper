"""
Módulo principal de scraping para recopilar datos de partidos de baloncesto de la ACB.

Este módulo provee funciones para extraer datos de partidos, estadísticas de jugadores
y perfiles de jugadores de la web de la ACB de forma secuencial y simple.
"""
import logging
from typing import Dict, List, Optional, Set, Any
import asyncio
from aiohttp import ClientSession, ClientError
from bs4 import BeautifulSoup

import constants as const
from http_client import fetch, create_client_session
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
    Procesa una lista de partidos de forma secuencial.
    
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
    
    # Crear una copia del conjunto de perfiles existentes para actualizarlo durante la ejecución
    current_profile_ids = existing_profile_ids.copy()
    logger.info(f"Comenzando con {len(current_profile_ids)} perfiles de jugadores ya existentes")
    
    # Crear sesión HTTP compartida
    async with await create_client_session() as session:
        # Procesar cada partido secuencialmente
        successful_results = []
        
        for game_id in new_match_ids:
            url = f"{base_url}{game_id}"
            try:
                # Procesar un partido a la vez
                result = await get_game_data(session, url, game_id, config, current_profile_ids)
                if result:
                    successful_results.append(result)
                    logger.info(f"Partido {game_id} procesado correctamente")
                    
                    # Actualizar el conjunto de perfiles existentes con los nuevos perfiles obtenidos
                    if 'player_profiles' in result and result['player_profiles']:
                        new_profiles_count = 0
                        for profile in result['player_profiles']:
                            if 'player_id' in profile:
                                try:
                                    player_id = int(profile['player_id'])
                                    if player_id not in current_profile_ids:
                                        current_profile_ids.add(player_id)
                                        new_profiles_count += 1
                                except (ValueError, TypeError):
                                    pass
                        if new_profiles_count > 0:
                            logger.info(f"Añadidos {new_profiles_count} nuevos perfiles de jugadores al caché")
            except Exception as e:
                logger.error(f"Error en partido {game_id}: {str(e)}")
        
        logger.info(
            f"Procesamiento completado: {len(successful_results)} exitosos "
            f"de {len(new_match_ids)} intentados"
        )
        logger.info(f"Total de perfiles de jugadores en caché: {len(current_profile_ids)}")
        
        return successful_results