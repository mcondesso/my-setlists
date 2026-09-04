import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { auth, logout, setToken } from "./auth.svelte";

vi.mock("./backend", () => ({
  login: vi.fn(),
  fetchMeAs: vi.fn(),
  refreshToken: vi.fn(),
}));

import { fetchMeAs, login, refreshToken } from "./backend";
import { completeLogin, startSessionRefresh } from "./session";

describe("completeLogin", () => {
  beforeEach(() => {
    logout();
    vi.mocked(login).mockReset();
    vi.mocked(fetchMeAs).mockReset();
  });

  it("sets auth.token and auth.user only once both calls succeed", async () => {
    vi.mocked(login).mockResolvedValue({
      access_token: "tok",
      token_type: "bearer",
    });
    vi.mocked(fetchMeAs).mockResolvedValue({
      id: "1",
      email: "a@example.com",
      display_name: "Ada",
      created_at: "now",
    });

    await completeLogin("a@example.com", "password123");

    expect(auth.token).toBe("tok");
    expect(auth.user?.display_name).toBe("Ada");
    expect(fetchMeAs).toHaveBeenCalledWith("tok");
  });

  it("leaves auth untouched if the profile fetch fails right after a successful login", async () => {
    // Regression test: this is the exact sequence that used to leave the app
    // stuck showing an authenticated screen with no user profile (issue
    // fixed by validating the token via fetchMeAs before calling setToken).
    vi.mocked(login).mockResolvedValue({
      access_token: "tok",
      token_type: "bearer",
    });
    vi.mocked(fetchMeAs).mockRejectedValue(new Error("network blip"));

    await expect(completeLogin("a@example.com", "password123")).rejects.toThrow(
      "network blip",
    );

    expect(auth.token).toBeNull();
    expect(auth.user).toBeNull();
  });

  it("never calls fetchMeAs if login itself fails", async () => {
    vi.mocked(login).mockRejectedValue(new Error("bad credentials"));

    await expect(completeLogin("a@example.com", "wrong")).rejects.toThrow(
      "bad credentials",
    );

    expect(fetchMeAs).not.toHaveBeenCalled();
    expect(auth.token).toBeNull();
  });
});

describe("startSessionRefresh", () => {
  beforeEach(() => {
    logout();
    vi.mocked(refreshToken).mockReset();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does nothing on a tick while logged out", async () => {
    startSessionRefresh(1000);

    await vi.advanceTimersByTimeAsync(1000);

    expect(refreshToken).not.toHaveBeenCalled();
  });

  it("refreshes the token on every tick while logged in", async () => {
    setToken("initial");
    vi.mocked(refreshToken).mockResolvedValue({
      access_token: "refreshed-1",
      token_type: "bearer",
    });

    startSessionRefresh(1000);
    await vi.advanceTimersByTimeAsync(1000);
    expect(auth.token).toBe("refreshed-1");

    vi.mocked(refreshToken).mockResolvedValue({
      access_token: "refreshed-2",
      token_type: "bearer",
    });
    await vi.advanceTimersByTimeAsync(1000);
    expect(auth.token).toBe("refreshed-2");
  });

  it("stops once the returned cleanup function is called", async () => {
    setToken("initial");
    vi.mocked(refreshToken).mockResolvedValue({
      access_token: "refreshed",
      token_type: "bearer",
    });

    const stop = startSessionRefresh(1000);
    stop();
    await vi.advanceTimersByTimeAsync(5000);

    expect(refreshToken).not.toHaveBeenCalled();
  });
});
