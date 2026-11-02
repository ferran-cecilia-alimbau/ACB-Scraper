"""CLI: acb-scraper backfill | sync | status | build.

Códigos de salida: 0 éxito, 1 error de uso, 2 API no disponible (reintentar más tarde), 3 otra ejecución en curso.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
import logging.handlers
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, backfill
from .client import AcbClient, ApiUnavailable

log = logging.getLogger("acb")


def setup_logging(data_dir: Path, verbose: bool) -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    log_dir = data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(log_dir / "acb-scraper.log", maxBytes=10_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


class Lock:
    """Evita dos ejecuciones simultáneas sobre el mismo directorio de datos."""

    def __init__(self, data_dir: Path):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / ".lock"
        self.fh = None

    def __enter__(self):
        self.fh = open(self.path, "w")
        try:
            fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(f"otra ejecución de acb-scraper está en curso ({self.path}); salida 3") from None
        self.fh.write(str(os.getpid()))
        self.fh.flush()
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.fh, fcntl.LOCK_UN)
        self.fh.close()


def record_run(data_dir: Path, record: dict) -> None:
    with open(data_dir / "logs" / "runs.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def cmd_fetch(args: argparse.Namespace, mode: str) -> int:
    client = AcbClient(args.data_dir, min_interval=args.interval, contact=args.contact)

    def on_signal(signum, _frame):
        log.warning("señal %s recibida: terminando la petición en curso y parando", signal.Signals(signum).name)
        client.stop_requested = True

    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, on_signal)

    competitions = [int(x) for x in args.competitions.split(",")]
    started = datetime.now(timezone.utc)
    t0 = time.time()
    code = 0
    record = {"mode": mode, "started": started.isoformat(timespec="seconds"), "competitions": competitions,
              "detail": args.detail, "version": __version__}
    try:
        stats = backfill.run(client, competitions, mode=mode, detail=args.detail, from_edition=args.from_edition,
                             to_edition=args.to_edition, people=not args.no_people, people_max_age=args.people_max_age)
        record.update(stats.as_dict())
        record["stopped_early"] = client.stop_requested
    except ApiUnavailable as exc:
        record["error"] = str(exc)
        code = 2
    except Exception as exc:  # noqa: BLE001 - queremos dejar constancia de cualquier fallo
        log.exception("fallo inesperado")
        record["error"] = f"{type(exc).__name__}: {exc}"
        code = 1
    finally:
        client.close()
        record.update({"seconds": round(time.time() - t0), "requests": client.requests, "cache_hits": client.cache_hits,
                       "exit_code": code})
        record_run(args.data_dir, record)
        log.info("resumen: %s", json.dumps(record, ensure_ascii=False))
    return code


def cmd_status(args: argparse.Namespace) -> int:
    raw = args.data_dir / "raw"
    routes = {
        "partidos (box score)": "matchdata/Result/boxscores",
        "play-by-play": "matchdata/PlayByPlay/play-by-play",
        "tiros": "matchdata/MatchShots/match-shots",
        "calendarios": "seasondata/Calendar/season-calendar",
        "plantillas": "seasondata/TeamProfile/current-roster",
        "fichas de persona": "seasondata/PlayerProfile/player-data",
    }
    total = 0
    size = 0
    for p in raw.rglob("*.json.gz") if raw.exists() else []:
        total += 1
        size += p.stat().st_size
    print(f"directorio: {args.data_dir.resolve()}")
    print(f"ficheros crudos: {total}  ({size / 1e6:.0f} MB)")
    for label, route in routes.items():
        d = raw / route
        n = sum(1 for _ in d.glob("*.json.gz")) if d.exists() else 0
        print(f"  {label:<22} {n}")
    # Completitud: partidos FINALIZED según los calendarios descargados sin box score en disco.
    from .client import RawStore
    store = RawStore(raw)
    finalized, missing = 0, []
    for _stem, cal in store.iter_route("/seasondata/Calendar/season-calendar"):
        for r in cal.get("rounds") or []:
            for m in r.get("matches") or []:
                if m.get("matchStatus") == "FINALIZED":
                    finalized += 1
                    if not store.path("/matchdata/Result/boxscores", {"matchId": m["id"]}).exists():
                        missing.append(m["id"])
    print(f"partidos finalizados en los calendarios: {finalized}; sin descargar: {len(missing)}"
          + (f" (p. ej. {missing[:5]})" if missing else ""))
    runs = args.data_dir / "logs" / "runs.jsonl"
    if runs.exists():
        lines = runs.read_text(encoding="utf-8").strip().splitlines()
        print(f"ejecuciones registradas: {len(lines)}")
        print("última:", lines[-1])
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="acb-scraper", description="Descarga cruda (JSON) de la API de la ACB.")
    ap.add_argument("--data-dir", type=Path, default=Path(os.environ.get("ACB_DATA_DIR", "data")),
                    help="directorio de datos (o variable ACB_DATA_DIR); por defecto ./data")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_fetch_args(p):
        p.add_argument("--competitions", default="1,2,3", help="ids separados por comas: 1 Liga, 2 Copa, 3 Supercopa, 10 Minicopa")
        p.add_argument("--detail", choices=["core", "full"], default="core",
                       help="core: cabecera, box score, play-by-play, tiros; full: añade quintetos, evolución, comparativa, líderes, avanzadas, eliminatoria y líderes de club")
        p.add_argument("--from-edition", type=int, help="edición mínima (91 = 2026-27, 48 = 1983-84)")
        p.add_argument("--to-edition", type=int, help="edición máxima")
        p.add_argument("--no-people", action="store_true", help="no descargar fichas de jugadores y técnicos")
        p.add_argument("--people-max-age", type=float, default=30.0, help="días tras los que se refresca una ficha")
        p.add_argument("--interval", type=float, default=1.0, help="segundos mínimos entre peticiones")
        p.add_argument("--contact", default=os.environ.get("ACB_CONTACT", ""), help="contacto para el User-Agent (o ACB_CONTACT)")

    b = sub.add_parser("backfill", help="descarga histórica de todas las ediciones (reanudable)")
    add_fetch_args(b)
    s = sub.add_parser("sync", help="actualización incremental de la temporada en curso")
    add_fetch_args(s)
    sub.add_parser("status", help="resumen de lo descargado")
    e = sub.add_parser("build", help="tablas Parquet/CSV desde data/raw (requiere pyarrow)")
    e.add_argument("--out", type=Path, default=None, help="por defecto <data-dir>/output/v2")

    args = ap.parse_args(argv)
    setup_logging(args.data_dir, args.verbose)
    if args.cmd == "status":
        return cmd_status(args)
    with Lock(args.data_dir):
        if args.cmd in ("backfill", "sync"):
            return cmd_fetch(args, args.cmd)
        from . import build  # pyarrow solo aquí
        build.build(args.data_dir, args.out or args.data_dir / "output" / "v2")
        return 0


def entrypoint() -> int:
    try:
        return main()
    except BrokenPipeError:  # p. ej. `acb-scraper status | head`
        return 0


if __name__ == "__main__":
    sys.exit(entrypoint())
