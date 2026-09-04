// Typed wrappers around the my-setlists API. Keeps request/response shaping
// out of the page components.

import { api } from "./api";
import type { DiscogsSearchResult, Setlist, SetlistWithEntries, Song, User } from "./types";

export function login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
  const form = new URLSearchParams({ username: email, password });
  return api.postForm("/auth/login", form);
}

export function register(email: string, displayName: string, password: string): Promise<User> {
  return api.post("/auth/register", { email, display_name: displayName, password });
}

export function fetchMe(): Promise<User> {
  return api.get("/users/me");
}

export function fetchSetlists(): Promise<Setlist[]> {
  return api.get("/setlists/");
}

export function fetchSetlist(id: string): Promise<SetlistWithEntries> {
  return api.get(`/setlists/${id}`);
}

export function createSetlist(data: {
  name: string;
  description?: string;
  is_public?: boolean;
}): Promise<Setlist> {
  return api.post("/setlists/", data);
}

export function removeSongFromSetlist(setlistId: string, songId: string): Promise<void> {
  return api.delete(`/setlists/${setlistId}/songs/${songId}`);
}

export function searchSongs(query: string): Promise<DiscogsSearchResult[]> {
  return api.get(`/songs/search?q=${encodeURIComponent(query)}`);
}

export function addSongToSetlist(setlistId: string, result: DiscogsSearchResult): Promise<Song> {
  return api.post("/songs/", {
    title: result.title,
    artist: result.artist,
    album: result.album,
    release_year: result.release_year,
    thumbnail: result.thumbnail,
    discogs_id: result.discogs_id,
    discogs_url: result.discogs_url,
    setlist_ids: [setlistId],
  });
}
