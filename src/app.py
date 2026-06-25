"""FastAPI application entrypoint for the Setlist API.

This module creates the application instance, registers API routers,
and initializes the database on startup.
"""

from src.database import init_db
from src.routers import songs

from fastapi import FastAPI

app = FastAPI(title="Setlist API")


@app.on_event("startup")
def on_startup():
    """Initialize the database schema when the application starts."""
    init_db()


app.include_router(songs.router, prefix="/songs", tags=["songs"])
