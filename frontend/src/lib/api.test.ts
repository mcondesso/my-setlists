import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, errorMessage, normalizeBaseUrl } from "./api";
import { auth, logout, setToken } from "./auth.svelte";

function mockFetchOnce(
  response: Partial<Response> & { json?: () => Promise<unknown> },
) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => ({}),
    ...response,
  } as Response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("normalizeBaseUrl", () => {
  it("strips one or more trailing slashes", () => {
    expect(normalizeBaseUrl("http://localhost:8000/")).toBe(
      "http://localhost:8000",
    );
    expect(normalizeBaseUrl("http://localhost:8000///")).toBe(
      "http://localhost:8000",
    );
  });

  it("leaves a URL with no trailing slash untouched", () => {
    expect(normalizeBaseUrl("http://localhost:8000")).toBe(
      "http://localhost:8000",
    );
  });
});

describe("errorMessage", () => {
  it("uses the ApiError's message", () => {
    expect(errorMessage(new ApiError(400, "bad request"), "fallback")).toBe(
      "bad request",
    );
  });

  it("uses the fallback for anything that isn't an ApiError", () => {
    expect(errorMessage(new Error("boom"), "fallback")).toBe("fallback");
    expect(errorMessage("not an error", "fallback")).toBe("fallback");
  });
});

describe("api requests", () => {
  beforeEach(() => {
    logout();
    vi.unstubAllGlobals();
  });

  it("attaches the stored bearer token", async () => {
    setToken("stored-token");
    const fetchMock = mockFetchOnce({ json: async () => ({ ok: true }) });

    await api.get("/whoami");

    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Headers).get("Authorization")).toBe(
      "Bearer stored-token",
    );
  });

  it("lets a caller-supplied Authorization header win over the stored token", async () => {
    setToken("stored-token");
    const fetchMock = mockFetchOnce({ json: async () => ({}) });

    await api.get("/whoami", {
      headers: { Authorization: "Bearer explicit-token" },
    });

    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Headers).get("Authorization")).toBe(
      "Bearer explicit-token",
    );
  });

  it("logs out on a 401 so a stale token isn't retried", async () => {
    setToken("expired-token");
    mockFetchOnce({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({ detail: "Could not validate credentials" }),
    });

    await expect(api.get("/secret")).rejects.toBeInstanceOf(ApiError);

    expect(auth.token).toBeNull();
  });

  it("extracts a FastAPI-style string detail on error", async () => {
    mockFetchOnce({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ detail: "Email already registered" }),
    });

    await expect(api.get("/x")).rejects.toThrow("Email already registered");
  });

  it("extracts slowapi's {error} shape on a 429", async () => {
    mockFetchOnce({
      ok: false,
      status: 429,
      statusText: "Too Many Requests",
      json: async () => ({ error: "Rate limit exceeded: 5 per 1 minute" }),
    });

    await expect(api.get("/auth/login")).rejects.toThrow(
      "Rate limit exceeded: 5 per 1 minute",
    );
  });

  it("falls back to the status text when the error body isn't JSON", async () => {
    mockFetchOnce({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: async () => {
        throw new Error("not json");
      },
    });

    await expect(api.get("/x")).rejects.toThrow("Bad Gateway");
  });

  it("returns undefined for a 204 without reading the body", async () => {
    const readBody = vi.fn();
    mockFetchOnce({ status: 204, json: readBody });

    await expect(api.delete("/x")).resolves.toBeUndefined();
    expect(readBody).not.toHaveBeenCalled();
  });
});
