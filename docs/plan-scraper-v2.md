# Plan de implementación: ACB Scraper v2 (desde cero)

Fecha: 2026-11-02. Temporada en curso: Liga Endesa 2026-27 (`editionId=91`).

## 0. Resumen ejecutivo

La web de la ACB ya no es un sitio HTML "clásico": `acb.com` y `live.acb.com` son
aplicaciones Next.js que se alimentan de una API JSON en `https://api2.acb.com/api`.
Esa API tiene **33 rutas GET**, se protege con una cabecera `X-APIKEY` cuyo valor es
**público** (va embebido en el bundle JavaScript de acb.com), no pagina, y cubre
box scores desde 1983-84, play-by-play y tiros con coordenadas desde 2016-17,
clasificaciones, calendarios, brackets de playoff, fichas de jugador, carrera,
game logs, plantillas, perfiles de club, récords, líderes y estadísticas avanzadas
(four factors, ratings, pace) tanto de equipo como de jugador.

**Decisión central:** el scraper v2 no debe parsear HTML ni usar Selenium. Debe ser
un **cliente de la API `api2.acb.com`** con capa de caché cruda (JSON tal cual),
modelos tipados y una base de datos analítica (DuckDB) encima. El parseo de HTML
(payload React Flight de Next.js) queda solo como mecanismo de contingencia.

Con ~1 petición/segundo, una temporada completa de Liga Endesa con todo el detalle
por partido cabe en ~1 hora, y el histórico completo de box scores (1983-84 → hoy)
en una tarde.

### Qué se ha podido verificar y qué no

Esta sesión se ejecuta en un entorno cloud cuya política de red **bloquea
`acb.com`, `live.acb.com` y `api2.acb.com`**, así que no he podido hacer
peticiones reales. El plan se apoya en cuatro fuentes:

1. **Especificación OpenAPI pública de `api2.acb.com`** (repositorio GitHub
   `saiemgilani/sdv-swagger`, fichero `acb-api.openapi.yaml`, versión
   `2026-10-12`, 21.000 líneas). Documenta las 33 rutas, parámetros, esquemas de
   respuesta, sistemas de identificadores, catálogo de tipos de jugada, sistemas
   de coordenadas de tiro y estados de partido. Sus autores afirman que todas las
   rutas respondían 200 el 2026-10-12.
2. **Paquete R `BAwiR` 1.5.6** (CRAN, 2026-10-13), que ya consume
   `/matchdata/MatchShots/match-shots` con `X-APIKEY` y extrae los IDs de partido
   del calendario de `acb.com`.
3. **Rutas reales de `acb.com` y `live.acb.com`** obtenidas de índices de
   búsqueda (listadas en el apéndice B).
4. **El scraper actual del repositorio**, que ya parseaba el payload React Flight
   de `acb.com` con las mismas estructuras (`initialMatchHeader`,
   `initialStatistics`, `playerData`) que devuelve la API.

**Actualización 2026-11-02:** con los dominios ya permitidos se ejecutó la
Fase 0 contra la API real y todas las hipótesis quedaron confirmadas
(`docs/fase0-verificacion.md`).

---

## 1. Inventario de datos disponibles

### 1.1 La API (`https://api2.acb.com/api`)

Cabeceras necesarias en toda petición:

```
X-APIKEY: <clave pública del bundle de acb.com>
Accept: application/json
Referer: https://live.acb.com/
User-Agent: acb-scraper-v2/0.1 (+contacto)
```

Sin `X-APIKEY` toda ruta responde **401**. Parámetro mal formado → **400**
(`application/problem+json`). Ruta o id desconocido → **404** (cuerpo vacío o
`text/plain`). `/matchdata/Overview/serie` devuelve **204** si el partido no es
de una eliminatoria.

#### Rutas de partido (`/matchdata/...`, todas con `matchId`)

| Ruta | Contenido | Desde |
|---|---|---|
| `MatchHeader/match-header` | Equipos, estado, marcador por cuarto, reloj, pestañas disponibles (`availableContent`), canales TV | 1983-84 |
| `Result/boxscores` | Box score por equipo y por periodo (`quarter 0` = total), árbitros, pabellón, asistencia, entrenador y ayudantes | 1983-84 |
| `PlayByPlay/play-by-play` | Jugada a jugada con `playType`, `playTag`, reloj, marcador y box score acumulado del jugador tras cada evento | 2016-17 |
| `MatchShots/match-shots` | Cada tiro de campo y tiro libre con `posX`, `posY`, `zone`, resultado, cuarto, reloj, marcador previo | 2016-17 |
| `Overview/lineup` | Titulares y banquillo con puntos, rebotes, asistencias, faltas, +/-, minutos, valoración | — |
| `Overview/lead-tracker` | Serie temporal del marcador (cuarto, minuto, segundo, puntos) + mayor racha, cambios de líder, máxima diferencia, tiempo por delante | — |
| `Overview/match-team-comparison` | Barras comparativas por periodo: tiros, rebotes, asistencias, pérdidas, robos, faltas, tiempos muertos, puntos de banquillo, de contraataque, en la pintura, tras pérdida, segunda oportunidad | — |
| `Overview/match-leaders` | Líderes del partido por equipo (puntos, rebotes, asistencias, valoración) | — |
| `Overview/serie` | Estado de la eliminatoria de playoff a la que pertenece el partido | — |
| `AdvancedStats/match-advanced-stats` | Por equipo: four factors, ratings ofensivo/defensivo/neto, pace, posesiones, puntos por posesión, TS%, eFG%, 3PAr, AST%, TOV%, STL%, BLK%, ORB%, DRB%, TRB%. Cada métrica trae valor del partido, de la temporada y splits victoria/derrota con diferencias | — |
| `AdvancedStats/player-advanced-stats` (+ `playerLicense`) | Las mismas métricas para **un** jugador del partido | — |
| `Preview/quickfacts` | Posición, balance y últimos resultados de cada equipo antes del partido | — |
| `Preview/season-leaders` | Líderes de temporada de cada equipo antes del partido | — |
| `Menu/matchlist` (`matchId`, `roundId` o `weekId`) | Partidos de la jornada o semana | — |
| `Menu/competition-data` (`competitionIds`) | Competición, edición, jornada y semana actuales; lista de ediciones con sus jornadas y semanas | — |

