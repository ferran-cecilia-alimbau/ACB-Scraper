"""Tests unitarios para modern_acb.py.

Cubren las funciones puras (sin red): el parser de React Flight,
el balanceador de llaves, los formateadores y las transformaciones de
boxscore. La extracción del payload se prueba con HTML sintético, no con
fixtures de la web real, para que estos tests sean reproducibles offline.
"""
from datetime import date

import pytest
from bs4 import BeautifulSoup

import modern_acb as M


# -----------------------------------------------------------------------------
# Formateadores numéricos
# -----------------------------------------------------------------------------

class TestFormatInt:
    def test_int_passthrough(self):
        assert M._format_int(7) == "7"

    def test_string_numeric(self):
        assert M._format_int("12") == "12"

    def test_none_returns_zero(self):
        assert M._format_int(None) == "0"

    def test_empty_string_returns_zero(self):
        assert M._format_int("") == "0"

    def test_invalid_returns_zero(self):
        assert M._format_int("abc") == "0"

    def test_truncates_float(self):
        # int(1.9) == 1; el helper no redondea.
        assert M._format_int(1.9) == "1"


class TestPct:
    def test_round_percentage(self):
        assert M._pct(5, 10) == "50"

    def test_decimal_percentage(self):
        assert M._pct(1, 3) == "33.3"

    def test_zero_attempted(self):
        assert M._pct(0, 0) == "0"
        assert M._pct(5, 0) == "0"

    def test_none_inputs(self):
        assert M._pct(None, None) == "0"

    def test_invalid_inputs(self):
        assert M._pct("foo", "bar") == "0"

    def test_string_numbers(self):
        assert M._pct("3", "4") == "75"


class TestSumPlayTimes:
    def test_sum_basic(self):
        players = [{"playTime": "20:30"}, {"playTime": "15:45"}]
        assert M._sum_play_times(players) == "36:15"

    def test_carry_over_minute(self):
        players = [{"playTime": "00:30"}, {"playTime": "00:45"}]
        assert M._sum_play_times(players) == "1:15"

    def test_empty_list(self):
        assert M._sum_play_times([]) == "0:00"

    def test_missing_play_time(self):
        assert M._sum_play_times([{"player": {"id": 1}}]) == "0:00"

    def test_invalid_format_skipped(self):
        players = [{"playTime": "not_a_time"}, {"playTime": "10:00"}]
        assert M._sum_play_times(players) == "10:00"


# -----------------------------------------------------------------------------
# Fechas
# -----------------------------------------------------------------------------

class TestFormatStart:
    def test_iso_with_z(self):
        fecha, hora = M._format_start("2025-10-15T18:30:00Z")
        # Madrid es UTC+1 (estándar) o UTC+2 (verano). 15-oct está en horario de
        # verano hasta el último domingo, así que UTC+2.
        assert fecha == "15/10/2025"
        assert hora == "20:30"

    def test_iso_with_offset(self):
        fecha, hora = M._format_start("2025-12-01T19:00:00+01:00")
        assert fecha == "01/12/2025"
        assert hora == "19:00"

    def test_empty_returns_pair_of_empty(self):
        assert M._format_start("") == ("", "")

    def test_invalid_returns_input_and_empty(self):
        fecha, hora = M._format_start("not-a-date")
        assert fecha == "not-a-date"
        assert hora == ""


class FakeDate(date):
    """date.today() congelado para tests."""
    @classmethod
    def today(cls):
        return date(2026, 5, 3)


class TestAgeFromBirthDate:
    def setup_method(self, method):
        self._real_date = M.date

    def teardown_method(self, method):
        M.date = self._real_date

    def test_age_dmy_dash(self, monkeypatch):
        monkeypatch.setattr(M, "date", FakeDate)
        assert M._age_from_birth_date("15-06-1990") == 35

    def test_age_dmy_slash(self, monkeypatch):
        monkeypatch.setattr(M, "date", FakeDate)
        assert M._age_from_birth_date("15/06/1990") == 35

    def test_age_iso(self, monkeypatch):
        monkeypatch.setattr(M, "date", FakeDate)
        assert M._age_from_birth_date("1990-06-15") == 35

    def test_birthday_not_yet(self, monkeypatch):
        monkeypatch.setattr(M, "date", FakeDate)
        # Cumple en mayo 4 (un día después de "today" simulado)
        assert M._age_from_birth_date("04-05-1990") == 35

    def test_birthday_today(self, monkeypatch):
        monkeypatch.setattr(M, "date", FakeDate)
        assert M._age_from_birth_date("03-05-1990") == 36

    def test_empty_returns_zero(self):
        assert M._age_from_birth_date("") == 0

    def test_invalid_returns_zero(self):
        assert M._age_from_birth_date("not-a-date") == 0


