"""
Cliente HTTP asíncrono con reintentos y rate limiting para ACB Scraper.
"""
import logging
import asyncio
import time
from typing import Dict, Any, Optional
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


class AdaptiveRateLimiter:
    """
    Controlador de rate limit adaptativo que ajusta el tiempo de espera
    basado en las respuestas del servidor.
    """
    
    def __init__(self, initial_rate_limit: float = const.DEFAULT_RATE_LIMIT):
        """
        Inicializa el rate limiter con un tiempo inicial.
        
        Args:
            initial_rate_limit: Tiempo inicial de espera en segundos
        """
        self.rate_limit = initial_rate_limit
        self.last_request_time = 0
        self.consecutive_errors = 0
        self.lock = asyncio.Lock()
    
    async def wait(self) -> None:
        """
        Espera el tiempo necesario según el rate limit actual.
        """
        async with self.lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            
            if time_since_last < self.rate_limit:
                wait_time = self.rate_limit - time_since_last
                logger.debug(f"Rate limit: esperando {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            
            self.last_request_time = time.time()
    
    def success(self) -> None:
        """
        Notifica una respuesta exitosa, potencialmente reduciendo
        el tiempo de espera si ha habido pocos errores.
        """
        self.consecutive_errors = 0
        # Reducir gradualmente el rate limit si no hay errores
        # pero no bajar de un mínimo
        if self.rate_limit > const.DEFAULT_RATE_LIMIT:
            self.rate_limit = max(const.DEFAULT_RATE_LIMIT, self.rate_limit * 0.95)
    
    def error(self) -> None:
        """
        Notifica un error, aumentando el tiempo de espera
        para evitar sobrecargar el servidor.
        """
        self.consecutive_errors += 1
        # Aumentar exponencialmente el rate limit con cada error consecutivo
        self.rate_limit = min(30, self.rate_limit * (1.5 ** self.consecutive_errors))
        logger.warning(f"Rate limit aumentado a {self.rate_limit:.2f}s tras error")


# Instancia global del rate limiter
rate_limiter = AdaptiveRateLimiter()


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
    y rate limiting adaptativo.
    
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
        
    # Obtener headers y parámetros
    headers = {'User-Agent': config.get('user_agent', const.DEFAULT_USER_AGENT)}
    timeout = aiohttp.ClientTimeout(total=config.get('timeout', 30))
    
    try:
        # Esperar según el rate limiter antes de hacer la petición
        await rate_limiter.wait()
        
        logger.info(f"Realizando petición HTTP a: {url}")
        async with session.get(url, headers=headers, timeout=timeout) as response:
            # Verificar que la respuesta es correcta
            response.raise_for_status()
            
            # Obtener el contenido
            content = await response.text()
            
            # Si llegamos aquí, la petición fue exitosa
            rate_limiter.success()
            
            # Verificar que el contenido es válido
            if not content or len(content) < 100:
                logger.warning(f"Respuesta demasiado corta de {url}: {len(content)} bytes")
                rate_limiter.error()
                raise ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message="Respuesta HTML demasiado corta",
                    headers=response.headers
                )
                
            return content
    except ClientError as e:
        # Notificar error para ajustar el rate limit
        rate_limiter.error()
        logger.error(f"Error en petición HTTP a {url}: {str(e)}")
        raise
    except asyncio.TimeoutError:
        rate_limiter.error()
        logger.error(f"Timeout en petición HTTP a {url}")
        raise
    except Exception as e:
        rate_limiter.error()
        logger.error(f"Error inesperado en petición HTTP a {url}: {str(e)}")
        raise


class ConcurrencyLimiter:
    """
    Limita el número de tareas concurrentes para evitar saturar
    el servidor o los recursos locales.
    """
    
    def __init__(self, max_concurrent: int = const.MAX_CONCURRENT_REQUESTS):
        """
        Inicializa el limitador con un número máximo de tareas concurrentes.
        
        Args:
            max_concurrent: Número máximo de tareas simultáneas
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        
    async def acquire(self) -> None:
        """Adquiere un slot para una nueva tarea."""
        await self.semaphore.acquire()
        
    def release(self) -> None:
        """Libera un slot al terminar una tarea."""
        self.semaphore.release()
        
    async def run(self, coro) -> Any:
        """
        Ejecuta una corutina respetando el límite de concurrencia.
        
        Args:
            coro: Corutina a ejecutar
            
        Returns:
            Resultado de la corutina
        """
        await self.acquire()
        try:
            return await coro
        finally:
            self.release()


# Instancia global del limitador de concurrencia
concurrency_limiter = ConcurrencyLimiter()


async def create_client_session() -> ClientSession:
    """
    Crea una sesión HTTP configurada correctamente.
    
    Returns:
        Sesión aiohttp configurada
    """
    # Configurar TCP connector con límites y conexiones persistentes
    connector = aiohttp.TCPConnector(
        limit=const.MAX_CONCURRENT_REQUESTS,
        limit_per_host=5,
        enable_cleanup_closed=True,
        force_close=False,
        ssl=False  # Cambiar a True si se requiere HTTPS verificado
    )
    
    # Crear y devolver la sesión
    return ClientSession(connector=connector)