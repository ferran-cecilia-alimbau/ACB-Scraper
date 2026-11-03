"""Cliente HTTP de api2.acb.com con caché cruda, límite de ritmo y reintentos.

Toda respuesta se guarda tal cual (gzip) en <data>/raw/<ruta>/<params>.json.gz antes de parsear.
El fichero es la única fuente de verdad: no se modifica nunca, solo se sustituye entero cuando
se pide un refresco. Las escrituras son atómicas (tmp + rename), así que un corte a mitad de
descarga nunca deja un fichero corrupto; y un fichero ilegible se descarta y se vuelve a pedir.
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Iterator

import httpx

from . import __version__
from .apikey import load_key

log = logging.getLogger("acb.client")

BASE_URL = "https://api2.acb.com/api"
# Respuestas sin cuerpo útil: se cachean como marcador para no volver a pedirlas.
EMPTY_MARKERS = {204: {"_status": 204}, 404: {"_status": 404}}
MAX_ATTEMPTS = 8          # errores de red por petición (espera creciente hasta ~4 min en total)
MAX_5XX_ATTEMPTS = 3      # un 5xx que persiste tras 3 intentos es un fallo de ese elemento, no de la API
MAX_CONSECUTIVE_FAILURES = 25  # red caída o API fuera: abortar y dejar que systemd reintente más tarde


class ApiError(RuntimeError):
    """Fallo definitivo de un elemento concreto (400, 401 persistente, 403, o 5xx que no se recupera)."""

    def __init__(self, status: int, route: str, params: dict[str, Any], body: str):
        super().__init__(f"HTTP {status} en {route} {params}: {body[:200]}")
        self.status = status


class ApiUnavailable(RuntimeError):
    """Demasiados fallos seguidos de red o 5xx: la ejecución debe abortar y reintentarse más tarde."""


class StopRequested(RuntimeError):
    """Parada solicitada por señal (Ctrl-C, systemd stop)."""


class RawStore:
    """Un fichero por petición: <root>/<ruta>/<k=v&k=v>.json.gz."""

    def __init__(self, root: Path):
        self.root = root

    def path(self, route: str, params: dict[str, Any]) -> Path:
        key = "&".join(f"{k}={v}" for k, v in sorted(params.items())) or "_"
        return self.root / route.strip("/") / f"{key}.json.gz"

    def age_days(self, route: str, params: dict[str, Any]) -> float | None:
        p = self.path(route, params)
        if not p.exists():
            return None
        return (time.time() - p.stat().st_mtime) / 86400

    def get(self, route: str, params: dict[str, Any]) -> Any | None:
        p = self.path(route, params)
        if not p.exists():
            return None
        try:
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, EOFError, json.JSONDecodeError, gzip.BadGzipFile) as exc:
            log.warning("caché ilegible %s (%s); se volverá a pedir", p, exc)
            p.unlink(missing_ok=True)
            return None

    def put(self, route: str, params: dict[str, Any], payload: Any) -> None:
        p = self.path(route, params)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
        try:
            with gzip.open(tmp, "wt", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False)
            os.replace(tmp, p)
        finally:
            tmp.unlink(missing_ok=True)

    def iter_route(self, route: str) -> Iterator[tuple[str, Any]]:
        d = self.root / route.strip("/")
        if not d.exists():
            return
        for p in sorted(d.glob("*.json.gz")):
            try:
                with gzip.open(p, "rt", encoding="utf-8") as fh:
                    yield p.name[: -len(".json.gz")], json.load(fh)
            except (OSError, EOFError, json.JSONDecodeError, gzip.BadGzipFile) as exc:
                log.warning("saltando fichero ilegible %s: %s", p, exc)

    def count(self, route: str) -> int:
        d = self.root / route.strip("/")
        return sum(1 for _ in d.glob("*.json.gz")) if d.exists() else 0


class AcbClient:
    def __init__(self, data_dir: Path, min_interval: float = 1.0, contact: str = "", timeout: float = 60.0):
        self.data_dir = data_dir
        self.raw = RawStore(data_dir / "raw")
        self.min_interval = max(0.0, min_interval)
        self.key_path = data_dir / ".apikey.json"
        self.key = load_key(self.key_path)
        self._last = 0.0
        self._consecutive_failures = 0
        self.stop_requested = False
        self.requests = 0
        self.cache_hits = 0
        self.errors = 0
        ua = f"acb-scraper-v2/{__version__}" + (f" (+{contact})" if contact else "")
        self.http = httpx.Client(
            base_url=BASE_URL,
            timeout=timeout,
            headers={"Accept": "application/json", "Referer": "https://live.acb.com/", "User-Agent": ua},
        )

    def close(self) -> None:
        self.http.close()

    # ------------------------------------------------------------------ red
    def _wait(self) -> None:
        delta = time.monotonic() - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last = time.monotonic()

    def _check_stop(self) -> None:
        if self.stop_requested:
            raise StopRequested()

    def _request(self, route: str, params: dict[str, Any]) -> tuple[int, Any]:
        backoff = 2.0
        key_refreshed = False
        server_errors = 0
        for _ in range(MAX_ATTEMPTS):
            self._check_stop()
            self._wait()
            try:
                r = self.http.get(route, params=params, headers={"X-APIKEY": self.key})
            except httpx.HTTPError as exc:
                self._failure(f"red en {route} {params}: {exc}", backoff)
                backoff = min(backoff * 2, 120)
                continue
            self.requests += 1
            if r.status_code == 200:
                self._consecutive_failures = 0
                try:
                    return 200, r.json()
                except ValueError:
                    self._failure(f"JSON inválido en {route} {params}", backoff)
                    backoff = min(backoff * 2, 120)
                    continue
            if r.status_code in EMPTY_MARKERS:
                self._consecutive_failures = 0
                return r.status_code, EMPTY_MARKERS[r.status_code]
            if r.status_code == 401 and not key_refreshed:
                log.warning("401: redescubriendo la X-APIKEY")
                self.key = load_key(self.key_path, force=True)
                key_refreshed = True
                continue
            if r.status_code in (400, 401, 403):
                raise ApiError(r.status_code, route, params, r.text)
            if r.status_code == 429:
                backoff = max(backoff, 30.0)
            elif r.status_code >= 500:
                server_errors += 1
                if server_errors >= MAX_5XX_ATTEMPTS:
                    # La API responde (no está caída) pero este elemento falla siempre: p. ej. career de la licencia 20210392.
                    raise ApiError(r.status_code, route, params, r.text)
            self._failure(f"HTTP {r.status_code} en {route} {params}", backoff)
            backoff = min(backoff * 2, 120)
        raise ApiUnavailable(f"agotados {MAX_ATTEMPTS} intentos en {route} {params}")

    def _failure(self, msg: str, backoff: float) -> None:
        self._consecutive_failures += 1
        log.warning("%s; reintento en %.0fs (%d fallos seguidos)", msg, backoff, self._consecutive_failures)
        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            raise ApiUnavailable(f"{self._consecutive_failures} fallos consecutivos; abortando")
        for _ in range(int(backoff)):
            self._check_stop()
            time.sleep(1)

    def get(self, route: str, refresh: bool = False, max_age_days: float | None = None,
            tolerate_server_error: bool = False, **params: Any) -> Any:
        """JSON de la ruta. Usa la caché salvo que `refresh` sea True o el fichero supere `max_age_days`.

        204 y 404 devuelven un marcador {"_status": n} (también cacheado). Con `tolerate_server_error`,
        un 5xx persistente también se guarda como marcador {"_status": 5xx} en vez de lanzar ApiError:
        la API lo devuelve de forma estable para algunas personas (p. ej. `career` del staff), y así no se
        reintenta en cada ejecución hasta que el marcador caduque por `max_age_days`.
        """
        params = {k: v for k, v in params.items() if v is not None}
        if not refresh:
            age = self.raw.age_days(route, params)
            if age is not None and (max_age_days is None or age <= max_age_days):
                cached = self.raw.get(route, params)
                if cached is not None:
                    self.cache_hits += 1
                    return cached
        try:
            status, payload = self._request(route, params)
        except ApiError as exc:
            if tolerate_server_error and exc.status >= 500:
                log.info("HTTP %s estable en %s %s; se guarda marcador", exc.status, route, params)
                payload = {"_status": exc.status}
            else:
                raise
        self.raw.put(route, params, payload)
        return payload

    # ------------------------------------------------------------ rutas de partido (inmutables una vez FINALIZED)
    def match_header(self, match_id: int, **kw):
        return self.get("/matchdata/MatchHeader/match-header", matchId=match_id, **kw)

    def boxscores(self, match_id: int, **kw):
        return self.get("/matchdata/Result/boxscores", matchId=match_id, **kw)

    def play_by_play(self, match_id: int, **kw):
        return self.get("/matchdata/PlayByPlay/play-by-play", matchId=match_id, **kw)

    def match_shots(self, match_id: int, **kw):
        return self.get("/matchdata/MatchShots/match-shots", matchId=match_id, **kw)

    def lineup(self, match_id: int, **kw):
        return self.get("/matchdata/Overview/lineup", matchId=match_id, **kw)

    def lead_tracker(self, match_id: int, **kw):
        return self.get("/matchdata/Overview/lead-tracker", matchId=match_id, **kw)

    def team_comparison(self, match_id: int, **kw):
        return self.get("/matchdata/Overview/match-team-comparison", matchId=match_id, **kw)

    def match_leaders(self, match_id: int, **kw):
        return self.get("/matchdata/Overview/match-leaders", matchId=match_id, **kw)

    def match_advanced(self, match_id: int, **kw):
        return self.get("/matchdata/AdvancedStats/match-advanced-stats", matchId=match_id, **kw)

    def player_advanced(self, match_id: int, licence_id: int, **kw):
        return self.get("/matchdata/AdvancedStats/player-advanced-stats", matchId=match_id, playerLicense=licence_id, **kw)

    def serie(self, match_id: int, **kw):
        return self.get("/matchdata/Overview/serie", matchId=match_id, **kw)

    # ------------------------------------------------------------ rutas de temporada (cambian mientras la temporada está viva)
    def competition_data(self, *competition_ids: int, **kw):
        return self.get("/matchdata/Menu/competition-data", competitionIds=list(competition_ids), **kw)

    def season_calendar(self, competition_id: int, edition_id: int, **kw):
        return self.get("/seasondata/Calendar/season-calendar", competitionId=competition_id, editionId=edition_id, **kw)

    def standings(self, competition_id: int, edition_id: int, round_id: int | None = None, **kw):
        return self.get("/seasondata/Competition/standings", competitionId=competition_id, editionId=edition_id, roundId=round_id, **kw)

    def bracket(self, competition_id: int, edition_id: int, **kw):
        return self.get("/seasondata/Competition/bracket", competitionId=competition_id, editionId=edition_id, **kw)

    def teams(self, competition_id: int, edition_id: int, **kw):
        return self.get("/seasondata/TeamProfile/teams", competitionId=competition_id, editionId=edition_id, **kw)

    def club_data(self, club_id: int, **kw):
        return self.get("/seasondata/TeamProfile/club-data", clubId=club_id, **kw)

    def roster(self, club_id: int, competition_id: int, edition_id: int, **kw):
        return self.get("/seasondata/TeamProfile/current-roster", clubId=club_id, competitionId=competition_id, editionId=edition_id, **kw)

    def team_stats(self, club_id: int, competition_id: int, edition_id: int, **kw):
        return self.get("/seasondata/TeamProfile/team-stats", clubId=club_id, competitionId=competition_id, editionId=edition_id, **kw)

    def team_leaders(self, club_id: int, competition_id: int, edition_id: int, n: int = 5, **kw):
        return self.get("/seasondata/TeamProfile/team-leaders", clubId=club_id, numberOfPlayers=n, competitionId=competition_id, editionId=edition_id, **kw)

    def team_records(self, club_id: int, **kw):
        return self.get("/seasondata/TeamProfile/team-records", clubId=club_id, **kw)

    def league_zones(self, competition_id: int, edition_id: int, **kw):
        return self.get("/seasondata/ShotChart/league-zones", competitionId=competition_id, editionId=edition_id, **kw)

    # ------------------------------------------------------------ personas
    def player_data(self, licence_id: int, **kw):
        return self.get("/seasondata/PlayerProfile/player-data", playerLicenceId=licence_id, **kw)

    def player_stats(self, licence_id: int, **kw):
        return self.get("/seasondata/PlayerProfile/player-stats", playerLicenceId=licence_id, **kw)

    def player_career(self, licence_id: int, **kw):
        return self.get("/seasondata/PlayerProfile/career", playerLicenceId=licence_id, **kw)

    def player_matches(self, licence_id: int, edition_id: int, **kw):
        return self.get("/seasondata/PlayerProfile/matches", playerLicenceId=licence_id, editionId=edition_id, **kw)
