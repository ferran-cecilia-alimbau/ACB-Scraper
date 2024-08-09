import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging

logger = logging.getLogger('basketball_scraper')

def get_game_data(url, game_id):
    """
    Función para extraer las estadísticas de un partido de baloncesto desde una URL.
    """
    logger.info(f"Obteniendo datos para el partido {game_id} desde {url}")
    
    # Hacer una solicitud GET a la URL
    try:
        response = requests.get(url)
        response.raise_for_status()  # Verifica que la solicitud fue exitosa
    except requests.RequestException as e:
        logger.error(f"No se pudieron obtener los datos para el partido {game_id}: {str(e)}")
        raise

    # Analizar el contenido HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extraer nombres de equipos y el marcador
    team_headers = soup.select('div.cabecera_partido h4')
    if len(team_headers) < 2:
        logger.error(f"No se encontraron los nombres de los equipos para el partido {game_id}")
        raise ValueError("No se encontraron los nombres de los equipos.")

    team1 = team_headers[0].text.strip()
    team2 = team_headers[1].text.strip()
    logger.info(f"Partido {game_id}: {team1} vs {team2}")

    # Extraer las estadísticas de los jugadores
    tables = soup.find_all('table', {'data-toggle': 'table-estadisticas'})
    if len(tables) < 2:
        logger.error(f"No se encontraron las tablas de estadísticas para el partido {game_id}")
        raise ValueError("No se encontraron las tablas de estadísticas.")

    # Procesar tablas y añadir columnas de identificación
    headers1, team1_stats = parse_table(tables[0], team1)
    headers2, team2_stats = parse_table(tables[1], team2)

    df_team1 = pd.DataFrame(team1_stats, columns=headers1)
    df_team2 = pd.DataFrame(team2_stats, columns=headers2)

    # Añadir columnas de identificación
    df_team1['id partido'] = game_id
    df_team1['equipo'] = team1
    df_team2['id partido'] = game_id
    df_team2['equipo'] = team2

    logger.info(f"Procesamiento de datos completado para el partido {game_id}")
    return df_team1, df_team2

def parse_table(table, team_name):
    """
    Función auxiliar para procesar la tabla de estadísticas de un equipo.
    """
    logger.debug(f"Analizando tabla de estadísticas para el equipo {team_name}")
    players_stats = []
    rows = table.find_all('tr')
    headers = [header.text.strip() for header in rows[1].find_all('th')]

    # Insertar la columna "Titular" justo después de "Dorsal"
    headers.insert(1, "Titular")

    # Excluir las últimas cuatro filas (totales y estadísticas adicionales)
    for row in rows[2:-4]:  # Excluir las últimas cuatro filas
        cols = row.find_all('td')
        player_data = [col.text.strip() for col in cols]

        # Separar "Titular" y "Dorsal"
        if player_data[0].startswith('*'):
            player_data[0] = player_data[0][1:]  # Quitar el asterisco para obtener el dorsal
            player_data.insert(1, '*')  # Es titular
        else:
            player_data.insert(1, '')  # No es titular

        # Verificar si el jugador no jugó (Tiempo Jugado vacío)
        if not player_data[3]:  # Columna de tiempo jugado está vacía
            player_data[3] = '00:00'  # Formato de tiempo jugado para jugadores que no jugaron
            for i in range(4, len(player_data)):
                player_data[i] = '0'  # Llenar con ceros el resto de columnas
            # Aseguramos que los porcentajes tengan formato "0%"
            for i in [6, 9, 12]:
                player_data[i] = '0%'  # Llenar porcentajes con "0%"

        # Separar "Defensivos", "Ofensivos" y calcular "Totales"
        reb_def_of = player_data[11].split("+")
        try:
            reb_defensivos = int(reb_def_of[0]) if reb_def_of[0] else 0  # Manejar vacío como 0
            reb_ofensivos = int(reb_def_of[1]) if len(reb_def_of) > 1 and reb_def_of[1] else 0  # Manejar vacío como 0
        except ValueError:
            reb_defensivos = 0
            reb_ofensivos = 0

        reb_totales = reb_defensivos + reb_ofensivos  # Rebotes Totales

        # Reemplazar en las posiciones correctas
        player_data[11] = str(reb_defensivos)  # Rebotes Defensivos
        player_data.insert(12, str(reb_ofensivos))  # Rebotes Ofensivos
        player_data[13] = str(reb_totales)  # Rebotes Totales

        players_stats.append(player_data)

    # Actualizar encabezados después de separar rebotes
    headers[11] = "Reb. Defensivos"
    headers.insert(12, "Reb. Ofensivos")
    headers[13] = "Reb. Totales"

    logger.debug(f"Análisis de tabla completado para el equipo {team_name}")
    return headers, players_stats