"""
Parsers para extraer datos de las páginas HTML de la ACB.
"""
import logging
import re
import constants as const

from typing import Dict, List, Optional, Tuple, Any, Set
from bs4 import BeautifulSoup
from aiohttp import ClientSession
from utils import (
    clean_percentage, 
    clean_height, 
    split_birthplace, 
    split_birth_info, 
    normalize_position, 
    normalize_spaces,
    validate_number,
    safe_extract_text
)
from http_client import fetch



logger = logging.getLogger('basketball_scraper')


def extract_player_id(row: BeautifulSoup) -> Optional[int]:
    """
    Extrae el ID del jugador a partir de la fila de la tabla.
    
    Args:
        row: Fila de la tabla de estadísticas
        
    Returns:
        ID del jugador como entero o None si no se encuentra
    """
    if row is None:
        return None
        
    try:
        player_link = row.select_one(const.SELECTORS["player_link"])
        if player_link and 'href' in player_link.attrs:
            match = re.search(r'/(\d+)-', player_link['href'])
            return int(match.group(1)) if match else None
        return None
    except Exception as e:
        logger.warning(f"Error al extraer ID de jugador: {str(e)}")
        return None


def extract_team_names(soup: BeautifulSoup) -> Tuple[str, str]:
    """
    Extrae los nombres de los equipos de la página del partido.
    
    Args:
        soup: Objeto BeautifulSoup con el HTML del partido
        
    Returns:
        Tupla con los nombres de los equipos (local, visitante)
        
    Raises:
        ValueError: Si no se encuentran los nombres de los equipos
    """
    if soup is None:
        raise ValueError("El objeto BeautifulSoup no puede ser None")
        
    try:
        team_headers = soup.select(const.SELECTORS["team_headers"])
        if len(team_headers) < 2:
            raise ValueError("No se encontraron los nombres de los equipos")
        return team_headers[0].text.strip(), team_headers[1].text.strip()
    except Exception as e:
        logger.error(f"Error al extraer nombres de equipos: {str(e)}")
        raise ValueError(f"Error al extraer nombres de equipos: {str(e)}")


def extract_game_info(soup: BeautifulSoup, game_id: int) -> Dict[str, str]:
    """
    Extrae la información general del partido.
    
    Args:
        soup: Objeto BeautifulSoup con el HTML del partido
        game_id: ID del partido
        
    Returns:
        Diccionario con la información del partido
    """
    if soup is None:
        return {'id_partido': game_id}
        
    game_info = {'id_partido': game_id}
    
    try:
        # Información de la cabecera
        header_info = soup.select_one(const.SELECTORS["game_header_info"])
        if header_info:
            info_text = header_info.text.strip().split('|')
            
            # Extraer jornada
            if info_text and len(info_text) > 0:
                jornada_text = info_text[0].strip()
                jornada_match = re.search(r'JORNADA\s+(\d+)', jornada_text)
                game_info['jornada'] = jornada_match.group(1) if jornada_match else jornada_text
            
            # Extraer fecha y hora
            if len(info_text) > 1:
                game_info['fecha'] = info_text[1].strip()
            if len(info_text) > 2:
                game_info['hora'] = info_text[2].strip()
            
            # Extraer pabellón
            pabellon = header_info.select_one('.clase_mostrar1280')
            if pabellon:
                game_info['pabellon'] = pabellon.text.strip()
            elif len(info_text) > 3:
                game_info['pabellon'] = info_text[3].strip()
            else:
                game_info['pabellon'] = ''
            
            # Extraer público
            publico_text = info_text[-1] if info_text and 'Público:' in info_text[-1] else ''
            if publico_text:
                publico_num = validate_number(
                    publico_text.split('Público:')[-1].strip(), 
                    min_value=0, 
                    max_value=100000
                )
                game_info['publico'] = str(publico_num) if publico_num is not None else ''
            else:
                game_info['publico'] = ''
        
        # Información de árbitros
        referees = soup.select_one(const.SELECTORS["referees_info"])
        if referees:
            referee_text = referees.text.replace('Árb:', '').strip()
            referee_list = [ref.strip() for ref in referee_text.split(',') if ref.strip()]
            
            # Guardar hasta 3 árbitros
            for i, ref in enumerate(referee_list[:3], start=1):
                game_info[f'arbitro{i}'] = ref
        
        # Resultados
        results = soup.select(const.SELECTORS["game_results"])
        if len(results) >= 2:
            game_info['resultado_local'] = results[0].text.strip()
            game_info['resultado_visitante'] = results[1].text.strip()
        
        # Parciales por cuarto
        quarters = soup.select_one(const.SELECTORS["quarter_scores"])
        if quarters:
            quarter_scores = quarters.text.strip().split()
            try:
                local_scores = [score.split('|')[0] for score in quarter_scores if '|' in score]
                visitor_scores = [score.split('|')[1] for score in quarter_scores if '|' in score]
                
                # Guardar los parciales como listas
                game_info['parciales_local'] = ','.join(local_scores)
                game_info['parciales_visitante'] = ','.join(visitor_scores)
            except (IndexError, ValueError) as e:
                logger.warning(f"Error al extraer parciales: {str(e)}")
        
        # Nombres de equipos
        team_local, team_visitor = extract_team_names(soup)
        game_info['local'] = team_local
        game_info['visitante'] = team_visitor
    
    except Exception as e:
        logger.error(f"Error al extraer información del partido {game_id}: {str(e)}")
    
    return game_info


