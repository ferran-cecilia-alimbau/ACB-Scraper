"""Orquestador idempotente para actualizar datos ACB.

El script coordina descubrimiento de IDs, scraping de estadisticas, scraping
PBP, backups y verificaciones. Esta pensado para ejecutarse desde Docker/systemd
en el servidor 24/7.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from get_match_ids import DEFAULT_CALENDAR_URL, get_match_ids


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DATA_DIR = REPO_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
PBP_DIR = DATA_DIR / "play_by_play"
BACKUP_DIR = DATA_DIR / "backups"
RUN_STATE_DIR = DATA_DIR / "run_state"
LOG_DIR = DATA_DIR / "logs"

MATCH_IDS_PATH = INPUT_DIR / "match_ids.json"
GAME_INFO_PATH = OUTPUT_DIR / "estadisticas_partido.csv"
PLAYER_STATS_PATH = OUTPUT_DIR / "estadisticas_todos_partidos.csv"
TEAM_STATS_PATH = OUTPUT_DIR / "estadisticas_equipos_por_partido.csv"
LAST_RUN_PATH = RUN_STATE_DIR / "last_run.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Actualiza todo el dataset ACB.")
    parser.add_argument("--calendar-url", default=DEFAULT_CALENDAR_URL)
    parser.add_argument("--skip-pbp", action="store_true", help="No ejecutar scraping PBP.")
    parser.add_argument("--verify-pbp", action="store_true", help="Ejecutar tambien el verificador PBP existente.")
    parser.add_argument("--pbp-workers", type=int, default=1, help="Navegadores concurrentes para PBP.")
    parser.add_argument("--force-pbp", action="store_true", help="Re-scrapear PBP dentro del alcance seleccionado.")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar acciones sin modificar datos.")
    parser.add_argument("--only", nargs="+", type=int, metavar="ID", help="Limitar la ejecucion a estos IDs.")
    parser.add_argument("--backup-retention", type=int, default=14, help="Backups rotativos a conservar (>=1).")
    parser.add_argument("--python", default=sys.executable, help="Interprete Python para subprocess.")
    parser.add_argument(
        "--subprocess-timeout",
        type=int,
        default=10800,
        help="Timeout en segundos por subproceso (stats/PBP). 0 desactiva.",
    )
    args = parser.parse_args()
    if args.backup_retention < 1:
        parser.error("--backup-retention debe ser >= 1")
    if args.subprocess_timeout < 0:
        parser.error("--subprocess-timeout no puede ser negativo")
    return args


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def open_log_file(dry_run: bool):
    if dry_run:
        return None
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return open(LOG_DIR / f"update_all_{timestamp()}.log", "a", encoding="utf-8")


def log(message: str, log_file=None) -> None:
    print(message, flush=True)
    if log_file:
        log_file.write(message + "\n")
        log_file.flush()


def read_match_ids(path: Path = MATCH_IDS_PATH) -> list[int]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return sorted({int(value) for value in data.get("match_ids", [])})


def write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4, ensure_ascii=False)
        handle.write("\n")
    os.replace(temp_path, path)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def int_or_none(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def read_csv_ids(path: Path, column: str) -> set[int]:
    ids: set[int] = set()
    for row in read_csv_rows(path):
        value = int_or_none(row.get(column))
        if value is not None:
            ids.add(value)
    return ids


def read_pbp_ids(pbp_dir: Path = PBP_DIR) -> set[int]:
    ids: set[int] = set()
    if not pbp_dir.exists():
        return ids
    for path in pbp_dir.glob("play_by_play_*.csv"):
        try:
            ids.add(int(path.stem.replace("play_by_play_", "")))
        except ValueError:
            continue
    return ids


def backup_data(retention: int, log_file=None) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / timestamp()
    backup_path.mkdir()

    for name in ("input", "output", "play_by_play"):
        source = DATA_DIR / name
        if source.exists():
            shutil.copytree(
                source,
                backup_path / name,
                ignore=shutil.ignore_patterns("*.tmp"),
            )

    backups = sorted(path for path in BACKUP_DIR.iterdir() if path.is_dir())
    for old_backup in backups[:-retention]:
        shutil.rmtree(old_backup)

    log(f"[BACKUP] Creado {backup_path}", log_file)
    return str(backup_path.relative_to(REPO_ROOT))


def format_cmd(command: Iterable[Any]) -> str:
    return " ".join(str(part) for part in command)


def run_command(
    command: list[Any],
    dry_run: bool,
    log_file=None,
    timeout: int | None = None,
) -> dict[str, Any]:
    command_text = format_cmd(command)
    if dry_run:
        log(f"[DRY-RUN] {command_text}", log_file)
        return {"command": command_text, "returncode": 0, "dry_run": True}

    log(f"[RUN] {command_text}", log_file)
    started = time.perf_counter()
    process = subprocess.Popen(
        [str(part) for part in command],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None
    timed_out = False
    deadline = (time.monotonic() + timeout) if timeout else None
    try:
        for line in process.stdout:
            log(line.rstrip("\n"), log_file)
            if deadline is not None and time.monotonic() > deadline:
                timed_out = True
                log(f"[TIMEOUT] superado timeout={timeout}s :: {command_text}", log_file)
                process.kill()
                break
        returncode = process.wait()
    except KeyboardInterrupt:
        process.kill()
        raise
    elapsed = round(time.perf_counter() - started, 2)
    log(f"[DONE] rc={returncode} elapsed={elapsed}s :: {command_text}", log_file)
    return {
        "command": command_text,
        "returncode": returncode,
        "elapsed_seconds": elapsed,
        "timed_out": timed_out,
    }


def verify_stats(target_ids: Iterable[int] | None = None) -> dict[str, Any]:
    games = read_csv_rows(GAME_INFO_PATH)
    players = read_csv_rows(PLAYER_STATS_PATH)
    teams = read_csv_rows(TEAM_STATS_PATH)

    if not games:
        return {"ok": False, "error": f"No hay datos en {GAME_INFO_PATH}"}
    if not players:
        return {"ok": False, "error": f"No hay datos en {PLAYER_STATS_PATH}"}
    if not teams:
        return {"ok": False, "error": f"No hay datos en {TEAM_STATS_PATH}"}

    game_ids = {value for value in (int_or_none(row.get("id_partido")) for row in games) if value is not None}
    target = set(target_ids) if target_ids is not None else game_ids

    player_counts: dict[int, int] = {}
    for row in players:
        game_id = int_or_none(row.get("id_partido"))
        if game_id is not None:
            player_counts[game_id] = player_counts.get(game_id, 0) + 1

    team_rows_by_game: dict[int, list[dict[str, str]]] = {}
    for row in teams:
        game_id = int_or_none(row.get("id_partido"))
        if game_id is not None:
            team_rows_by_game.setdefault(game_id, []).append(row)

    missing_games = sorted(target - game_ids)
    missing_players = sorted(game_id for game_id in target if player_counts.get(game_id, 0) == 0)
    low_player_counts = {
        str(game_id): count
        for game_id, count in sorted(player_counts.items())
        if game_id in target and count < 10
    }
    bad_team_counts = {
        str(game_id): len(rows)
        for game_id, rows in sorted(team_rows_by_game.items())
        if game_id in target and len(rows) != 2
    }
    missing_teams = sorted(game_id for game_id in target if game_id not in team_rows_by_game)

    score_mismatches = []
    for game in games:
        game_id = int_or_none(game.get("id_partido"))
        if game_id not in target:
            continue

        expected = [
            (game.get("local"), int_or_none(game.get("resultado_local"))),
            (game.get("visitante"), int_or_none(game.get("resultado_visitante"))),
        ]
        team_points = {
            row.get("equipo"): int_or_none(row.get("puntos"))
            for row in team_rows_by_game.get(game_id, [])
        }
        for team_name, expected_points in expected:
            if team_name not in team_points or team_points[team_name] != expected_points:
                score_mismatches.append({
                    "id_partido": game_id,
                    "equipo": team_name,
                    "esperado": expected_points,
                    "equipo_csv": team_points.get(team_name),
                })

    ok = not any([missing_games, missing_players, missing_teams, low_player_counts, bad_team_counts, score_mismatches])
    return {
        "ok": ok,
        "target_games": len(target),
        "games_rows": len(games),
        "player_rows": len(players),
        "team_rows": len(teams),
        "missing_games": missing_games,
        "missing_players": missing_players,
        "missing_teams": missing_teams,
        "low_player_counts": low_player_counts,
        "bad_team_counts": bad_team_counts,
        "score_mismatches": score_mismatches[:20],
    }


def score_lookup() -> dict[int, tuple[int, int]]:
    lookup: dict[int, tuple[int, int]] = {}
    for row in read_csv_rows(GAME_INFO_PATH):
        game_id = int_or_none(row.get("id_partido"))
        local = int_or_none(row.get("resultado_local"))
        visitor = int_or_none(row.get("resultado_visitante"))
        if game_id is not None and local is not None and visitor is not None:
            lookup[game_id] = (local, visitor)
    return lookup


def verify_pbp_files(target_ids: Iterable[int], min_events: int = 200, min_lineups: int = 5) -> dict[str, Any]:
    target = sorted(set(target_ids))
    expected_scores = score_lookup()
    missing: list[int] = []
    incomplete: list[dict[str, Any]] = []
    score_mismatches: list[dict[str, Any]] = []
    ok_count = 0

    for game_id in target:
        path = PBP_DIR / f"play_by_play_{game_id}.csv"
        if not path.exists():
            missing.append(game_id)
            continue

        rows = read_csv_rows(path)
        lineups = sum(
            1
            for row in rows
            if "quinteto" in (row.get("accion") or "").lower()
            or "cinco inicial" in (row.get("accion") or "").lower()
        )
        if len(rows) < min_events or lineups < min_lineups:
            incomplete.append({"id_partido": game_id, "events": len(rows), "lineups": lineups})

        last_local, last_visitor = 0, 0
        for row in rows:
            local = int_or_none(row.get("marcador_local"))
            visitor = int_or_none(row.get("marcador_visitante"))
            if local is None or visitor is None:
                continue
            last_local = max(last_local, local)
            last_visitor = max(last_visitor, visitor)

        expected = expected_scores.get(game_id)
        if expected and (last_local, last_visitor) != expected:
            score_mismatches.append({
                "id_partido": game_id,
                "pbp": f"{last_local}-{last_visitor}",
                "esperado": f"{expected[0]}-{expected[1]}",
            })
            continue

        ok_count += 1

    return {
        "ok": not any([missing, incomplete, score_mismatches]),
        "target_games": len(target),
        "ok_count": ok_count,
        "missing": missing,
        "incomplete": incomplete[:20],
        "score_mismatches": score_mismatches[:20],
    }


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    log_file = open_log_file(args.dry_run)
    state: dict[str, Any] = {
        "started_at": iso_now(),
        "dry_run": args.dry_run,
        "args": vars(args),
        "commands": [],
    }
    exit_code = 0

    try:
        previous_ids = read_match_ids()
        selected_ids = sorted(set(args.only or []))

        if selected_ids:
            discovered_ids = selected_ids
            updated_ids = sorted(set(previous_ids) | set(selected_ids))
            log(f"[IDS] Modo --only con {len(selected_ids)} IDs", log_file)
        else:
            log(f"[IDS] Descubriendo partidos desde {args.calendar_url}", log_file)
            discovered_ids = get_match_ids(args.calendar_url)
            if not discovered_ids:
                raise RuntimeError("No se descubrieron IDs; se aborta sin modificar match_ids.json")
            updated_ids = sorted(set(previous_ids) | set(discovered_ids))

        new_ids = sorted(set(updated_ids) - set(previous_ids))
        removed_from_calendar = sorted(set(previous_ids) - set(discovered_ids)) if not selected_ids else []

        stats_existing_before = read_csv_ids(GAME_INFO_PATH, "id_partido")
        scope_ids = set(selected_ids or updated_ids)
        stats_missing = sorted(scope_ids - stats_existing_before)
        pbp_existing_before = read_pbp_ids()
        pbp_missing_before = sorted((stats_existing_before & scope_ids) - pbp_existing_before)

        will_change = bool(
            updated_ids != previous_ids
            or stats_missing
            or (not args.skip_pbp and (pbp_missing_before or args.force_pbp))
        )

        state.update({
            "previous_match_ids": len(previous_ids),
            "discovered_match_ids": len(discovered_ids),
            "current_match_ids": len(updated_ids),
            "new_ids": new_ids,
            "removed_from_calendar": removed_from_calendar,
            "stats_missing_before": stats_missing,
            "pbp_missing_before": pbp_missing_before,
            "will_change": will_change,
        })

        log(
            "[PLAN] "
            f"new_ids={len(new_ids)} stats_missing={len(stats_missing)} "
            f"pbp_missing={len(pbp_missing_before)} will_change={will_change}",
            log_file,
        )

        subprocess_timeout = args.subprocess_timeout or None

        # Si los CSV estan vacios y no hay filtro --only, dejamos que main.py
        # procese todo desde match_ids.json sin pasar cientos de IDs por argv.
        cold_start = not stats_existing_before and not selected_ids
        stats_command = [args.python, "main.py"]
        if not cold_start:
            stats_command += ["--only", *stats_missing]

        if args.dry_run:
            if updated_ids != previous_ids:
                log(f"[DRY-RUN] Actualizaria {MATCH_IDS_PATH}", log_file)
            if will_change:
                log("[DRY-RUN] Crearia backup rotativo antes de modificar datos", log_file)
            if stats_missing:
                run_command(stats_command, True, log_file)
            if not args.skip_pbp:
                pbp_scope = scope_ids & (stats_existing_before | set(stats_missing))
                pbp_targets = sorted(pbp_scope if args.force_pbp else pbp_scope - pbp_existing_before)
                if pbp_targets:
                    run_command(
                        [args.python, "scripts/batch_play_by_play_v2.py", "--workers", args.pbp_workers, "--only", *pbp_targets],
                        True,
                        log_file,
                    )
            log("[DRY-RUN] No se ha modificado ningun fichero", log_file)
            return 0

        if will_change:
            state["backup_path"] = backup_data(args.backup_retention, log_file)

        if updated_ids != previous_ids:
            write_json_atomic(MATCH_IDS_PATH, {"match_ids": updated_ids})
            log(f"[IDS] match_ids.json actualizado: {len(previous_ids)} -> {len(updated_ids)}", log_file)

        if stats_missing:
            result = run_command(stats_command, False, log_file, timeout=subprocess_timeout)
            state["commands"].append(result)
            if result["returncode"] != 0:
                exit_code = 1
        else:
            log("[STATS] No hay estadisticas nuevas que scrapear", log_file)

        stats_existing_after = read_csv_ids(GAME_INFO_PATH, "id_partido")
        pbp_targets: list[int] = []
        if args.skip_pbp:
            log("[PBP] Saltado por --skip-pbp", log_file)
        elif exit_code == 0:
            pbp_scope = stats_existing_after & scope_ids
            pbp_existing_after = read_pbp_ids()
            pbp_targets = sorted(pbp_scope if args.force_pbp else pbp_scope - pbp_existing_after)
            if pbp_targets:
                command: list[Any] = [
                    args.python,
                    "scripts/batch_play_by_play_v2.py",
                    "--workers",
                    args.pbp_workers,
                    "--only",
                    *pbp_targets,
                ]
                if args.force_pbp:
                    command.insert(2, "--force")
                result = run_command(command, False, log_file, timeout=subprocess_timeout)
                state["commands"].append(result)
                if result["returncode"] != 0:
                    exit_code = 1
            else:
                log("[PBP] No hay PBP pendiente que scrapear", log_file)
        else:
            log("[PBP] Saltado porque el paso de stats fallo", log_file)

        verify_target_ids = sorted(stats_existing_after)
        # Verificacion global (informativa) y verificacion del alcance de la
        # corrida (decide exit_code: no queremos que problemas heredados de
        # corridas anteriores hagan fallar el cron actual).
        run_scope_ids = sorted(scope_ids & stats_existing_after) if not selected_ids else sorted(scope_ids)
        stats_verify = verify_stats(verify_target_ids)
        stats_verify_scope = verify_stats(run_scope_ids) if run_scope_ids else {"ok": True, "target_games": 0}
        state["stats_verify"] = stats_verify
        state["stats_verify_scope"] = stats_verify_scope
        log(f"[VERIFY][STATS][global] ok={stats_verify.get('ok')} target={stats_verify.get('target_games')}", log_file)
        log(f"[VERIFY][STATS][scope] ok={stats_verify_scope.get('ok')} target={stats_verify_scope.get('target_games')}", log_file)
        if not stats_verify.get("ok"):
            log(f"[VERIFY][STATS][global] Detalle: {json.dumps(stats_verify, ensure_ascii=False)}", log_file)
        if not stats_verify_scope.get("ok"):
            log(f"[VERIFY][STATS][scope] Detalle: {json.dumps(stats_verify_scope, ensure_ascii=False)}", log_file)
            exit_code = 1

        if args.skip_pbp:
            state["pbp_verify"] = {"skipped": True}
            state["pbp_verify_scope"] = {"skipped": True}
        else:
            pbp_verify = verify_pbp_files(verify_target_ids)
            pbp_verify_scope = verify_pbp_files(run_scope_ids) if run_scope_ids else {"ok": True, "target_games": 0}
            state["pbp_verify"] = pbp_verify
            state["pbp_verify_scope"] = pbp_verify_scope
            log(f"[VERIFY][PBP][global] ok={pbp_verify.get('ok')} target={pbp_verify.get('target_games')}", log_file)
            log(f"[VERIFY][PBP][scope] ok={pbp_verify_scope.get('ok')} target={pbp_verify_scope.get('target_games')}", log_file)
            if not pbp_verify.get("ok"):
                log(f"[VERIFY][PBP][global] Detalle: {json.dumps(pbp_verify, ensure_ascii=False)}", log_file)
            if not pbp_verify_scope.get("ok"):
                log(f"[VERIFY][PBP][scope] Detalle: {json.dumps(pbp_verify_scope, ensure_ascii=False)}", log_file)
                exit_code = 1

            if args.verify_pbp and verify_target_ids:
                result = run_command(
                    [
                        args.python,
                        "scripts/batch_play_by_play_v2.py",
                        "--verify",
                        "--only",
                        *verify_target_ids,
                    ],
                    False,
                    log_file,
                    timeout=subprocess_timeout,
                )
                state["commands"].append(result)
                if result["returncode"] != 0:
                    exit_code = 1

        state["pbp_targets"] = pbp_targets
        return exit_code

    except Exception as exc:
        exit_code = 1
        state["error"] = str(exc)
        log(f"[ERROR] {exc}", log_file)
        return exit_code
    finally:
        state["finished_at"] = iso_now()
        state["elapsed_seconds"] = round(time.perf_counter() - started, 2)
        state["exit_code"] = exit_code
        if not args.dry_run:
            write_json_atomic(LAST_RUN_PATH, state)
            log(f"[STATE] Escrito {LAST_RUN_PATH}", log_file)
        if log_file:
            log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
