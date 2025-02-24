import aiohttp
import asyncio
from bs4 import BeautifulSoup
import logging
from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt, wait_fixed
from typing import Dict, List, Optional, Tuple, Set
import re

logger = logging.getLogger('basketball_scraper')

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
async def fetch(session: ClientSession, url: str, config: Dict[str, any]) -> str:
    """Fetch the HTML content of a given URL."""
    headers = {'User-Agent': config.get('user_agent', 'BasketballStatsScraper/1.0')}
    logger.info(f"Realizando petición HTTP a: {url}")
    async with session.get(url, headers=headers) as response:
        await asyncio.sleep(config.get('rate_limit', 1))
        response.raise_for_status()
        return await response.text()


async def get_game_data(session: ClientSession, url: str, game_id: int, config: Dict[str, any], existing_profile_ids: Set[int]) -> Optional[Dict]:
    """Extract all relevant data for a game."""
    try:
        html = await fetch(session, url, config)
        soup = BeautifulSoup(html, 'html.parser')
        
        game_info = extract_game_info(soup, game_id)
        team1, team2 = extract_team_names(soup)
        
        tables = soup.find_all('table', {'data-toggle': 'table-estadisticas'})
        if len(tables) < 2:
            logger.error(f"No se encontraron las tablas de estadísticas para el partido {game_id}")
            return None

        team1_stats, team1_players = await parse_table(session, tables[0], team1, game_id, config, existing_profile_ids)
        team2_stats, team2_players = await parse_table(session, tables[1], team2, game_id, config, existing_profile_ids)
        
        team1_totals = extract_team_totals(tables[0], team1, game_id)
        team2_totals = extract_team_totals(tables[1], team2, game_id)

        return {
            'player_stats': team1_stats + team2_stats,
            'game_info': game_info,
            'team_totals': [team1_totals, team2_totals] if team1_totals and team2_totals else [],
            'player_profiles': team1_players + team2_players
        }
    except Exception as e:
        logger.error(f"Error al obtener datos del partido {game_id}: {str(e)}")
        return None


def extract_team_names(soup: BeautifulSoup) -> Tuple[str, str]:
    """Extract team names from the soup object."""
    team_headers = soup.select('div.cabecera_partido h4')
    if len(team_headers) < 2:
        raise ValueError("No se encontraron los nombres de los equipos")
    return team_headers[0].text.strip(), team_headers[1].text.strip()


