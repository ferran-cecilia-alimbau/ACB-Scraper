# Basketball Stats Scraper

## Descripción

**Basketball Stats Scraper** es un proyecto de scraping diseñado para recopilar estadísticas detalladas de partidos de baloncesto desde la web de ACB. El scraper procesa una lista de identificadores de partidos definidos en `match_ids.json`, descarga la información disponible y la almacena en archivos CSV para su posterior análisis.

El proyecto utiliza tecnologías asíncronas para optimizar la velocidad y eficiencia del scraping, respetando las limitaciones impuestas por el servidor web objetivo. Además, incluye un módulo de análisis con PySpark para procesar los datos recopilados y generar estadísticas avanzadas de baloncesto.

## Estructura del Proyecto

- **`config.json`**: Archivo de configuración donde se definen los parámetros clave del scraping, incluyendo URLs base, archivos de salida, y parámetros de control como límites de tasa y reintentos.

- **`main.py`**: Punto de entrada del proyecto. Ejecuta el scraper utilizando la configuración especificada en `config.json`.

- **`scraper.py`**: Módulo principal del scraper que implementa la lógica de recolección de datos. Utiliza `aiohttp` y `asyncio` para manejar solicitudes de manera asíncrona, con soporte para reintentos y límites de tasa.

- **`parsers.py`**: Contiene funciones para extraer y transformar datos de las páginas HTML obtenidas, como información de partidos, estadísticas de jugadores y perfiles de jugadores.

- **`http_client.py`**: Implementa un cliente HTTP asíncrono con funcionalidades avanzadas como rate limiting adaptativo y manejo de concurrencia.

- **`utils.py`**: Proporciona utilidades y funciones auxiliares para tareas comunes como limpieza de datos y normalización.

- **`constants.py`**: Centraliza valores constantes, URLs, selectores HTML y mapeos utilizados en todo el proyecto.

- **`logger.py`**: Módulo para la configuración del sistema de logging, permitiendo el registro detallado de eventos durante la ejecución del scraper.

- **`get_match_ids/get_match_ids.py`**: Script independiente para extraer IDs de partidos de la web de ACB y guardarlos en `match_ids.json`.

- **Archivos CSV de salida**:
  - `estadisticas_todos_partidos.csv`: Estadísticas de jugadores de todos los partidos procesados.
  - `estadisticas_partido.csv`: Estadísticas detalladas de partidos individuales.
  - `estadisticas_equipos_por_partido.csv`: Estadísticas totales de cada equipo por partido.
  - `perfiles_jugadores.csv`: Información detallada de los perfiles de jugadores.

## Requisitos

Para ejecutar este proyecto, necesitarás tener instalado Python 3.8 o superior, junto con las siguientes dependencias que se pueden instalar usando `pip`:

```bash
pip install -r requirements.txt
```

### Dependencias principales

- `aiohttp`: Manejo de solicitudes HTTP asíncronas.
- `asyncio`: Biblioteca estándar para concurrencia asíncrona en Python.
- `beautifulsoup4`: Para el parseo de HTML.
- `pandas`: Manipulación y análisis de datos.
- `requests`: Biblioteca simple para realizar solicitudes HTTP.
- `tenacity`: Gestión de reintentos con lógica customizable.
- `tqdm`: Visualización de progreso en la consola.
- `selenium`: Utilizada en `get_match_ids.py` para interactuar con páginas web dinámicas.
- `webdriver_manager`: Gestión de drivers para Selenium.

## Uso

### Extracción de IDs de Partidos

Antes de ejecutar el scraper principal, puedes utilizar el script `get_match_ids.py` para obtener los IDs de partidos de la temporada actual:

```bash
cd get_match_ids
python get_match_ids.py
```

Esto generará un archivo `match_ids.json` en el directorio raíz que será utilizado por el scraper principal.

### Configuración

Antes de ejecutar el scraper, asegúrate de configurar los parámetros en `config.json`. Aquí se definen las configuraciones críticas para el funcionamiento del scraper:

```json
{
    "base_url": "https://www.acb.com/partido/estadisticas/id/",
    "output_file": "estadisticas_todos_partidos.csv",
    "output_file_game": "estadisticas_partido.csv",
    "output_file_team_totals": "estadisticas_equipos_por_partido.csv",
    "output_file_player_profiles": "perfiles_jugadores.csv",
    "max_retries": 3,
    "retry_delay": 5,
    "user_agent": "BasketballStatsScraper/1.0",
    "rate_limit": 1
}
```

### Ejecución

Para iniciar el proceso de scraping, ejecuta el siguiente comando desde el directorio raíz:

```bash
python main.py
```

El scraper comenzará a recolectar datos de los partidos especificados en `match_ids.json` y los almacenará en los archivos de salida.

### Logging

El proyecto utiliza el módulo `logger.py` para registrar eventos importantes. Los logs se almacenan en el directorio `logs/` con un timestamp único para cada ejecución:

```
logs/scraper_20240105_123045.log
```

## Características de Rendimiento

El proyecto incluye varias optimizaciones para mejorar el rendimiento:

1. **Cliente HTTP Asíncrono**: Utiliza `aiohttp` con manejo asíncrono para maximizar la velocidad de descarga.

2. **Rate Limiting Adaptativo**: Ajusta dinámicamente los tiempos de espera entre solicitudes basado en la respuesta del servidor.

3. **Control de Concurrencia**: Limita el número de peticiones simultáneas para evitar sobrecargar el servidor.

4. **Procesamiento Eficiente de DataFrames**: Utiliza técnicas como el procesamiento por fragmentos para manejar conjuntos de datos grandes.

5. **Caché de Búsquedas**: Implementa estructuras de datos eficientes (como conjuntos) para búsquedas O(1) en lugar de O(n).

6. **Reintentos Inteligentes**: Sistema de reintentos con espera exponencial para manejar fallos temporales.

## Consideraciones

- **Respeto al Servidor**: El scraper está diseñado para ser respetuoso con el servidor destino, implementando límites de tasa adaptativos y reintentos controlados.

- **Modularidad**: El proyecto está diseñado de manera modular para facilitar futuras ampliaciones o modificaciones.

- **Manejo de Errores**: Implementa un sistema robusto de manejo de errores para garantizar la fiabilidad del proceso de scraping.

## Contribuciones

Las contribuciones al proyecto son bienvenidas. Si encuentras un bug o tienes una sugerencia para mejorar el scraper, no dudes en abrir un issue o enviar un pull request.