"""Setlist API application entry point."""

from fastapi import FastAPI

from src.database import init_db
from src.routers import auth, songs, users, setlists

app = FastAPI(title="Setlist API")


@app.on_event("startup")
def on_startup() -> None:
    """Initialize the database schema when the application starts."""
    init_db()


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(songs.router, prefix="/songs", tags=["songs"])
app.include_router(setlists.router, prefix="/setlists", tags=["setlists"])
