import { fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SetlistWithEntries } from "../lib/types";

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
    created_at: "now",
    entries: [],
    ...overrides,
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
