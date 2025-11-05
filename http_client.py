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


class RateLimiter:
    """Controlador de rate limiting para peticiones HTTP."""

    def __init__(self, rate_limit: float = 1.0):
        """
        Inicializa el rate limiter.

        Args:
            rate_limit: Tiempo mínimo en segundos entre peticiones
        """
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
        self._rate_limit = rate_limit

    async def wait_if_needed(self):
        """Espera si es necesario para respetar el rate limit."""
        async with self._lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time

            if time_since_last < self._rate_limit:
                wait_time = self._rate_limit - time_since_last
                logger.debug(f"Esperando {wait_time:.2f}s entre peticiones")
                await asyncio.sleep(wait_time)

            self._last_request_time = time.time()


# Instancia global del rate limiter (puede ser reemplazada si es necesario)
_default_rate_limiter = RateLimiter()


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

    # Control de velocidad de peticiones usando el rate limiter
    rate_limit = config.get('rate_limit', const.DEFAULT_RATE_LIMIT)
    _default_rate_limiter._rate_limit = rate_limit
    await _default_rate_limiter.wait_if_needed()

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
            if not content or len(content) < const.MIN_VALID_HTML_LENGTH:
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
        ssl=True  # SSL habilitado para verificar certificados HTTPS
    )
    
    # Crear y devolver la sesión
    return ClientSession(connector=connector)