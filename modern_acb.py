"""Parsers for the current ACB Live React payloads."""

import asyncio
import json
import logging
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from aiohttp import ClientSession
from bs4 import BeautifulSoup

import constants as const
from http_client import fetch
from utils import clean_height, normalize_position, normalize_spaces

logger = logging.getLogger('basketball_scraper')


def _react_flight_chunks(soup: BeautifulSoup) -> List[str]:
    chunks = []
    prefix = 'self.__next_f.push('

    for script in soup.find_all('script'):
        content = (script.string or script.get_text() or '').strip()
        if not content.startswith(prefix):
            continue

        try:
            payload = json.loads(content[len(prefix):-1])
        except (json.JSONDecodeError, IndexError, TypeError):
            continue

        if len(payload) > 1 and isinstance(payload[1], str):
            chunks.append(payload[1])

    return chunks


def _json_object_after(text: str, marker: str) -> Optional[Dict[str, Any]]:
    try:
        start = text.index(marker) + len(marker)
    except ValueError:
        return None

    while start < len(text) and text[start].isspace():
        start += 1

    if start >= len(text) or text[start] != '{':
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:index + 1])
                except json.JSONDecodeError as exc:
                    logger.warning(f"React payload JSON decode failed for {marker}: {exc}")
                    return None

    return None


def extract_react_object(soup: BeautifulSoup, key: str) -> Optional[Dict[str, Any]]:
    flight_text = ''.join(_react_flight_chunks(soup))
    if not flight_text:
        return None
    return _json_object_after(flight_text, f'"{key}":')


def _format_int(value: Any) -> str:
    try:
        return str(int(value or 0))
    except (TypeError, ValueError):
        return "0"


def _pct(made: Any, attempted: Any) -> str:
    try:
        made_num = float(made or 0)
        attempted_num = float(attempted or 0)
        if attempted_num == 0:
            return "0"
        value = round(made_num / attempted_num * 100, 1)
        return str(int(value)) if value.is_integer() else str(value)
    except (TypeError, ValueError):
        return "0"


def _stat(stats: Dict[str, Any], key: str, default: Any = 0) -> Any:
    value = stats.get(key, default)
    return default if value is None else value


def _sum_play_times(players: List[Dict[str, Any]]) -> str:
    total_seconds = 0
    for row in players:
        play_time = row.get('playTime') or '00:00'
        try:
            minutes, seconds = [int(part) for part in play_time.split(':', 1)]
        except (ValueError, AttributeError):
            continue
        total_seconds += minutes * 60 + seconds

    return f"{total_seconds // 60}:{total_seconds % 60:02d}"


def _format_start(start: str) -> Tuple[str, str]:
    if not start:
        return "", ""

    try:
        parsed = datetime.fromisoformat(start.replace('Z', '+00:00'))
        parsed = parsed.astimezone(ZoneInfo("Europe/Madrid"))
        return parsed.strftime("%d/%m/%Y"), parsed.strftime("%H:%M")
    except (ValueError, TypeError):
        return start, ""


def _age_from_birth_date(birth_date: str) -> int:
    if not birth_date:
        return 0

    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            born = datetime.strptime(birth_date, fmt).date()
        except ValueError:
            continue
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    return 0


def _full_player_name(player: Dict[str, Any]) -> str:
    first_name = player.get('firstName') or ''
    last_name = player.get('lastName') or ''
    full_name = normalize_spaces(f"{first_name} {last_name}")
    return full_name or player.get('nickname') or player.get('firstInitialAndLastName') or ""


