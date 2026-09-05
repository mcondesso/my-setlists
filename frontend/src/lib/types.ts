// Mirrors the response schemas in backend/src/models/*.py.

export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export type Platform =
  "discogs" | "youtube" | "spotify" | "apple_music" | "bandcamp";

export interface SongLink {
  platform: Platform;
  external_id: string;
  url: string | null;
}

interface SongBase {
  title: string;
  artist: string;
  duration_ms: number | null;
  album: string | null;
  release_year: number | null;
  thumbnail: string | null;
}

/** Matches response_model=SongRead — no `links`. What POST/PATCH /songs return. */
export interface SongRead extends SongBase {
  id: string;
}

/** Matches response_model=SongReadWithLinks — what the GET song endpoints return. */
export interface Song extends SongRead {
  links: SongLink[];
}

export interface SetlistEntry {
  setlist_id: string;
  song_id: string;
  position: number;
  added_at: string;
  song: Song;
}

export interface Setlist {
  id: string;
  name: string;
  description: string | null;
  is_public: boolean;
  is_library: boolean;
  owner_display_name: string;
  is_owner: boolean;
  created_at: string;
}

export interface SetlistWithEntries extends Setlist {
  entries: SetlistEntry[];
}

export interface DiscogsSearchResult {
  discogs_id: string;
  title: string;
  artist: string;
  album: string | null;
  release_year: number | null;
  discogs_url: string | null;
  thumbnail: string | null;
}
