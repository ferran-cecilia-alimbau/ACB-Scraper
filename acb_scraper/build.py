"""Construye tablas planas (Parquet + CSV) a partir de la caché cruda.

Tablas: editions, rounds, teams, matches, quarter_scores, boxscore_players, boxscore_teams,
pbp_events, shots, standings, rosters, staff, players, player_season_stats, career_stints, league_zones.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from .client import RawStore

log = logging.getLogger("acb.build")

TEAM_COLS = ("id", "clubId", "fullName", "shortName", "abbreviatedName", "primaryColorHex")


def _params(stem: str) -> dict[str, str]:
    return dict(kv.split("=", 1) for kv in stem.split("&")) if stem != "_" else {}


def _team(prefix: str, t: dict | None) -> dict:
    t = t or {}
    return {f"{prefix}_team_id": t.get("id"), f"{prefix}_club_id": t.get("clubId"), f"{prefix}_team": t.get("fullName")}


def _write(out_dir: Path, name: str, rows: list[dict]) -> None:
    if not rows:
        log.info("%s: sin filas", name)
        return
    cols: dict[str, list] = {}
    for r in rows:
        for k in r:
            cols.setdefault(k, None)
    table = pa.Table.from_pylist(rows, schema=None) if len(cols) < 1 else pa.Table.from_pylist([{k: r.get(k) for k in cols} for r in rows])
    pq.write_table(table, out_dir / f"{name}.parquet", compression="zstd")
    pacsv.write_csv(table, out_dir / f"{name}.csv")
    log.info("%s: %d filas, %d columnas", name, table.num_rows, table.num_columns)


def build(data_dir: Path, out_dir: Path) -> None:
    raw = RawStore(data_dir / "raw")
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- calendario: ediciones, jornadas, partidos, equipos
    editions, rounds, matches, teams = [], [], [], []
    seen_teams: set[int] = set()
    for stem, cal in raw.iter_route("/seasondata/Calendar/season-calendar"):
        p = _params(stem)
        comp, ed = int(p["competitionId"]), int(p["editionId"])
        if "_status" in cal:
            continue
        editions.append({"competition_id": comp, "edition_id": ed, "season_start_year": ed + 1935,
                         "rounds": len(cal.get("rounds", [])), "teams": len(cal.get("teams", []))})
        team_by_id = {t["id"]: t for t in cal.get("teams", [])}
        for t in cal.get("teams", []):
            if t["id"] not in seen_teams:
                seen_teams.add(t["id"])
                teams.append({"team_id": t["id"], "club_id": t.get("clubId"), "competition_id": comp, "edition_id": ed,
                              "full_name": t.get("fullName"), "short_name": t.get("shortName"),
                              "abbreviation": t.get("abbreviatedName"), "primary_color": t.get("primaryColorHex")})
        for r in cal.get("rounds", []):
            rounds.append({"competition_id": comp, "edition_id": ed, "round_id": r["id"], "round_number": r.get("roundNumber"),
                           "subphase_id": r.get("subphaseId"), "subphase_number": r.get("subphaseNumber"), "matches": len(r.get("matches", []))})
            for m in r.get("matches", []):
                h, a = team_by_id.get(m.get("homeTeamId"), {}), team_by_id.get(m.get("awayTeamId"), {})
                matches.append({"match_id": m["id"], "competition_id": comp, "edition_id": ed, "season": f"{ed + 1935}-{(ed + 1936) % 100:02d}",
                                "round_id": r["id"], "round_number": r.get("roundNumber"), "subphase_id": r.get("subphaseId"),
                                "start_utc": m.get("startDateTime"), "status": m.get("matchStatus"),
                                "home_team_id": m.get("homeTeamId"), "home_club_id": h.get("clubId"), "home_team": h.get("fullName"),
                                "away_team_id": m.get("awayTeamId"), "away_club_id": a.get("clubId"), "away_team": a.get("fullName"),
                                "home_score": m.get("homeScore"), "away_score": m.get("awayScore"), "last_quarter": m.get("currentQuarter")})
    # --- cabecera + box score por partido
    header_by_id = {int(_params(s)["matchId"]): h for s, h in raw.iter_route("/matchdata/MatchHeader/match-header") if "_status" not in h}
    quarter_scores, box_players, box_teams = [], [], []
    extra: dict[int, dict] = {}
    for stem, box in raw.iter_route("/matchdata/Result/boxscores"):
        if "_status" in box:
            continue
        mid = int(_params(stem)["matchId"])
        refs = box.get("referees") or []
        extra[mid] = {"arena": box.get("arena"), "attendance": box.get("attendance"),
                      "referee_1": refs[0] if len(refs) > 0 else None, "referee_2": refs[1] if len(refs) > 1 else None,
                      "referee_3": refs[2] if len(refs) > 2 else None}
        for i, t in enumerate(box.get("teamBoxscores") or []):
            side = "home" if i == 0 else "away"
            extra[mid][f"{side}_coach"] = t.get("headCoach")
            team = t.get("team") or {}
            for per in t.get("statsByPeriods") or []:
                q, st = per.get("quarter"), per.get("stats") or {}
                for pl in st.get("players") or []:
                    person = pl.pop("player", {}) or {}
                    box_players.append({"match_id": mid, "team_id": team.get("id"), "club_id": team.get("clubId"), "team": team.get("fullName"),
                                        "side": side, "quarter": q, "licence_id": person.get("id"), "player": person.get("nickname"),
                                        "short_name": person.get("firstInitialAndLastName"), "shirt_number": person.get("shirtNumber"),
                                        "position": person.get("gameRole"), **pl})
                for kind in ("total", "team"):
                    if st.get(kind):
                        box_teams.append({"match_id": mid, "team_id": team.get("id"), "club_id": team.get("clubId"), "team": team.get("fullName"),
                                          "side": side, "quarter": q, "kind": kind, **st[kind]})
    for mid, h in header_by_id.items():
        for q in h.get("quarterScores") or []:
            quarter_scores.append({"match_id": mid, "quarter": q["quarter"], "home_score": q["homeScore"], "away_score": q["awayScore"]})
        extra.setdefault(mid, {}).update({"header_home_score": h.get("currentHomeScore"), "header_away_score": h.get("currentAwayScore"),
                                          "has_pbp": (h.get("availableContent") or {}).get("playbyplay"),
                                          "has_advanced": (h.get("availableContent") or {}).get("advanced")})
    for m in matches:
        m.update(extra.get(m["match_id"], {}))

    # --- play-by-play y tiros
    pbp, shots = [], []
    for stem, p in raw.iter_route("/matchdata/PlayByPlay/play-by-play"):
        if "_status" in p:
            continue
        mid = int(_params(stem)["matchId"])
        for ev in p.get("plays") or []:
            if ev.get("playType") == 600:  # marcador de minuto, sin contenido
                continue
            st = ev.pop("playerStats", None) or {}
            ev.pop("playerImage", None)
            pbp.append({"match_id": mid, **ev, **{f"run_{k}": v for k, v in st.items()}})
    for stem, s in raw.iter_route("/matchdata/MatchShots/match-shots"):
        if "_status" in s:
            continue
        mid = int(_params(stem)["matchId"])
        era = "new_mm" if mid >= 100000 else "legacy_pct"
        for sh in s.get("shotPoints") or []:
            shots.append({"match_id": mid, "coord_system": era, **sh})

    # --- clasificación
    standings = []
    for stem, s in raw.iter_route("/seasondata/Competition/standings"):
        if "_status" in s:
            continue
        p = _params(stem)
        tb = {t["id"]: t for t in s.get("teams", [])}
        for row in s.get("standings") or []:
            row = dict(row)
            row.pop("rounds", None)
            t = tb.get(row.get("teamId"), {})
            standings.append({"competition_id": int(p["competitionId"]), "edition_id": int(p["editionId"]), "round_id": s.get("selectedFilters", {}).get("round"),
                              "club_id": t.get("clubId"), "team": t.get("fullName"), **row})

    # --- plantillas y staff
    rosters, staff = [], []
    for stem, r in raw.iter_route("/seasondata/TeamProfile/current-roster"):
        if "_status" in r:
            continue
        p = {k: int(v) for k, v in _params(stem).items()}
        for row in r.get("players") or []:
            pl = row.get("player") or {}
            rosters.append({"club_id": p["clubId"], "competition_id": p["competitionId"], "edition_id": p["editionId"], "licence_id": pl.get("id"),
                            "player": pl.get("nickname"), "first_name": pl.get("firstName"), "last_name": pl.get("lastName"), "position": pl.get("gameRole"),
                            "shirt_number": pl.get("shirtNumber"), "height_cm": row.get("height"), "age_today": row.get("age"),
                            "licensing": row.get("licensing"), "nationality": row.get("nationalityCountry")})
        for row in r.get("staff") or []:
            c = row.get("coach") or {}
            staff.append({"club_id": p["clubId"], "competition_id": p["competitionId"], "edition_id": p["editionId"], "licence_id": c.get("id"),
                          "name": c.get("nickname"), "role": c.get("gameRole"), "licensing": row.get("licensing"), "nationality": row.get("nationalityCountry"), "age_today": row.get("age")})

    # --- personas
    players, pstats, stints = [], [], []
    for stem, d in raw.iter_route("/seasondata/PlayerProfile/player-data"):
        if "_status" in d or not d.get("playerData"):
            continue
        pd_, pl = d["playerData"], d["playerData"].get("player") or {}
        players.append({"licence_id": pl.get("id"), "name": pl.get("nickname"), "first_name": pl.get("firstName"), "last_name": pl.get("lastName"),
                        "position": pl.get("gameRole"), "birth_date": pd_.get("birthDate"), "birth_place": pd_.get("birthPlace"),
                        "birth_country": pd_.get("birthCountry"), "nationality": pd_.get("nationality"), "height": pd_.get("height"),
                        "licensing": pd_.get("licensing"), "shirt_number": pd_.get("playerNumber"), "license_active": pd_.get("isLicenseActive"),
                        "current_team": (pd_.get("currentTeam") or {}).get("fullName"), "current_club_id": (pd_.get("currentTeam") or {}).get("clubId"),
                        "is_coach": bool((d.get("availableLicenses") or {}).get("coachLicenseData")),
                        "twitter": pd_.get("twitter"), "instagram": pd_.get("instagram"), "headshot_url": pl.get("headshotImageUrl")})
    for stem, d in raw.iter_route("/seasondata/PlayerProfile/player-stats"):
        if "_status" in d:
            continue
        lic = int(_params(stem)["playerLicenceId"])
        for row in d.get("statsByTeam") or []:
            team = (row.get("team") or {}).get("selected") or {}
            for kind in ("totals", "averages", "per40"):
                if row.get(kind):
                    pstats.append({"licence_id": lic, "competition_id": row.get("competitionId"), "edition_id": row.get("editionId"),
                                   "season": row.get("editionYear"), "team_id": row.get("teamEditionId"), "club_id": team.get("clubId"),
                                   "team": team.get("fullName"), "kind": kind, **row[kind]})
    for stem, d in raw.iter_route("/seasondata/PlayerProfile/career"):
        if "_status" in d:
            continue
        lic = int(_params(stem)["playerLicenceId"])
        for s in d.get("stints") or []:
            stints.append({"licence_id": lic, "club_id": (s.get("team") or {}).get("clubId"), "team": (s.get("team") or {}).get("fullName"),
                           "start_year": s.get("initialYear"), "end_year": s.get("endYear"), "seasons": len(s.get("editions") or [])})

    zones = []
    for stem, z in raw.iter_route("/seasondata/ShotChart/league-zones"):
        if "_status" in z:
            continue
        for row in z.get("zones") or []:
            zones.append({"competition_id": z.get("competitionId"), "edition_id": z.get("editionId"), **row})

    for name, rows in [("editions", editions), ("rounds", rounds), ("teams", teams), ("matches", matches), ("quarter_scores", quarter_scores),
                       ("boxscore_players", box_players), ("boxscore_teams", box_teams), ("pbp_events", pbp), ("shots", shots),
                       ("standings", standings), ("rosters", rosters), ("staff", staff), ("players", players),
                       ("player_season_stats", pstats), ("career_stints", stints), ("league_zones", zones)]:
        _write(out_dir, name, rows)