def _player_stats(game_id: int, team_name: str, row: Dict[str, Any]) -> Dict[str, str]:
    player = row.get('player') or {}
    return {
        "id_partido": game_id,
        "player_id": player.get('id'),
        "equipo": team_name,
        "es_titular": bool(row.get('isStarted')),
        "dorsal": player.get('shirtNumber') or "",
        "nombre": player.get('firstInitialAndLastName') or player.get('nickname') or _full_player_name(player),
        "minutos": row.get('playTime') or "00:00",
        "puntos": _format_int(_stat(row, 'points')),
        "t2_intentados": _format_int(_stat(row, 'twoPointersAttempted')),
        "t2_anotados": _format_int(_stat(row, 'twoPointersMade')),
        "t2_porcentaje": _pct(_stat(row, 'twoPointersMade'), _stat(row, 'twoPointersAttempted')),
        "t3_intentados": _format_int(_stat(row, 'threePointersAttempted')),
        "t3_anotados": _format_int(_stat(row, 'threePointersMade')),
        "t3_porcentaje": _pct(_stat(row, 'threePointersMade'), _stat(row, 'threePointersAttempted')),
        "tl_intentados": _format_int(_stat(row, 'freeThrowsAttempted')),
        "tl_anotados": _format_int(_stat(row, 'freeThrowsMade')),
        "tl_porcentaje": _pct(_stat(row, 'freeThrowsMade'), _stat(row, 'freeThrowsAttempted')),
        "rebotes_defensivos": _format_int(_stat(row, 'defRebounds')),
        "rebotes_ofensivos": _format_int(_stat(row, 'offRebounds')),
        "rebotes_totales": _format_int(_stat(row, 'totalRebounds')),
        "asistencias": _format_int(_stat(row, 'assists')),
        "robos": _format_int(_stat(row, 'steals')),
        "perdidas": _format_int(_stat(row, 'turnovers')),
        "tapones_favor": _format_int(_stat(row, 'blocks')),
        "tapones_contra": _format_int(_stat(row, 'receivedBlocks')),
        "mates": _format_int(_stat(row, 'dunks')),
        "faltas_cometidas": _format_int(_stat(row, 'personalFouls')),
        "faltas_recibidas": _format_int(_stat(row, 'foulsDrawn')),
        "plus_minus": _format_int(_stat(row, 'plusMinus')),
        "valoracion": _format_int(_stat(row, 'rating')),
    }


def _team_totals(game_id: int, team_name: str, stats: Dict[str, Any], players: List[Dict[str, Any]]) -> Dict[str, str]:
    return {
        "id_partido": game_id,
        "equipo": team_name,
        "minutos": _sum_play_times(players),
        "puntos": _format_int(_stat(stats, 'points')),
        "t2_encestados": _format_int(_stat(stats, 'twoPointersMade')),
        "t2_intentados": _format_int(_stat(stats, 'twoPointersAttempted')),
        "t2_porcentaje": _pct(_stat(stats, 'twoPointersMade'), _stat(stats, 'twoPointersAttempted')),
        "t3_encestados": _format_int(_stat(stats, 'threePointersMade')),
        "t3_intentados": _format_int(_stat(stats, 'threePointersAttempted')),
        "t3_porcentaje": _pct(_stat(stats, 'threePointersMade'), _stat(stats, 'threePointersAttempted')),
        "tl_encestados": _format_int(_stat(stats, 'freeThrowsMade')),
        "tl_intentados": _format_int(_stat(stats, 'freeThrowsAttempted')),
        "tl_porcentaje": _pct(_stat(stats, 'freeThrowsMade'), _stat(stats, 'freeThrowsAttempted')),
        "rebotes_totales": _format_int(_stat(stats, 'totalRebounds')),
        "rebotes_defensivos": _format_int(_stat(stats, 'defRebounds')),
        "rebotes_ofensivos": _format_int(_stat(stats, 'offRebounds')),
        "asistencias": _format_int(_stat(stats, 'assists')),
        "robos": _format_int(_stat(stats, 'steals')),
        "perdidas": _format_int(_stat(stats, 'turnovers')),
        "tapones_favor": _format_int(_stat(stats, 'blocks')),
        "tapones_contra": _format_int(_stat(stats, 'receivedBlocks')),
        "mates": _format_int(_stat(stats, 'dunks')),
        "faltas_cometidas": _format_int(_stat(stats, 'personalFouls')),
        "faltas_recibidas": _format_int(_stat(stats, 'foulsDrawn')),
        "plus_minus": _format_int(_stat(stats, 'plusMinus')),
        "valoracion": _format_int(_stat(stats, 'rating')),
    }


