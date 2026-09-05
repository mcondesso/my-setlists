# My Setlists

Build and share musical setlists.

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
