"""
Módulo principal de scraping para recopilar datos de partidos de baloncesto de la ACB.

Este módulo provee funciones para extraer datos de partidos, estadísticas de jugadores
y perfiles de jugadores de la web de la ACB de forma paralela y eficiente.
"""
import logging
from typing import Dict, List, Optional, Set, Any, Tuple, Callable
import asyncio
from aiohttp import ClientSession, ClientError
from bs4 import BeautifulSoup
from tqdm import tqdm
import time

import constants as const
from http_client import fetch, create_client_session
from modern_acb import build_modern_game_data
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
    existing_profile_ids: Set[int],
    semaphore: asyncio.Semaphore
) -> Optional[Dict[str, Any]]:
    """
    Extrae todos los datos relevantes de un partido con control de concurrencia.

    Args:
        session: Sesión HTTP para realizar peticiones
        url: URL del partido a scrapear
        game_id: ID del partido
        config: Configuración del scraper
        existing_profile_ids: Conjunto de IDs de perfiles ya existentes
        semaphore: Semáforo para controlar concurrencia

    Returns:
        Diccionario con todos los datos extraídos del partido o None si hay error
    """
    if not url or not game_id:
        logger.error("URL o ID de partido vacíos")
        return None

    async with semaphore:  # Limitar concurrencia
        extract_start = time.perf_counter()
        try:
            # Obtener el HTML del partido
            logger.info(f"Obteniendo datos del partido {game_id} desde {url}")
            fetch_start = time.perf_counter()
            html = await fetch(session, url, config)
            fetch_seconds = time.perf_counter() - fetch_start

            # Validar que hay contenido HTML
            if not html or len(html) < const.MIN_VALID_HTML_LENGTH:
                logger.error(f"El HTML del partido {game_id} es demasiado corto: {len(html)} bytes")
                return None

            # Parsear el HTML
            soup = BeautifulSoup(html, 'html.parser')

            # La web actual de ACB expone los datos en JSON React Flight. Usarlo
            # primero evita depender de clases CSS generadas e inestables.
            modern_result = await build_modern_game_data(
                session, soup, game_id, config, existing_profile_ids
            )
            if modern_result:
                logger.info(f"Partido {game_id} procesado con payload React Flight")
                metrics = modern_result.setdefault('_metrics', {})
                metrics['fetch_seconds'] = round(fetch_seconds, 3)
                metrics['total_extract_seconds'] = round(time.perf_counter() - extract_start, 3)
                logger.info(f"Metricas partido {game_id}: {metrics}")
                return modern_result
            logger.info(f"Payload React Flight no encontrado para {game_id}; usando parser HTML legacy")

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
            legacy_metrics = {
                'parser': 'legacy_html',
                'fetch_seconds': round(fetch_seconds, 3),
                'total_extract_seconds': round(time.perf_counter() - extract_start, 3),
                'full_profiles_downloaded': len(team1_players) + len(team2_players),
            }
            return {
                'game_id': game_id,
                'player_stats': team1_stats + team2_stats,
                'game_info': game_info,
                'team_totals': [t for t in [team1_totals, team2_totals] if t],
                'player_profiles': team1_players + team2_players,
                '_metrics': legacy_metrics,
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
    pbar: tqdm,
    on_result: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Tuple[List[Dict[str, Any]], Set[int]]:
    """
    Procesa un lote de partidos en paralelo.

    Args:
        session: Sesión HTTP compartida
        batch_ids: IDs de partidos a procesar en este lote
        base_url: URL base para construir las URLs
        config: Configuración del scraper
        existing_profile_ids: Conjunto de IDs de perfiles existentes
        semaphore: Semáforo para control de concurrencia
        pbar: Barra de progreso

    Returns:
        Tupla con lista de resultados exitosos y conjunto de nuevos perfiles
    """
    async def run_game(game_id: int) -> Tuple[int, Optional[Dict[str, Any]]]:
        url = f"{base_url}{game_id}"
        result = await get_game_data(session, url, game_id, config, existing_profile_ids, semaphore)
        return game_id, result

    tasks = [asyncio.create_task(run_game(game_id)) for game_id in batch_ids]
    successful_results = []
    new_profile_ids = set()

    for task in asyncio.as_completed(tasks):
        try:
            game_id, result = await task
        except Exception as e:
            logger.error(f"Error procesando partido en lote: {e}")
            pbar.update(1)
            continue

        if result is None:
            logger.warning(f"No se obtuvieron datos del partido {game_id}")
            pbar.update(1)
            continue

        successful_results.append(result)
        logger.info(f"Partido {game_id} procesado correctamente")

        if on_result:
            save_start = time.perf_counter()
            on_result(result)
            save_seconds = time.perf_counter() - save_start
            metrics = result.setdefault('_metrics', {})
            metrics['save_seconds'] = round(save_seconds, 3)
            metrics['total_with_save_seconds'] = round(
                metrics.get('total_extract_seconds', 0) + save_seconds,
                3
            )
            logger.info(
                f"Partido {game_id} guardado en CSV; "
                f"metricas={metrics}"
            )

        # Extraer nuevos IDs de perfiles
        if 'player_profiles' in result and result['player_profiles']:
            for profile in result['player_profiles']:
                if 'player_id' in profile:
                    try:
                        player_id = int(profile['player_id'])
                        new_profile_ids.add(player_id)
                    except (ValueError, TypeError):
                        pass

        pbar.update(1)

    return successful_results, new_profile_ids


async def process_games(
    match_ids: List[int],
    base_url: str,
    config: Dict[str, Any],
    existing_ids: Set[int],
    existing_profile_ids: Set[int],
    on_result: Optional[Callable[[Dict[str, Any]], None]] = None
) -> List[Dict[str, Any]]:
    """
    Procesa una lista de partidos de forma paralela con control de concurrencia.

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

    # Configuración de paralelización
    MAX_CONCURRENT = min(config.get('max_concurrent', const.MAX_CONCURRENT_REQUESTS), 10)
    BATCH_SIZE = min(config.get('batch_size', 20), 50)

    logger.info(f"Configuración: {MAX_CONCURRENT} peticiones concurrentes, lotes de {BATCH_SIZE}")

    # Crear una copia del conjunto de perfiles existentes para actualizarlo durante la ejecución
    current_profile_ids = existing_profile_ids.copy()

    logger.info(f"Comenzando con {len(current_profile_ids)} perfiles de jugadores ya existentes")

    # Semáforo para controlar la concurrencia
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    # Crear sesión HTTP compartida
    async with await create_client_session() as session:
        all_successful_results = []

        # Barra de progreso
        with tqdm(total=len(new_match_ids), desc="Procesando partidos") as pbar:
            # Procesar por lotes
            for i in range(0, len(new_match_ids), BATCH_SIZE):
                batch_start_time = time.time()

                # Obtener el lote actual
                batch = new_match_ids[i:i + BATCH_SIZE]
                logger.info(f"Procesando lote {i//BATCH_SIZE + 1} con {len(batch)} partidos")

                # Procesar lote en paralelo
                batch_results, new_profiles = await process_batch(
                    session, batch, base_url, config,
                    current_profile_ids, semaphore, pbar, on_result
                )

                # Actualizar resultados
                all_successful_results.extend(batch_results)

                # Actualizar conjunto de perfiles (seguro en asyncio single-threaded)
                profiles_before = len(current_profile_ids)
                current_profile_ids.update(new_profiles)
                profiles_added = len(current_profile_ids) - profiles_before

                if profiles_added > 0:
                    logger.info(f"Añadidos {profiles_added} nuevos perfiles al caché")

                # Tiempo de procesamiento del lote
                batch_time = time.time() - batch_start_time
                logger.info(f"Lote procesado en {batch_time:.2f} segundos")

                # Pausa entre lotes para no saturar el servidor
                # (excepto en el último lote)
                if i + BATCH_SIZE < len(new_match_ids):
                    pause_time = config.get('batch_pause', 2)
                    logger.debug(f"Pausando {pause_time} segundos entre lotes")
                    await asyncio.sleep(pause_time)

        # Resumen final
        logger.info(
            f"Procesamiento completado: {len(all_successful_results)} exitosos "
            f"de {len(new_match_ids)} intentados"
        )
        logger.info(f"Total de perfiles de jugadores en caché: {len(current_profile_ids)}")

        # Estadísticas de éxito
        success_rate = (len(all_successful_results) / len(new_match_ids) * 100) if new_match_ids else 0
        logger.info(f"Tasa de éxito: {success_rate:.1f}%")

        return all_successful_results
