# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

FastAPI + SQLModel REST API for building and sharing musical setlists. Users register,
create setlists, add globally-shared songs to them, and attach external platform links
(Discogs, YouTube, etc.) to songs. Browsable at `/docs`; the UI lives separately in
[`../frontend/`](../frontend/README.md) and talks to this API only over HTTP (JWT bearer
auth, CORS-enabled — see Configuration below).

This is the `backend/` package of the repo; run every command below from this
directory (its `.venv/`, `requirements.txt`, `ruff.toml`, `alembic.ini` are here).
Repo-wide files (`docker-compose.yml`, `.github/`, `docs/`) are one level up.

## Commands

```bash
# Setup (Python 3.12) — run from backend/; venv lives at backend/.venv/
pip install -r requirements.txt
cp .env.example .env       # .env is gitignored; all settings fields are required

# Run the app — serves on APP_PORT (8000 in .env.example)
docker compose up              # from repo root; Postgres (not needed when ENVIRONMENT=test)
alembic upgrade head           # apply migrations — the app does NOT create tables
python main.py

# Migrations (Alembic) — see migrations/README; point DATABASE_URL at real Postgres
alembic revision --autogenerate -m "..."
alembic check                  # fails if models drift from migrations

# Tests — conftest.py forces ENVIRONMENT=test (in-memory SQLite), no services needed
python -m pytest tests/ -q
python -m pytest tests/models/test_song.py -v            # one file
python -m pytest tests/models/test_song.py::test_x -v    # one test

# Lint / format (CI runs both as checks)
ruff check .
ruff format --check .      # use `ruff format .` to apply
```

CI (`../.github/workflows/tests.yml`) runs — with `working-directory: backend` — ruff
format check, ruff lint, pytest, and an Alembic drift check (`alembic upgrade head` +
`alembic check` against Postgres) on pushes/PRs to `main`.

## Configuration

`src/core/config.py` defines a pydantic-settings `Settings` loaded from `.env`. Most
fields are required (no defaults except `ENVIRONMENT` and `CORS_ORIGINS`), so a fresh
clone needs `cp .env.example .env` before anything runs. The `settings.database_url`
**property** — not the raw `DATABASE_URL` field — is what the engine uses: when
`ENVIRONMENT == "test"` it returns `sqlite:///:memory:`, otherwise `DATABASE_URL`.
`.env.example` ships `ENVIRONMENT=test`, so a `.env` copied straight from it runs
`python main.py` against throwaway in-memory SQLite until you set
`ENVIRONMENT=development`.

`CORS_ORIGINS` (default `http://localhost:5173`, comma-separated for more) is parsed by
the `settings.cors_origins` property and applied via `CORSMiddleware` in `src/app.py`.
Auth is a Bearer JWT rather than a cookie, so `allow_credentials` stays `False`.

## Architecture

### Models: one file per domain entity, table + schemas together

Each `src/models/*.py` holds the SQLModel table class **and** its API schemas
(`XCreate`, `XRead`, `XUpdate`, `XReadWithY`, `XReadNested`). Conventions that matter:

- Cross-model schema references (e.g. `setlist.py` using `SongReadWithLinks`) are
  imported **both** at module top level **and** again under `if TYPE_CHECKING:`. The
  runtime import is required so SQLAlchemy can resolve `Relationship` string targets;
  don't "clean up" the apparent duplication.
- `src/models/__init__.py` imports every table model; `src/database.py` and
  `migrations/env.py` both import `src.models` as a whole so all tables are registered
  on `SQLModel.metadata` before it is used (ORM relationship resolution, Alembic
  autogenerate).
- Primary keys are `UUID` (`default_factory=uuid4`). `created_at` / `added_at` are
  `datetime | None` with a `server_default=func.now()`, timezone-aware column.
- Read schemas with computed fields (e.g. `owner_display_name` from `setlist.user`)
  define an explicit `from_setlist` classmethod that routers call manually, rather than
  relying on FastAPI's `response_model` coercion.

### Domain rules

- **Library setlist**: every user gets one auto-created at registration with
  `is_library=True`. It cannot be renamed, have its description changed, or be deleted
  (enforced in `routers/setlists.py`).
