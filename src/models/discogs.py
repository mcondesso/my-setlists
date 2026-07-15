"""Discogs search result response schemas."""

from pydantic import BaseModel


class DiscogsSearchResultRead(BaseModel):
    """
    Response schema for a single Discogs search result.

    Shaped to match the fields required by POST /songs, so the client
    can pick a result and pass it directly to save a song.
    """

    discogs_id: str
    title: str
    artist: str
    album: str | None
    release_year: int | None
    discogs_url: str | None
    thumbnail: str | None
