"""Descarga histórica e incremental.

Reglas:
- Los datos de un partido FINALIZED son inmutables: se piden una vez y nunca se refrescan.
- Los datos de temporada (calendario, clasificación, bracket, equipos, plantillas, stats de equipo,
  zonas) cambian mientras la temporada está viva: se refrescan si tienen más de `snapshot_max_age`
  días (por defecto 1 día en la edición actual, 90 en las pasadas).
- Las fichas de personas se refrescan si tienen más de `people_max_age` días (30).
- Todo es reanudable y seguro ante cortes: cada respuesta se escribe atómicamente.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from .client import AcbClient, ApiError, ApiUnavailable, StopRequested

log = logging.getLogger("acb.backfill")

COMPETITION_NAMES = {1: "Liga Endesa", 2: "Copa del Rey", 3: "Supercopa Endesa", 10: "Minicopa Endesa"}


@dataclass
class RunStats:
    editions: int = 0
    matches_fetched: int = 0
    matches_cached: int = 0
    matches_pending: int = 0
    match_errors: int = 0
    people: int = 0
    people_partial: int = 0  # alguna ruta de la persona devuelve 5xx de forma estable (p. ej. career del staff)
    licences: set[int] = field(default_factory=set)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "licences"}
        d["licences"] = len(self.licences)
        return d


def season_label(edition_id: int) -> str:
    start = edition_id + 1935
    return f"{start}-{(start + 1) % 100:02d}"


def edition_ids(client: AcbClient, competition_id: int, max_age_days: float = 1.0) -> list[int]:
    """Ediciones de una competición, de la más reciente a la más antigua."""
    data = client.competition_data(competition_id, max_age_days=max_age_days)
    for comp in data.get("competitions") or []:
        if comp["id"] == competition_id:
            return sorted((e["id"] for e in comp["editions"]), reverse=True)
    return []


def _first_quarter_players(box: dict):
    for t in box.get("teamBoxscores") or []:
        q0 = next((x for x in t.get("statsByPeriods") or [] if x.get("quarter") == 0), None)
        for p in ((q0 or {}).get("stats") or {}).get("players") or []:
            yield p


def fetch_match(client: AcbClient, match_id: int, detail: str, stats: RunStats) -> None:
    """Descarga todo lo disponible de un partido ya finalizado."""
    already = client.raw.age_days("/matchdata/Result/boxscores", {"matchId": match_id}) is not None
    header = client.match_header(match_id)
    box = client.boxscores(match_id)
    for p in _first_quarter_players(box):
        pid = (p.get("player") or {}).get("id")
        if pid:
            stats.licences.add(pid)
    avail = header.get("availableContent") or {}
    if avail.get("playbyplay"):
        client.play_by_play(match_id)
        client.match_shots(match_id)
    if detail == "full":
        if avail.get("overview"):
            client.lineup(match_id)
            client.lead_tracker(match_id)
            client.team_comparison(match_id)
            client.match_leaders(match_id)
        if avail.get("advanced"):
            client.match_advanced(match_id)
        client.serie(match_id)
    if already:
        stats.matches_cached += 1
    else:
        stats.matches_fetched += 1


def sync_edition(client: AcbClient, competition_id: int, edition_id: int, detail: str, stats: RunStats,
                 snapshot_max_age: float) -> None:
    t0 = time.time()
    req0 = client.requests
    name = f"{COMPETITION_NAMES.get(competition_id, competition_id)} {season_label(edition_id)} (edición {edition_id})"
    kw = {"max_age_days": snapshot_max_age}

    cal = client.season_calendar(competition_id, edition_id, **kw)
    teams = client.teams(competition_id, edition_id, **kw)
    for fn in (client.standings, client.bracket, client.league_zones):
        try:
            fn(competition_id, edition_id, **kw)
        except ApiError as exc:
            log.warning("%s %s: %s", fn.__name__, name, exc)

    for team in teams.get("teams") or []:
        club_id = (team.get("selected") or team.get("latest") or {}).get("clubId")
        if not club_id:
            continue
        try:
            roster = client.roster(club_id, competition_id, edition_id, **kw)
            for row in roster.get("players") or []:
                stats.licences.add(row["player"]["id"])
            for row in roster.get("staff") or []:
                stats.licences.add(row["coach"]["id"])
            client.team_stats(club_id, competition_id, edition_id, **kw)
            if detail == "full":
                client.team_leaders(club_id, competition_id, edition_id, **kw)
        except ApiError as exc:
            log.warning("club %s en %s: %s", club_id, name, exc)

    pending = 0
    for r in cal.get("rounds") or []:
        for m in r.get("matches") or []:
            if m.get("matchStatus") != "FINALIZED":
                pending += 1
                continue
            try:
                fetch_match(client, m["id"], detail, stats)
            except ApiError as exc:
                stats.match_errors += 1
                log.error("partido %s: %s", m["id"], exc)
    stats.matches_pending += pending
    stats.editions += 1
    log.info("%s: %d partidos finalizados, %d pendientes, %d peticiones, %.0fs",
             name, sum(1 for r in cal.get("rounds") or [] for m in r.get("matches") or [] if m.get("matchStatus") == "FINALIZED"),
             pending, client.requests - req0, time.time() - t0)


def sync_people(client: AcbClient, licences: set[int], stats: RunStats, max_age_days: float) -> None:
    todo = sorted(licences)
    log.info("fichas de personas: %d licencias (refresco si > %.0f días)", len(todo), max_age_days)
    kw = {"max_age_days": max_age_days, "tolerate_server_error": True}
    for i, lic in enumerate(todo, 1):
        try:
            results = (client.player_data(lic, **kw), client.player_stats(lic, **kw), client.player_career(lic, **kw))
            stats.people += 1
            if any(isinstance(r, dict) and r.get("_status", 0) >= 500 for r in results):
                stats.people_partial += 1
        except ApiError as exc:
            log.warning("persona %s: %s", lic, exc)
        if i % 250 == 0:
            log.info("personas: %d/%d (%d peticiones)", i, len(todo), client.requests)


def run(client: AcbClient, competitions: list[int], mode: str = "backfill", detail: str = "core",
        from_edition: int | None = None, to_edition: int | None = None, people: bool = True,
        people_max_age: float = 30.0) -> RunStats:
    """mode='backfill': todas las ediciones. mode='sync': solo la edición más reciente de cada competición."""
    stats = RunStats()
    try:
        for comp in competitions:
            eds = edition_ids(client, comp)
            if not eds:
                log.warning("competición %s sin ediciones", comp)
                continue
            current = eds[0]
            if mode == "sync":
                eds = [current]
            if from_edition is not None:
                eds = [e for e in eds if e >= from_edition]
            if to_edition is not None:
                eds = [e for e in eds if e <= to_edition]
            log.info("%s: %d ediciones (%s … %s)", COMPETITION_NAMES.get(comp, comp), len(eds),
                     season_label(eds[0]) if eds else "-", season_label(eds[-1]) if eds else "-")
            for ed in eds:
                sync_edition(client, comp, ed, detail, stats, snapshot_max_age=1.0 if ed == current else 90.0)
        if people:
            sync_people(client, stats.licences, stats, people_max_age)
    except StopRequested:
        log.warning("parada solicitada; se puede reanudar más tarde sin perder nada")
    except ApiUnavailable as exc:
        log.error("API no disponible: %s", exc)
        raise
    return stats
