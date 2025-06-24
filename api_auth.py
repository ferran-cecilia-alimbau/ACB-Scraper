# api_auth.py

import time
import logging
from seleniumwire import undetected_chromedriver as uc

logger = logging.getLogger('basketball_scraper')

async def get_fresh_api_token() -> str | None:
    """
    Lanza un navegador de forma invisible para obtener un token de autorización fresco.
    Utiliza una estrategia robusta que espera a que la página cargue y luego busca
    el token en el historial de peticiones.
    """
    logger.info("Iniciando Fase 0: Obtención de un nuevo token de API (estrategia robusta)...")
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        driver = uc.Chrome(options=options)
        
        # Navega a la página y espera un tiempo prudencial para que se ejecuten los scripts
        driver.get("https://jv.acb.com/es/104452/jugadas")
        logger.info("Página cargada, esperando a que se generen las peticiones de API...")
        time.sleep(15) # Damos 15 segundos para que la página se estabilice

        # Revisa el historial de peticiones en busca del token
        for request in driver.requests:
            if 'api2.acb.com' in request.url and 'Authorization' in request.headers:
                token = request.headers['Authorization']
                logger.info("¡Token de API obtenido con éxito del historial de peticiones!")
                driver.quit()
                return token

        # Si el bucle termina y no hemos encontrado el token
        logger.error("No se pudo encontrar el token de autorización en ninguna de las peticiones interceptadas.")
        driver.quit()
        return None

    except Exception as e:
        logger.error(f"Fallo al obtener el token de la API: {e}")
        if driver:
            driver.quit()
        return None