#### Rutas de temporada (`/seasondata/...`)

| Ruta | Parámetros | Contenido |
|---|---|---|
| `Calendar/season-calendar` | `competitionId`, `editionId` | Todas las jornadas de una edición con sus partidos (id, fecha UTC, estado, equipos, marcador, TV, entradas) y la lista de equipos |
| `Competition/matches` | `competitionId`, `editionId`, `roundId` o `weekId`, `isRoundSelected` | Partidos de una jornada (incluye aplazados) |
| `Competition/standings` | `competitionId`, `editionId`, `roundId` | Clasificación tras una jornada: PJ, V, D, PF, PC, +/-, balance casa/fuera, tendencia, y el historial jornada a jornada de cada equipo |
| `Competition/bracket` | `competitionId`, `editionId` | Cuadro de playoff: cuartos, semis, final, con series y partidos |
| `TeamProfile/teams` | `competitionId`, `editionId` | Equipos inscritos (season-team id, clubId, nombre de esa temporada, colores, logos) |
| `TeamProfile/club-data` | `clubId` | Perfil del club: pabellón (nombre, dirección, aforo), año de fundación, web, redes, tienda, entradas |
| `TeamProfile/current-roster` | `clubId`, `competitionId`, `editionId` | Plantilla y cuerpo técnico de una edición: licencia, nacionalidad, altura (cm), posición, dorsal, imágenes; funciona para temporadas antiguas |
| `TeamProfile/team-stats` | `clubId`, `competitionId`, `editionId` | Totales, medias y per-40 de cada jugador y del equipo en la temporada |
| `TeamProfile/team-matches` | `clubId`, `competitionId`, `editionId` | Partidos del club en la edición |
| `TeamProfile/next-matches` | `clubId`, `numberOfMatches` | Últimos y próximos partidos |
| `TeamProfile/team-leaders` | `clubId`, `numberOfPlayers`, `competitionId`, `editionId` | Líderes del club de la temporada y de toda la historia, por 33 categorías |
| `TeamProfile/team-records` | `clubId` | Récords individuales del club en un partido (puntos, rebotes, asistencias, etc.) con partido y jugador |
| `PlayerProfile/player-data` | `playerLicenceId` | Bio: nombre legal y deportivo, fecha y lugar de nacimiento, nacionalidad, altura, posición, dorsal, equipo actual, licencia, redes sociales, imágenes, audio de pronunciación |
| `PlayerProfile/player-stats` | `playerLicenceId`, `competitionId`, `editionId` | Totales, medias y per-40 por temporada y equipo, más totales de carrera |
| `PlayerProfile/career` | `playerLicenceId` | Etapas por club (años) y títulos |
| `PlayerProfile/matches` | `playerLicenceId`, `editionId` | Game log de una temporada con medias y totales |
| `Search/search` | `searchTerm`, `limit` | Búsqueda de jugadores, equipos y entrenadores por nombre |
| `ShotChart/league-zones` | `editionId`, `competitionId` | Tiros intentados, anotados y puntos por zona de toda la liga |

#### Sistema de identificadores (fundamental para el modelo de datos)

| Identificador | Significado | Ejemplos |
|---|---|---|
| `competitionId` | 1 Liga Endesa, 2 Copa del Rey, 3 Supercopa Endesa, 10 Minicopa Endesa | |
| `editionId` | Temporada = **año de inicio − 1935** | 91 = 2026-27, 90 = 2025-26, 81 = 2016-17, 48 = 1983-84 |
| `matchId` | Global entre competiciones. Dos espacios: < 20.000 hasta 2019-20; ≥ 100.000 desde 2020-21 | 17718 (final 2016-17), 105401 (2026-27) |
| `clubId` | Estable entre temporadas y patrocinadores | 2 Barça, 9 Real Madrid, 13 Valencia Basket, 28 La Laguna Tenerife |
| season-team `id` | Inscripción de un club en una edición de una competición (`homeTeamId`, `awayTeamId`, `teamEditionId`) | 4467 |
| `playerLicenceId` / `playerLicense` / `player.id` / `playerLicenseId` | Número de licencia = id de persona en todas partes (jugadores y entrenadores) | 20209407 Edy Tavares; antiguas `2020xxxx`, recientes `3000xxxx` |
| `roundId` | Jornada, global entre temporadas (no es el número de jornada) | 6017 = J3 2026-27, 2600 = J1 2016-17 |
| `weekId` | Semana, global | 2989 = semana del 2026-10-10 |
| `phaseId` / `subphaseId` | 107 Liga Regular, 111 Play Off Título; subfases para rondas de playoff/copa | |

