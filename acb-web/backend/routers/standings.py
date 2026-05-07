"""Standings API routes."""

from fastapi import APIRouter

from ..services.data_loader import data
from ..services.preprocessing import calculate_standings, standings_evolution

router = APIRouter(prefix="/api/standings", tags=["standings"])


@router.get("")
def get_standings():
    standings = calculate_standings(data.game_info)
    records = []
    for pos, row in standings.iterrows():
        entry = {"pos": int(pos)}
        for col in standings.columns:
            val = row[col]
            entry[col] = val
        records.append(entry)
    return records


@router.get("/evolution")
def get_standings_evolution():
    return standings_evolution(data.game_info)