def create_player_dict(player_data: List[str], game_id: int, team_name: str, player_id: str) -> Dict[str, str]:
    """
    Crea un diccionario con las estadísticas del jugador.
    
    Args:
        player_data: Lista de datos del jugador
        game_id: ID del partido
        team_name: Nombre del equipo
        player_id: ID del jugador
        
    Returns:
        Diccionario con las estadísticas del jugador
    """
    if not player_data or len(player_data) < const.PLAYER_STATS_COLUMNS_COUNT:
        logger.warning(f"Datos insuficientes para crear estadísticas del jugador {player_id}")
        return {}
    
    try:
        # Procesar tiros de 2 puntos
        t2_data = player_data[4].split('/') if player_data[4] else ['0', '0']
        t2_anotados = t2_data[0] if len(t2_data) > 0 else "0"
        t2_intentados = t2_data[1] if len(t2_data) > 1 else "0"
        
        # Procesar tiros de 3 puntos
        t3_data = player_data[6].split('/') if player_data[6] else ['0', '0']
        t3_anotados = t3_data[0] if len(t3_data) > 0 else "0"
        t3_intentados = t3_data[1] if len(t3_data) > 1 else "0"
        
        # Procesar tiros libres
        tl_data = player_data[8].split('/') if player_data[8] else ['0', '0']
        tl_anotados = tl_data[0] if len(tl_data) > 0 else "0"
        tl_intentados = tl_data[1] if len(tl_data) > 1 else "0"
        
        # Procesar rebotes
        rebotes_str = player_data[11] if len(player_data) > 11 else "0+0"
        rebotes_def = rebotes_str.split('+')[0] if '+' in rebotes_str else '0'
        rebotes_of = rebotes_str.split('+')[1] if '+' in rebotes_str else '0'
        
        # Crear el diccionario de estadísticas
        player_dict = {
            "id_partido": game_id,
            "player_id": player_id,
            "equipo": team_name,
            "es_titular": player_data[0].startswith('*') if player_data[0] else False,
            "dorsal": player_data[0].strip('*') if player_data[0] else "",
            "nombre": player_data[1] if len(player_data) > 1 else "",
            "minutos": player_data[2] if len(player_data) > 2 and player_data[2] else "00:00",
            "puntos": player_data[3] if len(player_data) > 3 else "0",
            "t2_anotados": t2_anotados,
            "t2_intentados": t2_intentados,
            "t2_porcentaje": clean_percentage(player_data[5] if len(player_data) > 5 else ""),
            "t3_anotados": t3_anotados,
            "t3_intentados": t3_intentados,
            "t3_porcentaje": clean_percentage(player_data[7] if len(player_data) > 7 else ""),
            "tl_anotados": tl_anotados,
            "tl_intentados": tl_intentados,
            "tl_porcentaje": clean_percentage(player_data[9] if len(player_data) > 9 else ""),
            "rebotes_defensivos": rebotes_def,
            "rebotes_ofensivos": rebotes_of,
            "rebotes_totales": player_data[10] if len(player_data) > 10 else "0",
            "asistencias": player_data[12] if len(player_data) > 12 else "0",
            "robos": player_data[13] if len(player_data) > 13 else "0",
            "perdidas": player_data[14] if len(player_data) > 14 else "0",
            "tapones_favor": player_data[16] if len(player_data) > 16 else "0",
            "tapones_contra": player_data[17] if len(player_data) > 17 else "0",
            "mates": player_data[18] if len(player_data) > 18 else "0",
            "faltas_cometidas": player_data[19] if len(player_data) > 19 else "0",
            "faltas_recibidas": player_data[20] if len(player_data) > 20 else "0",
            "plus_minus": player_data[21] if len(player_data) > 21 else "0",
            "valoracion": player_data[22] if len(player_data) > 22 else "0"
        }
        
        # Si el jugador no jugó, rellenar con valores por defecto
        if not player_dict["minutos"] or player_dict["minutos"] == "00:00":
            for key in player_dict:
                if key not in const.NON_PLAYING_COLUMNS:
                    player_dict[key] = "0"
        
        return player_dict
    except Exception as e:
        logger.error(f"Error al crear diccionario de jugador {player_id}: {str(e)}")
        return {}


