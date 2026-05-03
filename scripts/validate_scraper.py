"""Valida el scraper ACB contra una muestra pequena de partidos reales.

El script escribe siempre en una carpeta temporal, no en data/output. Comprueba
que los CSVs se escriben tras el primer partido, que no hay duplicados de
perfiles, que los campos criticos existen y que los puntos oficiales cuadran.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from main import load_config, load_existing_data, load_match_ids, process_and_save_data
from scraper import process_games


OUTPUT_FILES = {
    'output_file': 'estadisticas_todos_partidos.csv',
    'output_file_game': 'estadisticas_partido.csv',
    'output_file_team_totals': 'estadisticas_equipos_por_partido.csv',
    'output_file_player_profiles': 'perfiles_jugadores.csv',
}

CRITICAL_COLUMNS = {
    'players': ['id_partido', 'player_id', 'equipo', 'nombre', 'minutos', 'puntos'],
    'games': ['id_partido', 'jornada', 'resultado_local', 'resultado_visitante', 'local', 'visitante'],
    'teams': ['id_partido', 'equipo', 'puntos', 't2_encestados', 't2_intentados'],
    'profiles': ['player_id', 'nombre', 'equipo', 'dorsal', 'posicion'],
}


EXPECTED_MATCHES = {
    104459: {'players': 24, 'local_score': 86, 'visitor_score': 68},
    104460: {'players': 24, 'local_score': 97, 'visitor_score': 79},
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Valida el scraper ACB con partidos reales.')
    parser.add_argument(
        '--matches',
        nargs='+',
        type=int,
        default=[104459, 104460],
        help='IDs de partido a validar. Por defecto: 104459 104460.',
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help='Directorio temporal de salida. Si se omite, se crea uno en la carpeta temporal del sistema.',
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Timeout HTTP por peticion, en segundos.',
    )
    return parser.parse_args()


def build_temp_config(output_dir: Path, match_ids: List[int], timeout: int) -> Dict[str, Any]:
    config = load_config()
    for key, filename in OUTPUT_FILES.items():
        config[key] = str(output_dir / filename)

    configured_match_ids = load_match_ids()
    known_jornadas = {match_id: (idx // 9) + 1 for idx, match_id in enumerate(configured_match_ids)}
    fallback_jornadas = {match_id: idx + 1 for idx, match_id in enumerate(match_ids)}
    config['_match_id_to_jornada'] = {**fallback_jornadas, **known_jornadas}
    config['batch_size'] = 1
    config['max_concurrent'] = 1
    config['rate_limit'] = 1
    config['timeout'] = timeout
    return config


def read_outputs(config: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    return {
        'players': pd.read_csv(config['output_file']),
        'games': pd.read_csv(config['output_file_game']),
        'teams': pd.read_csv(config['output_file_team_totals']),
        'profiles': pd.read_csv(config['output_file_player_profiles']),
    }


def fail(message: str) -> None:
    raise AssertionError(message)


def require_files_exist(config: Dict[str, Any]) -> None:
    missing = [path for path in (config[key] for key in OUTPUT_FILES) if not Path(path).exists()]
    if missing:
        fail(f'No se escribieron todos los CSVs esperados: {missing}')


def require_no_blank_critical_fields(outputs: Dict[str, pd.DataFrame]) -> None:
    for name, columns in CRITICAL_COLUMNS.items():
        df = outputs[name]
        for column in columns:
            if column not in df.columns:
                fail(f'Falta columna critica {name}.{column}')
            blanks = df[column].isna() | (df[column].astype(str).str.strip() == '')
            if blanks.any():
                fail(f'Campo critico vacio en {name}.{column}: {int(blanks.sum())} filas')


def require_expected_rows(outputs: Dict[str, pd.DataFrame], match_ids: Iterable[int]) -> None:
    match_ids = list(match_ids)
    expected_games = set(match_ids)

    players = outputs['players']
    games = outputs['games']
    teams = outputs['teams']
    profiles = outputs['profiles']

    if set(games['id_partido'].astype(int)) != expected_games:
        fail(f'Partidos en game_info no coinciden: {sorted(games["id_partido"].tolist())}')
    if set(players['id_partido'].astype(int)) != expected_games:
        fail('Partidos en estadisticas de jugadores no coinciden')
    if set(teams['id_partido'].astype(int)) != expected_games:
        fail('Partidos en estadisticas de equipos no coinciden')

    team_counts = teams.groupby('id_partido').size().to_dict()
    bad_team_counts = {game_id: count for game_id, count in team_counts.items() if count != 2}
    if bad_team_counts:
        fail(f'Cada partido debe tener dos filas de equipo: {bad_team_counts}')

    player_counts = players.groupby('id_partido').size().to_dict()
    bad_player_counts = {game_id: count for game_id, count in player_counts.items() if count < 10}
    if bad_player_counts:
        fail(f'Hay partidos con muy pocos jugadores: {bad_player_counts}')

    duplicate_profiles = int(profiles['player_id'].duplicated().sum())
    if duplicate_profiles:
        fail(f'Perfiles duplicados por player_id: {duplicate_profiles}')


def require_score_consistency(outputs: Dict[str, pd.DataFrame]) -> None:
    players = outputs['players']
    games = outputs['games']
    teams = outputs['teams']

    for _, game in games.iterrows():
        game_id = int(game['id_partido'])
        expected = [
            (game['local'], int(game['resultado_local'])),
            (game['visitante'], int(game['resultado_visitante'])),
        ]
        for team_name, score in expected:
            team_rows = teams[(teams['id_partido'] == game_id) & (teams['equipo'] == team_name)]
            if len(team_rows) != 1:
                fail(f'No hay una unica fila de equipo para {game_id} {team_name}')

            team_points = int(team_rows.iloc[0]['puntos'])
            player_points = int(
                pd.to_numeric(
                    players[(players['id_partido'] == game_id) & (players['equipo'] == team_name)]['puntos'],
                    errors='coerce',
                ).fillna(0).sum()
            )
            if team_points != score or player_points != score:
                fail(
                    f'Puntos no cuadran para {game_id} {team_name}: '
                    f'marcador={score}, equipo={team_points}, jugadores={player_points}'
                )


def require_known_markers(outputs: Dict[str, pd.DataFrame], match_ids: Iterable[int]) -> None:
    games = outputs['games']
    players = outputs['players']
    for game_id in match_ids:
        expected = EXPECTED_MATCHES.get(int(game_id))
        if not expected:
            continue
        game_rows = games[games['id_partido'].astype(int) == int(game_id)]
        if len(game_rows) != 1:
            fail(f'No hay una unica fila de partido para {game_id}')
        game = game_rows.iloc[0]
        local_score = int(game['resultado_local'])
        visitor_score = int(game['resultado_visitante'])
        if local_score != expected['local_score'] or visitor_score != expected['visitor_score']:
            fail(
                f'Marcador inesperado para {game_id}: '
                f'{local_score}-{visitor_score}, esperado '
                f"{expected['local_score']}-{expected['visitor_score']}"
            )
        player_count = int((players['id_partido'].astype(int) == int(game_id)).sum())
        if player_count != expected['players']:
            fail(f'Numero de jugadores inesperado para {game_id}: {player_count}')


def require_timing_metrics(timings: Dict[int, Dict[str, Any]], match_ids: Iterable[int]) -> None:
    required_keys = ['fetch_seconds', 'total_extract_seconds', 'profile_seconds', 'save_seconds_observed']
    for game_id in match_ids:
        metrics = timings.get(int(game_id))
        if not metrics:
            fail(f'Faltan metricas para {game_id}')
        for key in required_keys:
            value = metrics.get(key)
            if value is None:
                fail(f'Falta metrica {key} para {game_id}')
            if float(value) < 0:
                fail(f'Metrica negativa {key} para {game_id}: {value}')
        if metrics.get('full_profiles_downloaded') is None:
            fail(f'Falta full_profiles_downloaded para {game_id}')

def summarize(outputs: Dict[str, pd.DataFrame], timings: Dict[int, Dict[str, Any]]) -> None:
    print('Rows:')
    for name, df in outputs.items():
        print(f'  {name}: {len(df)}')

    print('Timings:')
    for game_id, metrics in timings.items():
        print(f'  {game_id}: {metrics}')


async def run_validation(match_ids: List[int], output_dir: Path, timeout: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    config = build_temp_config(output_dir, match_ids, timeout)
    dataframes, _ = load_existing_data(config)
    timings: Dict[int, Dict[str, Any]] = {}
    first_write_checked = False

    def save_single_result(result: Dict[str, Any]) -> None:
        nonlocal first_write_checked
        game_id = int(result['game_id'])
        save_start = time.perf_counter()
        process_and_save_data(config, [result], dataframes)
        save_seconds = time.perf_counter() - save_start
        metrics = dict(result.get('_metrics') or {})
        metrics['save_seconds_observed'] = round(save_seconds, 3)
        timings[game_id] = metrics

        if not first_write_checked:
            require_files_exist(config)
            partial_outputs = read_outputs(config)
            require_expected_rows(partial_outputs, [game_id])
            require_no_blank_critical_fields(partial_outputs)
            require_score_consistency(partial_outputs)
            require_known_markers(partial_outputs, [game_id])
            first_write_checked = True

    results = await process_games(match_ids, config['base_url'], config, set(), set(), on_result=save_single_result)
    if len(results) != len(match_ids):
        fail(f'Se esperaban {len(match_ids)} resultados y se obtuvieron {len(results)}')

    require_files_exist(config)
    outputs = read_outputs(config)
    require_expected_rows(outputs, match_ids)
    require_no_blank_critical_fields(outputs)
    require_score_consistency(outputs)
    require_known_markers(outputs, match_ids)
    require_timing_metrics(timings, match_ids)

    # Segundo pase: fuerza los mismos partidos con perfiles ya conocidos. Debe
    # devolver actualizaciones ligeras sin descargar fichas completas.
    existing_profile_ids = set(outputs['profiles']['player_id'].astype(int).tolist())
    known_profile_results = await process_games(
        [match_ids[0]],
        config['base_url'],
        config,
        set(),
        existing_profile_ids,
        on_result=None,
    )
    if not known_profile_results:
        fail('El segundo pase con perfiles conocidos no devolvio resultado')
    known_metrics = known_profile_results[0].get('_metrics') or {}
    if known_metrics.get('full_profiles_downloaded') != 0:
        fail(f'Se descargaron perfiles completos ya conocidos: {known_metrics}')

    timings[int(match_ids[0])]['known_profile_seconds'] = known_metrics.get('total_extract_seconds')
    timings[int(match_ids[0])]['known_profile_full_downloads'] = known_metrics.get('full_profiles_downloaded')

    summarize(outputs, timings)
    print(f'OK: validacion completada en {output_dir}')


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir or Path(tempfile.mkdtemp(prefix='acb-scraper-validation-'))
    try:
        asyncio.run(run_validation(args.matches, output_dir, args.timeout))
    except AssertionError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
