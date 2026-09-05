import { fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SetlistEntry, SetlistWithEntries } from "../lib/types";

vi.mock("../lib/backend", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/backend")>();
  return {
    ...actual,
    fetchSetlist: vi.fn(),
    updateSetlist: vi.fn(),
  };
});

import { fetchSetlist, updateSetlist } from "../lib/backend";
import SetlistDetail from "./SetlistDetail.svelte";

function setlist(
  id: string,
  name: string,
  overrides: Partial<SetlistWithEntries> = {},
): SetlistWithEntries {
  return {
    id,
    name,
    description: null,
    is_public: false,
    is_library: false,
    owner_display_name: "Ada",
    is_owner: true,
    created_at: "now",
    entries: [],
    ...overrides,
  };
}

function songEntry(
  songId: string,
  title: string,
  overrides: Partial<SetlistEntry["song"]> = {},
): SetlistEntry {
  return {
    setlist_id: "a",
    song_id: songId,
    position: 1,
    added_at: "now",
    song: {
      id: songId,
      title,
      artist: "Artist",
      duration_ms: null,
      album: null,
      release_year: null,
      thumbnail: null,
      links: [],
      ...overrides,
    },
  };
}

describe("SetlistDetail", () => {
  beforeEach(() => {
    vi.mocked(updateSetlist).mockReset();
  });

  it("edits the name and description via the Edit button", async () => {
    vi.mocked(fetchSetlist).mockResolvedValue(
      setlist("a", "Old Name", { description: "Old description" }),
    );
    vi.mocked(updateSetlist).mockResolvedValue({
      id: "a",
      name: "New Name",
      description: "New description",
      is_public: false,
      is_library: false,
      owner_display_name: "Ada",
      is_owner: true,
      created_at: "now",
    });

    render(SetlistDetail, { props: { id: "a" } });
    await waitFor(() => screen.getByRole("heading", { name: "Old Name" }));

    await fireEvent.click(screen.getByRole("button", { name: "Edit" }));

    const nameInput = screen.getByLabelText("Name");
    const descriptionInput = screen.getByLabelText("Description");
    await fireEvent.input(nameInput, { target: { value: "New Name" } });
    await fireEvent.input(descriptionInput, {
      target: { value: "New description" },
    });
    await fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => screen.getByRole("heading", { name: "New Name" }));
    expect(screen.getByText("New description")).toBeInTheDocument();
    expect(updateSetlist).toHaveBeenCalledWith("a", {
      name: "New Name",
      description: "New description",
    });
  });

  it("sends null to clear the description, not an omitted field", async () => {
    vi.mocked(fetchSetlist).mockResolvedValue(
      setlist("a", "Old Name", { description: "Old description" }),
    );
    vi.mocked(updateSetlist).mockResolvedValue({
      id: "a",
      name: "Old Name",
      description: null,
      is_public: false,
      is_library: false,
      owner_display_name: "Ada",
      is_owner: true,
      created_at: "now",
    });

    render(SetlistDetail, { props: { id: "a" } });
    await waitFor(() => screen.getByRole("heading", { name: "Old Name" }));

    await fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    await fireEvent.input(screen.getByLabelText("Description"), {
      target: { value: "" },
    });
    await fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(updateSetlist).toHaveBeenCalledWith("a", {
        name: "Old Name",
        description: null,
      }),
    );
  });

  it("does not offer editing for the library setlist", async () => {
    vi.mocked(fetchSetlist).mockResolvedValue(
      setlist("a", "Library", { is_library: true }),
    );

    render(SetlistDetail, { props: { id: "a" } });
    await waitFor(() => screen.getByRole("heading", { name: "Library" }));

    expect(
      screen.queryByRole("button", { name: "Edit" }),
    ).not.toBeInTheDocument();
  });

  it("does not offer editing, adding, or removing on someone else's public setlist", async () => {
    // Regression test: these actions all call owner-only endpoints, so a
    // non-owner viewing a public setlist must not be shown UI that would
    // just 403 on submit.
    vi.mocked(fetchSetlist).mockResolvedValue(
      setlist("a", "Someone Else's Set", {
        is_owner: false,
        is_public: true,
        entries: [songEntry("s1", "Song")],
      }),
    );

    render(SetlistDetail, { props: { id: "a" } });
    await waitFor(() =>
      screen.getByRole("heading", { name: "Someone Else's Set" }),
    );

    expect(
      screen.queryByRole("button", { name: "Edit" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Remove" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText("Search Discogs…")).toBeNull();
  });

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

  it("shows each song's duration in the list", async () => {
    vi.mocked(fetchSetlist).mockResolvedValue(
      setlist("a", "My Set", {
        entries: [songEntry("s1", "Song", { duration_ms: 185000 })],
      }),
    );

    render(SetlistDetail, { props: { id: "a" } });

    await waitFor(() => screen.getByRole("heading", { name: "My Set" }));
    expect(screen.getByText(/3:05/)).toBeInTheDocument();
  });
});
