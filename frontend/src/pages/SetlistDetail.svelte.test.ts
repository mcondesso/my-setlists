import { render, screen, waitFor } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import type { SetlistWithEntries } from "../lib/types";

vi.mock("../lib/backend", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/backend")>();
  return {
    ...actual,
    fetchSetlist: vi.fn(),
  };
});

import { fetchSetlist } from "../lib/backend";
import SetlistDetail from "./SetlistDetail.svelte";

function setlist(id: string, name: string): SetlistWithEntries {
  return {
    id,
    name,
    description: null,
    is_public: false,
    is_library: false,
    owner_display_name: "Ada",
    created_at: "now",
    entries: [],
  };
}

describe("SetlistDetail", () => {
  it("ignores a slower, stale response after navigating to a different setlist", async () => {
    // Regression test for the load-token guard: setlist A's request is
    // in flight when the user navigates to setlist B; B resolves first,
    // and A's late response must not overwrite it.
    let resolveA!: (value: SetlistWithEntries) => void;
    let resolveB!: (value: SetlistWithEntries) => void;
    const pendingA = new Promise<SetlistWithEntries>((resolve) => {
      resolveA = resolve;
    });
    const pendingB = new Promise<SetlistWithEntries>((resolve) => {
      resolveB = resolve;
    });

    vi.mocked(fetchSetlist).mockImplementation((id: string) =>
      id === "a" ? pendingA : pendingB,
    );

    const { rerender } = render(SetlistDetail, { props: { id: "a" } });
    await rerender({ id: "b" });

    resolveB(setlist("b", "Setlist B"));
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Setlist B" }),
      ).toBeInTheDocument();
    });

    resolveA(setlist("a", "Setlist A"));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(
      screen.getByRole("heading", { name: "Setlist B" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Setlist A" }),
    ).not.toBeInTheDocument();
  });
});
