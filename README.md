
# Basketball Stats Scraper

## Descripción

**Basketball Stats Scraper** es un proyecto de scraping diseñado para recopilar estadísticas detalladas de partidos de baloncesto desde la web de ACB. El scraper recorre un rango específico de identificadores de partidos, descarga la información disponible y la almacena en archivos CSV para su posterior análisis.

El proyecto utiliza tecnologías asíncronas para optimizar la velocidad y eficiencia del scraping, respetando las limitaciones impuestas por el servidor web objetivo.

## Estructura del Proyecto

- **`config.json`**: Archivo de configuración donde se definen los parámetros clave del scraping, incluyendo el rango de IDs de partidos a recolectar, URLs base, archivos de salida, y parámetros de control como límites de tasa y reintentos.

- **`scraper.py`**: Módulo principal del scraper que implementa la lógica de recolección de datos. Utiliza `aiohttp` y `asyncio` para manejar solicitudes de manera asíncrona, con soporte para reintentos y límites de tasa.

- **`main.py`**: Punto de entrada del proyecto. Ejecuta el scraper utilizando la configuración especificada en `config.json`.

- **`logger.py`**: Módulo para la configuración del sistema de logging, permitiendo el registro detallado de eventos durante la ejecución del scraper.

- **`estadisticas_todos_partidos.csv`**: Archivo CSV generado por el scraper que contiene las estadísticas agregadas de todos los partidos dentro del rango especificado.

- **`estadisticas_partido.csv`**: Archivo CSV que contiene las estadísticas detalladas de un partido individual, utilizado principalmente para pruebas y validaciones.

- **`requirements.txt`**: Archivo que lista las dependencias necesarias para ejecutar el proyecto. Estas incluyen bibliotecas para scraping, manejo de datos, y control de flujo asíncrono.

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
- `tqdm`: Progreso de procesos de scraping en la consola.

## Uso

### Configuración

Antes de ejecutar el scraper, asegúrate de configurar los parámetros en `config.json`. Aquí se define el rango de partidos a recolectar, así como otras configuraciones críticas como el nombre del archivo de salida y el user-agent.

```json
{
    "start_id": 103773,
    "end_id": 103850,
    "base_url": "https://www.acb.com/partido/estadisticas/id/",
    "output_file": "estadisticas_todos_partidos.csv",
    "output_file_game": "estadisticas_partido.csv",
    "max_retries": 3,
    "retry_delay": 5,
    "user_agent": "BasketballStatsScraper/1.0",
    "rate_limit": 1
}
```

### Ejecución

Para iniciar el proceso de scraping, ejecuta el siguiente comando:

```bash
python main.py
```

El scraper comenzará a recolectar datos de los partidos dentro del rango especificado y los almacenará en los archivos de salida definidos en la configuración.

### Logging

El proyecto utiliza el módulo `logger.py` para registrar eventos importantes, como el inicio y fin del scraping, errores y reintentos. Los logs se almacenan en la consola y se pueden redirigir a un archivo si se desea.

## Consideraciones

- **Rate Limiting**: El scraper respeta un límite de tasa (`rate_limit`) para evitar sobrecargar el servidor destino. Puedes ajustar este parámetro en `config.json`.

- **Reintentos**: En caso de fallas temporales en la red o respuestas inesperadas, el scraper intentará realizar un máximo de 3 reintentos (`max_retries`) antes de abandonar un partido.

- **Modularidad**: El proyecto está diseñado de manera modular para facilitar futuras ampliaciones o modificaciones, como la adaptación a nuevas fuentes de datos o el ajuste de las estrategias de recolección.

## Contribuciones

Las contribuciones al proyecto son bienvenidas. Si encuentras un bug o tienes una sugerencia para mejorar el scraper, no dudes en abrir un issue o enviar un pull request.
