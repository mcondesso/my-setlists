import { auth, logout } from "./auth.svelte";

/** Exported for testing — pure string logic, no import.meta.env plumbing needed. */
export function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

const BASE_URL: string = normalizeBaseUrl(
  import.meta.env.VITE_API_URL ?? "http://localhost:8000",
);

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** Shorthand for the `err instanceof ApiError ? err.message : fallback` check every catch block needs. */
export function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (body.detail) return JSON.stringify(body.detail);
    // slowapi's rate-limit handler uses {"error": "..."} rather than {"detail": "..."}.
    if (typeof body.error === "string") return body.error;
  } catch {
    // Response body wasn't JSON (or was empty) — fall through to the status text.
  }
  return response.statusText || `Request failed with status ${response.status}`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  // A caller-supplied Authorization header wins — used to validate a fresh
  // token (see lib/session.ts) before it becomes the app-wide auth.token.
  if (!headers.has("Authorization") && auth.token) {
    headers.set("Authorization", `Bearer ${auth.token}`);
  }
  if (
    init.body &&
    !(init.body instanceof URLSearchParams) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (response.status === 401) {
    // The token is missing, expired, or invalid — drop it so the UI falls
    // back to the login screen instead of retrying with a stale token.
    logout();
  }

  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorMessage(response));
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, init?: RequestInit): Promise<T> =>
    request<T>(path, init),
  post: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string): Promise<T> =>
    request<T>(path, { method: "DELETE" }),
  postForm: <T>(path: string, form: URLSearchParams): Promise<T> =>
    request<T>(path, { method: "POST", body: form }),
};