def extract_team_totals(table: BeautifulSoup, team_name: str, game_id: int) -> Dict[str, str]:
    """
    Extrae los totales del equipo a partir de la tabla de estadísticas.
    
    Args:
        table: Tabla de estadísticas del equipo
        team_name: Nombre del equipo
        game_id: ID del partido
        
    Returns:
        Diccionario con los totales del equipo
    """
    if table is None:
        logger.error(f"Tabla no encontrada para el equipo {team_name} en el partido {game_id}")
        return {}
    
    try:
        # Buscar la fila de totales
        totals_row = table.select_one(const.SELECTORS["team_totals_row"])
        if not totals_row:
            logger.error(f"No se encontró la fila de totales para el equipo {team_name} en el partido {game_id}")
            return {}
        
        # Extraer las celdas
        cols = totals_row.find_all('td')
        if len(cols) < const.PLAYER_STATS_COLUMNS_COUNT:
            logger.error(f"Número insuficiente de columnas en la fila de totales para el equipo {team_name}")
            return {}
        
        # Procesar tiros de 2 puntos
        t2_str = cols[4].text.strip() if len(cols) > 4 else "0/0"
        t2_parts = t2_str.split('/')
        t2_encestados = t2_parts[0] if len(t2_parts) > 0 else "0"
        t2_intentados = t2_parts[1] if len(t2_parts) > 1 else "0"
        
        # Procesar tiros de 3 puntos
        t3_str = cols[6].text.strip() if len(cols) > 6 else "0/0"
        t3_parts = t3_str.split('/')
        t3_encestados = t3_parts[0] if len(t3_parts) > 0 else "0"
        t3_intentados = t3_parts[1] if len(t3_parts) > 1 else "0"
        
        # Procesar tiros libres
        tl_str = cols[8].text.strip() if len(cols) > 8 else "0/0"
        tl_parts = tl_str.split('/')
        tl_encestados = tl_parts[0] if len(tl_parts) > 0 else "0"
        tl_intentados = tl_parts[1] if len(tl_parts) > 1 else "0"
        
        # Procesar rebotes
        rebotes_str = cols[11].text.strip() if len(cols) > 11 else "0+0"
        rebotes_def = rebotes_str.split('+')[0].strip() if '+' in rebotes_str else "0"
        rebotes_of = rebotes_str.split('+')[1].strip() if '+' in rebotes_str else "0"
        
        # Crear el diccionario con los totales
        return {
            "id_partido": game_id,
            "equipo": team_name,
            "minutos": cols[2].text.strip() if len(cols) > 2 else "00:00",
            "puntos": cols[3].text.strip() if len(cols) > 3 else "0",
            "t2_encestados": t2_encestados,
            "t2_intentados": t2_intentados,
            "t2_porcentaje": clean_percentage(cols[5].text.strip() if len(cols) > 5 else ""),
            "t3_encestados": t3_encestados,
            "t3_intentados": t3_intentados,
            "t3_porcentaje": clean_percentage(cols[7].text.strip() if len(cols) > 7 else ""),
            "tl_encestados": tl_encestados,
            "tl_intentados": tl_intentados,
            "tl_porcentaje": clean_percentage(cols[9].text.strip() if len(cols) > 9 else ""),
            "rebotes_totales": cols[10].text.strip() if len(cols) > 10 else "0",
            "rebotes_defensivos": rebotes_def,
            "rebotes_ofensivos": rebotes_of,
            "asistencias": cols[12].text.strip() if len(cols) > 12 else "0",
            "robos": cols[13].text.strip() if len(cols) > 13 else "0",
            "perdidas": cols[14].text.strip() if len(cols) > 14 else "0",
            "tapones_favor": cols[16].text.strip() if len(cols) > 16 else "0",
            "tapones_contra": cols[17].text.strip() if len(cols) > 17 else "0",
            "mates": cols[18].text.strip() if len(cols) > 18 else "0",
            "faltas_cometidas": cols[19].text.strip() if len(cols) > 19 else "0",
            "faltas_recibidas": cols[20].text.strip() if len(cols) > 20 else "0",
            "plus_minus": cols[21].text.strip() if len(cols) > 21 else "0",
            "valoracion": cols[22].text.strip() if len(cols) > 22 else "0"
        }
    except Exception as e:
        logger.error(f"Error al extraer totales del equipo {team_name}: {str(e)}")
        return {}


