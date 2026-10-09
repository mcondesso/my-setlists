# My Setlists

## Setup

1. Clone the repository
2. Create and activate a Python virtual environment
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Its `DATABASE_URL` already matches `docker-compose.yml`'s default Postgres
   credentials, so no edits are needed for local dev — except `ENVIRONMENT`,
   which ships set to `test` (in-memory SQLite, no Postgres needed) rather
   than `development`. Change it if you want `python main.py` to actually
   talk to Postgres.

   Two external API keys go in `.env` too:

   | Variable | Needed for | Where to get it |
   |----------|------------|-----------------|
   | `DISCOGS_API_TOKEN` | Song search (required) | [Discogs developer settings](https://www.discogs.com/settings/developers) → "Generate new token" |
   | `GEMINI_API_KEY` | Song recommendations (optional) | [Google AI Studio](https://aistudio.google.com/apikey) — free tier, no billing needed |

   Without `GEMINI_API_KEY` the app runs normally; setlists just show "No
   recommendations". `GEMINI_MODEL` picks the Gemini model and defaults to
   `gemini-3.5-flash-lite`.

## Running the application

Start the database and other services with Docker Compose:
```bash
docker compose up
```

Apply database migrations (see [migrations/README](migrations/README)):
```bash
alembic upgrade head
```

Then run the FastAPI app in a separate terminal:
```bash
python main.py
```

The app does not create tables on startup — `alembic upgrade head` is
required after a fresh checkout and after pulling changes that add a
migration.

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

Run a specific test file or test:
```bash
python -m pytest tests/routers/test_auth.py -v
python -m pytest tests/models/test_setlist.py::test_name -v
```

Tests are split into `tests/models/` (direct DB/model behaviour), `tests/tasks/`
(background jobs), `tests/core/` (config/settings), and `tests/routers/` (endpoint
behaviour, including middleware like CORS and rate limiting, via `TestClient`).
`tests/conftest.py` forces `ENVIRONMENT=test`, so every run uses a fresh in-memory
SQLite database and no external services are needed.

## Architecture

### Authentication and public access

Auth is a JWT bearer token from `POST /auth/login`. Most endpoints require
it, but reading public content doesn't:

| Without a token | Requires a token |
|-----------------|------------------|
| `GET /setlists/` (public setlists only) | Creating, editing and deleting setlists |
| `GET /setlists/{id}`, `/songs`, `/recommendation` (public setlists only) | Adding, removing and reordering songs |
| `GET /songs/`, `GET /songs/{id}` | Refreshing a recommendation |
| | `GET /songs/search` (spends Discogs API quota) |

Read endpoints use `get_optional_user` (`src/core/dependencies.py`), which
returns `None` when no token is sent. A token that is sent but invalid or
expired still gets a 401, so the frontend notices and logs out instead of
silently browsing as anonymous. Private setlists are only visible to their
owner; anyone else, logged in or not, gets a 403.

A setlist is private unless created with `is_public: true`, and its owner
can switch it either way later with `PATCH /setlists/{id}`
(`{"is_public": true}`). That includes the Library setlist, even though its
name and description can't be changed.

### Database Relationships & Cascade Delete

The application uses SQLAlchemy 2.0's cascade delete functionality to automatically clean up related records:

- **User → Setlists**: When a user is deleted, all their setlists are automatically deleted
- **Setlist → SetlistEntries**: When a setlist is deleted, all song entries are automatically removed
- **Song → SetlistEntries**: When a song is deleted, all its entries across setlists are cleaned up

This eliminates the need for manual cascading deletes in route handlers.

### Model layout & type safety

Each file in `src/models/` holds one entity's SQLModel table class together with its
API schemas (`*Create`, `*Read`, `*Update`, `*ReadWith*`). Relationships use `Mapped`
annotations from SQLAlchemy 2.0. Primary keys are `UUID`.

```python
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from src.models.user import User

class Setlist(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    user: Mapped[Optional["User"]] = Relationship(back_populates="setlists")
```

Key patterns:
- **Forward references** use `Optional["ClassName"]` (not `"ClassName" | None`) to work with `Mapped` types
- Cross-model schema references are imported both at module top level (so SQLAlchemy can
  resolve relationship strings) and again under `TYPE_CHECKING` for annotations
- `src/models/__init__.py` imports every table model so all tables are registered on
  `SQLModel.metadata`, which the ORM and Alembic autogenerate both rely on (the app
  itself no longer creates tables — migrations do)
- **Cascade configuration** is defined via `sa_relationship_kwargs` on relationship fields

### Discogs track matching

Discogs' search API only matches at the release/master (album) level —
searching "Darkside Heart" would otherwise return the "Psychic" album, not
the "Heart" track on it. `src/services/discogs.py`'s `search_discogs()`
works around this:

1. Search masters (albums) as normal, taking the top `CANDIDATE_MASTERS` (8)
   results.
2. Fetch each candidate's full tracklist concurrently (`ThreadPoolExecutor`)
   — this keeps total latency close to that of the slowest single request
   (~1s) instead of the sum of eight sequential ones (~4-5s).
3. Score every track against the query with an F1-style word-overlap metric
   over the track's title + artist (`precision = matched / candidate_words`,
   `recall = matched / query_words`). Plain character-sequence similarity
   (`difflib.SequenceMatcher`) was tried first and rejected — it penalizes
   word reordering so heavily that "Zombie Cranberries" ranked an unrelated
   Cranberries track above the actual "Zombie".
4. Return the top-scoring tracks across all candidate masters.

A failed tracklist fetch for one candidate doesn't fail the whole search —
that master is just skipped in favour of the others. See
`tests/services/test_discogs.py` for the cases this covers.

### Song recommendations

Each setlist has one recommended song, stored in `setlist_recommendations`
and returned with `GET /setlists/{id}`:

1. Any change to a setlist's songs (adding or removing, from either the
   setlist or the song endpoints — reordering doesn't count) marks its
   recommendation `pending` and queues a background task
   (`src/tasks/recommendations.py`).
2. The task waits 3 seconds, so a burst of edits costs one Gemini call, then
   asks Gemini (`src/services/gemini.py`) for 3 songs that fit the setlist,
   using structured JSON output.
3. It keeps the first suggestion that `discogs.find_track()` confirms — a
   strict lookup where every word of the title and artist must match, so a
   song the model made up never reaches the page. Songs already in the
   setlist and the previous recommendation are skipped.
4. Every request gets a new `request_id`; a run only saves its result if
   its id is still the current one, so out-of-order runs can't overwrite a
   newer result.

The owner can ask for a different song with
`POST /setlists/{id}/recommendation/refresh` (rate-limited to 5/minute to
protect the free-tier quota); anyone who can view the setlist can poll
`GET /setlists/{id}/recommendation`. The recommendation is stored shaped
like a Discogs search result rather than as a `Song`, so recommendations
nobody adds don't linger in the global catalog.

## Database Schema

The database schema is shown below. The diagram was generated with dbdiagram.io:

- Diagram link: https://dbdiagram.io/d/MySetlists-6a3969b39340ecc065ef0adf

![Database schema](../docs/my-setlists-schema.png)