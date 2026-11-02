"""CLI: python -m acb_scraper backfill|build [opciones]."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import backfill, build


def main() -> None:
    ap = argparse.ArgumentParser(prog="acb_scraper")
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("backfill", help="descarga histórica reanudable")
    b.add_argument("--competitions", default="1", help="ids separados por comas: 1 Liga, 2 Copa, 3 Supercopa, 10 Minicopa")
    b.add_argument("--detail", choices=["core", "full"], default="core")
    b.add_argument("--from-edition", type=int)
    b.add_argument("--to-edition", type=int)
    b.add_argument("--no-people", action="store_true")
    b.add_argument("--contact", default="")

    e = sub.add_parser("build", help="genera tablas Parquet/CSV desde data/raw")
    e.add_argument("--out", type=Path, default=Path("data/output/v2"))

    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if args.cmd == "backfill":
        backfill.run(args.data_dir, [int(x) for x in args.competitions.split(",")], detail=args.detail,
                     from_edition=args.from_edition, to_edition=args.to_edition, people=not args.no_people, contact=args.contact)
    else:
        build.build(args.data_dir, args.out)


if __name__ == "__main__":
    main()
