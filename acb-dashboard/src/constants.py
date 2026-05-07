"""Constantes del dashboard: colores de equipos, mapeo de posiciones, rutas de datos."""

import os

# Ruta base al directorio de datos
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(_PROJECT_ROOT, "data", "output")
PBP_DIR = os.path.join(_PROJECT_ROOT, "data", "play_by_play")

# Ficheros CSV
PLAYER_STATS_PATH = os.path.join(DATA_DIR, "estadisticas_todos_partidos.csv")
GAME_INFO_PATH = os.path.join(DATA_DIR, "estadisticas_partido.csv")
TEAM_STATS_PATH = os.path.join(DATA_DIR, "estadisticas_equipos_por_partido.csv")
PLAYER_PROFILES_PATH = os.path.join(DATA_DIR, "perfiles_jugadores.csv")

# Colores de equipos ACB (primary, secondary)
TEAM_COLORS = {
    "Unicaja": ("#00A651", "#FFFFFF"),
    "Surne Bilbao": ("#000000", "#FF0000"),
    "Recoletas Salud": ("#0033A0", "#D50032"),
    "Bàsquet Girona": ("#E31837", "#FFFFFF"),
    "La Laguna TFE": ("#FFD700", "#003DA5"),
    "BAXI Manresa": ("#E31837", "#FFFFFF"),
    "Hiopos Lleida": ("#003DA5", "#FFD700"),
    "Río Breogán": ("#004D40", "#FFFFFF"),
    "Barça": ("#A50044", "#004D98"),
    "Real Madrid": ("#FFFFFF", "#00529F"),
    "Joventut": ("#00A651", "#000000"),
    "Casademont Zgz": ("#D50032", "#FFFFFF"),
    "Valencia Basket": ("#FF6600", "#000000"),
    "MoraBanc And": ("#E31837", "#1B365D"),
    "UCAM Murcia": ("#E31837", "#000000"),
    "Coviran Granada": ("#D50032", "#000000"),
    "Dreamland GC": ("#FFD700", "#003DA5"),
    "Baskonia": ("#003DA5", "#D50032"),
    "Kosner Baskonia": ("#003DA5", "#D50032"),
}

# Mapeo de posiciones (código → nombre completo)
POSITION_MAP = {
    "B": "Base",
    "E": "Escolta",
    "A": "Alero",
    "AP": "Ala-Pívot",
    "P": "Pívot",
}

POSITION_ORDER = ["B", "E", "A", "AP", "P"]

# Normalización de nombres de equipo
TEAM_NAME_MAP = {
    "Kosner Baskonia": "Baskonia",
    "Recoletas Salud San Pablo Burgos": "Recoletas Salud",
    "Casademont Zaragoza": "Casademont Zgz",
    "Dreamland Gran Canaria": "Dreamland GC",
    "La Laguna Tenerife": "La Laguna TFE",
    "MoraBanc Andorra": "MoraBanc And",
    "Joventut Badalona": "Joventut",
    "Asisa Joventut": "Joventut",
    "ASISA Joventut": "Joventut",
    "Surne Bilbao Basket": "Surne Bilbao",
}

# 18 equipos únicos (Baskonia normalizado)
ALL_TEAMS = sorted([
    "Unicaja", "Surne Bilbao", "Recoletas Salud", "Bàsquet Girona",
    "La Laguna TFE", "BAXI Manresa", "Hiopos Lleida", "Río Breogán",
    "Barça", "Real Madrid", "Joventut", "Casademont Zgz",
    "Valencia Basket", "MoraBanc And", "UCAM Murcia",
    "Coviran Granada", "Dreamland GC", "Baskonia",
])

# Categorías para radar chart de jugadores
RADAR_CATEGORIES = [
    "Puntos", "Eficiencia", "Rebotes", "Asistencias",
    "Robos", "Tapones", "Pérdidas (inv)", "Valoración"
]
