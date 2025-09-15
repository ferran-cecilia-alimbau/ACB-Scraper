# Basketball Stats Scraper

## Descripción

**Basketball Stats Scraper** es un proyecto de scraping de alto rendimiento diseñado para recopilar estadísticas detalladas de partidos de baloncesto desde la web de ACB. El scraper procesa una lista de identificadores de partidos definidos en `match_ids.json`, descarga la información disponible y la almacena en archivos CSV para su posterior análisis.

El proyecto utiliza tecnologías asíncronas con **procesamiento paralelo** para optimizar la velocidad y eficiencia del scraping, respetando las limitaciones impuestas por el servidor web objetivo. Incluye un sistema robusto de reintentos, control de concurrencia y seguimiento visual del progreso.

## Características Principales

- **🚀 Procesamiento Paralelo**: Procesa múltiples partidos simultáneamente con control de concurrencia
- **📊 Barra de Progreso**: Visualización en tiempo real del avance
- **🔄 Reintentos Inteligentes**: Sistema de reintentos con backoff exponencial
- **💾 Caché de Perfiles**: Evita descargar perfiles de jugadores duplicados
- **📝 Logging Detallado**: Registro completo de todas las operaciones
- **⚡ Alto Rendimiento**: ~40-50% más rápido que el procesamiento secuencial

## Estructura del Proyecto

### Archivos Principales

- **`config.json`**: Archivo de configuración donde se definen los parámetros clave del scraping, incluyendo URLs base, archivos de salida, límites de concurrencia y parámetros de control.

- **`main.py`**: Punto de entrada del proyecto. Coordina el proceso de scraping, carga la configuración, procesa los partidos y almacena los resultados.

- **`scraper.py`**: Módulo principal del scraper que implementa la lógica de recolección de datos con procesamiento paralelo. Utiliza `aiohttp` y `asyncio` para manejar múltiples solicitudes simultáneas con control de concurrencia.

- **`parsers.py`**: Contiene funciones para extraer y transformar datos de las páginas HTML obtenidas, como información de partidos, estadísticas de jugadores y perfiles de jugadores.

- **`http_client.py`**: Implementa un cliente HTTP asíncrono con funcionalidades avanzadas como rate limiting y manejo de reintentos exponenciales.

- **`utils.py`**: Proporciona utilidades y funciones auxiliares para tareas comunes como limpieza de datos, normalización y validación.

- **`constants.py`**: Centraliza valores constantes, URLs, selectores HTML y mapeos utilizados en todo el proyecto.

- **`logger.py`**: Módulo para la configuración del sistema de logging, permitiendo el registro detallado de eventos durante la ejecución del scraper.

### Scripts Auxiliares

- **`scripts/get_match_ids.py`**: Script independiente para extraer IDs de partidos de la web de ACB y guardarlos en `match_ids.json`.

- **`scripts/batch_play_by_play.py`**: Script especializado para extraer datos de play-by-play usando Selenium con Chrome headless. Procesa múltiples partidos de forma concurrente y genera archivos CSV con todas las jugadas detalladas de cada partido.

- **`scripts/verify_pbp_completeness.py`**: Utilidad para verificar la completitud de los archivos CSV de play-by-play. Identifica partidos con datos incompletos basándose en marcadores clave como "Cinco Inicial" y "Final del Partido".

### Archivos de Salida

Los datos se almacenan en archivos CSV dentro del directorio `data/output/`:

- **`estadisticas_todos_partidos.csv`**: Estadísticas individuales de jugadores de todos los partidos procesados
- **`estadisticas_partido.csv`**: Información general de cada partido (fecha, resultado, árbitros, etc.)
- **`estadisticas_equipos_por_partido.csv`**: Estadísticas totales de cada equipo por partido
- **`perfiles_jugadores.csv`**: Información detallada de los perfiles de jugadores

Los datos de play-by-play se almacenan en `data/play_by_play/`:
- **`play_by_play_[ID].csv`**: Registro detallado de todas las jugadas de un partido específico, incluyendo tiempo, marcador, equipo, jugador y tipo de acción

## Requisitos

### Python
Python 3.8 o superior

### Dependencias

```bash
pip install -r requirements.txt
```

#### Dependencias principales:

- `aiohttp`: Manejo de solicitudes HTTP asíncronas
- `asyncio`: Biblioteca estándar para concurrencia asíncrona
- `beautifulsoup4`: Parseo de HTML
- `pandas`: Manipulación y análisis de datos
- `tenacity`: Gestión de reintentos con lógica personalizable
- `tqdm`: Visualización de progreso en la consola
- `requests`: Solicitudes HTTP simples (usado en get_match_ids.py)
- `selenium`: Automatización de navegador para extracción de play-by-play
- `undetected-chromedriver`: Driver de Chrome optimizado para evitar detección
- `beautifulsoup4`: Parseo adicional de HTML para datos complejos

## Uso

### 1. Extracción de IDs de Partidos

Antes de ejecutar el scraper principal, obtén los IDs de partidos de la temporada:

```bash
cd scripts
python get_match_ids.py
cd ..
```

Esto generará el archivo `data/input/match_ids.json` con los IDs de los partidos a procesar.

### 2. Configuración

El archivo `config.json` contiene todos los parámetros configurables:

```json
{
    "base_url": "https://www.acb.com/partido/estadisticas/id/",
    "output_file": "data/output/estadisticas_todos_partidos.csv",
    "output_file_game": "data/output/estadisticas_partido.csv",
    "output_file_team_totals": "data/output/estadisticas_equipos_por_partido.csv",
    "output_file_player_profiles": "data/output/perfiles_jugadores.csv",
    "max_retries": 3,
    "retry_delay": 5,
    "user_agent": "BasketballStatsScraper/1.0",
    "rate_limit": 1,
    "max_concurrent": 5,
    "batch_size": 20,
    "batch_pause": 2,
    "timeout": 30
}
```

