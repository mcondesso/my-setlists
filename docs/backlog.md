# Backlog

Known issues and follow-ups surfaced during the September 2026 code review.
Ordered roughly by priority.

## Test infrastructure

### No router / `TestClient` tests
All current tests call router functions directly with a `Session`, so FastAPI's
`response_model` validation and serialization are never exercised. The two serialization
bugs fixed in this branch (null `SongLink.url`, reversed setlist order) were invisible to
the suite for that reason.

- Add `TestClient` tests over the `songs`, `song_links`, and `setlists` routers covering
  the happy path and the response shape.

## Schema management

### No migration tool
[src/database.py](../src/database.py) calls `SQLModel.metadata.create_all()` on startup.
That never alters an existing table, so any model change (including the new
`song_links` `UniqueConstraint(song_id, platform)` added in this branch) will not reach a
database that already has the table.

- Adopt Alembic; generate an initial revision from the current models.
- Apply the `song_links` unique constraint to any existing deployment by hand until then.

## API hardening

- **No CORS middleware** — a browser frontend on another origin can't call the API. Add
  `CORSMiddleware` with an allowlist once the frontend origin is known.
- **Login rate limit is per-process and per-IP** — `slowapi` now throttles
  `POST /auth/login`, but with in-memory storage the limit is per worker/container, and
  it keys on the client IP so a shared NAT is limited as one client. Move to a shared
  store (Redis) when running more than one process, and make sure the deployment forwards
  the real client IP (see `src/core/rate_limit.py`).

## Performance

- **`limit` / `offset` pagination is offset-based** — fine for now; revisit with cursor
  pagination if result sets get large or rows shift between page fetches.
