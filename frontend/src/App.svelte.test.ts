import { render, screen, waitFor } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { auth, logout, setToken } from "./lib/auth.svelte";

vi.mock("./lib/backend", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./lib/backend")>();
  return {
    ...actual,
    fetchMe: vi.fn(),
    fetchSetlists: vi.fn().mockResolvedValue([]),
  };
});

import { fetchMe } from "./lib/backend";
import App from "./App.svelte";

describe("App", () => {
  beforeEach(() => {
    logout();
    window.location.hash = "";
    vi.mocked(fetchMe).mockReset();
  });

  it("shows the login form when there is no stored token", () => {
    render(App);

    expect(screen.getByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });

  it("shows the setlists screen once a stored token is confirmed valid", async () => {
    setToken("good-token");
    vi.mocked(fetchMe).mockResolvedValue({
      id: "1",
      email: "a@example.com",
      display_name: "Ada",
      created_at: "now",
    });

    render(App);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Setlists" }),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Ada")).toBeInTheDocument();
  });

  it("logs back out if a stored token can no longer be verified", async () => {
    // Regression test: a non-401 fetchMe failure (network error, 500) used
    // to leave auth.token set with auth.user permanently null instead of
    // returning to the login screen.
    setToken("stale-token");
    vi.mocked(fetchMe).mockRejectedValue(new Error("network error"));

    render(App);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Log in" }),
      ).toBeInTheDocument();
    });
    expect(auth.token).toBeNull();
  });
});
