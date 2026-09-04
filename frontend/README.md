# My Setlists — frontend

A small Vite + Svelte 5 SPA over the [`backend/`](../backend/) JSON API. No
server-side rendering, no component library — plain CSS in `src/app.css`.

## Setup

Node version pinned in `.nvmrc` (`nvm use`).

```bash
npm install
cp .env.example .env      # VITE_API_URL, defaults to http://localhost:8000
npm run dev                # http://localhost:5173
```

The backend must be running and reachable at `VITE_API_URL` with that origin
allowed in its `CORS_ORIGINS` setting (`backend/.env.example` already includes
`http://localhost:5173`).

## Commands

```bash
npm run dev        # dev server with HMR
npm run build      # type-checks (svelte-check) then builds to dist/
npm run check       # svelte-check + tsc, no build
npm test            # vitest run — unit + component tests, no watch
npm run test:e2e    # playwright — real browser against the real backend, see e2e/README.md
npm run lint        # eslint .
npm run format      # prettier --write .   (format:check for CI)
npm run preview     # serve the production build locally
```

## Structure

```
src/
  lib/
    api.ts            # fetch wrapper: base URL, Bearer header, error shaping
    backend.ts         # typed functions for each API call the UI makes
    session.ts          # completeLogin() — composes backend.ts + auth.svelte.ts
    auth.svelte.ts      # reactive auth state (token + current user), persisted to localStorage
    router.svelte.ts    # ~15-line hash router (no routing library)
    types.ts            # TS interfaces mirroring backend/src/models/*.py schemas
  components/
    OwnerBadge.svelte   # "by X · Public" line shared by Setlists and SetlistDetail
  pages/
    Login.svelte, Register.svelte, Setlists.svelte, SetlistDetail.svelte
  App.svelte             # header/nav + route switch
```

`*.test.ts` files sit next to what they test (e.g. `lib/api.test.ts`,
`App.svelte.test.ts`). Run with `npm test`; Vitest + `@testing-library/svelte`,
configured in `vite.config.ts` / `vitest-setup.ts`. `e2e/` is separate —
Playwright specs, real browser, real backend — see `e2e/README.md`.

## Auth

The API issues a JWT (`POST /auth/login`, form-encoded per
`OAuth2PasswordRequestForm`). `lib/session.ts`'s `completeLogin()` validates
the token (fetches `/users/me` with it directly) _before_ committing it to
the reactive `auth` store — so a failure anywhere in the login sequence never
leaves the app in a half-authenticated state. The token then lives in
`localStorage` and is sent as `Authorization: Bearer <token>` on every
request — no cookies, so no CSRF handling is needed. A 401 response clears
the stored token and the app falls back to the login screen (see `lib/api.ts`).

While the app is open, `lib/session.ts`'s `startSessionRefresh()` calls
`POST /auth/refresh` every 15 minutes to extend the session — without it, a
user mid-session would be hard-logged-out after exactly
`ACCESS_TOKEN_EXPIRE_MINUTES`. There's no separate longer-lived refresh
token, so this only helps while the current token is still valid; once it's
actually expired, only logging back in gets you a new one.

## What's covered

Register, login, list setlists (paginated, "Load more"), create a setlist,
view one with its songs in order, search Discogs and add a result to a
setlist, remove a song. Song links, editing a setlist's name/visibility, and
the user's own library setlist have no dedicated UI yet — the API supports
all of it; only the screens are missing.