Las mismas claves aparecen en las URLs de la web: `acb.com/es/liga/equipos/real-madrid-9/plantilla?editionId=91`,
`acb.com/es/liga/jugadores/walter-tavares-20209407/partidos`,
`live.acb.com/es/partidos/<slug>-105425/estadisticas`.

### 1.2 Catálogos que hay que versionar en el repo

- **Tipos de jugada** (`playType`, ~130 códigos). Los esenciales: 92/96 TL anotado/fallado, 93/97 T2, 94/98 T3, 100 mate, 533 mate fallado, 101/104 rebote ofensivo/defensivo, 102 tapón, 105 tapón recibido, 103 robo, 106 pérdida (detalle en `playTag`), 107/108 asistencia en T2/T3, 109 falta en ataque, 110 falta recibida, 112/115 entra/sale, 113/118 tiempo muerto/TV, 121/116 inicio/fin de periodo, 122/123 inicio/fin de partido, 130/131 contraataque, 159-179 familia de faltas (personal, antideportiva, descalificante, técnica, con 0-3 TL), 178/179 salto ganado/perdido, 200 descalificado, 405-417 instant replay y challenges, 599 quinteto inicial (5 filas por equipo a 10:00 del 1C), 748/749 challenge ganado/perdido, 537-787 variantes de técnicas y faltas. Código 600 sin documentar: marcador de minuto (40 por partido, sin jugador). Lista completa en el apéndice C.
- **`playTag`** (detalle de pérdida): 2 tres segundos, 7 24 s, 8 8 s, 9 14 s, 10 5 s saque, 11 5 s balón retenido, 12 mal pase, 13 balón controlado, 14 dobles, 15 campo atrás.
- **Estados de partido**: `NOT_SCHEDULED`, `NOT_STARTED`, `STARTED`, `SUSPENDED`, `POSTPONED`, `FINALIZED`.
- **Zonas de tiro**: `restricted_area`, `paint`, `mid_range_left|center|right`, `corner_three_left|right`, `wing_three_left|right`, `top_three`.
- **Sistemas de coordenadas de tiro** (dos, según el espacio de `matchId`):
  - *Legacy* (ids < 20.000, 2016-17 a 2019-20): porcentaje 0-100 de la **pista completa**, sin espejar (los equipos cambian de canasta al descanso). La `zone` legacy es poco fiable.
  - *Nuevo* (ids ≥ 100.000, 2020-21 →): **milímetros** desde el centro de la canasta atacada, `posX` hacia medio campo (nunca negativo, medio campo ≈ 12.425), `posY` lateral entre −7.500 y +7.500 (negativo = izquierda del tirador). Todos los tiros espejados a una sola canasta. Tiros libres en (0,0) con `zone` y `points` nulos.
- **Nombres de país** en castellano (`EE.UU.`, `Eslovenia`...), mapeables a ISO.
- **Posiciones** (`gameRole`) en castellano: Base, Escolta, Alero, Ala-pívot, Pívot.

### 1.3 Lo que la web tiene y la API no (y viceversa)

- Árbitros: solo nombres (lista de strings en `boxscores.referees`), sin id.
- Entrenadores: nombre en `boxscores.headCoach`; con licencia e imágenes en `current-roster.staff`. La ficha de entrenador de la web (`/es/liga/entrenadores/<slug>-<id>`) usa el mismo espacio de licencias; no hay ruta específica documentada, pero `player-data` admite `availableLicenses.coachLicenseData` (a verificar en Fase 0).
- Crónicas y noticias (`/cronica`, `/noticias`): fuera de alcance.
- Tabla de mercado (`/es/liga/tabla-mercado/2026-27`): página editorial; no hay ruta. Si interesa, se parsea del HTML en una fase posterior.
- Estadísticas de jugador "por categoría" de la web (`/estadisticas-avanzadas?categoria=blocks&filtro=temporada`) se construyen en el cliente a partir de `player-stats` y `matches`.

---

## 2. Arquitectura propuesta

```
acb_scraper/                     # paquete Python (nuevo, independiente del código actual)
├── client/
│   ├── apikey.py                # descubrimiento y caché de la X-APIKEY
│   ├── http.py                  # httpx.AsyncClient + rate limit + reintentos + caché cruda
│   └── endpoints.py             # una función tipada por ruta (33)
├── models/                      # pydantic v2: Team, Player, MatchHeader, Boxscore, Play, Shot...
├── reference/                   # play_types.json, play_tags.json, zones.json, countries.json
├── store/
│   ├── raw.py                   # data/raw/<ruta>/<hash-params>.json.gz + índice
│   └── db.py                    # DuckDB: DDL, upserts idempotentes
├── pipelines/
│   ├── discover.py              # competiciones → ediciones → jornadas → partidos → equipos → jugadores
│   ├── sync_match.py            # todo lo de un partido
│   ├── sync_player.py           # bio, stats, carrera, game log
│   ├── sync_club.py             # perfil, plantillas, stats, líderes, récords
│   ├── sync_season.py           # calendario, clasificación por jornada, bracket, zonas de liga
│   └── validate.py              # reglas de consistencia
├── transform/                   # tablas derivadas: quintetos, posesiones, coordenadas normalizadas
└── cli.py                       # typer: acb discover | sync | backfill | validate | export
data/
├── raw/                         # respuestas JSON intactas (gzip), nunca se reescriben
├── acb.duckdb                   # base analítica
└── export/                      # parquet / csv por tabla
tests/
├── fixtures/                    # JSON capturados en Fase 0 (una muestra por ruta y por era)
└── ...
```

