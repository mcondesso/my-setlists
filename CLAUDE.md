# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

FastAPI + SQLModel REST API for building and sharing musical setlists. Users register,
create setlists, add globally-shared songs to them, and attach external platform links
(Discogs, YouTube, etc.) to songs. No frontend — API only, browsable at `/docs`.

## Commands

```bash
# Setup (Python 3.12, venv at .venv/)
pip install -r requirements.txt
cp .env.example .env       # .env is gitignored; all settings fields are required

# Run the app — serves on APP_PORT (8000 in .env.example)
python main.py
# Needs Postgres unless ENVIRONMENT=test: docker compose up

# Tests — conftest.py forces ENVIRONMENT=test (in-memory SQLite), no services needed
python -m pytest tests/ -q
python -m pytest tests/models/test_song.py -v            # one file
python -m pytest tests/models/test_song.py::test_x -v    # one test

# Lint / format (CI runs both as checks)
ruff check .
ruff format --check .      # use `ruff format .` to apply
```

CI (`.github/workflows/tests.yml`) runs ruff format check, ruff lint, and pytest on
pushes/PRs to `main`.

## Configuration

`src/core/config.py` defines a pydantic-settings `Settings` loaded from `.env`. All
fields are required (no defaults except `ENVIRONMENT`), so a fresh clone needs
`cp .env.example .env` before anything runs. The `settings.database_url` **property**
— not the raw `DATABASE_URL` field — is what the engine uses: when
`ENVIRONMENT == "test"` it returns `sqlite:///:memory:`, otherwise `DATABASE_URL`.
`.env.example` ships `ENVIRONMENT=test`, so a `.env` copied straight from it runs
`python main.py` against throwaway in-memory SQLite until you set
`ENVIRONMENT=development`.

## Architecture

### Models: one file per domain entity, table + schemas together

Each `src/models/*.py` holds the SQLModel table class **and** its API schemas
(`XCreate`, `XRead`, `XUpdate`, `XReadWithY`, `XReadNested`). Conventions that matter:

- Cross-model schema references (e.g. `setlist.py` using `SongReadWithLinks`) are
  imported **both** at module top level **and** again under `if TYPE_CHECKING:`. The
  runtime import is required so SQLAlchemy can resolve `Relationship` string targets;
  don't "clean up" the apparent duplication.
- `src/models/__init__.py` imports every table model, and `src/database.py` imports
  `src.models` as a whole. This registration must happen before `init_db()` calls
  `SQLModel.metadata.create_all()`, or tables go missing.
- Primary keys are `UUID` (`default_factory=uuid4`). `created_at` uses a
  `server_default=func.now()` column.
- Read schemas with computed fields (e.g. `owner_display_name` from `setlist.user`)
  define an explicit `from_orm` classmethod that routers call manually, rather than
  relying on FastAPI's `response_model` coercion.

### Domain rules

- **Library setlist**: every user gets one auto-created at registration with
  `is_library=True`. It cannot be renamed, have its description changed, or be deleted
  (enforced in `routers/setlists.py`).
- **Songs are global and deduplicated** by a `UniqueConstraint(title, artist)`. Creating
  a song that already exists reuses the existing row. A song is only removed from the
  global `songs` table when no `SetlistEntry` anywhere references it.
- **Setlist ↔ Song is many-to-many through `SetlistEntry`** (composite PK
  `setlist_id + song_id`, plus `position` for ordering).
- **Song authorization** is implicit: a user may modify/delete a song only if it appears
  in one of their own setlists (`user_has_song_access` in `routers/songs.py`).
- **Visibility**: setlists are private unless `is_public=True`; public ones are readable
  by any authenticated user but only mutable by the owner.

### Cascade deletes

Deletion cascades are handled at the **database** level: FK columns declare
`ondelete="CASCADE"` and relationships set `passive_deletes=True`. SQLite does not
enforce FKs by default, so `tests/conftest.py` registers a `connect` event listener
running `PRAGMA foreign_keys=ON`. Keep both sides in sync when adding relationships.

### Auth

OAuth2 password flow with JWT (HS256, `src/core/security.py`). Token `sub` claim is the
user's UUID string. `get_current_user` (in `src/core/dependencies.py`) is the auth
dependency for protected routes. `/auth/login` takes **form data**
(`OAuth2PasswordRequestForm`); `/auth/register` takes JSON. Passwords hashed with
`pwdlib` (argon2). `/auth/login` is rate-limited via `slowapi` (`src/core/rate_limit.py`),
which is disabled when `ENVIRONMENT=test`.

### Routers

`src/routers/{auth,users,songs,song_links,setlists}.py`, wired in `src/app.py`.
`song_links` is mounted under `/songs/{song_id}/links` and keyed by `Platform` enum
value in the path (one link per song per platform).

### External services & background tasks

- `src/services/discogs.py` — synchronous `httpx` call to the Discogs search API,
  used by `GET /songs/search`. Needs `DISCOGS_API_TOKEN`.
- `src/services/youtube.py` — scrapes YouTube via the `youtube-search` package.
- `src/tasks/youtube.py` — FastAPI `BackgroundTasks` job queued on song creation that
  finds the most-viewed YouTube video and saves a `SongLink`. Opens its own `Session`
  from the shared `engine`; failures are logged, never raised.

## Notes

- Known issues and deferred follow-ups (missing migrations, no router tests, API
  hardening) are tracked in [docs/backlog.md](docs/backlog.md).
- Tests call router functions directly with a `Session`, so FastAPI `response_model`
  validation/serialization is not exercised; there are no `TestClient` tests yet.
- The committed `docs/my-setlists-schema.png` is generated from dbdiagram.io (link in
  `README.md`) and is not auto-updated.
