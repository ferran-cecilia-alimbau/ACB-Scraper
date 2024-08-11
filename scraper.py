import aiohttp
import asyncio
from bs4 import BeautifulSoup
import logging
from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt, wait_fixed
from typing import Dict, List, Optional

logger = logging.getLogger('basketball_scraper')

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
async def fetch(session: ClientSession, url: str, game_id: int, config: Dict[str, any]) -> str:
    """
    Fetch the HTML content of a given URL.

    Args:
        session (ClientSession): The aiohttp client session.
        url (str): The URL to fetch.
        game_id (int): The ID of the game being fetched.
        config (Dict[str, any]): The configuration dictionary.

    Returns:
        str: The HTML content of the page.

    Raises:
        aiohttp.ClientResponseError: If the HTTP request fails.
    """
    headers = {'User-Agent': config.get('user_agent', 'BasketballStatsScraper/1.0')}
    async with session.get(url, headers=headers) as response:
        await asyncio.sleep(config.get('rate_limit', 1))
        response.raise_for_status()
        return await response.text()

async def get_game_data(session: ClientSession, url: str, game_id: int, config: Dict[str, any]) -> Optional[Dict]:
    """
    Extract game data from a given URL.

    Args:
        session (ClientSession): The aiohttp client session.
        url (str): The URL to fetch game data from.
        game_id (int): The ID of the game.
        config (Dict[str, any]): The configuration dictionary.

    Returns:
        Optional[Dict]: A dictionary containing player stats and game info, or None if extraction fails.
    """
    logger.info(f"Obteniendo datos para el partido {game_id} desde {url}")
    
    try:
        html = await fetch(session, url, game_id, config)
    except Exception as e:
        logger.error(f"No se pudieron obtener los datos para el partido {game_id}: {str(e)}")
        return None

    soup = BeautifulSoup(html, 'html.parser')

    game_info = extract_game_info(soup, game_id)

    team_headers = soup.select('div.cabecera_partido h4')
    if len(team_headers) < 2:
        logger.error(f"No se encontraron los nombres de los equipos para el partido {game_id}")
        return None

    team1 = team_headers[0].text.strip()
    team2 = team_headers[1].text.strip()
    logger.info(f"Partido {game_id}: {team1} vs {team2}")

    tables = soup.find_all('table', {'data-toggle': 'table-estadisticas'})
    if len(tables) < 2:
        logger.error(f"No se encontraron las tablas de estadísticas para el partido {game_id}")
        return None

    team1_stats = parse_table(tables[0], team1, game_id)
    team2_stats = parse_table(tables[1], team2, game_id)

    combined_stats = team1_stats + team2_stats
    logger.info(f"Procesamiento de datos completado para el partido {game_id}. Total de jugadores: {len(combined_stats)}")
    
    return {
        'player_stats': combined_stats,
        'game_info': game_info
    }

def extract_game_info(soup: BeautifulSoup, game_id: int) -> Dict[str, str]:
    """
    Extract game information from the BeautifulSoup object.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object containing the parsed HTML.
        game_id (int): The ID of the game.

    Returns:
        Dict[str, str]: A dictionary containing extracted game information.
    """
    game_info = {'id_partido': game_id}
    
    header_info = soup.select_one('.datos_fecha')
    if header_info:
        info_text = header_info.text.strip().split('|')
        game_info['jornada'] = info_text[0].strip().replace('JORNADA ', '')
        game_info['fecha'] = info_text[1].strip()
        game_info['hora'] = info_text[2].strip()
        
        pabellon_span = header_info.select_one('.clase_mostrar1280')
        if pabellon_span:
            game_info['pabellon'] = pabellon_span.text.strip()
        else:
            game_info['pabellon'] = info_text[3].strip() if len(info_text) > 3 else ''

    public_info = soup.select_one('.datos_fecha')
    if public_info:
        public_text = public_info.text.strip().split('Público:')
        if len(public_text) > 1:
            game_info['publico'] = public_text[1].strip()

    referees = soup.select_one('.datos_arbitros')
    if referees:
        referee_list = referees.text.replace('Árb:', '').strip().split(',')
        for i, ref in enumerate(referee_list[:3], start=1):
            game_info[f'arbitro{i}'] = ref.strip()

    results = soup.select('.resultado')
    if len(results) == 2:
        game_info['resultado_local'] = results[0].text.strip()
        game_info['resultado_visitante'] = results[1].text.strip()

    quarters = soup.select_one('.parciales_por_cuarto')
    if quarters:
        quarter_scores = quarters.text.strip().split()
        local_scores = []
        visitor_scores = []
        for i in range(0, len(quarter_scores)):
            local, visitor = quarter_scores[i].split('|')
            local_scores.append(local)
            visitor_scores.append(visitor)
        game_info['parciales_local'] = ','.join(local_scores)
        game_info['parciales_visitante'] = ','.join(visitor_scores)

    return game_info

