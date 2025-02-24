"""
Utilidades y funciones auxiliares para el proyecto ACB Scraper.
"""
from typing import Tuple, Any, Optional
import re
import logging
from constants import POSITION_MAP

logger = logging.getLogger('basketball_scraper')


def clean_percentage(percentage_str: str) -> str:
    """
    Limpia un string de porcentaje eliminando el símbolo %.
    
    Args:
        percentage_str: String con el porcentaje (ej: "45.5%")
        
    Returns:
        String con el porcentaje limpio (ej: "45.5")
    """
    if not percentage_str:
        return "0"
    try:
        # Eliminar el símbolo % y cualquier espacio
        clean_str = percentage_str.strip().replace('%', '')
        return clean_str
    except ValueError:
        logger.warning(f"Error al limpiar porcentaje: {percentage_str}")
        return "0"


def clean_height(height_str: str) -> str:
    """
    Convierte la altura del formato '2,03 m' a centímetros '203'.
    
    Args:
        height_str: String con la altura en metros (ej: "2,03 m")
        
    Returns:
        String con la altura en centímetros (ej: "203")
    """
    if not height_str:
        return ""
        
    try:
        # Eliminar 'm' y espacios, reemplazar ',' por '.'
        height = height_str.replace('m', '').strip()
        height = float(height.replace(',', '.'))
        # Convertir a centímetros como entero
        return str(int(height * 100))
    except (ValueError, TypeError) as e:
        logger.warning(f"Error al procesar altura '{height_str}': {str(e)}")
        return ""


def split_birthplace(birthplace_str: str) -> Tuple[str, str]:
    """
    Separa el lugar de nacimiento en ciudad y país.
    
    Args:
        birthplace_str: String con el lugar de nacimiento (ej: "Madrid, España")
        
    Returns:
        Tupla con la ciudad y el país (ej: ("Madrid", "España"))
    """
    if not birthplace_str:
        return "", ""
        
    try:
        if ',' not in birthplace_str:
            return birthplace_str.strip(), ""
        
        parts = birthplace_str.split(',', 1)
        city = parts[0].strip()
        country = parts[1].strip()
        return city, country
    except Exception as e:
        logger.warning(f"Error al procesar lugar de nacimiento '{birthplace_str}': {str(e)}")
        return birthplace_str.strip(), ""


def split_birth_info(birth_info: str) -> Tuple[str, int]:
    """
    Separa la información de nacimiento en fecha y edad.
    
    Args:
        birth_info: String con info de nacimiento (ej: "25/06/1992 (32 años)")
        
    Returns:
        Tupla con fecha de nacimiento y edad (ej: ("25/06/1992", 32))
    """
    if not birth_info:
        return "", 0
        
    try:
        # Si no tiene el formato esperado
        if '(' not in birth_info:
            return birth_info.strip(), 0
            
        # Separar fecha y edad
        birth_date = birth_info.split('(')[0].strip()
        
        # Extraer solo el número de la edad
        age_match = re.search(r'\((\d+)', birth_info)
        age = int(age_match.group(1)) if age_match else 0
        
        return birth_date, age
    except Exception as e:
        logger.warning(f"Error al procesar fecha y edad '{birth_info}': {str(e)}")
        return birth_info.strip(), 0


def normalize_position(position: str) -> str:
    """
    Normaliza las posiciones de juego a formato abreviado.
    
    Args:
        position: String con la posición (ej: "Base")
        
    Returns:
        Posición en formato abreviado (ej: "B")
    """
    if not position:
        return ""
        
    try:
        clean_position = position.strip()
        return POSITION_MAP.get(clean_position, position)
    except Exception as e:
        logger.warning(f"Error al normalizar posición '{position}': {str(e)}")
        return position


def normalize_spaces(text: str) -> str:
    """
    Normaliza múltiples espacios a un solo espacio.
    
    Args:
        text: String con espacios múltiples
        
    Returns:
        String con espacios normalizados
    """
    if not text:
        return ""
        
    try:
        # Reemplaza múltiples espacios por uno solo y elimina espacios al inicio y final
        return ' '.join(text.split())
    except Exception as e:
        logger.warning(f"Error al normalizar espacios en texto '{text}': {str(e)}")
        return text


def safe_extract_text(element: Any, selector: str, default: str = "") -> str:
    """
    Extrae texto de un elemento HTML de forma segura con manejo de errores.
    
    Args:
        element: Elemento BeautifulSoup del que extraer
        selector: Selector CSS para encontrar el subelemento
        default: Valor por defecto si hay error
        
    Returns:
        Texto extraído o valor por defecto
    """
    if element is None:
        return default
        
    try:
        found = element.select_one(selector)
        return found.text.strip() if found else default
    except Exception as e:
        logger.warning(f"Error al extraer texto con selector '{selector}': {str(e)}")
        return default


def validate_number(value: str, min_value: int = 0, max_value: int = 1000000) -> Optional[int]:
    """
    Valida y convierte un string a número dentro de un rango.
    
    Args:
        value: String a validar
        min_value: Valor mínimo aceptable
        max_value: Valor máximo aceptable
        
    Returns:
        Entero validado o None si es inválido
    """
    if not value:
        return None
        
    try:
        num = int(re.sub(r'[^\d]', '', value))
        if min_value <= num <= max_value:
            return num
        logger.warning(f"Valor numérico fuera de rango permitido: {num}")
        return None
    except (ValueError, TypeError) as e:
        logger.warning(f"Error al validar número '{value}': {str(e)}")
        return None