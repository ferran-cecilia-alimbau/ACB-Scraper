"""FastAPI application — ACB Stats API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .services.data_loader import data
from .routers import standings, teams, players, games, rankings, league


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load all data at startup
    data.load_all()
    print(f"Data loaded: {len(data.player_stats)} player rows, "
          f"{len(data.game_info)} games, {len(data.team_stats)} team rows, "
          f"{len(data.player_profiles)} profiles")
    yield


app = FastAPI(title="ACB Stats API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(standings.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(games.router)
app.include_router(rankings.router)
app.include_router(league.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
