"""
Constantes y configuraciones para el proyecto ACB Scraper.
Centraliza URLs, tamaños, y otros valores constantes.
"""
from typing import Dict, Any, List

# URLs base
BASE_URL = "https://www.acb.com/partido/estadisticas/id/"
PLAYER_PROFILE_URL = "https://www.acb.com/jugador/ver/{player_id}"

# Archivos
CONFIG_FILE = "config.json"
MATCH_IDS_FILE = "data/input/match_ids.json"

# Configuraciones de scraping
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MAX_RETRIES = 3
RETRY_MIN_WAIT = 2
RETRY_MAX_WAIT = 10
RETRY_MULTIPLIER = 1
DEFAULT_RATE_LIMIT = 1
MAX_CONCURRENT_REQUESTS = 5

# Validación de HTML
MIN_VALID_HTML_LENGTH = 200  # Bytes mínimos para considerar HTML válido

# Procesamiento de datos
CHUNK_SIZE = 10000  # Tamaño para procesamiento eficiente en memoria

# Selectores HTML comunes
SELECTORS = {
    "team_headers": "div.cabecera_partido h4",
    "team_stats_table": "table[data-toggle='table-estadisticas']",
    "team_totals_row": "tr.totales",
    "player_link": "td.nombre.jugador.ellipsis a",
    "game_header_info": ".datos_fecha",
    "referees_info": ".datos_arbitros",
    "game_results": ".resultado",
    "quarter_scores": ".parciales_por_cuarto",
    "player_profile_container": "section.contenedora_contenido_interior.contenedora_entidad.contenedora_jugadores.contenedora_temporadas",
    "player_name": "h1.f-l-a-100.roboto_condensed_bold.mayusculas",
    "player_basic_data": "div.f-l-a-100.contenedora_datos_basicos",
    "player_secondary_data": "div.f-l-a-100.contenedora_datos_secundarios"
}

# Mapeos para posiciones de juego
POSITION_MAP = {
    'Base': 'B',
    'Escolta': 'E',
    'Alero': 'A',
    'Ala-pívot': 'AP',
    'Ala-Pívot': 'AP',
    'Ala-pivot': 'AP',
    'Ala-Pivot': 'AP',
    'Pívot': 'P',
    'Pivot': 'P'
}

# Configuración de columnas para jugadores que no jugaron
NON_PLAYING_COLUMNS = [
    "id_partido", "player_id", "equipo", "es_titular", 
    "dorsal", "nombre", "minutos"
]

# Índices para ignorar filas en tablas de estadísticas
TABLE_HEADER_ROWS = 2
TABLE_FOOTER_ROWS = 4

# Varios
PLAYER_STATS_COLUMNS_COUNT = 23