async def scrape_player_profile(
    session: ClientSession, 
    player_id: int, 
    config: Dict[str, Any]
) -> Optional[Dict[str, str]]:
    """
    Extrae el perfil de un jugador a partir de su ID.
    
    Args:
        session: Sesión HTTP para realizar la petición
        player_id: ID del jugador
        config: Configuración con parámetros como user_agent
        
    Returns:
        Diccionario con el perfil del jugador o None si hay error
    """
    if not player_id:
        logger.warning("ID de jugador vacío al intentar extraer perfil")
        return None
    
    # Construir la URL del perfil
    url = const.PLAYER_PROFILE_URL.format(player_id=player_id)
    
    try:
        # Obtener el HTML del perfil
        html = await fetch(session, url, config)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar el contenedor principal
        container = soup.select_one(const.SELECTORS["player_profile_container"])
        if not container:
            logger.warning(f"No se encontró el contenedor del perfil para el jugador {player_id}")
            return None
        
        # Inicializar el perfil con el ID del jugador
        profile = {'player_id': str(player_id)}
        
        # Extraer el nombre
        player_name_el = container.select_one(const.SELECTORS["player_name"])
        if player_name_el:
            profile['nombre'] = player_name_el.text.strip()
        else:
            logger.warning(f"No se encontró el nombre para el jugador {player_id}")
            return None
        
        # Extraer datos básicos
        datos_basicos = container.select_one(const.SELECTORS["player_basic_data"])
        if datos_basicos:
            # Extraer posición
            position_el = datos_basicos.find('div', class_='datos_basicos posicion roboto_condensed')
            position_span = position_el.find('span', class_='roboto_condensed_bold') if position_el else None
            position = position_span.text.strip() if position_span else ""
            
            # Actualizar perfil con datos básicos
            profile.update({
                'equipo': safe_extract_text(datos_basicos, 'div.datos_basicos.equipo.roboto_condensed span.roboto_condensed_bold'),
                'dorsal': safe_extract_text(datos_basicos, 'div.datos_basicos.dorsal.roboto_condensed span.roboto_condensed_bold'),
                'posicion': normalize_position(position),
                'altura': clean_height(safe_extract_text(datos_basicos, 'div.datos_basicos.altura.roboto_condensed span.roboto_condensed_bold'))
            })
        
        # Extraer datos secundarios
        datos_secundarios = container.select_one(const.SELECTORS["player_secondary_data"])
        if datos_secundarios:
            # Lugar de nacimiento
            birth_place = safe_extract_text(
                datos_secundarios, 
                'div.datos_secundarios.lugar_nacimiento.roboto_condensed span.roboto_condensed_bold'
            )
            city, country = split_birthplace(birth_place)
            
            # Fecha de nacimiento y edad
            birth_info = safe_extract_text(
                datos_secundarios, 
                'div.datos_secundarios.fecha_nacimiento.roboto_condensed span.roboto_condensed_bold'
            )
            birth_date, age = split_birth_info(birth_info)
            
            # Nombre completo
            full_name = safe_extract_text(
                datos_secundarios, 
                'div.datos_secundarios.roboto_condensed span.roboto_condensed_bold'
            )
            
            # Actualizar perfil con datos secundarios
            profile.update({
                'nombre_completo': normalize_spaces(full_name),
                'ciudad_nacimiento': city,
                'pais_nacimiento': country,
                'fecha_nacimiento': birth_date,
                'edad': age,
                'nacionalidad': safe_extract_text(
                    datos_secundarios, 
                    'div.datos_secundarios.nacionalidad.roboto_condensed span.roboto_condensed_bold'
                ),
                'licencia': safe_extract_text(
                    datos_secundarios, 
                    'div.datos_secundarios.licencia.roboto_condensed span.roboto_condensed_bold'
                )
            })
        
        return profile
    except Exception as e:
        logger.error(f"Error al extraer perfil del jugador {player_id}: {str(e)}")
        return None


