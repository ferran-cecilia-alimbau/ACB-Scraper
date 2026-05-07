"""League averages API route."""

from fastapi import APIRouter

from ..services.data_loader import data
from ..services.preprocessing import compute_league_averages

router = APIRouter(prefix="/api/league", tags=["league"])


@router.get("/averages")
def get_league_averages():
    return compute_league_averages(data.team_stats, data.player_stats)
