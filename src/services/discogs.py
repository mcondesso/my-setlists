"""Discogs API client for searching and retrieving music metadata."""

import httpx

from src.core.config import settings

DISCOGS_URL = "https://www.discogs.com"
DISCOGS_API_URL = "https://api.discogs.com"
DISCOGS_HEADERS = {
    "Authorization": f"Discogs token={settings.DISCOGS_API_TOKEN}",
    "User-Agent": "MySetlists/1.0",
}


class DiscogsSearchResult:
    """Shaped search result ready to be passed to POST /songs."""

    def __init__(
        self,
        discogs_id: str,
        title: str,
        artist: str,
        album: str | None,
        release_year: int | None,
        discogs_url: str | None,
        thumbnail: str | None,
    ) -> None:
        self.discogs_id = discogs_id
        self.title = title
        self.artist = artist
        self.album = album
        self.release_year = release_year
        self.discogs_url = discogs_url
        self.thumbnail = thumbnail


def search_discogs(query: str, limit: int = 5) -> list[DiscogsSearchResult]:
    """
    Search the Discogs API for recordings matching the query string.

    Returns up to `limit` results shaped as DiscogsSearchResult objects.
    Raises httpx.HTTPError if the Discogs API request fails.
    """
    response = httpx.get(
        f"{DISCOGS_API_URL}/database/search",
        headers=DISCOGS_HEADERS,
        params={
            "q": query,
            "type": "master",
            "per_page": limit,
            "page": 1,
        },
    )
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("results", []):
        artist, title = _parse_title(item.get("title", ""))
        url = None
        if uri := item.get("uri"):
            url = DISCOGS_URL + uri
        results.append(
            DiscogsSearchResult(
                discogs_id=str(item["id"]),
                title=title,
                artist=artist,
                album=None,
                release_year=_parse_year(item.get("year")),
                discogs_url=url,
                thumbnail=item.get("thumb"),
            )
        )
    return results


def _parse_title(raw_title: str) -> tuple[str, str]:
    """
    Split a Discogs title string into artist and title components.

    Discogs returns titles in the format 'Artist - Title'.
    Falls back to ('Unknown Artist', raw_title) if the format is unexpected.
    """
    if " - " in raw_title:
        artist, title = raw_title.split(" - ", maxsplit=1)
        return artist.strip(), title.strip()
    return "Unknown Artist", raw_title.strip()


def _parse_year(year: str | None) -> int | None:
    """Parse a year string to an integer, returning None if invalid."""
    try:
        return int(year) if year else None
    except (ValueError, TypeError):
        return None