### 2.1 Principios

1. **Capturar crudo, transformar después.** Cada respuesta se guarda íntegra con
   ruta, parámetros, timestamp y hash. Reparsear nunca exige volver a pedir.
2. **Idempotencia.** Toda escritura en DuckDB es un upsert por clave natural.
   Relanzar un sync no duplica.
3. **Estados, no fechas.** Un partido se considera cerrado cuando
   `matchStatus == FINALIZED` y todas sus rutas de detalle se han capturado; hasta
   entonces se vuelve a pedir en cada ejecución incremental.
4. **Una petición por segundo, un solo cliente.** La propia especificación pide
   espaciar ≥ 1 s. Sin concurrencia agresiva; la API no pagina y responde rápido.
5. **Tipado estricto en el borde.** Los modelos pydantic fallan ruidosamente ante
   un cambio de esquema; la captura cruda sigue guardándose aunque el parseo falle.
6. **Sin navegador.** Nada de Selenium/Playwright en el camino principal.

### 2.2 Stack

| Pieza | Elección | Motivo |
|---|---|---|
| Python | 3.12 | tipado moderno, `zoneinfo` |
| HTTP | `httpx` (async, HTTP/2) + `tenacity` | reintentos con backoff, timeouts, un solo cliente |
| Modelos | `pydantic` v2 | validación + serialización rápida |
| Almacén | `duckdb` + Parquet | analítica columnar en un fichero, sin servidor; exporta a CSV/Parquet trivialmente |
| CLI | `typer` | subcomandos y `--help` gratis |
| Logs | `structlog` | logs estructurados para los jobs programados |
| Tests | `pytest` + `respx` | fixtures JSON reales, sin red |
| Programación | `systemd timer` o `cron` (ya hay units en `deploy/systemd/`) | un `acb sync --incremental` diario y otro cada 15 min en días de jornada |

### 2.3 Descubrimiento de la `X-APIKEY`

La clave vive en el bundle de Next.js de `acb.com` bajo
`sharedServicesConfigDotnet.apiKey`. Valor documentado el 2026-10-12:
`0dd94928-6f57-4c08-a3bd-b1b2f092976e`. Es pública (cualquier visitante la
descarga), pero puede rotar, así que:

1. Descargar `https://www.acb.com/` y buscar la expresión
   `apiKey["']?\s*:\s*["']([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`.
2. Si no aparece en el HTML, iterar los `<script src="/_next/static/chunks/...">`
   y buscar en cada uno.
3. Cachear en `data/.apikey.json` con fecha. Ante un `401`, invalidar y repetir.
4. Fallback final: el valor documentado, con un aviso en el log.

### 2.4 Modelo de datos (DuckDB)

Tablas núcleo (clave primaria entre paréntesis):

| Tabla | Clave | Origen |
|---|---|---|
| `competitions` | (competition_id) | competition-data |
| `editions` | (competition_id, edition_id) | competition-data / season-calendar |
| `phases`, `rounds`, `weeks` | (round_id) / (week_id) | season-calendar, competition-data |
| `clubs` | (club_id) | teams, club-data |
| `teams` | (season_team_id) | teams, season-calendar |
| `persons` | (licence_id) | player-data, current-roster (jugadores y staff) |
| `rosters` | (season_team_id, licence_id) | current-roster |
| `matches` | (match_id) | season-calendar, match-header, boxscores (árbitros, pabellón, asistencia, entrenadores) |
| `match_quarter_scores` | (match_id, quarter) | match-header |
| `boxscore_players` | (match_id, licence_id, quarter) | boxscores |
| `boxscore_teams` | (match_id, season_team_id, quarter, kind ∈ {total, team}) | boxscores |
| `pbp_events` | (match_id, order) | play-by-play |
| `shots` | (match_id, shot_id) | match-shots |
| `lead_tracker` | (match_id, seq) | lead-tracker |
| `match_lead_stats` | (match_id) | lead-tracker.stats |
| `match_comparison` | (match_id, quarter, stat, side) | match-team-comparison |
| `match_advanced_team` | (match_id, season_team_id, metric, split) | match-advanced-stats |
| `match_advanced_player` | (match_id, licence_id, metric, split) | player-advanced-stats |
| `series` | (match_id) | serie / bracket |
| `standings` | (competition_id, edition_id, round_id, season_team_id) | standings |
| `player_season_stats` | (licence_id, competition_id, edition_id, season_team_id, kind ∈ {totals, averages, per40}) | player-stats |
| `player_career_stints`, `player_trophies` | (licence_id, club_id, start_year) | career |
| `player_game_log` | (licence_id, match_id) | matches (cruce con boxscores) |
| `club_profiles` | (club_id) | club-data |
| `team_season_stats` | (season_team_id, licence_id nullable, kind) | team-stats |
| `team_leaders` | (club_id, edition_id nullable, category, rank) | team-leaders |
| `team_records` | (club_id, category) | team-records |
| `league_shot_zones` | (competition_id, edition_id, zone) | league-zones |
| `raw_requests` | (route, params_hash) | índice de la caché cruda |

Tablas derivadas (`transform/`):

- `shots_normalized`: `x_m`, `y_m` en metros desde la canasta para ambas eras,
  `distance_m`, `zone_computed` (recalculada geométricamente; la zona legacy no se
  usa), `is_three` coherente con `points`.
