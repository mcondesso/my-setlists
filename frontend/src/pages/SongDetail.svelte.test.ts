import { fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import type { Setlist, Song } from "../lib/types";

vi.mock("../lib/backend", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/backend")>();
  return {
    ...actual,
    fetchSong: vi.fn(),
    fetchSetlists: vi.fn(),
    addExistingSongToSetlist: vi.fn(),
  };
});

import {
  addExistingSongToSetlist,
  fetchSetlists,
  fetchSong,
} from "../lib/backend";
import SongDetail from "./SongDetail.svelte";

function song(overrides: Partial<Song> = {}): Song {
  return {
    id: "song-1",
    title: "Heart",
    artist: "Darkside",
    duration_ms: null,
    album: null,
    release_year: null,
    thumbnail: null,
    links: [],
    ...overrides,
  };
}

function setlist(id: string, name: string, isOwner: boolean): Setlist {
  return {
    id,
    name,
    description: null,
    is_public: false,
    is_library: false,
    owner_display_name: isOwner ? "Me" : "Someone Else",
    is_owner: isOwner,
    created_at: "now",
  };
}

describe("SongDetail", () => {
  it("shows the song's title, artist, album, and year", async () => {
    vi.mocked(fetchSong).mockResolvedValue(
      song({ album: "Psychic", release_year: 2013, artist: "Darkside" }),
    );
    vi.mocked(fetchSetlists).mockResolvedValue([]);

    render(SongDetail, { props: { id: "song-1" } });

    await waitFor(() => screen.getByRole("heading", { name: "Heart" }));
    expect(screen.getByText(/Darkside/)).toBeInTheDocument();
    expect(screen.getByText(/Psychic/)).toBeInTheDocument();
    expect(screen.getByText(/2013/)).toBeInTheDocument();
  });

  it("links out to YouTube when a youtube link is present", async () => {
    vi.mocked(fetchSong).mockResolvedValue(
      song({
        links: [
          {
            platform: "youtube",
            external_id: "abc123",
            url: "https://youtube.com/watch?v=abc123",
          },
        ],
      }),
    );
    vi.mocked(fetchSetlists).mockResolvedValue([]);

    render(SongDetail, { props: { id: "song-1" } });
    await waitFor(() => screen.getByRole("heading", { name: "Heart" }));

    const link = screen.getByRole("link", { name: "Listen on YouTube" });
    expect(link).toHaveAttribute("href", "https://youtube.com/watch?v=abc123");
    expect(link.querySelector("svg.platform-icon")).toBeInTheDocument();
  });

  it("shows an icon for a Discogs link too", async () => {
    vi.mocked(fetchSong).mockResolvedValue(
      song({
        links: [
          {
            platform: "discogs",
            external_id: "5967",
            url: "https://www.discogs.com/master/5967",
          },
        ],
      }),
    );
    vi.mocked(fetchSetlists).mockResolvedValue([]);

    render(SongDetail, { props: { id: "song-1" } });
    await waitFor(() => screen.getByRole("heading", { name: "Heart" }));

    const link = screen.getByRole("link", { name: "View on Discogs" });
    expect(link.querySelector("svg.platform-icon")).toBeInTheDocument();
  });

  it("does not show a links list when no link has a url", async () => {
    vi.mocked(fetchSong).mockResolvedValue(
      song({ links: [{ platform: "youtube", external_id: "x", url: null }] }),
    );
    vi.mocked(fetchSetlists).mockResolvedValue([]);

    render(SongDetail, { props: { id: "song-1" } });
    await waitFor(() => screen.getByRole("heading", { name: "Heart" }));

    const links = screen
      .getAllByRole("link")
      .filter((link) => link.textContent !== "← All setlists");
    expect(links).toHaveLength(0);
  });

  it("only offers the viewer's own setlists in the add-to picker", async () => {
    vi.mocked(fetchSong).mockResolvedValue(song());
    vi.mocked(fetchSetlists).mockResolvedValue([
      setlist("mine", "My Setlist", true),
      setlist("theirs", "Their Public Setlist", false),
    ]);

    render(SongDetail, { props: { id: "song-1" } });
    await waitFor(() => screen.getByRole("heading", { name: "Heart" }));

    expect(
      screen.getByRole("option", { name: "My Setlist" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("option", { name: "Their Public Setlist" }),
    ).not.toBeInTheDocument();
  });

  it("adds the song to the selected setlist and shows a confirmation", async () => {
    vi.mocked(fetchSong).mockResolvedValue(song());
    vi.mocked(fetchSetlists).mockResolvedValue([
      setlist("mine", "My Setlist", true),
    ]);
    vi.mocked(addExistingSongToSetlist).mockResolvedValue(undefined);

    render(SongDetail, { props: { id: "song-1" } });
    await waitFor(() => screen.getByRole("heading", { name: "Heart" }));

    await fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() =>
      expect(screen.getByText("Added to My Setlist.")).toBeInTheDocument(),
    );
    expect(addExistingSongToSetlist).toHaveBeenCalledWith("mine", "song-1");
  });

  it("tells the viewer they have no setlists to add to", async () => {
    vi.mocked(fetchSong).mockResolvedValue(song());
    vi.mocked(fetchSetlists).mockResolvedValue([
      setlist("theirs", "Their Public Setlist", false),
    ]);

    render(SongDetail, { props: { id: "song-1" } });
    await waitFor(() => screen.getByRole("heading", { name: "Heart" }));

    expect(
      screen.getByText("You don't have any setlists yet."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Add" }),
    ).not.toBeInTheDocument();
  });

  it("shows an error message when the song fails to load", async () => {
    vi.mocked(fetchSong).mockRejectedValue(new Error("boom"));
    vi.mocked(fetchSetlists).mockResolvedValue([]);

    render(SongDetail, { props: { id: "song-1" } });

    await waitFor(() =>
      expect(screen.getByText("Could not load song.")).toBeInTheDocument(),
    );
  });
});
