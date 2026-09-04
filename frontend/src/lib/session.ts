// Composes backend.ts (API calls) with auth.svelte.ts (reactive auth state).
// Kept separate from both so neither has to import the other.

import { auth, setToken } from "./auth.svelte";
import { fetchMeAs, login, refreshToken } from "./backend";

const REFRESH_INTERVAL_MS = 15 * 60 * 1000;

/**
 * Log in and establish the session, or throw and leave the session untouched.
 *
 * Validates the token (via fetchMeAs) before calling setToken, so a failure
 * anywhere in this sequence — bad credentials, or the profile fetch failing
 * right after a successful login — never leaves auth.token set without a
 * corresponding auth.user. App.svelte's routing only switches away from
 * Login/Register once both are known good.
 */
export async function completeLogin(
  email: string,
  password: string,
): Promise<void> {
  const { access_token } = await login(email, password);
  const user = await fetchMeAs(access_token);
  setToken(access_token);
  auth.user = user;
}

/**
 * Periodically exchange the current token for a fresh one while the app is
 * open, so an active session doesn't hard-expire after
 * ACCESS_TOKEN_EXPIRE_MINUTES (there's no separate longer-lived refresh
 * token — once a token has actually expired, this can't revive it, only
 * re-login can). Call once from App.svelte's onMount; returns a cleanup
 * function to stop it.
 */
export function startSessionRefresh(
  intervalMs: number = REFRESH_INTERVAL_MS,
): () => void {
  const id = setInterval(async () => {
    if (!auth.token) return;
    try {
      const { access_token } = await refreshToken();
      setToken(access_token);
    } catch {
      // A 401 already triggers logout() in api.ts; any other failure just
      // means we try again on the next tick.
    }
  }, intervalMs);

  return () => clearInterval(id);
}