- `lineup_stints`: quintetos en pista reconstruidos a partir de `599` (quinteto
  inicial) y `112`/`115` (cambios), con inicio/fin, marcador y posesiones.
- `possessions`: inferidas del play-by-play (cambios de posesión por canasta,
  pérdida, rebote defensivo, final de periodo). El motor de `acb-pbp-analytics`
  se puede portar aquí.

---

## 3. Fases

### Fase 0. Verificación con tráfico real (medio día) — HECHA el 2026-11-02

Resultado en `docs/fase0-verificacion.md`: las 33 rutas responden, la clave se
extrae del bundle, y todas las reglas de consistencia se cumplen en los partidos
de muestra. Fixtures en `tests/fixtures/api2/`. Ajustes derivados: seguir
redirecciones y recorrer chunks JS para la clave; ignorar `playType 600`;
`playTag 1` sin mapear; fichas de entrenador vía `player-data`; consultar
`availableContent` antes de pedir detalle en ediciones ≤ 2019-20.

Objetivo original: confirmar que la API responde como dice la especificación y
capturar fixtures. Hay que hacerlo desde una máquina con acceso a `acb.com`.

1. Comprobar `https://acb.com/robots.txt` y el aviso legal. La especificación
   indica que `robots.txt` permite `/` y que el aviso legal reclama derechos de
   base de datos: uso personal/educativo, ritmo moderado, sin redistribución
   masiva. Dejarlo documentado en el README.
2. Extraer la clave del bundle y probar:

```bash
KEY=$(curl -s https://www.acb.com/ | grep -oE 'apiKey"?:"?[0-9a-f-]{36}' | head -1 | grep -oE '[0-9a-f-]{36}')
echo "$KEY"
curl -s -H "X-APIKEY: $KEY" -H "Referer: https://live.acb.com/" \
  "https://api2.acb.com/api/matchdata/MatchHeader/match-header?matchId=105401" | head -c 600
```

3. Capturar una muestra por ruta y por era (ids 105401 → 2026-27, 17718 → 2016-17,
   12559 → 2005-06; `editionId` 91, 90, 81; `clubId` 2; `playerLicenceId`
   20209407) y guardarla en `tests/fixtures/`.
4. Verificar supuestos concretos: `competitionIds` repetido vs. lista con comas
   (la spec dice que la coma da 400); `serie` → 204; formato de `birthDate`
   (`DD-MM-YYYY`); altura como `"2,20"` en `player-data` pero `220` en roster;
   que `player-data` exponga licencias de entrenador; el código 600 del PBP.
5. Medir latencia y confirmar que no hay bloqueo a 1 req/s durante ~500 peticiones.

Entregable: fixtures + `docs/fase0-verificacion.md` con lo observado.

### Fase 1. Núcleo: cliente, caché cruda, modelos y temporada actual (1 semana)

1. `client/http.py`: `AsyncClient` único, limitador de 1 req/s (token bucket),
   reintentos exponenciales en 5xx/timeout/red, **sin** reintento en 401/404,
   invalidación de clave en 401.
2. `store/raw.py`: guardar cada respuesta antes de parsear.
3. Modelos pydantic para: competition-data, season-calendar, teams, standings,
   match-header, boxscores, current-roster, player-data.
4. DDL de DuckDB y upserts.
5. `pipelines/discover.py` + `sync_season.py`: para `(competitionId=1, editionId=91)`
   cargar ediciones, jornadas, equipos, plantillas, calendario y clasificación de
   todas las jornadas jugadas.
6. `pipelines/sync_match.py` (parte 1): header + boxscores de cada partido
   `FINALIZED`; estado `complete` por partido y por ruta.
7. CLI: `acb discover`, `acb sync season --competition 1 --edition 91`,
   `acb sync match 105401`.
8. Validaciones básicas (ver §4).

Resultado: las tablas que hoy produce el scraper viejo (partidos, estadísticas
por jugador, totales de equipo, perfiles) quedan cubiertas con más campos y sin
HTML.

### Fase 2. Eventos del partido (1 semana)

Añadir a `sync_match.py`: play-by-play, match-shots, lineup, lead-tracker,
match-team-comparison, match-leaders, serie, match-advanced-stats. Catálogos de
`playType`/`playTag`/zonas como tablas de referencia. `transform/shots.py` con la
normalización de coordenadas de ambas eras. Validaciones de PBP y tiros.

Opción cara: `player-advanced-stats` requiere **una petición por jugador y
partido** (~24 por partido, ~8.000 por temporada). Se implementa con flag
`--player-advanced` y se ejecuta solo para la temporada actual o bajo demanda.

### Fase 3. Entidades: jugadores, clubes, entrenadores (3-4 días)

- `sync_player.py`: `player-data`, `player-stats` (todas las temporadas y
  competiciones), `career`, `matches` por edición. Se dispara para toda licencia
  vista en plantillas o box scores.
- `sync_club.py`: `club-data`, `current-roster` por edición, `team-stats`,
  `team-matches`, `team-leaders` (temporada e histórico), `team-records`.
- Staff: desde `current-roster.staff` (licencia, rol, nacionalidad, edad).
- `Search/search` solo como utilidad de CLI (`acb find tavares`).

### Fase 4. Otras competiciones, playoffs y robustez (3 días)

