# ACB-Scraper

Scraper de estadisticas, motor analitico play-by-play y web editorial para explorar datos de la Liga Endesa ACB.

## Componentes

| Componente | Descripcion | Ubicacion |
|------------|-------------|-----------|
| **Scraper** | Scraping asincrono de estadisticas y play-by-play desde acb.com | Raiz del proyecto + `scripts/` |
| **Web editorial** | Frontend Next.js y backend FastAPI para consultar los datos procesados | `acb-web/` |
| **Motor PBP** | Motor de analisis play-by-play con modulos de posesiones, quintetos, clutch y tiro | `acb-pbp-analytics/` |
| **Automatizacion** | Orquestador incremental, Docker Compose y unidades systemd | `scripts/update_all.py`, `Dockerfile`, `deploy/systemd/` |

## Estructura del proyecto

```text
ACB-Scraper/
├── main.py, scraper.py, parsers.py, ...   # Scraper core
├── config.json                            # Configuracion del scraper
├── scripts/
│   ├── get_match_ids.py                   # Descubre IDs de partidos
│   ├── update_all.py                      # Orquestador incremental
│   ├── batch_play_by_play_v2.py           # Scraper PBP con Selenium
│   └── verify_pbp_completeness.py         # Verificacion de PBP
├── data/
│   ├── input/match_ids.json
│   ├── output/*.csv                       # CSVs de estadisticas
│   └── play_by_play/play_by_play_*.csv    # Ficheros PBP por partido
├── acb-web/
│   ├── backend/                           # API FastAPI
│   └── frontend/                          # Web Next.js
├── acb-pbp-analytics/
│   ├── src/                               # Modulos core
│   ├── analysis/                          # Analisis avanzado
│   └── visualizations/                    # Visualizaciones reutilizables
└── deploy/systemd/                        # Service + timer para produccion
```

Los CSVs generados, logs, backups, caches locales y play-by-play descargados estan ignorados por Git salvo los IDs de entrada versionados.

## Scraper

### Archivos principales

| Archivo | Funcion |
|---------|---------|
| `main.py` | Punto de entrada, coordina scraping y almacena resultados |
| `scraper.py` | Logica de scraping con `aiohttp` y procesamiento paralelo |
| `parsers.py` | Extraccion de datos de HTML: partidos, jugadores y perfiles |
| `http_client.py` | Cliente HTTP asincrono con rate limiting y reintentos |
| `utils.py` | Utilidades de limpieza y normalizacion de datos |
| `constants.py` | URLs, selectores HTML y mapeos constantes |
| `logger.py` | Configuracion del sistema de logging |

### Scripts auxiliares

| Script | Funcion |
|--------|---------|
| `scripts/get_match_ids.py` | Extrae IDs de partidos del calendario ACB |
| `scripts/update_all.py` | Orquesta actualizacion completa, backups y verificaciones |
| `scripts/batch_play_by_play_v2.py` | Scraper PBP con Selenium |
| `scripts/batch_play_by_play.py` | Scraper PBP v1 legacy |
| `scripts/verify_pbp_completeness.py` | Verifica completitud de ficheros PBP |
| `scripts/validate_scraper.py` | Ejecuta validaciones de salida sobre una muestra temporal |

### Uso

```bash
# Instalar dependencias con Python 3.12
python -m pip install -r requirements.txt

# Actualizar todo el dataset incrementalmente
python scripts/update_all.py --verify-pbp

# Validar scraper con salidas temporales
python scripts/validate_scraper.py

# Simular una ejecucion sin modificar datos
python scripts/update_all.py --dry-run
```

El scraper guarda los CSVs tras cada partido procesado correctamente. En logs se registran metricas por partido: descarga, parseo, perfiles, guardado y numero de perfiles completos descargados.

## Web Editorial (`acb-web/`)

La web actual combina:

- Backend FastAPI para exponer endpoints de clasificacion, partidos, equipos, jugadores, rankings y play-by-play.
- Frontend Next.js con paginas editoriales para explorar temporada, jornadas, partidos y perfiles.

### Backend

```bash
python -m uvicorn acb-web.backend.main:app --port 8000 --reload
```

### Frontend

```bash
cd acb-web/frontend
npm install
npm run dev
```

Web local: `http://localhost:3000`

## Motor PBP (`acb-pbp-analytics/`)

Procesa ficheros PBP crudos y genera metricas avanzadas.

### Modulos core

| Modulo | Funcion |
|--------|---------|
| `pbp_loader.py` | Carga y parseo de ficheros PBP |
| `time_utils.py` | Conversion de tiempos: periodos, reloj y segundos absolutos |
| `lineup_tracker.py` | Seguimiento de quintetos en pista a partir de eventos PBP |
| `possession_engine.py` | Estimacion de posesiones a partir de eventos |

### Modulos de analisis

| Modulo | Funcion |
|--------|---------|
| `clutch.py` | Rendimiento en situaciones clutch |
| `fouls.py` | Analisis de faltas por jugador, equipo y periodo |
| `game_state_performance.py` | Rendimiento segun estado del marcador |
| `lineup_combos.py` | Estadisticas de combinaciones de jugadores |
| `momentum.py` | Deteccion de rachas y cambios de momentum |
| `pace.py` | Ritmo de juego |
| `shooting_patterns.py` | Patrones de tiro por zona, periodo y situacion |
| `substitutions.py` | Analisis de rotaciones y cambios |

## Datos

### CSVs de estadisticas (`data/output/`)

| Archivo | Contenido |
|---------|-----------|
| `estadisticas_todos_partidos.csv` | Stats individuales por jugador y partido |
| `estadisticas_partido.csv` | Info general de cada partido |
| `estadisticas_equipos_por_partido.csv` | Totales de equipo por partido |
| `perfiles_jugadores.csv` | Datos biograficos de jugadores |

Los totales de equipo son los oficiales de ACB. Algunas estadisticas pueden incluir valores de equipo no asignados a jugadores individuales, por lo que no siempre coinciden exactamente con la suma de filas de jugadores.

### Play-by-play (`data/play_by_play/`)

Ficheros `play_by_play_[ID].csv` con todas las jugadas de cada partido. Cada registro contiene id_partido, periodo, tiempo, marcador, equipo, jugador, accion y estadistica. El scraper PBP verifica el marcador final contra `estadisticas_partido.csv`.

### Normalizacion de nombres de equipos

Los datos pueden mezclar nombres cortos, nombres con sponsor y nombres oficiales. La normalizacion vive en los servicios del backend y en los mapeos compartidos de la web.

## Automatizacion

```bash
docker compose build
docker compose run --rm scraper python scripts/update_all.py --dry-run
docker compose run --rm scraper python scripts/update_all.py --verify-pbp
docker compose run --rm scraper pytest
```

En produccion, el MiniPC puede usar las unidades de `deploy/systemd/`:

```bash
sudo systemctl enable --now acb-scraper.timer
journalctl -u acb-scraper.service -n 200
```

## Requisitos

- Python 3.12
- Node.js y npm para el frontend
- Chromium/Chromedriver para scraping PBP fuera de Docker
- Docker Compose para despliegue automatizado

Dependencias principales:

- `requirements.txt`: scraper, Selenium, pandas y utilidades de red.
- `acb-web/backend/requirements.txt`: API FastAPI.
- `acb-web/frontend/package.json`: web Next.js.
- `acb-pbp-analytics/requirements.txt`: pandas, numpy y plotly.
