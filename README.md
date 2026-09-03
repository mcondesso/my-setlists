# My Setlists

Build and share musical setlists.

## Layout

| Path | What |
|------|------|
| [`backend/`](backend/) | FastAPI + SQLModel REST API — see [`backend/README.md`](backend/README.md) |
| `frontend/` | Web UI (not added yet) |
| [`docs/`](docs/) | Cross-cutting docs, including the [backlog](docs/backlog.md) |
| `docker-compose.yml` | Local services (Postgres) |

## Quick start

```bash
docker compose up                      # Postgres
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                    # fill in real values
alembic upgrade head
python main.py
```

See [`backend/README.md`](backend/README.md) for details.