- Copa del Rey (2), Supercopa (3), Minicopa (10): mismo pipeline con otro
  `competitionId`. `bracket` para fases finales.
- `league-zones` por edición.
- Fallback HTML: un parser mínimo del payload React Flight
  (`self.__next_f.push`) para `www.acb.com/partido/estadisticas/id/<id>` y
  `/jugador/ver/<id>`, reutilizando la lógica de `modern_acb.py`, activable con
  `--source html` si la API dejara de ser accesible.
- Alertas: contador de 401/404/5xx por ejecución, aviso si cambia la clave o si
  pydantic rechaza una respuesta.

### Fase 5. Histórico y operación (1 semana, mayormente tiempo de máquina)

- `acb backfill --competition 1 --from-edition 48 --to-edition 90`: box scores y
  headers desde 1983-84; PBP, tiros y overview desde 2016-17 (`editionId ≥ 81`).
  Respetar `availableContent` del header para no pedir rutas vacías.
- Jobs programados: `acb sync --incremental` diario (partidos nuevos
  `FINALIZED`, jugadores y plantillas cambiadas) y cada 15 min en ventanas de
  jornada. Reutilizar `deploy/systemd/`.
- `acb export --format parquet|csv` por tabla para el backend FastAPI existente.
- Documentación: README del paquete, diccionario de datos generado desde los
  modelos.

### Fase 6 (opcional). Analítica derivada

Portar `acb-pbp-analytics` al nuevo modelo: quintetos, on/off, posesiones,
clutch, rachas, tiros por zona normalizada. Ahora con `playType` numérico en
lugar de texto en castellano, lo que elimina la mayor parte del parseo frágil.

### Estimación de volumen (a 1 req/s)

| Bloque | Peticiones | Tiempo |
|---|---|---|
| Temporada actual, núcleo por partido (9 rutas × ~333 partidos) | ~3.000 | ~50 min |
| + `player-advanced-stats` | ~8.000 | ~2,2 h |
| Jugadores activos (~250 × 4 rutas) y clubes (18 × 6) | ~1.100 | ~20 min |
| Histórico box scores 1983-84 → 2025-26 (~12.500 partidos × 2) | ~25.000 | ~7 h |
| Histórico PBP + tiros + overview 2016-17 → 2025-26 (~3.300 × 7) | ~23.000 | ~6,5 h |

---

## 4. Reglas de validación (se ejecutan tras cada sync)

1. `match-header.currentHomeScore/AwayScore` = suma de `quarterScores` =
   `boxscores.total.points` (quarter 0) = último `scoreHome/Away` del PBP.
2. Para cada equipo y periodo: `total` = Σ `players` + `team` en todas las columnas.
3. Box score `quarter 0` = Σ box scores de los cuartos (jugador a jugador).
4. PBP: exactamente 5 filas `599` por equipo; cada `115` tiene un `112` emparejado;
   el `playerStats` acumulado en el último evento de cada jugador coincide con su
   línea del box score.
5. Tiros (ids ≥ 100.000): nº de tiros de campo en `shotPoints` = FGA del box
   score; `points==3` ⇔ distancia a canasta ≥ 6,75 m (con tolerancia de 5 cm;
   esquinas ≥ 6,60 m laterales).
6. Clasificación: `wins + loses == matchesPlayed`; `plusMinus == pointsFor − pointsAgainst`.
7. Calendario vs. jornada: `Competition/matches` de cada `roundId` devuelve los
   mismos ids que `season-calendar` (detecta aplazamientos).
8. Game log del jugador (`PlayerProfile/matches`) coincide con sus filas de
   `boxscore_players` para esa edición.

Cada regla escribe en `validation_issues(match_id, rule, detail, seen_at)`; el
sync incremental re-pide los partidos con incidencias abiertas.

---

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Rotación de la `X-APIKEY` | 401 global | descubrimiento automático desde el bundle; alerta |
| API no oficial: cambios de esquema sin aviso | parseo roto | caché cruda intacta + modelos estrictos + fixtures por era en tests |
| Bloqueo por ritmo | pérdida de acceso | 1 req/s, un solo cliente, UA identificativo, sin reintentos en 4xx |
| Derechos de base de datos del aviso legal | legal | uso personal/educativo, no publicar volcados masivos, documentar la fuente |
| Dos eras de ids y de coordenadas | datos inconsistentes | columna `era` en `matches`; normalización explícita; zona legacy descartada |
| `player-advanced-stats` muy caro | horas de scraping | opt-in y solo temporada actual |
| Partidos aplazados/suspendidos | huecos | estado por partido, re-sync mientras no sea `FINALIZED`, diff calendario/jornada |
| Rutas "server-only" (PlayerProfile, TeamProfile) descubiertas por sondeo | podrían cerrarse | fallback HTML de Fase 4 para bio y plantillas |

---

## 6. Primeros pasos concretos

1. Permitir `acb.com`, `www.acb.com`, `live.acb.com` y `api2.acb.com` en la red
   del entorno (o ejecutar la Fase 0 en local).
2. Ejecutar los `curl` de la Fase 0 y guardar fixtures.
3. Crear el paquete `acb_scraper/` con `client/`, `models/` y `store/` y hacer
   pasar un test que parsee los fixtures de `match-header` y `boxscores`.
4. Implementar `acb sync season --competition 1 --edition 91` de extremo a extremo.
5. Decidir si el código viejo (`main.py`, `scraper.py`, `parsers.py`,
   `modern_acb.py`, `scripts/batch_play_by_play*.py`) se archiva en `legacy/` o
   se elimina una vez el backend FastAPI lea de DuckDB/Parquet.