#### Parámetros de Paralelización:

- **`max_concurrent`**: Número máximo de peticiones simultáneas (1-10, recomendado: 5)
- **`batch_size`**: Número de partidos por lote (10-50, recomendado: 20)
- **`batch_pause`**: Pausa en segundos entre lotes (1-5, recomendado: 2)
- **`timeout`**: Tiempo máximo de espera por petición en segundos

### 3. Ejecución

Para iniciar el proceso de scraping:

```bash
python main.py
```

El scraper:
1. Cargará la configuración y los IDs de partidos
2. Identificará qué partidos ya han sido procesados
3. Procesará los partidos nuevos en paralelo
4. Mostrará una barra de progreso en tiempo real
5. Guardará los resultados en los archivos CSV correspondientes

### 4. Extracción de Play-by-Play

Para extraer datos detallados de jugadas:

```bash
cd scripts
python batch_play_by_play.py
cd ..
```

Este script:
1. Usa Selenium para navegar por las páginas de play-by-play
2. Extrae todas las jugadas de cada partido
3. Genera archivos CSV individuales para cada partido
4. Ofrece opciones para procesar todos los partidos o un rango específico

### 5. Verificación de Completitud

Para verificar que los archivos de play-by-play están completos:

```bash
cd scripts
python verify_pbp_completeness.py
cd ..
```

Este script identifica partidos con datos incompletos basándose en:
- Presencia de al menos 9 eventos "Cinco Inicial"
- Presencia de "Final del Partido"

### 6. Reprocesar Partidos

Si necesitas reprocesar partidos específicos:

1. Haz backup de los archivos actuales:
```bash
cp data/output/estadisticas_partido.csv data/output/estadisticas_partido.csv.backup
cp data/output/estadisticas_equipos_por_partido.csv data/output/estadisticas_equipos_por_partido.csv.backup
```

2. Borra las líneas correspondientes de **ambos** archivos CSV

3. Ejecuta el scraper nuevamente

## Características de Rendimiento

### Procesamiento Paralelo

El scraper implementa un sistema sofisticado de procesamiento paralelo:

1. **División en Lotes**: Los partidos se dividen en lotes configurables
2. **Control de Concurrencia**: Semáforo que limita las peticiones simultáneas
3. **Pausas entre Lotes**: Evita saturar el servidor
4. **Caché Dinámico**: Actualización en tiempo real del caché de perfiles

### Optimizaciones Implementadas

- **Cliente HTTP Asíncrono**: Maximiza la velocidad con `aiohttp`
- **Rate Limiting**: Control de velocidad entre peticiones
- **Procesamiento Eficiente**: DataFrames procesados por chunks para grandes volúmenes
- **Búsquedas O(1)**: Uso de sets para verificación de IDs existentes
- **Reintentos Inteligentes**: Backoff exponencial para fallos temporales

### Rendimiento Esperado

- **Procesamiento secuencial**: ~2-3 segundos/partido
- **Procesamiento paralelo**: ~0.5-1 segundo/partido efectivo
- **Mejora**: 40-50% más rápido
- **300 partidos**: ~8-10 minutos (antes: ~15 minutos)

## Logging

Los logs se almacenan en `data/logs/` con timestamp único:

```
data/logs/scraper_20240105_123045.log
```

Niveles de logging:
- **INFO**: Operaciones normales y progreso
- **WARNING**: Situaciones anómalas pero recuperables
- **ERROR**: Errores que impiden procesar un partido
- **DEBUG**: Información detallada para debugging

## Consideraciones

### Respeto al Servidor

- Rate limiting configurable
- Pausas entre lotes
- Límite de concurrencia conservador
- Reintentos con espera exponencial

### Robustez

- Manejo exhaustivo de errores
- Continúa procesando aunque fallen partidos individuales
- Validación de datos en múltiples puntos
- Logs detallados para debugging

### Escalabilidad

- Configuración flexible para diferentes cargas
- Procesamiento por chunks para grandes volúmenes
- Caché eficiente de perfiles de jugadores

## Solución de Problemas

### Error 429 (Too Many Requests)
- Reduce `max_concurrent` a 3 en `config.json`
- Aumenta `rate_limit` a 2 segundos

### Timeouts Frecuentes
- Aumenta `timeout` a 45 o 60 segundos
- Reduce `max_concurrent` para menor carga

### Memoria Insuficiente
- Reduce `batch_size` a 10
- Procesa menos partidos por ejecución

## Estructura de Datos

### estadisticas_todos_partidos.csv
Contiene estadísticas individuales de cada jugador por partido, incluyendo:
- Identificación: id_partido, player_id, equipo, dorsal, nombre
- Estadísticas: puntos, rebotes, asistencias, etc.
- Métricas avanzadas: +/-, valoración

### estadisticas_partido.csv
Información general de cada partido:
- Identificación: id_partido, jornada
- Datos del encuentro: fecha, hora, pabellón, público
- Resultados: puntuaciones finales y parciales
- Árbitros

### estadisticas_equipos_por_partido.csv
Totales de equipo por partido, agregando todas las estadísticas individuales.

### perfiles_jugadores.csv
Información biográfica de jugadores:
- Datos personales: nombre completo, fecha de nacimiento, nacionalidad
- Datos físicos: altura, posición
- Datos de equipo: dorsal, licencia

### play_by_play_[ID].csv
Registro detallado de jugadas por partido:
- Identificación: id_partido, periodo, tiempo
- Marcador: puntuación local y visitante en cada jugada
- Acción: equipo, jugador, tipo de jugada (tiro, rebote, falta, etc.)
- Estadísticas: información adicional sobre la jugada

## Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.