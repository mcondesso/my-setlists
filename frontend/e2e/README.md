# E2E tests

Playwright, driving a real browser against a production frontend build and
a real backend — the one thing `npm test` can't prove, since there
everything past `fetch()` is mocked.

## Running locally

Needs a backend the E2E run can reach: either have your own
`python main.py` + Postgres already running (`cd backend && python main.py`,
per `backend/README.md`), or let Playwright start one (it will, using
`backend/.env`, if nothing answers `http://localhost:8000/health` yet).

```bash
npx playwright install chromium   # once, downloads the browser binary
npm run test:e2e
```

`playwright.config.ts`'s `webServer` entries start (or reuse) both the
backend and a `vite preview` of the frontend. Each test registers its own
throwaway user (a timestamped email), so runs don't collide with real data
or each other.

## Scope

One smoke path: register → land on Setlists (auto-login) → create a setlist
→ open it → log out → log back in → the setlist is still there. Deliberately
doesn't touch Discogs search (`GET /songs/search`) — that needs a real
`DISCOGS_API_TOKEN` and a live third-party API, which would make this
flaky and slow for no correctness benefit over the mocked coverage
`SetlistDetail.svelte.test.ts` already has for that flow.