---

## Apéndice A. Rutas de la API con sus parámetros

```
GET /matchdata/MatchHeader/match-header?matchId=
GET /matchdata/Result/boxscores?matchId=
GET /matchdata/PlayByPlay/play-by-play?matchId=
GET /matchdata/MatchShots/match-shots?matchId=
GET /matchdata/Overview/lineup?matchId=
GET /matchdata/Overview/lead-tracker?matchId=
GET /matchdata/Overview/match-team-comparison?matchId=
GET /matchdata/Overview/match-leaders?matchId=
GET /matchdata/Overview/serie?matchId=                       (204 si no es playoff)
GET /matchdata/AdvancedStats/match-advanced-stats?matchId=
GET /matchdata/AdvancedStats/player-advanced-stats?matchId=&playerLicense=
GET /matchdata/Preview/quickfacts?matchId=
GET /matchdata/Preview/season-leaders?matchId=
GET /matchdata/Menu/matchlist?matchId= | roundId= | weekId=  [&format=]
GET /matchdata/Menu/competition-data?competitionIds=1&competitionIds=2
GET /seasondata/Calendar/season-calendar?competitionId=&editionId=
GET /seasondata/Competition/matches?competitionId=&editionId=&roundId= | weekId=&isRoundSelected=
GET /seasondata/Competition/standings?competitionId=&editionId=[&roundId=]
GET /seasondata/Competition/bracket?competitionId=&editionId=
GET /seasondata/TeamProfile/teams?competitionId=&editionId=
GET /seasondata/TeamProfile/club-data?clubId=
GET /seasondata/TeamProfile/current-roster?clubId=&competitionId=&editionId=
GET /seasondata/TeamProfile/team-stats?clubId=&competitionId=&editionId=
GET /seasondata/TeamProfile/team-matches?clubId=&competitionId=&editionId=
GET /seasondata/TeamProfile/next-matches?clubId=&numberOfMatches=5[&competitionId=&editionId=]
GET /seasondata/TeamProfile/team-leaders?clubId=&numberOfPlayers=&competitionId=&editionId=
GET /seasondata/TeamProfile/team-records?clubId=
GET /seasondata/PlayerProfile/player-data?playerLicenceId=
GET /seasondata/PlayerProfile/player-stats?playerLicenceId=[&competitionId=&editionId=]
GET /seasondata/PlayerProfile/career?playerLicenceId=
GET /seasondata/PlayerProfile/matches?playerLicenceId=[&editionId=]
GET /seasondata/Search/search?searchTerm=&limit=
GET /seasondata/ShotChart/league-zones?editionId=&competitionId=
```

Campos del box score por jugador (`boxscores.statsByPeriods[].stats.players[]`):
`isStarted`, `onCourt`, `playTime` (mm:ss), `points`, `twoPointersMade/Attempted`,
`threePointersMade/Attempted`, `freeThrowsMade/Attempted`, `offRebounds`,
`defRebounds`, `totalRebounds`, `assists`, `steals`, `turnovers`, `blocks`,
`receivedBlocks`, `dunks`, `personalFouls`, `foulsDrawn`, `plusMinus`, `rating`,
más `player` (licencia, nombres legal y deportivo, posición, dorsal, imágenes).

Campos de cada jugada (`play-by-play.plays[]`): `order`, `quarter`, `minute`,
`second`, `playType`, `playTag`, `local`, `playerLicenseId`, `playerName`,
`playerNumber`, `licenseType`, `scoreHome`, `scoreAway`, `playerStats` (acumulado
del jugador: puntos, tiros, rebotes, asistencias, robos, pérdidas, tapones, faltas).

Campos de cada tiro (`match-shots.shotPoints[]`): `id`, `local`,
`playerLicenseId`, `playType`, `made`, `points`, `posX`, `posY`, `zone`,
`quarter`, `minute`, `second`, `scoreHome`, `scoreAway`.

## Apéndice B. Mapa de URLs de la web (para navegar y para el fallback HTML)

```
acb.com/es/liga                                   portada Liga Endesa
acb.com/es/liga/calendario?temporada=91          calendario (RSC con roundNumber y matches[].id)
acb.com/es/liga/partidos                          resultados de la jornada
acb.com/es/liga/clasificacion                     clasificación
acb.com/es/clasificacion?temporada=90&jornada=5886
acb.com/es/liga/estadisticas/estadisticas-de-jugador | estadisticas-de-equipo
acb.com/es/liga/equipos/<slug>-<clubId>/plantilla?editionId=91 | partidos | estadisticas
acb.com/es/liga/jugadores/<slug>-<licencia>                 ficha
acb.com/es/liga/jugadores/<slug>-<licencia>/temporada | partidos | trayectoria | estadisticas-avanzadas
acb.com/es/liga/entrenadores/<slug>-<licencia>
acb.com/es/liga/tabla-mercado/2026-27
acb.com/es/copa-del-rey/calendario | noticias
acb.com/es/supercopa/calendario | partidos | bracket | ediciones-anteriores/2025-26
acb.com/docs/calendario/calendarioLigaEndesa202627.pdf
live.acb.com/es/partidos/<slug>-<matchId>/resumen | estadisticas | estadisticas-avanzadas | jugadas | cronica
www.acb.com/partido/estadisticas/id/<matchId>    ruta legacy, sigue viva (Next.js, payload React Flight)
www.acb.com/jugador/ver/<licencia>               ruta legacy, sigue viva
www.acb.com/club/plantilla/id/<clubId>/temporada_id/<año>
```

