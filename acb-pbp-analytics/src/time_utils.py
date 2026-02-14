"""Conversión de periodo+tiempo a segundos absolutos del partido.

Convenciones:
  - 1C 10:00 → 0 seg (inicio del partido)
  - 1C 00:00 → 600 seg (fin del 1er cuarto)
  - 4C 00:00 → 2400 seg (fin del tiempo reglamentario)
  - PR1 05:00 → 2400 seg (inicio de la primera prórroga)
  - PR1 00:00 → 2700 seg (fin de la primera prórroga)
"""

# Duración en segundos de cada periodo
PERIOD_DURATION = {
    "1C": 600,
    "2C": 600,
    "3C": 600,
    "4C": 600,
}

# Offset acumulado al inicio de cada periodo
PERIOD_OFFSET = {
    "1C": 0,
    "2C": 600,
    "3C": 1200,
    "4C": 1800,
}

OVERTIME_DURATION = 300  # 5 minutos por prórroga


def parse_clock(clock_str: str) -> float:
    """Convierte 'MM:SS' a segundos restantes en el periodo."""
    parts = clock_str.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])


def period_to_offset(period: str) -> int:
    """Devuelve el offset en segundos del inicio del periodo."""
    if period in PERIOD_OFFSET:
        return PERIOD_OFFSET[period]
    # Prórrogas: PR1, PR2, ...
    if period.startswith("PR"):
        ot_num = int(period[2:])
        return 2400 + (ot_num - 1) * OVERTIME_DURATION
    raise ValueError(f"Periodo desconocido: {period}")


def period_duration(period: str) -> int:
    """Duración en segundos de un periodo."""
    if period in PERIOD_DURATION:
        return PERIOD_DURATION[period]
    if period.startswith("PR"):
        return OVERTIME_DURATION
    raise ValueError(f"Periodo desconocido: {period}")


def to_absolute_seconds(period: str, clock_str: str) -> float:
    """Convierte periodo + reloj a segundos absolutos desde el inicio del partido.

    Ejemplos:
        to_absolute_seconds("1C", "10:00") → 0.0
        to_absolute_seconds("1C", "09:00") → 60.0
        to_absolute_seconds("4C", "00:00") → 2400.0
        to_absolute_seconds("PR1", "05:00") → 2400.0
        to_absolute_seconds("PR1", "00:00") → 2700.0
    """
    offset = period_to_offset(period)
    dur = period_duration(period)
    remaining = parse_clock(clock_str)
    return offset + (dur - remaining)


def format_game_time(abs_seconds: float) -> str:
    """Formatea segundos absolutos a representación legible (ej: '3Q 05:30')."""
    if abs_seconds < 2400:
        quarter = int(abs_seconds // 600) + 1
        elapsed_in_q = abs_seconds - (quarter - 1) * 600
        remaining = 600 - elapsed_in_q
    else:
        ot_seconds = abs_seconds - 2400
        ot_num = int(ot_seconds // 300) + 1
        elapsed_in_ot = ot_seconds - (ot_num - 1) * 300
        remaining = 300 - elapsed_in_ot
        mins = int(remaining) // 60
        secs = int(remaining) % 60
        return f"PR{ot_num} {mins:02d}:{secs:02d}"

    mins = int(remaining) // 60
    secs = int(remaining) % 60
    return f"{quarter}C {mins:02d}:{secs:02d}"
