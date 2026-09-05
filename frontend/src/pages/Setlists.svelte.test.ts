import { render, screen, waitFor } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import type { Setlist } from "../lib/types";

vi.mock("../lib/backend", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/backend")>();
  return {
    ...actual,
    fetchSetlists: vi.fn(),
  };
});

import { fetchSetlists } from "../lib/backend";
import Setlists from "./Setlists.svelte";

function makeSetlists(
  count: number,
  startAt: number,
  overrides: Partial<Setlist> = {},
): Setlist[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `id-${startAt + i}`,
    name: `Setlist ${startAt + i}`,
    description: null,
    is_public: false,
    is_library: false,
    owner_display_name: "Ada",
    is_owner: true,
    created_at: "now",
    ...overrides,
  }));
}

describe("Setlists pagination", () => {
  it("shows Load more only while a full page comes back, and appends the next page", async () => {
    const firstPage = makeSetlists(20, 0);
    const secondPage = makeSetlists(5, 20);
    vi.mocked(fetchSetlists)
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce(secondPage);

    render(Setlists);

    await waitFor(() => {
      expect(screen.getByText("Setlist 0")).toBeInTheDocument();
    });
    expect(fetchSetlists).toHaveBeenNthCalledWith(1, 20, 0);
    const loadMore = screen.getByRole("button", { name: "Load more" });

    loadMore.click();

    await waitFor(() => {
      expect(screen.getByText("Setlist 20")).toBeInTheDocument();
    });
    expect(fetchSetlists).toHaveBeenNthCalledWith(2, 20, 20);
    // The second page was short (5 < 20), so there's nothing more to load.
    expect(
      screen.queryByRole("button", { name: "Load more" }),
    ).not.toBeInTheDocument();
  });

  it("hides Load more when the first page is already short", async () => {
    vi.mocked(fetchSetlists).mockResolvedValueOnce(makeSetlists(3, 0));

    render(Setlists);

    await waitFor(() => {
      expect(screen.getByText("Setlist 0")).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: "Load more" }),
    ).not.toBeInTheDocument();
  });
});

describe("Setlists grouping", () => {
  it("separates the caller's own setlists from public ones", async () => {
    vi.mocked(fetchSetlists).mockResolvedValueOnce([
      ...makeSetlists(2, 0, { is_owner: true }),
      ...makeSetlists(2, 10, { is_owner: false, owner_display_name: "Bob" }),
    ]);

    render(Setlists);

    await waitFor(() => screen.getByText("Setlist 0"));
    expect(
      screen.getByRole("heading", { name: "My setlists" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Public setlists" }),
    ).toBeInTheDocument();
  });

  it("omits a section heading when that group is empty", async () => {
    vi.mocked(fetchSetlists).mockResolvedValueOnce(
      makeSetlists(2, 0, { is_owner: true }),
    );

    render(Setlists);

    await waitFor(() => screen.getByText("Setlist 0"));
    expect(
      screen.getByRole("heading", { name: "My setlists" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Public setlists" }),
    ).not.toBeInTheDocument();
  });
});
