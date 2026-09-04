# Backlog

Known issues and follow-ups surfaced during the September 2026 code review.
Ordered roughly by priority.

## API hardening

- **Rate limits are per-process and per-IP** — `slowapi` throttles `/auth/login`,
  `/auth/register`, and `/auth/refresh`, but with in-memory storage the limit is per
  worker/container, and it keys on the client IP so a shared NAT is limited as one
  client. Move to a shared store (Redis) when running more than one process, and make
  sure the deployment forwards the real client IP (see `backend/src/core/rate_limit.py`).
- **Session refresh isn't real refresh-token rotation** — `POST /auth/refresh` just
  re-signs a new access token off a still-valid one, and the frontend calls it every 15
  minutes to keep an open tab logged in (`frontend/src/lib/session.ts`). A leaked token
  therefore stays usable indefinitely as long as *something* keeps refreshing it, not
  just for its original `ACCESS_TOKEN_EXPIRE_MINUTES` lifetime. Proper refresh-token
  rotation (separate long-lived token, revocation on logout, rotated on each use) would
  close that, at the cost of real complexity — worth it if this ever handles data more
  sensitive than setlists.

## Performance

- **`limit` / `offset` pagination is offset-based** — fine for now; revisit with cursor
  pagination if result sets get large or rows shift between page fetches.