- **Songs are global and deduplicated** by a `UniqueConstraint(title, artist)`. Creating
  a song that already exists reuses the existing row, backfilling any of its
  thumbnail/album/release_year/duration_ms left empty by that earlier save (never
  overwriting fields it already has). A song is only removed from the global `songs`
  table when no `SetlistEntry` anywhere references it.
- **Setlist ↔ Song is many-to-many through `SetlistEntry`** (composite PK
  `setlist_id + song_id`, plus `position` for ordering).
- **Song authorization** is implicit: a user may modify/delete a song only if it appears
  in one of their own setlists (`user_has_song_access` in `routers/songs.py`).
- **Visibility**: setlists are private unless `is_public=True`; public ones are readable
  by any authenticated user but only mutable by the owner.

### Schema & migrations

Alembic owns the schema (`migrations/`, config in `alembic.ini`). `migrations/env.py`
pulls the URL from `settings.DATABASE_URL` and the metadata from `SQLModel.metadata`.
The app never creates tables; run `alembic upgrade head` after a checkout or a pull that
adds a revision. After a model change: `alembic revision --autogenerate -m "..."`
against real Postgres, then review the generated file. Tests bypass Alembic — conftest
builds tables with `SQLModel.metadata.create_all` on its own in-memory engine.

### Cascade deletes

Deletion cascades are handled at the **database** level: FK columns declare
`ondelete="CASCADE"` and relationships set `passive_deletes=True`. SQLite does not
enforce FKs by default, so `tests/conftest.py` registers a `connect` event listener
running `PRAGMA foreign_keys=ON`. Keep both sides in sync when adding relationships.

### Auth

OAuth2 password flow with JWT (HS256, `src/core/security.py`). Token `sub` claim is the
user's UUID string. `get_current_user` (in `src/core/dependencies.py`) is the auth
dependency for protected routes. `/auth/login` takes **form data**
(`OAuth2PasswordRequestForm`); `/auth/register` takes JSON. `/auth/refresh` (protected,
takes no body) exchanges a still-valid token for a new one with a fresh expiry — there's
no separate longer-lived refresh token, so this can't revive an already-expired one; the
frontend calls it periodically to keep an open session alive past
`ACCESS_TOKEN_EXPIRE_MINUTES`. Passwords hashed with `pwdlib` (argon2). All three
endpoints (`login`, `register`, `refresh`) are rate-limited via `slowapi`
(`src/core/rate_limit.py`), which is disabled when `ENVIRONMENT=test`.

### Routers

`src/routers/{auth,users,songs,song_links,setlists}.py`, wired in `src/app.py`.
`song_links` is mounted under `/songs/{song_id}/links` and keyed by `Platform` enum
value in the path (one link per song per platform).

### External services & background tasks

- `src/services/discogs.py` — used by `GET /songs/search`. Needs `DISCOGS_API_TOKEN`.
  Discogs only searches at the release/master (album) level, so this searches masters
  first, then fetches the tracklist of each candidate master (concurrently, via a
  thread pool — these are synchronous `httpx` calls) and scores every track's title
  against the query, returning individual matching tracks rather than albums.
- `src/services/youtube.py` — scrapes YouTube via the `youtube-search` package.
- `src/tasks/youtube.py` — FastAPI `BackgroundTasks` job queued on song creation that
  finds the most-viewed YouTube video and saves a `SongLink`. It opens its own `Session`
  on the engine `create_song` passes it (`session.get_bind()`), so it writes to the same
  database as the request; failures are logged, never raised. An autouse conftest fixture
  stubs the lookup so tests never hit the network.

## Tests

- `tests/models/`, `tests/tasks/`, and `tests/core/` call functions directly
  (with a `Session` where one's needed); `tests/routers/` drives the app through
  `TestClient` (via the `authenticated_client` fixture) and is where `response_model`
  serialization and middleware (CORS, rate limiting) are covered.
- `conftest.py` forces `ENVIRONMENT=test`, uses one in-memory SQLite engine
  (`StaticPool`) recreated per test, and disables the rate limiter and YouTube lookup.

## Notes

- Deferred follow-ups (rate-limit scale-out, session-refresh design, offset
  pagination) are tracked in [../docs/backlog.md](../docs/backlog.md).
- The committed `../docs/my-setlists-schema.png` is generated from dbdiagram.io (link in
  `README.md`) and is not auto-updated.