# -----------------------------------------------------------------------------
# Parser React Flight
# -----------------------------------------------------------------------------

class TestReactFlightChunks:
    def test_extracts_string_chunks(self):
        html = '''
        <html><head>
          <script>self.__next_f.push([1,"chunk-a"])</script>
          <script>self.__next_f.push([1,"chunk-b"])</script>
        </head></html>
        '''
        soup = BeautifulSoup(html, "html.parser")
        assert M._react_flight_chunks(soup) == ["chunk-a", "chunk-b"]

    def test_ignores_non_flight_scripts(self):
        html = '''
        <script>console.log('hello')</script>
        <script>self.__next_f.push([1,"only-this"])</script>
        '''
        soup = BeautifulSoup(html, "html.parser")
        assert M._react_flight_chunks(soup) == ["only-this"]

    def test_skips_payloads_without_string_content(self):
        html = '<script>self.__next_f.push([0])</script>'
        soup = BeautifulSoup(html, "html.parser")
        assert M._react_flight_chunks(soup) == []

    def test_skips_invalid_json(self):
        html = '<script>self.__next_f.push(garbage)</script>'
        soup = BeautifulSoup(html, "html.parser")
        assert M._react_flight_chunks(soup) == []


class TestJsonObjectAfter:
    def test_basic_extraction(self):
        text = '"foo":{"a":1,"b":2}'
        assert M._json_object_after(text, '"foo":') == {"a": 1, "b": 2}

    def test_nested_objects(self):
        text = '"x":{"a":{"b":{"c":1}},"d":2}'
        assert M._json_object_after(text, '"x":') == {"a": {"b": {"c": 1}}, "d": 2}

    def test_handles_strings_with_braces(self):
        # La llave dentro del string no debe contar para el balance.
        text = '"k":{"label":"a {nested} value","n":1}'
        assert M._json_object_after(text, '"k":') == {
            "label": "a {nested} value",
            "n": 1,
        }

    def test_handles_escaped_quotes(self):
        text = r'"k":{"label":"with \"quotes\"","n":2}'
        assert M._json_object_after(text, '"k":') == {
            "label": 'with "quotes"',
            "n": 2,
        }

    def test_marker_not_found(self):
        assert M._json_object_after('{"foo":1}', '"missing":') is None

    def test_marker_followed_by_non_object(self):
        # "k": 1  ← valor escalar, no objeto: el helper solo soporta {…}.
        assert M._json_object_after('"k":1', '"k":') is None

    def test_handles_whitespace_after_marker(self):
        text = '"foo":   {"a":1}'
        assert M._json_object_after(text, '"foo":') == {"a": 1}

    def test_unclosed_braces_returns_none(self):
        assert M._json_object_after('"foo":{"a":1', '"foo":') is None


class TestExtractReactObject:
    def test_full_pipeline(self):
        html = '''
        <script>self.__next_f.push([1,"prelude:"])</script>
        <script>self.__next_f.push([1,"\\"initialMatchHeader\\":{\\"id\\":42,\\"teams\\":{\\"home\\":{\\"fullName\\":\\"Madrid\\"}}}"])</script>
        '''
        soup = BeautifulSoup(html, "html.parser")
        result = M.extract_react_object(soup, "initialMatchHeader")
        assert result == {"id": 42, "teams": {"home": {"fullName": "Madrid"}}}

    def test_missing_key_returns_none(self):
        html = '<script>self.__next_f.push([1,"\\"otherKey\\":{\\"id\\":1}"])</script>'
        soup = BeautifulSoup(html, "html.parser")
        assert M.extract_react_object(soup, "initialMatchHeader") is None

    def test_no_flight_chunks_returns_none(self):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        assert M.extract_react_object(soup, "initialMatchHeader") is None


