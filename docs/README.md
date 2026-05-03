# ACB-Scraper

Scraper de estadísticas + motor analítico play-by-play + dashboard Streamlit para la Liga Endesa ACB.

## Componentes

| Componente | Descripción | Ubicación |
|------------|-------------|-----------|
| **Scraper** | Scraping asíncrono de estadísticas y play-by-play desde acb.com | Raíz del proyecto + `scripts/` |
| **Dashboard** | Dashboard interactivo Streamlit con 8 páginas de análisis | `acb-dashboard/` |
| **Motor PBP** | Motor de análisis play-by-play con 8 módulos de análisis | `acb-pbp-analytics/` |

## Estructura del proyecto

```
ACB-Scraper/
├── main.py, scraper.py, parsers.py, ...   # Scraper core
├── config.json                             # Configuración del scraper
├── scripts/
│   ├── get_match_ids.py                    # Descubre IDs de partidos
│   ├── batch_play_by_play_v2.py            # Scraper PBP (Selenium)
│   ├── batch_play_by_play.py               # PBP v1 (legacy)
│   └── verify_pbp_completeness.py          # Verificación de PBP
├── data/
│   ├── input/match_ids.json
│   ├── output/*.csv                        # 4 CSVs de estadísticas
│   └── play_by_play/play_by_play_*.csv     # 152 ficheros PBP
├── acb-dashboard/
│   ├── app.py                              # Entry point Streamlit
│   ├── pages/ (8 páginas)
│   └── src/ (6 módulos)
├── acb-pbp-analytics/
│   ├── src/ (4 módulos core)
│   ├── analysis/ (8 módulos)
│   └── visualizations/ (2 módulos)
└── docs/
```

## Scraper

### Archivos principales

| Archivo | Función |
|---------|---------|
| `main.py` | Punto de entrada, coordina scraping y almacena resultados |
| `scraper.py` | Lógica de scraping con `aiohttp` + procesamiento paralelo |
| `parsers.py` | Extracción de datos de HTML (partidos, jugadores, perfiles) |
| `http_client.py` | Cliente HTTP asíncrono con rate limiting y reintentos |
| `utils.py` | Utilidades de limpieza y normalización de datos |
| `constants.py` | URLs, selectores HTML y mapeos constantes |
| `logger.py` | Configuración del sistema de logging |

### Scripts auxiliares

| Script | Función |
|--------|---------|
| `scripts/get_match_ids.py` | Extrae IDs de partidos del calendario ACB |
| `scripts/batch_play_by_play_v2.py` | Scraper PBP con Selenium + webdriver-manager (versión actual) |
| `scripts/batch_play_by_play.py` | Scraper PBP v1 (legacy, usa undetected-chromedriver) |
| `scripts/verify_pbp_completeness.py` | Verifica completitud de ficheros PBP |

### Uso

```bash
# 0. Instalar dependencias con Python 3.12
py -3.12 -m pip install -r requirements.txt

# 1. Obtener IDs de partidos
py -3.12 scripts/get_match_ids.py

# 2. Validar scraper con salidas temporales
py -3.12 scripts/validate_scraper.py

# 3. Scrapear estadísticas (4 CSVs)
py -3.12 main.py

# 4. Scrapear play-by-play
py -3.12 scripts/batch_play_by_play_v2.py
```

El scraper guarda los CSVs tras cada partido procesado correctamente. En logs se registran métricas por partido: descarga, parseo, perfiles, guardado y número de perfiles completos descargados. `scripts/validate_scraper.py` ejecuta 1-2 partidos en una carpeta temporal, comprueba filas, duplicados, campos críticos, marcador y un segundo pase con perfiles ya existentes.

### Configuración (`config.json`)

```json
{
    "max_concurrent": 5,
    "batch_size": 20,
    "batch_pause": 2,
    "rate_limit": 1,
    "max_retries": 3,
    "timeout": 30
}
```

- `max_concurrent`: Peticiones simultáneas (1-10, recomendado: 5)
- `batch_size`: Partidos por lote (10-50, recomendado: 20)
- `batch_pause`: Pausa en segundos entre lotes
- `rate_limit`: Segundos mínimos entre peticiones

### Rendimiento

- Procesamiento paralelo con `aiohttp` + `asyncio`
- Búsquedas O(1) con sets para verificación de IDs
- Rate limiting entre lotes (no bloqueante)
- ~0.5-1 segundo/partido efectivo (~40-50% más rápido que secuencial)

## Dashboard (`acb-dashboard/`)

Dashboard Streamlit interactivo para análisis estadístico de la Liga Endesa. Diseñado con tema oscuro.

### Ejecución

```bash
cd acb-dashboard
pip install -r requirements.txt
streamlit run app.py
```

### Páginas

