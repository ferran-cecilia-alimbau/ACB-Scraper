"""
Cliente HTTP asíncrono simplificado para ACB Scraper.
"""
import logging
import asyncio
import time
from typing import Dict, Any
import aiohttp
from aiohttp import ClientSession, ClientError, ClientResponseError
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type,
    before_sleep_log
)
import constants as const

logger = logging.getLogger('basketball_scraper')

# Variable global para controlar el tiempo entre peticiones
last_request_time = 0
rate_limit_lock = asyncio.Lock()

@retry(
    retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
    stop=stop_after_attempt(const.MAX_RETRIES),
    wait=wait_exponential(
        multiplier=const.RETRY_MULTIPLIER,
        min=const.RETRY_MIN_WAIT,
        max=const.RETRY_MAX_WAIT
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def fetch(session: ClientSession, url: str, config: Dict[str, Any]) -> str:
    """
    Obtiene el contenido HTML de una URL con reintentos exponenciales
    y una simple pausa entre peticiones.
    
    Args:
        session: Sesión aiohttp para hacer la petición
        url: URL a la que hacer la petición
        config: Configuración con parámetros como user_agent
        
    Returns:
        Contenido HTML de la respuesta
        
    Raises:
        ClientError: Si hay un error en la petición tras los reintentos
        asyncio.TimeoutError: Si la petición excede el timeout
    """
    if not url:
        raise ValueError("La URL no puede estar vacía")
    
    # Control simple de velocidad de peticiones
    global last_request_time
    async with rate_limit_lock:
        current_time = time.time()
        time_since_last = current_time - last_request_time
        rate_limit = config.get('rate_limit', const.DEFAULT_RATE_LIMIT)
        
        if time_since_last < rate_limit:
            wait_time = rate_limit - time_since_last
            logger.debug(f"Esperando {wait_time:.2f}s entre peticiones")
            await asyncio.sleep(wait_time)
        
        last_request_time = time.time()
    
    # Obtener headers y parámetros
    headers = {'User-Agent': config.get('user_agent', const.DEFAULT_USER_AGENT)}
    timeout = aiohttp.ClientTimeout(total=config.get('timeout', 30))
    
    try:
        logger.info(f"Realizando petición HTTP a: {url}")
        async with session.get(url, headers=headers, timeout=timeout) as response:
            # Verificar que la respuesta es correcta
            response.raise_for_status()
            
            # Obtener el contenido
            content = await response.text()
            
            # Verificar que el contenido es válido
            if not content or len(content) < 100:
                logger.warning(f"Respuesta demasiado corta de {url}: {len(content)} bytes")
                raise ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message="Respuesta HTML demasiado corta",
                    headers=response.headers
                )
                
            return content
    except ClientError as e:
        logger.error(f"Error en petición HTTP a {url}: {str(e)}")
        raise
    except asyncio.TimeoutError:
        logger.error(f"Timeout en petición HTTP a {url}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado en petición HTTP a {url}: {str(e)}")
        raise

async def create_client_session() -> ClientSession:
    """
    Crea una sesión HTTP configurada correctamente.
    
    Returns:
        Sesión aiohttp configurada
    """
    # Configurar TCP connector con límites y conexiones persistentes
    connector = aiohttp.TCPConnector(
        limit=10,  # Límite conservador
        limit_per_host=5,
        enable_cleanup_closed=True,
        force_close=False,
        ssl=False  # Cambiar a True si se requiere HTTPS verificado
    )
    
    # Crear y devolver la sesión
    return ClientSession(connector=connector)