def _extract_jornada_from_header(header: Dict[str, Any]) -> Optional[int]:
    """Intenta sacar la jornada del payload React.

    Los partidos de ACB Live exponen la jornada en distintos campos según la
    versión del payload. Probamos los más comunes con fallback null.
    """
    candidates: List[Any] = [
        header.get('matchday'),
        header.get('round'),
        header.get('roundNumber'),
        header.get('week'),
        header.get('journey'),
    ]
    phase = header.get('phase') or {}
    if isinstance(phase, dict):
        candidates.extend([
            phase.get('matchday'),
            phase.get('round'),
            phase.get('roundNumber'),
            phase.get('number'),
        ])

    for value in candidates:
        if value is None:
            continue
        try:
            jornada = int(value)
            if jornada > 0:
                return jornada
        except (TypeError, ValueError):
            continue
    return None


def _game_info(game_id: int, header: Dict[str, Any], stats: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, str]:
    teams = header.get('teams') or {}
    home = teams.get('home') or {}
    away = teams.get('away') or {}
    fecha, hora = _format_start(header.get('start') or '')
    quarters = header.get('quarterScores') or []
    referees = stats.get('referees') or []

    # Preferimos la jornada que viene en el payload; el mapping por índice del
    # input es un fallback frágil (asume calendario completo y sin aplazamientos).
    jornada: Any = _extract_jornada_from_header(header)
    if jornada is None:
        jornada = (config.get('_match_id_to_jornada') or {}).get(game_id, "")

    info = {
        "id_partido": game_id,
        "jornada": str(jornada),
        "fecha": fecha,
        "hora": hora,
        "pabellon": stats.get('arena') or "",
        "publico": _format_int(stats.get('attendance')) if stats.get('attendance') is not None else "",
        "resultado_local": _format_int(header.get('currentHomeScore')),
        "resultado_visitante": _format_int(header.get('currentAwayScore')),
        "local": home.get('fullName') or home.get('shortName') or "",
        "visitante": away.get('fullName') or away.get('shortName') or "",
        "parciales_local": ','.join(_format_int(q.get('home')) for q in quarters),
        "parciales_visitante": ','.join(_format_int(q.get('away')) for q in quarters),
    }

    for index, referee in enumerate(referees[:3], start=1):
        info[f'arbitro{index}'] = referee

    return info


def _profile_from_player_data(player_id: int, data: Dict[str, Any]) -> Optional[Dict[str, str]]:
    root = (data.get('playerData') or {}).get('playerData') or data.get('playerData') or {}
    player = root.get('player') or {}
    if not player:
        return None

    birth_place = root.get('birthPlace') or ""
    birth_country = root.get('birthCountry') or ""
    birth_date = root.get('birthDate') or ""
    current_team = root.get('currentTeam') or {}
    full_name = _full_player_name(player)

    if root.get('playerNumber') is not None:
        dorsal = _format_int(root.get('playerNumber'))
    else:
        dorsal = player.get('shirtNumber') or ""

    return {
        "player_id": player_id,
        "nombre": player.get('firstInitialAndLastName') or player.get('nickname') or full_name,
        "nombre_completo": full_name,
        "equipo": current_team.get('fullName') or current_team.get('shortName') or "",
        "dorsal": dorsal,
        "posicion": normalize_position(player.get('gameRole') or ""),
        "altura": clean_height(root.get('height') or ""),
        "ciudad_nacimiento": birth_place,
        "pais_nacimiento": birth_country,
        "fecha_nacimiento": birth_date,
        "edad": _age_from_birth_date(birth_date),
        "nacionalidad": root.get('nationality') or "",
        "licencia": root.get('licensing') or "",
    }

def _profile_from_boxscore_player(player_id: int, team_name: str, row: Dict[str, Any]) -> Dict[str, str]:
    player = row.get('player') or {}
    return {
        "player_id": player_id,
        "nombre": player.get('firstInitialAndLastName') or player.get('nickname') or _full_player_name(player),
        "equipo": team_name,
        "dorsal": player.get('shirtNumber') or "",
        "posicion": normalize_position(player.get('gameRole') or ""),
    }

