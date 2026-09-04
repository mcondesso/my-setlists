import { beforeEach, describe, expect, it } from "vitest";
import { auth, logout, setToken } from "./auth.svelte";

describe("auth store", () => {
  beforeEach(() => {
    logout();
    localStorage.clear();
  });

  it("setToken updates auth.token and persists it", () => {
    setToken("abc123");

    expect(auth.token).toBe("abc123");
    expect(localStorage.getItem("setlists.token")).toBe("abc123");
  });

  it("setToken(null) clears the persisted token", () => {
    setToken("abc123");

    setToken(null);

    expect(auth.token).toBeNull();
    expect(localStorage.getItem("setlists.token")).toBeNull();
  });

  it("logout clears both the token and the current user", () => {
    setToken("abc123");
    auth.user = { id: "1", email: "a@example.com", display_name: "Ada", created_at: "now" };

    logout();

    expect(auth.token).toBeNull();
    expect(auth.user).toBeNull();
  });
});
