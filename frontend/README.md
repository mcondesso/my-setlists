# My Setlists — frontend

A small Vite + Svelte 5 SPA over the [`backend/`](../backend/) JSON API. No
server-side rendering, no component library — plain CSS in `src/app.css`.

## Setup

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
npm run preview     # serve the production build locally
```

## Structure

```
src/
  lib/
    api.ts            # fetch wrapper: base URL, Bearer header, error shaping
    backend.ts         # typed functions for each API call the UI makes
    auth.svelte.ts      # reactive auth state (token + current user), persisted to localStorage
    router.svelte.ts    # ~15-line hash router (no routing library)
    types.ts            # TS interfaces mirroring backend/src/models/*.py schemas
  pages/
    Login.svelte, Register.svelte, Setlists.svelte, SetlistDetail.svelte
  App.svelte             # header/nav + route switch
```

## Auth

The API issues a JWT (`POST /auth/login`, form-encoded per
`OAuth2PasswordRequestForm`). The frontend stores it in `localStorage` and
sends `Authorization: Bearer <token>` on every request — no cookies, so no
CSRF handling is needed. A 401 response clears the stored token and the app
falls back to the login screen (see `lib/api.ts`).

## What's covered

Register, login, list setlists, create a setlist, view one with its songs in
order, search Discogs and add a result to a setlist, remove a song. Song
links, editing a setlist's name/visibility, and the user's own library
setlist have no dedicated UI yet — the API supports all of it; only the
screens are missing.
