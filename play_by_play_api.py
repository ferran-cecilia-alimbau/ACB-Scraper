# play_by_play_api.py

import asyncio
import os
import csv
import logging
from typing import Dict, Any, List
from aiohttp import ClientSession

logger = logging.getLogger('basketball_scraper')

async def fetch_pbp_page(session: ClientSession, url: str, headers: Dict[str, str], params: Dict[str, int]) -> List[Dict]:
    """Obtiene una única página de jugadas de la API."""
    try:
        async with session.get(url, headers=headers, params=params, timeout=20) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Error en API PBP para URL {url} con params {params}. Status: {response.status}")
                return []
    except asyncio.TimeoutError:
        logger.error(f"Timeout en API PBP para URL {url} con params {params}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado en API PBP para {url}: {e}")
        return []

async def get_play_by_play_from_api(
    session: ClientSession, 
    game_id: int, 
    config: Dict[str, Any]
):
    """
    Obtiene todos los datos de Play-by-Play para un partido usando la API oficial.
    """
    output_dir = config.get("output_dir_play_by_play", "data/play_by_play")
    output_filepath = os.path.join(output_dir, f"play_by_play_{game_id}.csv")
    
    if os.path.exists(output_filepath):
        logger.info(f"PBP para {game_id} ya existe (API). Saltando.")
        return
    
    base_url = f"{config['pbp_api_url']}{game_id}"
    headers = {
        "Authorization": config["acb_api_token"],
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    all_plays = []
    offset = 0
    limit = 50 # Pedimos de 50 en 50 para ser más eficientes
    
    logger.info(f"Iniciando descarga de PBP desde API para partido {game_id}")
    while True:
        params = {'ot': offset, 'nt': limit}
        plays_page = await fetch_pbp_page(session, base_url, headers, params)
        
        if not plays_page:
            # Si no hay más jugadas, terminamos el bucle
            break
        
        all_plays.extend(plays_page)
        offset += limit
        await asyncio.sleep(0.2) # Pequeña pausa para no saturar la API

    if not all_plays:
        logger.warning(f"No se encontraron jugadas desde la API para el partido {game_id}")
        return

    # Mapear los datos de la API a nuestro formato de CSV
    extracted_data = []
    for play in all_plays:
        extracted_data.append({
            'periodo': play.get('idPeriod'),
            'tiempo': play.get('time'),
            'marcador_local': play.get('scoreLocal'),
            'marcador_visitante': play.get('scoreVisitor'),
            'equipo': play.get('team', {}).get('team_actual_name'),
            'jugador': play.get('player', {}).get('player_short_name'),
            'accion': play.get('playType', {}).get('name'),
            'estadistica': play.get('playInfo')
        })

    logger.info(f"Se obtuvieron {len(extracted_data)} jugadas para el partido {game_id} desde la API.")
    
    # Guardar en CSV
    os.makedirs(output_dir, exist_ok=True)
    fieldnames = ['periodo', 'tiempo', 'marcador_local', 'marcador_visitante', 'equipo', 'jugador', 'accion', 'estadistica']
    try:
        with open(output_filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(extracted_data)
        logger.info(f"PBP para {game_id} guardado correctamente en {output_filepath}")
    except IOError as e:
        logger.error(f"Error al guardar CSV para PBP de {game_id}: {e}")