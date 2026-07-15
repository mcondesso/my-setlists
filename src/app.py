"""Setlist API application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import init_db
from src.routers import auth, setlists, songs, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    init_db()
    yield


app = FastAPI(title="Setlist API", lifespan=lifespan)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(songs.router, prefix="/songs", tags=["songs"])
app.include_router(setlists.router, prefix="/setlists", tags=["setlists"])


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Return a basic readiness response for CI and deployment checks."""
    return {"status": "ok"}
