import { afterEach, describe, expect, it } from "vitest";
import { navigate, router } from "./router.svelte";

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