async def parse_table(session: ClientSession, table: BeautifulSoup, team_name: str, game_id: int, config: Dict[str, any], existing_profile_ids: Set[int]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Parse a team's statistics table."""
    players_stats = []
    players_profiles = []
    rows = table.find_all('tr')[2:-4]  # Ignoramos las filas de cabecera y totales
    
    for row in rows:
        player_data = [col.text.strip() for col in row.find_all('td')]
        if len(player_data) < 23:
            logger.warning(f"Datos incompletos para un jugador en el equipo {team_name}, partido {game_id}. Saltando...")
            continue

        player_id = extract_player_id(row)
        if player_id is None:
            continue

        # Crear el diccionario de estadísticas con el player_id como string
        player_stats = create_player_dict(player_data, game_id, team_name, str(player_id))
        players_stats.append(player_stats)

        # Comprobar si necesitamos obtener el perfil
        if player_id not in existing_profile_ids:
            logger.info(f"Obteniendo perfil para jugador {player_id} (no existente en la base de datos)")
            profile = await scrape_player_profile(session, f"https://www.acb.com/jugador/ver/{player_id}", str(player_id), config)
            if profile:
                players_profiles.append(profile)
        else:
            logger.debug(f"Jugador {player_id} ya existe en la base de datos, saltando obtención de perfil")

    return players_stats, players_profiles


def extract_player_id(row: BeautifulSoup) -> Optional[int]:
    """Extract player ID from the row."""
    player_link = row.select_one('td.nombre.jugador.ellipsis a')
    if player_link and 'href' in player_link.attrs:
        match = re.search(r'/(\d+)-', player_link['href'])
        # Convertimos directamente a entero aquí
        return int(match.group(1)) if match else None
    return None


def create_player_dict(player_data: List[str], game_id: int, team_name: str, player_id: str) -> Dict[str, str]:
    """Create a dictionary of player statistics."""
    
    # Procesamos los tiros para obtener intentados y anotados
    t2_data = player_data[4].split('/')
    t2_anotados = t2_data[0] if len(t2_data) > 0 else "0"
    t2_intentados = t2_data[1] if len(t2_data) > 1 else "0"
    
    t3_data = player_data[6].split('/')
    t3_anotados = t3_data[0] if len(t3_data) > 0 else "0"
    t3_intentados = t3_data[1] if len(t3_data) > 1 else "0"
    
    tl_data = player_data[8].split('/')  # Cambiado de t1 a tl
    tl_anotados = tl_data[0] if len(tl_data) > 0 else "0"
    tl_intentados = tl_data[1] if len(tl_data) > 1 else "0"

    player_dict = {
        "id_partido": game_id,
        "player_id": player_id,
        "equipo": team_name,
        "es_titular": player_data[0].startswith('*'),
        "dorsal": player_data[0].strip('*'),
        "nombre": player_data[1],
        "minutos": player_data[2] if player_data[2] else "00:00",
        "puntos": player_data[3],
        "t2_anotados": t2_anotados,
        "t2_intentados": t2_intentados,
        "t2_porcentaje": clean_percentage(player_data[5]),
        "t3_anotados": t3_anotados,
        "t3_intentados": t3_intentados,
        "t3_porcentaje": clean_percentage(player_data[7]),
        "tl_anotados": tl_anotados,  # Cambiado de t1 a tl
        "tl_intentados": tl_intentados,  # Cambiado de t1 a tl
        "tl_porcentaje": clean_percentage(player_data[9]),  # Cambiado de t1 a tl
        "rebotes_defensivos": player_data[11].split('+')[0] if '+' in player_data[11] else '0',
        "rebotes_ofensivos": player_data[11].split('+')[1] if '+' in player_data[11] else '0',
        "rebotes_totales": player_data[10],
        "asistencias": player_data[12],
        "robos": player_data[13],
        "perdidas": player_data[14],
        "tapones_favor": player_data[16],
        "tapones_contra": player_data[17],
        "mates": player_data[18],
        "faltas_cometidas": player_data[19],
        "faltas_recibidas": player_data[20],
        "plus_minus": player_data[21],
        "valoracion": player_data[22]
    }

    # Si el jugador no jugó, rellenar con valores por defecto
    if not player_dict["minutos"] or player_dict["minutos"] == "00:00":
        for key in player_dict:
            if key not in ["id_partido", "player_id", "equipo", "es_titular", "dorsal", "nombre", "minutos"]:
                player_dict[key] = "0"
                if key.endswith('porcentaje'):
                    player_dict[key] = "0"

    return player_dict


def extract_game_info(soup: BeautifulSoup, game_id: int) -> Dict[str, str]:
    """Extract game information from the soup object."""
    game_info = {'id_partido': game_id}
    
    header_info = soup.select_one('.datos_fecha')
    if header_info:
        info_text = header_info.text.strip().split('|')
        game_info.update({
            'jornada': info_text[0].strip().replace('JORNADA ', ''),
            'fecha': info_text[1].strip(),
            'hora': info_text[2].strip(),
            'pabellon': header_info.select_one('.clase_mostrar1280').text.strip() if header_info.select_one('.clase_mostrar1280') else info_text[3].strip() if len(info_text) > 3 else '',
        })
        
        publico_text = info_text[-1] if 'Público:' in info_text[-1] else ''
        if publico_text:
            publico_num = ''.join(c for c in publico_text.split('Público:')[-1].strip() if c.isdigit())
            game_info['publico'] = publico_num
        else:
            game_info['publico'] = ''

    referees = soup.select_one('.datos_arbitros')
    if referees:
        referee_list = referees.text.replace('Árb:', '').strip().split(',')
        for i, ref in enumerate(referee_list[:3], start=1):
            game_info[f'arbitro{i}'] = ref.strip()

    results = soup.select('.resultado')
    if results:
        game_info['resultado_local'] = results[0].text.strip()
        game_info['resultado_visitante'] = results[1].text.strip()

    quarters = soup.select_one('.parciales_por_cuarto')
    if quarters:
        quarter_scores = quarters.text.strip().split()
        local_scores = [score.split('|')[0] for score in quarter_scores]
        visitor_scores = [score.split('|')[1] for score in quarter_scores]
        
        # Guardamos los parciales como listas
        game_info['parciales_local'] = ','.join(local_scores)
        game_info['parciales_visitante'] = ','.join(visitor_scores)

    team_headers = soup.select('div.cabecera_partido h4')
    if len(team_headers) >= 2:
        game_info['local'] = team_headers[0].text.strip()
        game_info['visitante'] = team_headers[1].text.strip()

    return game_info


def extract_team_totals(table: BeautifulSoup, team_name: str, game_id: int) -> Dict[str, str]:
    """Extract team totals from the table."""
    totals_row = table.select_one('tr.totales')
    if not totals_row:
        logger.error(f"No se encontró la fila de totales para el equipo {team_name} en el partido {game_id}")
        return {}

    cols = totals_row.find_all('td')
    if len(cols) < 23:
        logger.error(f"Número insuficiente de columnas en la fila de totales para el equipo {team_name} en el partido {game_id}")
        return {}

    return {
        "id_partido": game_id,
        "equipo": team_name,
        "minutos": cols[2].text.strip() or "00:00",
        "puntos": cols[3].text.strip(),
        "t2_encestados": cols[4].text.strip().split('/')[0] if '/' in cols[4].text else "0",
        "t2_intentados": cols[4].text.strip().split('/')[1] if '/' in cols[4].text else "0",
        "t2_porcentaje": clean_percentage(cols[5].text.strip()),
        "t3_encestados": cols[6].text.strip().split('/')[0] if '/' in cols[6].text else "0",
        "t3_intentados": cols[6].text.strip().split('/')[1] if '/' in cols[6].text else "0",
        "t3_porcentaje": clean_percentage(cols[7].text.strip()),
        "tl_encestados": cols[8].text.strip().split('/')[0] if '/' in cols[8].text else "0",
        "tl_intentados": cols[8].text.strip().split('/')[1] if '/' in cols[8].text else "0",
        "tl_porcentaje": clean_percentage(cols[9].text.strip()),
        "rebotes_totales": cols[10].text.strip(),
        "rebotes_defensivos": cols[11].text.split('+')[0].strip() if '+' in cols[11].text else "0",
        "rebotes_ofensivos": cols[11].text.split('+')[1].strip() if '+' in cols[11].text else "0",
        "asistencias": cols[12].text.strip(),
        "robos": cols[13].text.strip(),
        "perdidas": cols[14].text.strip(),
        "tapones_favor": cols[16].text.strip(),
        "tapones_contra": cols[17].text.strip(),
        "mates": cols[18].text.strip(),
        "faltas_cometidas": cols[19].text.strip(),
        "faltas_recibidas": cols[20].text.strip(),
        "+/-": cols[21].text.strip(),
        "valoracion": cols[22].text.strip()
    }


async def scrape_player_profile(session: ClientSession, url: str, player_id: str, config: Dict[str, any]) -> Optional[Dict[str, str]]:
    """Scrape player profile from the given URL."""
    try:
        html = await fetch(session, url, config)
        soup = BeautifulSoup(html, 'html.parser')
        
        container = soup.find('section', class_='contenedora_contenido_interior contenedora_entidad contenedora_jugadores contenedora_temporadas')
        if not container:
            logger.warning(f"No se pudo encontrar el contenedor principal para el jugador con ID {player_id}. URL: {url}")
            return None
        
        profile = {'player_id': player_id}
        profile['nombre'] = container.find('h1', class_='f-l-a-100 roboto_condensed_bold mayusculas').text.strip()
        
        datos_basicos = container.find('div', class_='f-l-a-100 contenedora_datos_basicos')
        position_element = datos_basicos.find('div', class_='datos_basicos posicion roboto_condensed').find('span', class_='roboto_condensed_bold')
        
        profile.update({
            'equipo': datos_basicos.find('div', class_='datos_basicos equipo roboto_condensed').find('span', class_='roboto_condensed_bold').text.strip(),
            'dorsal': datos_basicos.find('div', class_='datos_basicos dorsal roboto_condensed').find('span', class_='roboto_condensed_bold').text.strip(),
            'posicion': normalize_position(position_element.text.strip()),
            'altura': clean_height(datos_basicos.find('div', class_='datos_basicos altura roboto_condensed').find('span', class_='roboto_condensed_bold').text.strip())
        })

        datos_secundarios = container.find('div', class_='f-l-a-100 contenedora_datos_secundarios')
        birth_city, birth_country = split_birthplace(
            datos_secundarios.find('div', class_='datos_secundarios lugar_nacimiento roboto_condensed')
            .find('span', class_='roboto_condensed_bold').text.strip()
        )
        
        birth_info = datos_secundarios.find('div', class_='datos_secundarios fecha_nacimiento roboto_condensed').find('span', class_='roboto_condensed_bold').text.strip()
        birth_date, age = split_birth_info(birth_info)
        
        full_name = datos_secundarios.find('div', class_='datos_secundarios roboto_condensed').find('span', class_='roboto_condensed_bold').text.strip()
        
        profile.update({
            'nombre_completo': normalize_spaces(full_name),
            'ciudad_nacimiento': birth_city,
            'pais_nacimiento': birth_country,
            'fecha_nacimiento': birth_date,
            'edad': age,
            'nacionalidad': datos_secundarios.find('div', class_='datos_secundarios nacionalidad roboto_condensed').find('span', class_='roboto_condensed_bold').text.strip(),
            'licencia': datos_secundarios.find('div', class_='datos_secundarios licencia roboto_condensed').find('span', class_='roboto_condensed_bold').text.strip()
        })

        return profile
    except Exception as e:
        logger.error(f"Error al obtener el perfil del jugador desde {url}: {str(e)}")
        return None
    

def clean_percentage(percentage_str: str) -> str:
    """Limpia string de porcentaje y elimina el símbolo %."""
    if not percentage_str:
        return "0"
    try:
        # Eliminar el símbolo % y cualquier espacio
        clean_str = percentage_str.strip().replace('%', '')
        return clean_str
    except ValueError:
        return "0"


def clean_height(height_str: str) -> str:
    """Convierte altura del formato '2,03 m' a '203'."""
    try:
        # Elimina 'm' y espacios, reemplaza ',' por '.'
        height = height_str.replace('m', '').strip()
        height = float(height.replace(',', '.'))
        # Convierte a centímetros como entero
        return str(int(height * 100))
    except (ValueError, TypeError):
        logger.warning(f"No se pudo procesar la altura: {height_str}")
        return ""


def split_birthplace(birthplace_str: str) -> Tuple[str, str]:
    """Separa el lugar de nacimiento en ciudad y país."""
    try:
        if not birthplace_str or ',' not in birthplace_str:
            return birthplace_str, ""
        
        parts = birthplace_str.split(',', 1)
        city = parts[0].strip()
        country = parts[1].strip()
        return city, country
    except Exception as e:
        logger.warning(f"Error al procesar lugar de nacimiento: {birthplace_str}. Error: {str(e)}")
        return birthplace_str, ""
    

def split_birth_info(birth_info: str) -> Tuple[str, int]:
    """Separa la información de nacimiento en fecha y edad."""
    try:
        # Formato esperado: "25/06/1992 (32 años)"
        if '(' not in birth_info:
            return birth_info, 0
            
        # Separar fecha y edad
        birth_date = birth_info.split('(')[0].strip()
        
        # Extraer solo el número de la edad
        age_str = birth_info.split('(')[1].split()[0]
        age = int(age_str)
        
        return birth_date, age
    except Exception as e:
        logger.warning(f"Error al procesar fecha y edad: {birth_info}. Error: {str(e)}")
        return birth_info, 0
    
def normalize_position(position: str) -> str:
    """Normaliza las posiciones de juego a formato abreviado."""
    position_map = {
        'Base': 'B',
        'Escolta': 'E',
        'Alero': 'A',
        'Ala-pívot': 'AP',
        'Ala-Pívot': 'AP',  # Añadimos variante con mayúscula
        'Ala-pivot': 'AP',  # Añadimos variante sin tilde
        'Ala-Pivot': 'AP',  # Añadimos variante sin tilde y con mayúscula
        'Pívot': 'P',
        'Pivot': 'P'  # Añadimos variante sin tilde
    }
    try:
        # Solo limpiamos espacios, sin convertir a título
        clean_position = position.strip()
        return position_map.get(clean_position, position)
    except Exception as e:
        logger.warning(f"Error al normalizar posición: {position}. Error: {str(e)}")
        return position
    
def normalize_spaces(text: str) -> str:
    """Normaliza múltiples espacios a un solo espacio."""
    try:
        # Reemplaza múltiples espacios por uno solo y elimina espacios al inicio y final
        return ' '.join(text.split())
    except Exception as e:
        logger.warning(f"Error al normalizar espacios en texto: {text}. Error: {str(e)}")
        return text