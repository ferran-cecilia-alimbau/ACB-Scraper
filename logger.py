"""
Módulo de configuración de logging para el proyecto ACB Scraper.
Proporciona funcionalidad para configurar y obtener loggers consistentes.
"""
import logging
import os
from datetime import datetime
from typing import Optional, Union


def setup_logger(
    name: str = 'basketball_scraper',
    log_level: int = logging.DEBUG,
    log_dir: str = 'data/logs',
    console_level: Optional[int] = logging.INFO,
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
) -> logging.Logger:
    """
    Configura y devuelve un logger con handlers para archivo y opcionalmente consola.

    Args:
        name: Nombre del logger
        log_level: Nivel de logging para el archivo
        log_dir: Directorio donde se guardarán los logs
        console_level: Nivel de logging para la consola (None para deshabilitar)
        log_format: Formato de los mensajes de log

    Returns:
        Un logger configurado
    """
    # Validar parámetros
    if not isinstance(name, str) or not name:
        raise ValueError("El nombre del logger debe ser una cadena no vacía")
    
    if not isinstance(log_dir, str) or not log_dir:
        raise ValueError("El directorio de logs debe ser una cadena no vacía")
    
    # Crear directorio de logs de forma segura
    log_dir_abs = os.path.abspath(log_dir)
    os.makedirs(log_dir_abs, exist_ok=True)

    # Crear y configurar el logger
    logger = logging.getLogger(name)
    
    # Si el logger ya tiene handlers, asumimos que ya está configurado
    if logger.handlers:
        return logger
        
    logger.setLevel(log_level)
    
    # Crear timestamp único para el archivo de log
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = os.path.join(log_dir_abs, f"scraper_{timestamp}.log")
    
    # Configurar file handler
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(log_level)
    
    # Crear formateador y añadirlo a los handlers
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    
    # Añadir file handler al logger
    logger.addHandler(file_handler)
    
    # Configurar console handler si está habilitado
    if console_level is not None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    logger.info(f"Logger configurado. Logs guardados en: {log_filename}")
    return logger