## Apéndice C. Catálogo completo de `playType`

```
92 FREE_THROW_MADE            96 FREE_THROW_MISSED
93 TWO_POINTER_MADE           97 TWO_POINTER_MISSED
94 THREE_POINTER_MADE         98 THREE_POINTER_MISSED
100 DUNK                      533 DUNK_MISSED
101 OFFENSIVE_REBOUND         104 DEFENSIVE_REBOUND
102 BLOCK                     105 BLOCK_RECEIVED
103 STEAL                     106 TURNOVER (detalle en playTag)
107 ASSIST_TWO_POINTS_SHOT    108 ASSIST_THREE_POINTS_SHOT   119 ASSIST_FOUL_RECEIVED
109 OFFENSIVE_FOUL            110 FOUL_RECEIVED
112 SUBSTITUTION_IN           115 SUBSTITUTION_OUT
113 TIMEOUT                   118 TIMEOUT_TV
121 START_OF_QUARTER          116 END_OF_QUARTER
122 START_OF_GAME             123 END_OF_GAME
130 FAST_BREAK_TWO_POINTS     131 FAST_BREAK_THREE_POINTS
159 FOUL_NO_FREE_THROW        160 FOUL_ONE_FREE_THROW        161 FOUL_TWO_FREE_THROW
162 PERSONAL_FOUL_THREE_FREE_THROW   163 DOUBLE_PERSONAL_FOUL_NO_FREE_THROW   164 PERSONAL_FOUL_NO_TEAM_FOUL
165-169 UNSPORTSMANLIKE_FOUL_{ONE,TWO,THREE}_FREE_THROW / DOUBLE_NO_FREE_THROW / NO_TEAM_FOUL
170 DISQUALIFYING_FOUL        171 DISQUALIFYING_FOUL_NO_TEAM_FOUL
172 TECHNICAL_FOUL            173 DOUBLE_TECHNICAL_FOUL_NO_FREE_THROW   174 TECHNICAL_FOUL_NO_TEAM_FOUL
175 FIGHT                     176 TECHNICAL_FOUL_COACH        177 TECHNICAL_FOUL_BENCH
178 WON_JUMP                  179 LOST_JUMP
200 GAME_DISQUALIFYING
405 INSTANT_REPLAY  406-415 IR_REVIEW_* (tipo de tiro, validez, reloj posesión, reloj partido, pelea,
    tipo de falta, violación, último toque, acción jugador, sustitución)
416 IR_CHALLENGE_HOME_COACH   417 IR_CHALLENGE_AWAY_COACH    748 IR_CHALLENGE_WON   749 IR_CHALLENGE_LOST
537-539 FOUL_TECHNICAL_{1,2,3}_FREE_THROW
540-543 TECHNICAL_FOUL_COACH_{1,2,3}_FREE_THROW / DOUBLE_NO_FREE_THROW
544-547 TECHNICAL_FOUL_BENCH_{1,2,3}_FREE_THROW / DOUBLE_NO_FREE_THROW
548-551 DISQUALIFYING_FOUL_{1,2,3}_FREE_THROW / NO_FREE_THROW
552-556 FIGHT_{1,2,3}_FREE_THROW / DOUBLE_NO / NO_FREE_THROW
559-563 TECHNICAL_FOUL_BENCH_NO_ACCUMULATE_* / WITH_ACCUMULATE_DOUBLE / NO_FREE_THROW
599 STARTING_LINEUP (una fila por titular a 10:00 del 1C)
600 (sin documentar) marcador de minuto, 40 por partido, sin jugador
750-754 TECHNICAL_FOUL_BD_DISQUALIFYING_*    755-759 DISRUPTIVE_FOUL_*    760-764 FLAGRANT_FOUL_*
765-769 TECHNICAL_FOUL_BD_*    770-777 TECHNICAL_FOUL_{BENCH,COACH}_CAT1_*
778-782 TECHNICAL_FOUL_CAT1_*  783-787 TECHNICAL_FOUL_CAT2_*
```

Métricas de `match-advanced-stats` / `player-advanced-stats` (cada una con
`partido`, `temporada`, `win`, `loss` y sus diferencias): `fourFactors`
(efgPct, tovPct, orbPct, fTr), `ratings` (oer, der, netRating), `gameRhythm`
(possessions, pace, pointsPerPossession), `points` (pointsPerHundredPossessions,
pp2ps, pp3ps, ppft), `shooting` (tsPct, efgPct, threePAr, ppt), `rebounds`
(orbPct, drbPct, trbPct), `ballHandling` (astPct, astRatio, tovPct, stlPct,
stlRatio, blkPct).

## Apéndice D. Fuentes consultadas

- `https://github.com/saiemgilani/sdv-swagger` → `acb-api.openapi.yaml` (2026-10-12).
- CRAN `BAwiR` 1.5.6 (2026-10-13): `do_scrape_shots_acb.R`, `do_scrape_days_acb.R`.
- Rutas de `acb.com` / `live.acb.com` indexadas públicamente (apéndice B).
- Código actual del repositorio (`modern_acb.py`, `scripts/get_match_ids.py`,
  `scripts/batch_play_by_play_v2.py`, `catalogo_acciones.txt`).