def parse_table(table: BeautifulSoup, team_name: str, game_id: int) -> List[Dict[str, str]]:
    """
    Parse a table containing player statistics.

    Args:
        table (BeautifulSoup): The BeautifulSoup object containing the table to parse.
        team_name (str): The name of the team.
        game_id (int): The ID of the game.

    Returns:
        List[Dict[str, str]]: A list of dictionaries, each containing a player's statistics.
    """
    logger.debug(f"Analizando tabla de estadísticas para el equipo {team_name}")
    players_stats = []
    rows = table.find_all('tr')
    
    headers = [
        "id_partido", "equipo", "titular", "dorsal", "nombre", "minutos", "puntos",
        "T2", "T2 %", "T3", "T3 %", "T1", "T1 %", "rebotes_defensivos", "rebotes_ofensivos",
        "rebotes_totales", "asistencias", "robos", "perdidas", "C", "tapones_favor",
        "tapones_contra", "mates", "faltas_cometidas", "faltas_recibidas", "+/-", "V"
    ]

    for row in rows[2:-4]:  # Ignoramos las filas de cabecera y totales
        cols = row.find_all('td')
        player_data = [col.text.strip() for col in cols]
        
        if len(player_data) < 23:
            logger.warning(f"Datos incompletos para un jugador en el equipo {team_name}, partido {game_id}. Saltando...")
            continue

        player_dict = create_player_dict(player_data, game_id, team_name)

        # Asegurarse de que todas las claves estén presentes
        for header in headers:
            if header not in player_dict:
                player_dict[header] = ""

        # Ordenar el diccionario según el orden de los headers
        ordered_dict = {key: player_dict[key] for key in headers}
        players_stats.append(ordered_dict)

    logger.debug(f"Análisis de tabla completado para el equipo {team_name}. Jugadores procesados: {len(players_stats)}")
    return players_stats

def create_player_dict(player_data: List[str], game_id: int, team_name: str) -> Dict[str, str]:
    """
    Create a dictionary of player statistics from raw data.

    Args:
        player_data (List[str]): Raw player data from the table.
        game_id (int): The ID of the game.
        team_name (str): The name of the team.

    Returns:
        Dict[str, str]: A dictionary containing the player's statistics.
    """
    player_dict = {
        "id_partido": game_id,
        "equipo": team_name,
        "titular": '*' if player_data[0].startswith('*') else '',
        "dorsal": player_data[0].strip('*'),
        "nombre": player_data[1],
        "minutos": player_data[2],
        "puntos": player_data[3],
        "T2": player_data[4],
        "T2 %": player_data[5],
        "T3": player_data[6],
        "T3 %": player_data[7],
        "T1": player_data[8],
        "T1 %": player_data[9],
    }

    # Procesar rebotes
    d_o = player_data[11].split('+')
    player_dict["rebotes_defensivos"] = d_o[0] if len(d_o) > 0 else '0'
    player_dict["rebotes_ofensivos"] = d_o[1] if len(d_o) > 1 else '0'
    player_dict["rebotes_totales"] = player_data[10]

    # Resto de estadísticas
    player_dict.update({
        "asistencias": player_data[12],
        "robos": player_data[13],
        "perdidas": player_data[14],
        "C": player_data[15],
        "tapones_favor": player_data[16],
        "tapones_contra": player_data[17],
        "mates": player_data[18],
        "faltas_cometidas": player_data[19],
        "faltas_recibidas": player_data[20],
        "+/-": player_data[21],
        "V": player_data[22]
    })

    # Si el jugador no jugó (minutos vacíos), rellenar con ceros manteniendo el formato
    if not player_dict["minutos"]:
        for key in player_dict:
            if key in ["id_partido", "equipo", "titular", "dorsal", "nombre"]:
                continue
            elif key == "minutos":
                player_dict[key] = "00:00"
            elif key in ["T2 %", "T3 %", "T1 %"]:
                player_dict[key] = "0%"
            elif key in ["T2", "T3", "T1"]:
                player_dict[key] = "0/0"
            else:
                player_dict[key] = "0"

    return player_dict