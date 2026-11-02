# ACB Scraper

Descarga **cruda** (JSON) de la API que alimenta acb.com y live.acb.com:
partidos (cabecera, box score, play-by-play, tiros con coordenadas), calendarios,
clasificaciones, brackets, plantillas, estadísticas de equipo y fichas de jugadores
y técnicos de Liga Endesa, Copa del Rey y Supercopa, desde 1983-84.

Pensado para correr desatendido en un servidor doméstico y servir de dataset para
proyectos de ingeniería de datos. No transforma nada: cada respuesta se guarda tal
cual en `data/raw/`.

## Uso rápido

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
```

```bash
.venv/bin/acb-scraper backfill      # histórico completo (10-14 h a 1 req/s), reanudable
```

```bash
.venv/bin/acb-scraper sync          # temporada en curso; programar a diario
```

```bash
.venv/bin/acb-scraper status        # qué hay descargado y qué falta
```

Manual completo (opciones, garantías, formato de los datos, despliegue con
systemd): [`acb_scraper/README.md`](acb_scraper/README.md).

## Estructura

```text
acb_scraper/        paquete Python y su README
deploy/systemd/     servicio de backfill, servicio y timer de sync
docs/               plan de diseño y verificación contra la API real
tests/              tests offline sobre respuestas reales capturadas
```

## Tests

```bash
.venv/bin/pip install -e ".[dev]" && .venv/bin/pytest
```

## Proyecto no oficial

No está afiliado a la ACB. Usa una API pública no documentada, a una petición por
segundo, con fines personales y educativos. Las marcas y logotipos pertenecen a sus
propietarios. El aviso legal de acb.com reclama derechos sobre su base de datos: no
redistribuyas volcados masivos.
