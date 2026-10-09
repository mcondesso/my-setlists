import { afterEach, describe, expect, it } from "vitest";
import { navigate, router, takeReturnPath } from "./router.svelte";

async function flush(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

afterEach(async () => {
  window.location.hash = "";
  await flush();
});

describe("router", () => {
  it("defaults to /setlists when there is no hash", () => {
    expect(router.path).toBe("/setlists");
  });

  it("navigate() sets the hash and updates router.path", async () => {
    navigate("/login");
    await flush();

    expect(window.location.hash).toBe("#/login");
    expect(router.path).toBe("/login");
  });

  it("reacts to the hash changing outside of navigate() too", async () => {
    window.location.hash = "#/setlists/abc-123";
    await flush();

    expect(router.path).toBe("/setlists/abc-123");
  });

  it("falls back to /setlists when the hash is cleared", async () => {
    navigate("/register");
    await flush();
    expect(router.path).toBe("/register");

    window.location.hash = "";
    await flush();
    expect(router.path).toBe("/setlists");
  });
});

describe("return path after logging in", () => {
  it("remembers the page the visitor left for /login", async () => {
    navigate("/setlists/abc-123");
    await flush();
    navigate("/login");
    await flush();

    expect(takeReturnPath()).toBe("/setlists/abc-123");
  });

  it("keeps the original page when hopping between /login and /register", async () => {
    navigate("/songs/xyz");
    await flush();
    navigate("/login");
    await flush();
    navigate("/register");
    await flush();

    expect(takeReturnPath()).toBe("/songs/xyz");
  });

  it("is used once, then falls back to /setlists", async () => {
    navigate("/songs/xyz");
    await flush();
    navigate("/login");
    await flush();

    takeReturnPath();
    expect(takeReturnPath()).toBe("/setlists");
  });
});
