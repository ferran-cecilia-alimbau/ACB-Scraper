# acb_scraper (v2)

Descarga **cruda** de la API JSON que alimenta acb.com y live.acb.com
(`https://api2.acb.com/api`). Cada respuesta se guarda tal cual, comprimida, en
`data/raw/<ruta>/<parámetros>.json.gz`. No transforma nada: la capa de tablas es
opcional (`build`) y se puede rehacer siempre a partir del crudo.

Documentación de la API y del plan: `docs/plan-scraper-v2.md`, `docs/fase0-verificacion.md`.

## Instalación

```bash
python3 -m venv .venv
.venv/bin/pip install -e .          # añade "[build]" si quieres generar Parquet/CSV
```

## Uso

```bash
acb-scraper backfill                 # todo el histórico de Liga, Copa y Supercopa (10-14 h a 1 req/s)
acb-scraper backfill --competitions 1 --from-edition 81     # solo Liga desde 2016-17
acb-scraper sync                     # temporada en curso: partidos nuevos, clasificación, plantillas, fichas
acb-scraper status                   # qué hay descargado
acb-scraper build                    # tablas Parquet + CSV en data/output/v2 (requiere pyarrow)
```

Opciones comunes: `--detail full` (añade quintetos, evolución del marcador,
comparativa, líderes, avanzadas, eliminatorias y líderes de club), `--no-people`,
`--interval 1.0`, `--data-dir` o la variable `ACB_DATA_DIR`, `--contact` o `ACB_CONTACT`
(se incluye en el User-Agent).

Códigos de salida: `0` bien, `1` error de uso o inesperado, `2` API no disponible
(reintentar más tarde), `3` ya hay otra ejecución en curso.

## Garantías

- **Reanudable:** lo ya descargado no se vuelve a pedir. Se puede parar con Ctrl-C o
  `systemctl stop` y relanzar; termina la petición en curso y sale limpiamente.
- **Escrituras atómicas:** un corte de luz nunca deja un fichero a medias. Un fichero
  corrupto se detecta, se borra y se vuelve a pedir.
- **Partidos inmutables:** un partido `FINALIZED` se pide una vez. Nunca se descargan
  partidos en juego o sin jugar.
- **Datos vivos con caducidad:** calendario, clasificación, bracket, equipos, plantillas
  y stats de equipo se refrescan si tienen más de 1 día (edición actual) o 90 días
  (ediciones pasadas). Fichas de personas: 30 días (`--people-max-age`).
- **Clave de API:** se extrae del bundle JavaScript de acb.com, se cachea 7 días y se
  redescubre automáticamente ante un 401.
- **Ritmo:** 1 petición por segundo; reintentos con espera exponencial en errores de red
  y 5xx; aborta con salida 2 tras 25 fallos seguidos para que systemd lo reintente más tarde.
- **Un solo proceso por directorio de datos** (fichero `.lock`).
- **Registro:** `data/logs/acb-scraper.log` (rotado, 5 × 10 MB) y una línea JSON por
  ejecución en `data/logs/runs.jsonl`.

## Qué se descarga

| Ámbito | Rutas (core) | Desde |
|---|---|---|
| Competición/edición | competition-data, season-calendar, standings, bracket, league-zones, teams | 1983-84 |
| Club por edición | current-roster, team-stats (+ team-leaders en `full`) | 1983-84 |
| Partido | match-header, boxscores | 1983-84 |
| Partido | play-by-play, match-shots | 2016-17 |
| Partido (`full`) | lineup, lead-tracker, match-team-comparison, match-leaders, match-advanced-stats, serie | 2016-17 / 2020-21 |
| Persona | player-data, player-stats, career | todas |

No se descargan `player-advanced-stats` (una petición por jugador y partido),
`club-data`, `team-records`, `next-matches`, `quickfacts`, `season-leaders`,
`matchlist` ni `search`; el cliente tiene métodos para todas ellas.

## Servicio en Ubuntu Server

```bash
sudo useradd -r -m -d /opt/acb-scraper acb
sudo -u acb git clone <repo> /opt/acb-scraper
sudo -u acb python3 -m venv /opt/acb-scraper/.venv
sudo -u acb /opt/acb-scraper/.venv/bin/pip install -e /opt/acb-scraper
sudo cp deploy/systemd/acb-scraper-v2*.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start acb-scraper-v2-backfill       # histórico, una vez; reanudable
sudo systemctl enable --now acb-scraper-v2.timer   # sync diario a las 04:30
journalctl -u acb-scraper-v2-backfill -f
```

Edita `User`, rutas y `ACB_CONTACT` en los ficheros `.service` antes de copiarlos.

## Formato de los datos crudos

Un fichero por petición. El nombre codifica los parámetros ordenados
(`matchId=105401.json.gz`, `clubId=2&competitionId=1&editionId=91.json.gz`). Las
respuestas 204/404 se guardan como `{"_status": 204}`. Ids: `editionId` = año de
inicio − 1935 (91 = 2026-27); `competitionId` 1 Liga, 2 Copa, 3 Supercopa, 10 Minicopa;
licencia = id de persona; `clubId` estable entre temporadas.

Particularidades por época (el esquema es el mismo, el contenido no):

- Hasta 2019-20 el box score solo trae el total (`quarter 0`); desde 2020-21, por cuartos.
- Campos no registrados en temporadas antiguas vienen a 0 (no nulos): +/-, mates,
  tapones recibidos, faltas recibidas.
- Coordenadas de tiro: ids de partido < 20000 (2016-17 a 2019-20) en porcentaje 0-100
  de la pista completa sin espejar; ids ≥ 100000 en milímetros desde la canasta atacada.
- Play-by-play: `playType 600` es un marcador de minuto sin contenido.
