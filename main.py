"""Entrypoint for the webserver running the FastAPI application"""

import uvicorn

from src.core.config import settings


if __name__ == "__main__":
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=settings.UVICORN_RELOAD)
