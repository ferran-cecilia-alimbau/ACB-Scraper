# ACB Scraper

Proyecto de portfolio para extraer, transformar y visualizar datos publicos de la Liga Endesa ACB.

El repositorio incluye:

- Scraper Python para estadisticas de partidos, equipos y jugadores.
- Extraccion y analisis de play-by-play.
- Pipeline automatizable con Docker Compose y systemd.
- Backend FastAPI para servir los datos procesados.
- Web editorial en Next.js para explorar clasificacion, partidos, jugadores y rankings.
- Dashboard Streamlit historico y prototipos de analitica avanzada.

## Proyecto no oficial

Este proyecto no esta afiliado, patrocinado ni aprobado por ACB, Liga Endesa, clubes o entidades relacionadas.

Los datos se obtienen de fuentes publicas disponibles en la web de ACB y se usan con fines educativos, tecnicos y de portfolio. Las marcas, nombres de equipos y logotipos pertenecen a sus respectivos propietarios. Si se despliega publicamente, conviene revisar el uso de logotipos y sustituirlos por monogramas propios si se quiere minimizar riesgo de marca.

## Estructura

```text
.
├── acb-web/              # Web Next.js + backend FastAPI
├── acb-dashboard/        # Dashboard Streamlit historico
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

## Licencia

No se ha definido una licencia open source explicita. Sin licencia, el codigo queda protegido por copyright por defecto.
