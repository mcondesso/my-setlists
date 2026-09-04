"""Tests for application settings parsing."""

from src.core.config import Settings

_REQUIRED_FIELDS = {
    "DATABASE_URL": "sqlite:///:memory:",
    "ACCESS_TOKEN_EXPIRE_MINUTES": 60,
    "SECRET_KEY": "test-secret",
    "UVICORN_RELOAD": False,
    "APP_PORT": 8000,
    "DISCOGS_API_TOKEN": "test-token",
}


def test_cors_origins_defaults_to_the_frontend_dev_origin():
    settings = Settings(**_REQUIRED_FIELDS)  # type: ignore[arg-type]

    assert settings.cors_origins == ["http://localhost:5173"]


def test_cors_origins_splits_and_strips_a_comma_separated_list():
    settings = Settings(
        **_REQUIRED_FIELDS,  # type: ignore[arg-type]
        CORS_ORIGINS="http://localhost:5173, https://example.com ,https://other.example.com",
    )

    assert settings.cors_origins == [
        "http://localhost:5173",
        "https://example.com",
        "https://other.example.com",
    ]


def test_cors_origins_ignores_empty_entries():
    settings = Settings(**_REQUIRED_FIELDS, CORS_ORIGINS="http://localhost:5173,,")  # type: ignore[arg-type]

    assert settings.cors_origins == ["http://localhost:5173"]
