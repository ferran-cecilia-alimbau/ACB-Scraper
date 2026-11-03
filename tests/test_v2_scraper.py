"""Tests offline del scraper v2: caché cruda, cliente (transporte simulado), backfill y clave."""

import gzip
import json
import time
from pathlib import Path

import httpx
import pytest

from acb_scraper import apikey, backfill
from acb_scraper.client import AcbClient, ApiError, ApiUnavailable, RawStore, StopRequested

FIXTURES = Path(__file__).parent / "fixtures" / "api2"


def fixture(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- RawStore

def test_rawstore_roundtrip_and_params_order(tmp_path):
    store = RawStore(tmp_path)
    store.put("/x/y", {"b": 2, "a": 1}, {"ok": True})
    assert store.path("/x/y", {"a": 1, "b": 2}).name == "a=1&b=2.json.gz"
    assert store.get("/x/y", {"a": 1, "b": 2}) == {"ok": True}
    assert store.count("/x/y") == 1
    assert list(store.iter_route("/x/y")) == [("a=1&b=2", {"ok": True})]


def test_rawstore_corrupt_file_is_discarded(tmp_path):
    store = RawStore(tmp_path)
    p = store.path("/r", {"id": 1})
    p.parent.mkdir(parents=True)
    p.write_bytes(b"not gzip")
    assert store.get("/r", {"id": 1}) is None
    assert not p.exists()


def test_rawstore_write_is_atomic_no_tmp_left(tmp_path):
    store = RawStore(tmp_path)
    store.put("/r", {"id": 1}, {"a": 1})
    assert [p.name for p in (tmp_path / "r").iterdir()] == ["id=1.json.gz"]


# --------------------------------------------------------------------------- cliente con transporte simulado

def make_client(tmp_path, handler, **kw):
    (tmp_path / ".apikey.json").write_text(json.dumps({"key": "test-key", "fetched_at": time.time()}))
    c = AcbClient(tmp_path, min_interval=0.0, **kw)
    c.http = httpx.Client(base_url="https://api2.acb.com/api", transport=httpx.MockTransport(handler),
                          headers={"Accept": "application/json"})
    return c


def test_client_caches_and_sends_key(tmp_path):
    calls = []

    def handler(req: httpx.Request):
        calls.append(req)
        assert req.headers["X-APIKEY"] == "test-key"
        return httpx.Response(200, json=fixture("header_105401"))

    c = make_client(tmp_path, handler)
    h1 = c.match_header(105401)
    h2 = c.match_header(105401)
    assert h1 == h2 and h1["currentHomeScore"] == 89
    assert len(calls) == 1 and c.cache_hits == 1 and c.requests == 1


def test_client_refresh_and_max_age(tmp_path):
    n = {"calls": 0}

    def handler(req):
        n["calls"] += 1
        return httpx.Response(200, json={"n": n["calls"]})

    c = make_client(tmp_path, handler)
    assert c.standings(1, 91)["n"] == 1
    assert c.standings(1, 91, max_age_days=1.0)["n"] == 1   # reciente: caché
    assert c.standings(1, 91, max_age_days=0.0)["n"] == 2   # caducado: se refresca
    assert c.standings(1, 91, refresh=True)["n"] == 3


def test_client_204_and_404_markers_are_cached(tmp_path):
    n = {"calls": 0}

    def handler(req):
        n["calls"] += 1
        return httpx.Response(204 if "serie" in req.url.path else 404)

    c = make_client(tmp_path, handler)
    assert c.serie(105401) == {"_status": 204}
    assert c.serie(105401) == {"_status": 204}
    assert c.club_data(0) == {"_status": 404}
    assert n["calls"] == 2


def test_client_400_raises_without_retry(tmp_path):
    n = {"calls": 0}

    def handler(req):
        n["calls"] += 1
        return httpx.Response(400, json={"title": "validation"})

    c = make_client(tmp_path, handler)
    with pytest.raises(ApiError):
        c.competition_data(1, 2)
    assert n["calls"] == 1
    assert c.raw.count("/matchdata/Menu/competition-data") == 0


def test_client_retries_5xx_then_succeeds(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    n = {"calls": 0}

    def handler(req):
        n["calls"] += 1
        return httpx.Response(503) if n["calls"] < 3 else httpx.Response(200, json={"ok": 1})

    c = make_client(tmp_path, handler)
    assert c.match_header(1) == {"ok": 1}
    assert n["calls"] == 3


def test_client_persistent_500_is_item_error_not_outage(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    n = {"calls": 0}

    def handler(req):
        n["calls"] += 1
        return httpx.Response(500) if "career" in req.url.path else httpx.Response(200, json={})

    c = make_client(tmp_path, handler)
    with pytest.raises(ApiError):
        c.player_career(20210392)
    assert n["calls"] == 3
    assert c.player_data(20210392) == {}  # la API sigue usable
    assert c.raw.count("/seasondata/PlayerProfile/career") == 0  # no se cachea: se reintenta en la próxima ejecución


def test_client_tolerated_500_is_cached_as_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    n = {"calls": 0}

    def handler(req):
        n["calls"] += 1
        return httpx.Response(500)

    c = make_client(tmp_path, handler)
    assert c.player_career(20300929, tolerate_server_error=True) == {"_status": 500}
    assert c.player_career(20300929, tolerate_server_error=True) == {"_status": 500}
    assert n["calls"] == 3  # 3 intentos la primera vez, caché la segunda


def test_sync_people_counts_partial_persons(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def handler(req):
        if "career" in req.url.path and req.url.params["playerLicenceId"] == "20300929":
            return httpx.Response(500)
        return httpx.Response(200, json={})

    c = make_client(tmp_path, handler)
    stats = backfill.RunStats()
    backfill.sync_people(c, {20300929, 20209407}, stats, max_age_days=30)
    assert stats.people == 2 and stats.people_partial == 1
    assert c.raw.count("/seasondata/PlayerProfile/career") == 2


def test_client_aborts_after_consecutive_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def handler(req):
        raise httpx.ConnectError("down")

    c = make_client(tmp_path, handler)
    with pytest.raises(ApiUnavailable):
        for i in range(10):
            c.match_header(i)


def test_client_401_rediscovers_key(tmp_path, monkeypatch):
    monkeypatch.setattr(apikey, "discover_key", lambda **kw: "new-key")
    seen = []

    def handler(req):
        seen.append(req.headers["X-APIKEY"])
        return httpx.Response(401) if req.headers["X-APIKEY"] == "test-key" else httpx.Response(200, json={})

    c = make_client(tmp_path, handler)
    c.match_header(1)
    assert seen == ["test-key", "new-key"]
    assert json.loads((tmp_path / ".apikey.json").read_text())["key"] == "new-key"


def test_client_stop_requested(tmp_path):
    c = make_client(tmp_path, lambda req: httpx.Response(200, json={}))
    c.stop_requested = True
    with pytest.raises(StopRequested):
        c.match_header(1)


# --------------------------------------------------------------------------- backfill sobre fixtures

def route_handler(req: httpx.Request) -> httpx.Response:
    path, q = req.url.path, dict(req.url.params)
    table = {
        "/api/matchdata/Menu/competition-data": "compdata_rep",
        "/api/seasondata/Calendar/season-calendar": "calendar_91",
        "/api/seasondata/TeamProfile/teams": "teams_91",
        "/api/seasondata/Competition/standings": "standings_91",
        "/api/seasondata/Competition/bracket": "bracket_90",
        "/api/seasondata/ShotChart/league-zones": "zones_91",
        "/api/seasondata/TeamProfile/current-roster": "roster_2_91",
        "/api/seasondata/TeamProfile/team-stats": "tstats_2_91",
        "/api/matchdata/MatchHeader/match-header": "header_105401",
        "/api/matchdata/Result/boxscores": "box_105401",
        "/api/matchdata/PlayByPlay/play-by-play": "pbp_105401",
        "/api/matchdata/MatchShots/match-shots": "shots_105401",
        "/api/seasondata/PlayerProfile/player-data": "pdata_tavares",
        "/api/seasondata/PlayerProfile/player-stats": "pstats_tavares",
        "/api/seasondata/PlayerProfile/career": "career_tavares",
    }
    name = table.get(path)
    if name is None:
        return httpx.Response(404)
    return httpx.Response(200, json=fixture(name))


def test_backfill_sync_current_edition_is_resumable(tmp_path):
    c = make_client(tmp_path, route_handler)
    stats = backfill.run(c, [1], mode="sync", people=False)
    cal = fixture("calendar_91")
    finalized = sum(1 for r in cal["rounds"] for m in r["matches"] if m["matchStatus"] == "FINALIZED")
    assert stats.editions == 1
    assert stats.matches_fetched == finalized == c.raw.count("/matchdata/Result/boxscores")
    assert c.raw.count("/matchdata/PlayByPlay/play-by-play") == finalized
    assert c.raw.count("/seasondata/TeamProfile/current-roster") == 18
    assert len(stats.licences) > 20
    first_requests = c.requests
    # segunda pasada: partidos desde caché, nada nuevo pedido salvo los snapshots (que son recientes: tampoco)
    stats2 = backfill.run(c, [1], mode="sync", people=False)
    assert stats2.matches_cached == finalized and stats2.matches_fetched == 0
    assert c.requests == first_requests


def test_backfill_people_fetches_three_routes_per_licence(tmp_path):
    c = make_client(tmp_path, route_handler)
    stats = backfill.RunStats()
    backfill.sync_people(c, {20209407, 20212243}, stats, max_age_days=30)
    assert stats.people == 2
    assert c.raw.count("/seasondata/PlayerProfile/player-data") == 2
    assert c.raw.count("/seasondata/PlayerProfile/career") == 2


def test_backfill_skips_pbp_when_not_available(tmp_path):
    def handler(req):
        if "match-header" in req.url.path:
            return httpx.Response(200, json=fixture("header_12559"))
        if "boxscores" in req.url.path:
            return httpx.Response(200, json=fixture("box_12559"))
        return httpx.Response(200, json={})

    c = make_client(tmp_path, handler)
    stats = backfill.RunStats()
    backfill.fetch_match(c, 12559, "core", stats)
    assert c.raw.count("/matchdata/PlayByPlay/play-by-play") == 0
    assert stats.matches_fetched == 1


# --------------------------------------------------------------------------- clave

def test_apikey_regex_matches_bundle_and_escaped_forms():
    assert apikey.KEY_RE.search('x,apiKey:"0dd94928-6f57-4c08-a3bd-b1b2f092976e",y').group(1).startswith("0dd94928")
    assert apikey.KEY_RE.search('\\"apiKey\\":\\"0dd94928-6f57-4c08-a3bd-b1b2f092976e\\"').group(1).endswith("976e")


def test_apikey_cache_and_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(apikey, "discover_key", lambda **kw: None)
    p = tmp_path / "k.json"
    assert apikey.load_key(p) == apikey.FALLBACK_KEY
    p.write_text(json.dumps({"key": "cached", "fetched_at": time.time()}))
    assert apikey.load_key(p) == "cached"
    p.write_text(json.dumps({"key": "old", "fetched_at": 0}))
    assert apikey.load_key(p) == apikey.FALLBACK_KEY
