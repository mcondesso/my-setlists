# My Setlists

Build and share musical setlists.

Full-stack app — FastAPI/SQLModel backend, Svelte 5/Vite frontend, PostgreSQL
— with JWT authentication and a CI pipeline (GitHub Actions) enforcing lint,
formatting, and tests on every push. Coverage spans all three layers: pytest
(backend), Vitest (frontend unit/component), and Playwright (end-to-end).

One notable piece: Discogs' search API only returns album-level results, so
`GET /songs/search` fetches each candidate album's full tracklist and scores
individual tracks against the query to surface the actual song — see
[Discogs track matching](backend/README.md#discogs-track-matching) for how.

## Layout

| Path | What |
|------|------|
| [`backend/`](backend/) | FastAPI + SQLModel REST API — see [`backend/README.md`](backend/README.md) |
| [`frontend/`](frontend/) | Vite + Svelte SPA — see [`frontend/README.md`](frontend/README.md) |
| [`docs/`](docs/) | Cross-cutting docs, including the [backlog](docs/backlog.md) |
| `docker-compose.yml` | Local services (Postgres) |

## Quick start

```bash
docker compose up                      # Postgres

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
sed -i 's/^ENVIRONMENT=test/ENVIRONMENT=development/' .env   # .env.example defaults to test (in-memory SQLite)
alembic upgrade head
python main.py                          # http://localhost:8000

# in another terminal
cd frontend
npm install
cp .env.example .env
npm run dev                             # http://localhost:5173
```

See [`backend/README.md`](backend/README.md) and
[`frontend/README.md`](frontend/README.md) for details.
