# ACB Scraper

Proyecto de portfolio para extraer, transformar y visualizar datos publicos de la Liga Endesa ACB.

El repositorio incluye:

- Scraper Python para estadisticas de partidos, equipos y jugadores.
- Extraccion y analisis de play-by-play.
- Pipeline automatizable con Docker Compose y systemd.
- Backend FastAPI para servir los datos procesados.
- Web editorial en Next.js para explorar clasificacion, partidos, jugadores y rankings.

## Proyecto no oficial

Este proyecto no esta afiliado, patrocinado ni aprobado por ACB, Liga Endesa, clubes o entidades relacionadas.

Los datos se obtienen de fuentes publicas disponibles en la web de ACB y se usan con fines educativos, tecnicos y de portfolio. Las marcas, nombres de equipos y logotipos pertenecen a sus respectivos propietarios. Si se despliega publicamente, conviene revisar el uso de logotipos y sustituirlos por monogramas propios si se quiere minimizar riesgo de marca.

## Estructura

```text
.
├── acb-web/              # Web Next.js + backend FastAPI
├── acb-pbp-analytics/    # Analisis de play-by-play
├── scripts/              # Automatizacion y scraping batch
├── deploy/systemd/       # Units para ejecucion programada
├── data/input/           # IDs de partidos versionados
└── docs/                 # Planes y specs tecnicas
```

Los CSVs generados, logs, backups y play-by-play locales estan ignorados por Git.

## Ejecucion local

Backend:

```bash
python -m uvicorn acb-web.backend.main:app --port 8000 --reload
```

Frontend:

```bash
cd acb-web/frontend
npm install
npm run dev
```

Web: `http://localhost:3000`

## Automatizacion

El pipeline de actualizacion esta preparado para ejecutarse con Docker Compose:

```bash
docker compose build
docker compose run --rm scraper python scripts/update_all.py --dry-run
docker compose run --rm scraper python scripts/update_all.py --verify-pbp
```

En `deploy/systemd/` hay un service y timer para lanzar la actualizacion diaria en un servidor Linux.

## Seguridad y datos locales

Antes de publicar cambios, revisa que no se hayan anadido por error:

- `.env` o ficheros de credenciales.
- `data/output/`, `data/play_by_play/`, `data/logs/` o `data/backups/`.
- caches como `.venv/`, `.next/`, `node_modules/` o `scripts/.wdm/`.

## Capturas de Pantalla

<img width="1470" height="832" alt="Captura de pantalla 2026-05-08 a las 18 18 14" src="https://github.com/user-attachments/assets/fb905946-f8cf-4f02-b147-1a5f9779e6d3" />
<img width="1470" height="830" alt="Captura de pantalla 2026-05-08 a las 18 18 36" src="https://github.com/user-attachments/assets/054e1347-62d4-4f04-b052-b2e2a6c00dad" />
<img width="1466" height="835" alt="Captura de pantalla 2026-05-08 a las 18 19 10" src="https://github.com/user-attachments/assets/cf7483a9-59e2-45c5-b891-b44dcd061064" />
<img width="1470" height="842" alt="Captura de pantalla 2026-05-08 a las 18 18 50" src="https://github.com/user-attachments/assets/87f9cb18-79cc-472e-847d-9c8e2a9a3937" />


## Licencia

No se ha definido una licencia open source explicita. Sin licencia, el codigo queda protegido por copyright por defecto.