async def parse_table(
    session: ClientSession, 
    table: BeautifulSoup, 
    team_name: str, 
    game_id: int, 
    config: Dict[str, Any], 
    existing_profile_ids: Set[int]
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Parsea la tabla de estadísticas de un equipo.
    
    Args:
        session: Sesión HTTP para realizar peticiones
        table: Tabla de estadísticas del equipo
        team_name: Nombre del equipo
        game_id: ID del partido
        config: Configuración con parámetros como user_agent
        existing_profile_ids: Conjunto de IDs de perfiles ya existentes
        
    Returns:
        Tupla con las estadísticas de los jugadores y sus perfiles
    """
    if table is None:
        logger.error(f"Tabla no encontrada para el equipo {team_name} en el partido {game_id}")
        return [], []
    
    players_stats = []
    players_profiles = []
    
    try:
        # Extraer filas de jugadores (ignorando cabeceras y totales)
        rows = table.find_all('tr')[
            const.TABLE_HEADER_ROWS:-const.TABLE_FOOTER_ROWS
        ]
        
        # Procesar cada fila (jugador)
        for row in rows:
            # Extraer datos de la fila
            player_data = [col.text.strip() for col in row.find_all('td')]
            
            # Verificar si hay suficientes datos
            if len(player_data) < const.PLAYER_STATS_COLUMNS_COUNT:
                logger.warning(
                    f"Datos incompletos para un jugador en el equipo {team_name}, "
                    f"partido {game_id}. Encontrados {len(player_data)} campos."
                )
                continue
            
            # Extraer ID del jugador
            player_id = extract_player_id(row)
            if player_id is None:
                logger.warning(f"No se pudo extraer ID de jugador en el equipo {team_name}")
                continue
            
            # Crear diccionario de estadísticas
            player_stats = create_player_dict(player_data, game_id, team_name, str(player_id))
            if player_stats:
                players_stats.append(player_stats)
            
            # Comprobar si necesitamos obtener el perfil
            if player_id not in existing_profile_ids:
                # Obtener perfil directamente
                profile = await scrape_player_profile(session, player_id, config)
                
                if profile:
                    players_profiles.append(profile)
                    logger.info(f"Perfil de jugador {player_id} obtenido correctamente")
            else:
                logger.debug(f"Jugador {player_id} ya existe en la base de datos, omitiendo perfil")
    
    except Exception as e:
        logger.error(f"Error al parsear tabla del equipo {team_name}: {str(e)}")
    
    return players_stats, players_profiles