# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

- **`backend/`** — the FastAPI + SQLModel backend. It has its own
  [`backend/CLAUDE.md`](backend/CLAUDE.md) with commands and architecture;
  run all backend tooling (`pytest`, `ruff`, `alembic`, `python main.py`)
  from inside `backend/`, where its `.venv/`, `requirements.txt`,
  `ruff.toml` and `alembic.ini` live.
- **`frontend/`** — web UI; not added yet.
- **`docs/`** — cross-cutting docs; [`docs/backlog.md`](docs/backlog.md) tracks
  deferred work.
- **`docker-compose.yml`**, **`.github/`**, `LICENSE`, `.gitignore` — repo-wide,
  stay at the root. CI (`.github/workflows/tests.yml`) runs backend steps with
  `working-directory: backend`.
