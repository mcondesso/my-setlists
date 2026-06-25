"""FastAPI application entrypoint for the Setlist API.

This module creates the application instance, registers API routers,
and initializes the database on startup.
"""

from fastapi import FastAPI
from src.database import init_db

app = FastAPI(title="Setlist API")


@app.on_event("startup")
def on_startup():
    """Initialize the database schema when the application starts."""
    init_db()
