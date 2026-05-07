# Automatización del scraping ACB

> Estado: implementado en `scripts/update_all.py`, `Dockerfile`, `docker-compose.yml` y `deploy/systemd/`.

## Uso local

```bash
python scripts/update_all.py --dry-run
python scripts/update_all.py --verify-pbp
python scripts/update_all.py --skip-pbp
python scripts/update_all.py --only 104459 104460
```

El orquestador:

1. Descubre IDs desde el calendario ACB.
2. Compara contra `data/input/match_ids.json`.
3. Crea backup rotativo si va a modificar datos.
4. Ejecuta `main.py --only <ids>` solo para partidos sin estadísticas.
5. Ejecuta `scripts/batch_play_by_play_v2.py --only <ids>` solo para PBP faltante.
6. Verifica integridad de estadísticas y PBP.
7. Escribe resumen en `data/run_state/last_run.json`.

## Docker

```bash
docker compose build
docker compose run --rm scraper python scripts/update_all.py --dry-run
docker compose run --rm scraper python scripts/update_all.py --verify-pbp
docker compose run --rm scraper pytest
```

La imagen incluye Python 3.12, Chromium y Chromedriver. `./data` se monta como volumen persistente en `/app/data`.

## systemd

Los units están en `deploy/systemd/`. Por defecto asumen el repositorio en `/opt/acb-scraper` y ejecutan cada día a las `03:30`.

```bash
sudo cp deploy/systemd/acb-scraper.service /etc/systemd/system/
sudo cp deploy/systemd/acb-scraper.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now acb-scraper.timer
journalctl -u acb-scraper.service -n 200
```

El service usa `flock` para evitar ejecuciones solapadas.

## Datos generados

- `data/backups/`: backups rotativos de `input`, `output` y `play_by_play`.
- `data/logs/update_all_*.log`: logs de ejecución del orquestador.
- `data/run_state/last_run.json`: último resumen estructurado.

Estos directorios están ignorados por Git.
