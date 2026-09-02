"""Setlist API application entry point."""

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.core.rate_limit import limiter
from src.routers import auth, setlists, song_links, songs, users

# The schema is managed by Alembic (`alembic upgrade head`), not created at
# startup — see migrations/.
app = FastAPI(title="Setlist API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(songs.router, prefix="/songs", tags=["songs"])
app.include_router(song_links.router, prefix="/songs/{song_id}/links", tags=["song links"])
app.include_router(setlists.router, prefix="/setlists", tags=["setlists"])


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Return a basic readiness response for CI and deployment checks."""
    return {"status": "ok"}
