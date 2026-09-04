import { beforeEach, describe, expect, it, vi } from "vitest";
import { auth, logout } from "./auth.svelte";

vi.mock("./backend", () => ({
  login: vi.fn(),
  fetchMeAs: vi.fn(),
}));

import { fetchMeAs, login } from "./backend";
import { completeLogin } from "./session";

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
