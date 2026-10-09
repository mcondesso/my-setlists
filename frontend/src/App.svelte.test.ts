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

  it("shows a logged-out visitor the public setlists, not a login wall", async () => {
    render(App);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Setlists", level: 1 }),
      ).toBeInTheDocument();
    });
    expect(screen.queryByRole("heading", { name: "New setlist" })).toBeNull();
    expect(
      screen.getByText(
        "Browse the public setlists below, or log in to create your own.",
      ),
    ).toBeInTheDocument();
  });

  it("shows the login form at #/login", async () => {
    window.location.hash = "#/login";
    // hashchange fires asynchronously; let the router see it first.
    await new Promise((resolve) => setTimeout(resolve, 0));

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
    // to leave auth.token set with auth.user permanently null.
    setToken("stale-token");
    vi.mocked(fetchMe).mockRejectedValue(new Error("network error"));

    render(App);

    await waitFor(() => expect(auth.token).toBeNull());
    expect(
      screen.getByRole("navigation").querySelector('a[href="#/login"]'),
    ).toBeInTheDocument();
  });
});
