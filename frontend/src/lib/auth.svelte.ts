import type { User } from "./types";

const STORAGE_KEY = "setlists.token";

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export const auth = $state<{ token: string | null; user: User | null }>({
  token: readStoredToken(),
  user: null,
});

export function setToken(token: string | null): void {
  auth.token = token;
  try {
    if (token) localStorage.setItem(STORAGE_KEY, token);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // localStorage unavailable (private mode, etc.) — falls back to session-only auth.
  }
}

export function logout(): void {
  setToken(null);
  auth.user = null;
}
