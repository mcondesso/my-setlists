"""Discogs API client for searching and retrieving music metadata.

Discogs' search endpoint only matches at the release/master level (an
album), not individual tracks — searching "Darkside Heart" surfaces the
"Psychic" master, not the "Heart" track on it. search_discogs() works
around this by fetching each candidate master's full tracklist and
picking the track that best matches the query, so callers get individual
songs back rather than albums.
"""

import re
from concurrent.futures import ThreadPoolExecutor

import httpx

from src.core.config import settings

DISCOGS_URL = "https://www.discogs.com"
DISCOGS_API_URL = "https://api.discogs.com"
REQUEST_TIMEOUT_SECONDS = 10.0
DISCOGS_HEADERS = {
    "Authorization": f"Discogs token={settings.DISCOGS_API_TOKEN}",
    "User-Agent": "MySetlists/1.0",
}

# How many candidate masters (from the initial search) to inspect the
# tracklists of. Each one costs an extra Discogs API call, so this is kept
# well above `limit` (some masters won't have a good-matching track, or
# their detail fetch may fail) without letting a single search fan out too
# far.
CANDIDATE_MASTERS = 8


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
        duration_ms: int | None,
    ) -> None:
        self.discogs_id = discogs_id
        self.title = title
        self.artist = artist
        self.album = album
        self.release_year = release_year
        self.discogs_url = discogs_url
        self.thumbnail = thumbnail
        self.duration_ms = duration_ms


class _MasterCandidate:
    """A master release returned by the initial search, before its tracklist is fetched."""

    def __init__(
        self,
        master_id: int,
        artist: str,
        album: str,
        year: int | None,
        thumbnail: str | None,
        url: str | None,
    ) -> None:
        self.master_id = master_id
        self.artist = artist
        self.album = album
        self.year = year
        self.thumbnail = thumbnail
        self.url = url


def search_discogs(query: str, limit: int = 5) -> list[DiscogsSearchResult]:
    """
    Search the Discogs catalog for individual tracks matching the query.

    Discogs has no track-level search, so this searches masters (albums)
    first, then fetches the tracklist of up to CANDIDATE_MASTERS of them
    and scores every track's title against the query. Returns the
    `limit` best-matching tracks across all inspected masters.

    Raises httpx.HTTPError if the initial Discogs search request fails.
    A failure fetching one master's tracklist is not fatal — that
    candidate is just skipped in favour of the others.
    """
    masters = _search_masters(query, CANDIDATE_MASTERS)
    if not masters:
        return []

    # Each master's tracklist is a separate Discogs request; fetching them
    # concurrently keeps overall latency close to that of the slowest one
    # instead of their sum.
    with ThreadPoolExecutor(max_workers=len(masters)) as executor:
        tracklists = list(executor.map(lambda m: _fetch_tracklist(m.master_id), masters))

    scored: list[tuple[float, DiscogsSearchResult]] = []
    for master, tracks in zip(masters, tracklists, strict=True):
        for track_title, position, duration_ms in tracks:
            score = _match_score(query, track_title, master.artist)
            scored.append(
                (
                    score,
                    DiscogsSearchResult(
                        discogs_id=f"{master.master_id}-{position}",
                        title=track_title,
                        artist=master.artist,
                        album=master.album,
                        release_year=master.year,
                        discogs_url=master.url,
                        thumbnail=master.thumbnail,
                        duration_ms=duration_ms,
                    ),
                )
            )

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [result for _, result in scored[:limit]]


def _search_masters(query: str, limit: int) -> list[_MasterCandidate]:
    response = httpx.get(
        f"{DISCOGS_API_URL}/database/search",
        headers=DISCOGS_HEADERS,
        params={
            "q": query,
            "type": "master",
            "per_page": limit,
            "page": 1,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()

    masters = []
    for item in data.get("results", []):
        artist, album = _parse_title(item.get("title", ""))
        url = DISCOGS_URL + item["uri"] if item.get("uri") else None
        masters.append(
            _MasterCandidate(
                master_id=item["id"],
                artist=artist,
                album=album,
                year=_parse_year(item.get("year")),
                thumbnail=item.get("thumb"),
                url=url,
            )
        )
    return masters


def _fetch_tracklist(master_id: int) -> list[tuple[str, str, int | None]]:
    """
    Return (title, position, duration_ms) for every real track on a master.

    Returns an empty list if the lookup fails — the caller treats that
    master as having nothing to offer rather than failing the search.
    """
    try:
        response = httpx.get(
            f"{DISCOGS_API_URL}/masters/{master_id}",
            headers=DISCOGS_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    tracks = []
    for entry in response.json().get("tracklist", []):
        if entry.get("type_") != "track":
            continue
        title = (entry.get("title") or "").strip()
        if title:
            tracks.append(
                (
                    title,
                    entry.get("position") or title,
                    _parse_duration(entry.get("duration")),
                )
            )
    return tracks


def _parse_duration(duration: str | None) -> int | None:
    """Parse a Discogs 'M:SS' or 'H:MM:SS' duration string into milliseconds."""
    if not duration:
        return None
    parts = duration.strip().split(":")
    try:
        parts_int = [int(part) for part in parts]
    except ValueError:
        return None
    seconds = 0
    for part in parts_int:
        seconds = seconds * 60 + part
    return seconds * 1000 if seconds > 0 else None


def _match_score(query: str, track_title: str, artist: str) -> float:
    """
    How well a track matches the search query, 0-1 (an F1 score over words).

    Word overlap, not raw character-sequence similarity: "Zombie
    Cranberries" and "Cranberries Zombie" must score identically, and a
    track whose title merely contains extra words the query doesn't ask
    for (e.g. "Darkside Of The Heart" against the query "Darkside Heart")
    must not outrank the track that's actually just "Heart" by Darkside.
    Precision (how much of the candidate's words are in the query) does
    that job; recall (how much of the query is covered) rewards actually
    containing every word asked for.
    """
    query_words = _words(query)
    candidate_words = _words(track_title) | _words(artist)
    matched = query_words & candidate_words
    if not matched:
        return 0.0
    precision = len(matched) / len(candidate_words)
    recall = len(matched) / len(query_words)
    return 2 * precision * recall / (precision + recall)


def _words(text: str) -> set[str]:
    return set(_normalize(text).split())


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


# Discogs disambiguates same-named artists with a trailing index, e.g.
# "Darkside (22)" — strip it so the stored artist name is clean.
_ARTIST_DISAMBIGUATOR = re.compile(r"\s*\(\d+\)$")


def _parse_title(raw_title: str) -> tuple[str, str]:
    """
    Split a Discogs title string into artist and title components.

    Discogs returns titles in the format 'Artist - Title'.
    Falls back to ('Unknown Artist', raw_title) if the format is unexpected.
    """
    if " - " in raw_title:
        artist, title = raw_title.split(" - ", maxsplit=1)
        return _ARTIST_DISAMBIGUATOR.sub("", artist.strip()), title.strip()
    return "Unknown Artist", raw_title.strip()


def _parse_year(year: str | None) -> int | None:
    """Parse a year string to an integer, returning None if invalid."""
    try:
        return int(year) if year else None
    except (ValueError, TypeError):
        return None