# -----------------------------------------------------------------------------
# Extracción de jornada
# -----------------------------------------------------------------------------

class TestExtractJornada:
    def test_top_level_matchday(self):
        assert M._extract_jornada_from_header({"matchday": 7}) == 7

    def test_top_level_round_number(self):
        assert M._extract_jornada_from_header({"roundNumber": 12}) == 12

    def test_phase_round(self):
        assert M._extract_jornada_from_header({"phase": {"round": 3}}) == 3

    def test_phase_number(self):
        assert M._extract_jornada_from_header({"phase": {"number": 18}}) == 18

    def test_string_numeric_value(self):
        assert M._extract_jornada_from_header({"matchday": "5"}) == 5

    def test_zero_falls_through(self):
        assert M._extract_jornada_from_header({"matchday": 0, "roundNumber": 4}) == 4

    def test_missing_returns_none(self):
        assert M._extract_jornada_from_header({}) is None

    def test_phase_not_dict(self):
        # Si phase llega como string, no debe romper.
        assert M._extract_jornada_from_header({"phase": "regular"}) is None

    def test_invalid_value_skipped(self):
        assert M._extract_jornada_from_header({"matchday": "abc", "round": 9}) == 9


# -----------------------------------------------------------------------------
# Transformaciones de boxscore
# -----------------------------------------------------------------------------

class TestPlayerStats:
    def test_full_row(self):
        row = {
            "isStarted": True,
            "playTime": "25:30",
            "points": 18,
            "twoPointersAttempted": 8,
            "twoPointersMade": 5,
            "threePointersAttempted": 4,
            "threePointersMade": 2,
            "freeThrowsAttempted": 3,
            "freeThrowsMade": 2,
            "defRebounds": 4,
            "offRebounds": 1,
            "totalRebounds": 5,
            "assists": 3,
            "steals": 1,
            "turnovers": 2,
            "blocks": 1,
            "receivedBlocks": 0,
            "dunks": 0,
            "personalFouls": 2,
            "foulsDrawn": 4,
            "plusMinus": 7,
            "rating": 22,
            "player": {
                "id": 9001,
                "shirtNumber": "23",
                "firstInitialAndLastName": "L. James",
                "firstName": "LeBron",
                "lastName": "James",
            },
        }
        out = M._player_stats(101, "Lakers", row)
        assert out["id_partido"] == 101
        assert out["player_id"] == 9001
        assert out["equipo"] == "Lakers"
        assert out["es_titular"] is True
        assert out["dorsal"] == "23"
        assert out["nombre"] == "L. James"
        assert out["minutos"] == "25:30"
        assert out["puntos"] == "18"
        assert out["t2_porcentaje"] == "62.5"
        assert out["t3_porcentaje"] == "50"
        assert out["tl_porcentaje"] == "66.7"
        assert out["valoracion"] == "22"
        assert out["plus_minus"] == "7"

    def test_minimal_row_defaults_to_zero(self):
        row = {"player": {"id": 1}}
        out = M._player_stats(99, "X", row)
        assert out["minutos"] == "00:00"
        assert out["puntos"] == "0"
        assert out["t2_porcentaje"] == "0"
        assert out["es_titular"] is False
        assert out["dorsal"] == ""


class TestTeamTotals:
    def test_basic(self):
        stats = {
            "points": 88,
            "twoPointersMade": 20,
            "twoPointersAttempted": 35,
            "threePointersMade": 8,
            "threePointersAttempted": 22,
            "freeThrowsMade": 12,
            "freeThrowsAttempted": 16,
            "totalRebounds": 32,
            "assists": 18,
            "rating": 95,
        }
        players = [{"playTime": "10:00"}, {"playTime": "20:00"}]
        out = M._team_totals(101, "Lakers", stats, players)
        assert out["id_partido"] == 101
        assert out["equipo"] == "Lakers"
        assert out["minutos"] == "30:00"
        assert out["puntos"] == "88"
        assert out["t3_porcentaje"] == "36.4"
        assert out["valoracion"] == "95"


