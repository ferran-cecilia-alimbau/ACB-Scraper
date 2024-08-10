import aiohttp
import asyncio
from bs4 import BeautifulSoup
import logging
from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger('basketball_scraper')

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
async def fetch(session: ClientSession, url: str, game_id: int, config: dict) -> str:
    headers = {'User-Agent': config.get('user_agent', 'BasketballStatsScraper/1.0')}
    async with session.get(url, headers=headers) as response:
        await asyncio.sleep(config.get('rate_limit', 1))
        response.raise_for_status()
        return await response.text()

async def get_game_data(session: ClientSession, url: str, game_id: int, config: dict):
    logger.info(f"Obteniendo datos para el partido {game_id} desde {url}")
    
    try:
        html = await fetch(session, url, game_id, config)
    except Exception as e:
        logger.error(f"No se pudieron obtener los datos para el partido {game_id}: {str(e)}")
        return None

    soup = BeautifulSoup(html, 'html.parser')

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
    return combined_stats

def parse_table(table, team_name, game_id):
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
            "faltas_cometidas": player_data[19],  # Cambiado el orden
            "faltas_recibidas": player_data[20],  # Cambiado el orden
            "+/-": player_data[21],
            "V": player_data[22]
        })

        # Asegurarse de que todas las claves estén presentes
        for header in headers:
            if header not in player_dict:
                player_dict[header] = ""

        # Ordenar el diccionario según el orden de los headers
        ordered_dict = {key: player_dict[key] for key in headers}
        players_stats.append(ordered_dict)

    logger.debug(f"Análisis de tabla completado para el equipo {team_name}. Jugadores procesados: {len(players_stats)}")
    return players_stats