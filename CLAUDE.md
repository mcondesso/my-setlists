# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

- **`backend/`** — the FastAPI + SQLModel backend. It has its own
  [`backend/CLAUDE.md`](backend/CLAUDE.md) with commands and architecture;
  run all backend tooling (`pytest`, `ruff`, `alembic`, `python main.py`)
  from inside `backend/`, where its `.venv/`, `requirements.txt`,
  `ruff.toml` and `alembic.ini` live.
- **`frontend/`** — a Vite + Svelte 5 SPA over the backend's JSON API. See
  [`frontend/README.md`](frontend/README.md); run `npm` commands from inside
  `frontend/`, where its `node_modules/`, `package.json` and `vite.config.ts`
  live. No routing/state library — a ~15-line hash router and Svelte 5 runes
  cover the app's four screens.
- **`docs/`** — cross-cutting docs; [`docs/backlog.md`](docs/backlog.md) tracks
  deferred work.
- **`docker-compose.yml`**, **`.github/`**, `LICENSE`, `.gitignore` — repo-wide,
  stay at the root. CI (`.github/workflows/tests.yml`) runs backend steps with
  `working-directory: backend`.

## Cross-cutting notes

- Auth between the two: the backend issues a JWT (`POST /auth/login`); the
  frontend stores it in `localStorage` and sends it as `Authorization: Bearer`
  — no cookies, no CSRF handling needed on either side. While a tab stays
  open, the frontend calls `POST /auth/refresh` every 15 minutes
  (`frontend/src/lib/session.ts`) to extend the session past the backend's
  `ACCESS_TOKEN_EXPIRE_MINUTES` — a change to one side of that contract
  (the endpoint's shape, or how often the frontend calls it) affects the other.
- CORS: `backend/src/core/config.py` has a `CORS_ORIGINS` setting (default
  `http://localhost:5173`, comma-separated for more) applied via
  `CORSMiddleware` in `backend/src/app.py`. Add the frontend's deployed origin
  there when it has one.
