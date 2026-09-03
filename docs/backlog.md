# Backlog

Known issues and follow-ups surfaced during the September 2026 code review.
Ordered roughly by priority.

## API hardening

- **No CORS middleware** — a browser frontend on another origin can't call the API. Add
  `CORSMiddleware` with an allowlist once the frontend origin is known.
- **Login rate limit is per-process and per-IP** — `slowapi` now throttles
  `POST /auth/login`, but with in-memory storage the limit is per worker/container, and
  it keys on the client IP so a shared NAT is limited as one client. Move to a shared
  store (Redis) when running more than one process, and make sure the deployment forwards
  the real client IP (see `backend/src/core/rate_limit.py`).

## Performance

- **`limit` / `offset` pagination is offset-based** — fine for now; revisit with cursor
  pagination if result sets get large or rows shift between page fetches.
