"""Cliente HTTP de api2.acb.com con caché cruda, límite de ritmo y reintentos.

Toda respuesta se guarda tal cual (gzip) en data/raw/<ruta>/<params>.json.gz antes de parsear,
de modo que una ejecución interrumpida se reanuda sin repetir peticiones.
"""

from __future__ import annotations

import gzip
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from . import __version__
from .apikey import load_key

log = logging.getLogger("acb.client")

BASE_URL = "https://api2.acb.com/api"
# Marcadores que se guardan en caché para respuestas sin cuerpo útil.
EMPTY_MARKERS = {204: {"_status": 204}, 404: {"_status": 404}}


class ApiError(RuntimeError):
    def __init__(self, status: int, route: str, params: dict[str, Any], body: str):
        super().__init__(f"{status} en {route} {params}: {body[:200]}")
        self.status = status


class RawStore:
    def __init__(self, root: Path):
        self.root = root

    def path(self, route: str, params: dict[str, Any]) -> Path:
        key = "&".join(f"{k}={v}" for k, v in sorted(params.items())) or "_"
        return self.root / route.strip("/") / f"{key}.json.gz"

    def get(self, route: str, params: dict[str, Any]) -> Any | None:
        p = self.path(route, params)
        if not p.exists():
            return None
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            return json.load(fh)

    def put(self, route: str, params: dict[str, Any], payload: Any) -> None:
        p = self.path(route, params)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        tmp.replace(p)

    def iter_route(self, route: str):
        d = self.root / route.strip("/")
        if not d.exists():
            return
        for p in sorted(d.glob("*.json.gz")):
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                yield p.stem.replace(".json", ""), json.load(fh)


class AcbClient:
    def __init__(self, data_dir: Path, min_interval: float = 1.0, contact: str = "", timeout: float = 60.0):
        self.data_dir = data_dir
        self.raw = RawStore(data_dir / "raw")
        self.min_interval = min_interval
        self.key_path = data_dir / ".apikey.json"
        self.key = load_key(self.key_path)
        self._last = 0.0
        self.requests = 0
        self.cache_hits = 0
        ua = f"acb-scraper-v2/{__version__}" + (f" (+{contact})" if contact else "")
        self.http = httpx.Client(
            base_url=BASE_URL,
            timeout=timeout,
            headers={"Accept": "application/json", "Referer": "https://live.acb.com/", "User-Agent": ua},
        )

    # ------------------------------------------------------------------ red
    def _wait(self) -> None:
        delta = time.monotonic() - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last = time.monotonic()

    def _request(self, route: str, params: dict[str, Any]) -> tuple[int, Any]:
        backoff = 2.0
        key_refreshed = False
        for attempt in range(7):
            self._wait()
            try:
                r = self.http.get(route, params=params, headers={"X-APIKEY": self.key})
            except httpx.HTTPError as exc:
                log.warning("red: %s (%s), reintento en %.0fs", route, exc, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)
                continue
            self.requests += 1
            if r.status_code == 200:
                return 200, r.json()
            if r.status_code in EMPTY_MARKERS:
                return r.status_code, EMPTY_MARKERS[r.status_code]
            if r.status_code == 401 and not key_refreshed:
                log.warning("401: redescubriendo la X-APIKEY")
                self.key = load_key(self.key_path, force=True)
                key_refreshed = True
                continue
            if r.status_code in (400, 401):
                raise ApiError(r.status_code, route, params, r.text)
            log.warning("HTTP %s en %s %s, reintento en %.0fs", r.status_code, route, params, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
        raise ApiError(599, route, params, "agotados los reintentos")

    def get(self, route: str, **params: Any) -> Any:
        """Devuelve el JSON de la ruta, desde caché si ya se pidió. 204/404 devuelven un marcador."""
        params = {k: v for k, v in params.items() if v is not None}
        cached = self.raw.get(route, params)
        if cached is not None:
            self.cache_hits += 1
            return cached
        status, payload = self._request(route, params)
        self.raw.put(route, params, payload)
        return payload

    # ------------------------------------------------------------ rutas
    def match_header(self, match_id: int):
        return self.get("/matchdata/MatchHeader/match-header", matchId=match_id)

    def boxscores(self, match_id: int):
        return self.get("/matchdata/Result/boxscores", matchId=match_id)

    def play_by_play(self, match_id: int):
        return self.get("/matchdata/PlayByPlay/play-by-play", matchId=match_id)

    def match_shots(self, match_id: int):
        return self.get("/matchdata/MatchShots/match-shots", matchId=match_id)

    def lineup(self, match_id: int):
        return self.get("/matchdata/Overview/lineup", matchId=match_id)

    def lead_tracker(self, match_id: int):
        return self.get("/matchdata/Overview/lead-tracker", matchId=match_id)

    def team_comparison(self, match_id: int):
        return self.get("/matchdata/Overview/match-team-comparison", matchId=match_id)

    def match_advanced(self, match_id: int):
        return self.get("/matchdata/AdvancedStats/match-advanced-stats", matchId=match_id)

    def serie(self, match_id: int):
        return self.get("/matchdata/Overview/serie", matchId=match_id)

    def competition_data(self, *competition_ids: int):
        return self.get("/matchdata/Menu/competition-data", competitionIds=list(competition_ids))

    def season_calendar(self, competition_id: int, edition_id: int):
        return self.get("/seasondata/Calendar/season-calendar", competitionId=competition_id, editionId=edition_id)

    def standings(self, competition_id: int, edition_id: int, round_id: int | None = None):
        return self.get("/seasondata/Competition/standings", competitionId=competition_id, editionId=edition_id, roundId=round_id)

    def bracket(self, competition_id: int, edition_id: int):
        return self.get("/seasondata/Competition/bracket", competitionId=competition_id, editionId=edition_id)

    def teams(self, competition_id: int, edition_id: int):
        return self.get("/seasondata/TeamProfile/teams", competitionId=competition_id, editionId=edition_id)

    def club_data(self, club_id: int):
        return self.get("/seasondata/TeamProfile/club-data", clubId=club_id)

    def roster(self, club_id: int, competition_id: int, edition_id: int):
        return self.get("/seasondata/TeamProfile/current-roster", clubId=club_id, competitionId=competition_id, editionId=edition_id)

    def team_stats(self, club_id: int, competition_id: int, edition_id: int):
        return self.get("/seasondata/TeamProfile/team-stats", clubId=club_id, competitionId=competition_id, editionId=edition_id)

    def team_records(self, club_id: int):
        return self.get("/seasondata/TeamProfile/team-records", clubId=club_id)

    def player_data(self, licence_id: int):
        return self.get("/seasondata/PlayerProfile/player-data", playerLicenceId=licence_id)

    def player_stats(self, licence_id: int):
        return self.get("/seasondata/PlayerProfile/player-stats", playerLicenceId=licence_id)

    def player_career(self, licence_id: int):
        return self.get("/seasondata/PlayerProfile/career", playerLicenceId=licence_id)

    def league_zones(self, competition_id: int, edition_id: int):
        return self.get("/seasondata/ShotChart/league-zones", competitionId=competition_id, editionId=edition_id)