| # | Página | Descripción |
|---|--------|-------------|
| 1 | Clasificación | Tabla + ORtg/DRtg scatter + diferencial + evolución |
| 2 | Equipo | Ficha de equipo: ofensivo/defensivo/resultados/jugadores |
| 3 | Jugador | Ficha de jugador: radar + evolución + splits + rankings |
| 4 | Comparador | Comparación: jugador vs jugador, equipo vs equipo, multi-jugador |
| 5 | Partido | Box score + Four Factors + PBP análisis completo |
| 6 | Rankings | Líderes estadísticos + rankings de equipos + mejores actuaciones |
| 7 | Quintetos | Análisis de lineups, minutos compartidos, stints |
| 8 | Clutch | Rendimiento en los últimos minutos de partidos igualados |

### Módulos (`src/`)

| Módulo | Función |
|--------|---------|
| `data_loader.py` | Carga y caché de CSVs |
| `preprocessing.py` | Transformación y normalización de datos |
| `metrics.py` | Cálculos estadísticos (ORtg, DRtg, Four Factors, etc.) |
| `charts.py` | Gráficos Plotly + CSS personalizado para tema oscuro |
| `constants.py` | Mapeos de equipos, colores, PBP game remap |
| `pbp_bridge.py` | Puente entre dashboard y motor PBP (resuelve ficheros PBP) |

## Motor PBP (`acb-pbp-analytics/`)

Motor de análisis play-by-play. Procesa los ficheros PBP crudos y genera métricas avanzadas.

### Módulos core (`src/`)

| Módulo | Función |
|--------|---------|
| `pbp_loader.py` | Carga y parseo de ficheros PBP |
| `time_utils.py` | Conversión de tiempos (periodos, reloj, segundos absolutos) |
| `lineup_tracker.py` | Seguimiento de quintetos en pista a partir de eventos PBP |
| `possession_engine.py` | Estimación de posesiones a partir de eventos |

### Módulos de análisis (`analysis/`)

| Módulo | Función |
|--------|---------|
| `clutch.py` | Rendimiento en situaciones clutch |
| `fouls.py` | Análisis de faltas por jugador/equipo/periodo |
| `game_state_performance.py` | Rendimiento según estado del marcador |
| `lineup_combos.py` | Estadísticas de combinaciones de jugadores |
| `momentum.py` | Detección de rachas y cambios de momentum |
| `pace.py` | Ritmo de juego (posesiones/minuto) |
| `shooting_patterns.py` | Patrones de tiro por zona, periodo, situación |
| `substitutions.py` | Análisis de rotaciones y cambios |

### Visualizaciones (`visualizations/`)

| Módulo | Función |
|--------|---------|
| `game_flow.py` | Gráfico de flujo de partido (marcador en el tiempo) |
| `lineup_matrix.py` | Matriz de minutos compartidos entre jugadores |

## Datos

### CSVs de estadísticas (`data/output/`)

| Archivo | Contenido | Columnas |
|---------|-----------|----------|
| `estadisticas_todos_partidos.csv` | Stats individuales por jugador y partido | 30 |
| `estadisticas_partido.csv` | Info general de cada partido | 15 |
| `estadisticas_equipos_por_partido.csv` | Totales de equipo por partido | 25 |
| `perfiles_jugadores.csv` | Datos biográficos de jugadores | 13 |

Los totales de equipo son los oficiales de ACB. Algunas estadísticas pueden incluir valores de equipo no asignados a jugadores individuales, por lo que no siempre coinciden exactamente con la suma de filas de jugadores.

### Play-by-play (`data/play_by_play/`)

152 ficheros `play_by_play_[ID].csv` con todas las jugadas de cada partido. Cada registro contiene: id_partido, periodo, tiempo, marcador, equipo (LOCAL/VISITANTE), jugador, acción.

**Bug conocido**: 75 de los 152 ficheros contienen datos de un partido diferente al indicado por el nombre del fichero (bug off-by-one en el scraper). Solo 77 partidos tienen datos PBP correctos. La solución está implementada en `acb-dashboard/src/constants.py` (diccionarios `PBP_GAME_REMAP` y `PBP_REVERSE_REMAP`) y en `acb-dashboard/src/pbp_bridge.py` que resuelve el fichero correcto automáticamente.

### Normalización de nombres de equipos

Los datos de partidos usan nombres cortos (ej. "Baskonia") mientras que los perfiles de jugadores usan nombres largos con sponsor (ej. "Kosner Baskonia"). El mapeo entre ambos está en `acb-dashboard/src/constants.py`.

## Requisitos

- **Python 3.12**
- Dependencias por componente:
  - `requirements.txt` (scraper): aiohttp, beautifulsoup4, pandas, selenium, webdriver-manager, tenacity, tqdm
  - `acb-dashboard/requirements.txt`: streamlit, plotly, pandas, numpy
  - `acb-pbp-analytics/requirements.txt`: pandas, numpy, plotly

## Quick Start

```bash
# Scraping
python scripts/get_match_ids.py
python main.py
python scripts/batch_play_by_play_v2.py

# Dashboard
cd acb-dashboard
pip install -r requirements.txt
streamlit run app.py
```