class TestGameInfo:
    def test_uses_payload_jornada_over_index_map(self):
        header = {
            "matchday": 5,
            "start": "2025-10-15T18:30:00Z",
            "currentHomeScore": 90,
            "currentAwayScore": 80,
            "teams": {
                "home": {"fullName": "Real Madrid"},
                "away": {"fullName": "Barça"},
            },
            "quarterScores": [
                {"home": 22, "away": 18},
                {"home": 20, "away": 22},
            ],
        }
        stats = {"arena": "WiZink", "attendance": 12000, "referees": ["A", "B", "C", "D"]}
        # El mapping del input dice 99, pero el payload manda con 5.
        config = {"_match_id_to_jornada": {101: 99}}
        out = M._game_info(101, header, stats, config)
        assert out["jornada"] == "5"
        assert out["fecha"] == "15/10/2025"
        assert out["resultado_local"] == "90"
        assert out["local"] == "Real Madrid"
        assert out["visitante"] == "Barça"
        assert out["pabellon"] == "WiZink"
        assert out["publico"] == "12000"
        assert out["parciales_local"] == "22,20"
        assert out["parciales_visitante"] == "18,22"
        assert out["arbitro1"] == "A"
        assert out["arbitro2"] == "B"
        assert out["arbitro3"] == "C"
        # Cuarto árbitro descartado (solo 3 huecos).
        assert "arbitro4" not in out

    def test_falls_back_to_index_map_when_payload_missing(self):
        header = {"start": "", "teams": {}}
        stats = {}
        config = {"_match_id_to_jornada": {101: 17}}
        out = M._game_info(101, header, stats, config)
        assert out["jornada"] == "17"

    def test_empty_when_no_jornada_anywhere(self):
        header = {"start": "", "teams": {}}
        out = M._game_info(101, header, {}, {})
        assert out["jornada"] == ""


# -----------------------------------------------------------------------------
# Helpers de jugador
# -----------------------------------------------------------------------------

class TestFullPlayerName:
    def test_full_name_from_first_and_last(self):
        assert M._full_player_name({"firstName": "Sergio", "lastName": "Llull"}) == "Sergio Llull"

    def test_collapses_extra_spaces(self):
        assert M._full_player_name({"firstName": "Juan ", "lastName": "  Carlos"}) == "Juan Carlos"

    def test_falls_back_to_nickname(self):
        assert M._full_player_name({"nickname": "Tako"}) == "Tako"

    def test_empty_returns_empty(self):
        assert M._full_player_name({}) == ""


class TestProfileFromBoxscore:
    def test_basic(self):
        row = {
            "player": {
                "id": 42,
                "shirtNumber": "10",
                "firstInitialAndLastName": "S. Llull",
                "gameRole": "Base",
            }
        }
        out = M._profile_from_boxscore_player(42, "Real Madrid", row)
        assert out == {
            "player_id": 42,
            "nombre": "S. Llull",
            "equipo": "Real Madrid",
            "dorsal": "10",
            "posicion": "B",
        }


class TestProfileFromPlayerData:
    def test_full_profile(self):
        data = {
            "playerData": {
                "playerData": {
                    "player": {
                        "firstName": "Sergio",
                        "lastName": "Llull",
                        "firstInitialAndLastName": "S. Llull",
                        "gameRole": "Escolta",
                        "shirtNumber": "23",
                    },
                    "playerNumber": 23,
                    "birthPlace": "Mahón",
                    "birthCountry": "España",
                    "birthDate": "1987-11-15",
                    "currentTeam": {"fullName": "Real Madrid"},
                    "height": "1,90 m",
                    "nationality": "ESP",
                    "licensing": "JFL",
                }
            }
        }
        out = M._profile_from_player_data(7, data)
        assert out is not None
        assert out["player_id"] == 7
        assert out["nombre_completo"] == "Sergio Llull"
        assert out["equipo"] == "Real Madrid"
        assert out["dorsal"] == "23"
        assert out["posicion"] == "E"
        assert out["altura"] == "190"
        assert out["nacionalidad"] == "ESP"

    def test_missing_player_returns_none(self):
        assert M._profile_from_player_data(7, {"playerData": {}}) is None