async def scrape_modern_player_profile(session: ClientSession, player_id: int, config: Dict[str, Any]) -> Optional[Dict[str, str]]:
    url = const.PLAYER_PROFILE_URL.format(player_id=player_id)
    html = await fetch(session, url, config)
    soup = BeautifulSoup(html, 'html.parser')
    player_data = extract_react_object(soup, 'playerData')
    if not player_data:
        return None
    return _profile_from_player_data(player_id, player_data)


async def build_modern_game_data(
    session: ClientSession,
    soup: BeautifulSoup,
    game_id: int,
    config: Dict[str, Any],
    existing_profile_ids: set,
) -> Optional[Dict[str, Any]]:
    parse_start = time.perf_counter()
    header = extract_react_object(soup, 'initialMatchHeader')
    statistics = extract_react_object(soup, 'initialStatistics')

    if not header or not statistics:
        return None

    team_boxscores = statistics.get('teamBoxscores') or []
    if len(team_boxscores) < 2:
        return None
    parse_seconds = time.perf_counter() - parse_start

    player_stats = []
    team_totals = []
    profile_updates = []
    player_ids_to_fetch = []
    profile_updates_by_id = {}
    profile_seconds = 0.0

    for team_boxscore in team_boxscores[:2]:
        team = team_boxscore.get('team') or {}
        team_name = team.get('fullName') or team.get('shortName') or ""
        periods = team_boxscore.get('statsByPeriods') or []
        period_zero = next((p for p in periods if p.get('quarter') == 0), periods[0] if periods else {})
        stats = period_zero.get('stats') or {}
        players = stats.get('players') or []
        totals = stats.get('total') or stats.get('team') or {}

        for row in players:
            player = row.get('player') or {}
            player_id = player.get('id')
            if player_id is None:
                continue
            player_stats.append(_player_stats(game_id, team_name, row))
            profile_update = _profile_from_boxscore_player(player_id, team_name, row)
            profile_updates.append(profile_update)
            profile_updates_by_id[player_id] = profile_update
            if player_id not in existing_profile_ids:
                existing_profile_ids.add(player_id)
                player_ids_to_fetch.append(player_id)

        if totals:
            team_totals.append(_team_totals(game_id, team_name, totals, players))

    profiles = []
    if player_ids_to_fetch:
        profile_start = time.perf_counter()
        unique_ids = list(dict.fromkeys(player_ids_to_fetch))
        # Limitar la concurrencia de perfiles dentro de un mismo partido. El
        # semáforo externo (en scraper.py) acota partidos en paralelo, no las
        # sub-peticiones de perfil que se disparan dentro de cada uno.
        profile_concurrency = max(1, int(config.get('profile_concurrency', 3)))
        inner_sem = asyncio.Semaphore(profile_concurrency)

        async def _bounded(pid: int):
            async with inner_sem:
                return await scrape_modern_player_profile(session, pid, config)

        tasks = [_bounded(player_id) for player_id in unique_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        profile_seconds = time.perf_counter() - profile_start
        for player_id, profile in zip(unique_ids, results):
            if isinstance(profile, Exception):
                logger.warning(f"No se pudo obtener perfil moderno del jugador {player_id}: {profile}")
                continue
            if profile:
                profile.update(profile_updates_by_id.get(player_id, {}))
                profiles.append(profile)

    return {
        'game_id': game_id,
        'player_stats': player_stats,
        'game_info': _game_info(game_id, header, statistics, config),
        'team_totals': team_totals,
        'player_profiles': profile_updates + profiles,
        '_metrics': {
            'parser': 'react_flight',
            'parse_seconds': round(parse_seconds, 3),
            'profile_seconds': round(profile_seconds, 3),
            'full_profiles_downloaded': len(player_ids_to_fetch),
            'profile_updates': len(profile_updates),
        },
    }
