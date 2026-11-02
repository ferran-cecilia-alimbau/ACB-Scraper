"""Descarga histórica: todas las ediciones de una o varias competiciones.

Orden: ediciones de la más reciente a la más antigua. Por edición: calendario, equipos,
clasificación final, bracket, plantillas y zonas de tiro; después cada partido FINALIZED
(cabecera + box score siempre; play-by-play y tiros si `availableContent.playbyplay`;
rutas de overview/avanzadas si se pide `--detail full`). Al final, fichas de todos los
jugadores y técnicos vistos. Todo es reanudable: lo ya cacheado no se vuelve a pedir.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .client import AcbClient, ApiError

log = logging.getLogger("acb.backfill")

COMPETITION_NAMES = {1: "Liga Endesa", 2: "Copa del Rey", 3: "Supercopa Endesa", 10: "Minicopa Endesa"}


def edition_ids(client: AcbClient, competition_id: int) -> list[int]:
    data = client.competition_data(competition_id)
    for comp in data.get("competitions", []):
        if comp["id"] == competition_id:
            return sorted((e["id"] for e in comp["editions"]), reverse=True)
    return []


def backfill_edition(client: AcbClient, competition_id: int, edition_id: int, detail: str, licences: set[int]) -> dict:
    t0 = time.time()
    stats = {"matches": 0, "skipped": 0, "errors": 0}
    cal = client.season_calendar(competition_id, edition_id)
    teams = client.teams(competition_id, edition_id)
    try:
        client.standings(competition_id, edition_id)
    except ApiError as exc:
        log.warning("standings %s/%s: %s", competition_id, edition_id, exc)
    for fn in (client.bracket, client.league_zones):
        try:
            fn(competition_id, edition_id)
        except ApiError as exc:
            log.warning("%s %s/%s: %s", fn.__name__, competition_id, edition_id, exc)

    for team in teams.get("teams", []):
        club_id = (team.get("selected") or team.get("latest") or {}).get("clubId")
        if not club_id:
            continue
        try:
            roster = client.roster(club_id, competition_id, edition_id)
            for row in roster.get("players", []) or []:
                licences.add(row["player"]["id"])
            for row in roster.get("staff", []) or []:
                licences.add(row["coach"]["id"])
            client.team_stats(club_id, competition_id, edition_id)
        except ApiError as exc:
            log.warning("roster/team-stats club %s %s/%s: %s", club_id, competition_id, edition_id, exc)

    matches = [m for r in cal.get("rounds", []) for m in r.get("matches", [])]
    for m in matches:
        if m.get("matchStatus") != "FINALIZED":
            stats["skipped"] += 1
            continue
        mid = m["id"]
        try:
            header = client.match_header(mid)
            box = client.boxscores(mid)
            for t in box.get("teamBoxscores", []) or []:
                for p in (next((x for x in t["statsByPeriods"] if x["quarter"] == 0), {}).get("stats", {}).get("players") or []):
                    licences.add(p["player"]["id"])
            avail = header.get("availableContent") or {}
            if avail.get("playbyplay"):
                client.play_by_play(mid)
                client.match_shots(mid)
            if detail == "full":
                if avail.get("overview"):
                    client.lineup(mid)
                    client.lead_tracker(mid)
                    client.team_comparison(mid)
                if avail.get("advanced"):
                    client.match_advanced(mid)
                client.serie(mid)
            stats["matches"] += 1
        except ApiError as exc:
            stats["errors"] += 1
            log.error("partido %s: %s", mid, exc)
    log.info(
        "%s %s (edition %s): %d partidos, %d no jugados, %d errores, %.0fs, %d peticiones acumuladas",
        COMPETITION_NAMES.get(competition_id, competition_id), season_label(edition_id), edition_id,
        stats["matches"], stats["skipped"], stats["errors"], time.time() - t0, client.requests,
    )
    return stats


def backfill_people(client: AcbClient, licences: set[int]) -> None:
    done = 0
    for lic in sorted(licences):
        try:
            client.player_data(lic)
            client.player_stats(lic)
            client.player_career(lic)
        except ApiError as exc:
            log.warning("persona %s: %s", lic, exc)
        done += 1
        if done % 200 == 0:
            log.info("personas: %d/%d (%d peticiones)", done, len(licences), client.requests)


def season_label(edition_id: int) -> str:
    start = edition_id + 1935
    return f"{start}-{(start + 1) % 100:02d}"


def run(data_dir: Path, competitions: list[int], detail: str = "core", from_edition: int | None = None,
        to_edition: int | None = None, people: bool = True, contact: str = "") -> None:
    client = AcbClient(data_dir, contact=contact)
    licences: set[int] = set()
    for comp in competitions:
        eds = edition_ids(client, comp)
        if from_edition is not None:
            eds = [e for e in eds if e >= from_edition]
        if to_edition is not None:
            eds = [e for e in eds if e <= to_edition]
        log.info("%s: %d ediciones (%s … %s)", COMPETITION_NAMES.get(comp, comp), len(eds),
                 season_label(eds[0]) if eds else "-", season_label(eds[-1]) if eds else "-")
        for ed in eds:
            backfill_edition(client, comp, ed, detail, licences)
    if people:
        log.info("descargando %d fichas de jugadores y técnicos", len(licences))
        backfill_people(client, licences)
    log.info("fin: %d peticiones, %d aciertos de caché", client.requests, client.cache_hits)
