// Composes backend.ts (API calls) with auth.svelte.ts (reactive auth state).
// Kept separate from both so neither has to import the other.

import { auth, setToken } from "./auth.svelte";
import { fetchMeAs, login } from "./backend";

/**
 * Log in and establish the session, or throw and leave the session untouched.
 *
 * Validates the token (via fetchMeAs) before calling setToken, so a failure
 * anywhere in this sequence — bad credentials, or the profile fetch failing
 * right after a successful login — never leaves auth.token set without a
 * corresponding auth.user. App.svelte's routing only switches away from
 * Login/Register once both are known good.
 */
export async function completeLogin(email: string, password: string): Promise<void> {
  const { access_token } = await login(email, password);
  const user = await fetchMeAs(access_token);
  setToken(access_token);
  auth.user = user;
}
