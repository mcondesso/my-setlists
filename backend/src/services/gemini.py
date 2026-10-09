"""Gemini API client for suggesting songs that fit a setlist."""

import json
from collections.abc import Sequence

import httpx

from src.core.config import settings

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT_SECONDS = 30.0
SUGGESTION_COUNT = 3

# Structured output: Gemini returns exactly this JSON shape, so there's no
# free-form text to parse.
_RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "artist": {"type": "STRING"},
            "title": {"type": "STRING"},
        },
        "required": ["artist", "title"],
    },
}


class GeminiNotConfiguredError(RuntimeError):
    """GEMINI_API_KEY is not set."""


def suggest_songs(
    songs: Sequence[tuple[str, str]],
    exclude: Sequence[tuple[str, str]] = (),
) -> list[tuple[str, str]]:
    """
    Ask Gemini for up to SUGGESTION_COUNT (artist, title) songs that fit the
    given setlist, avoiding the setlist's own songs and any in `exclude`.

    The suggestions are unverified — the model can name songs that don't
    exist, so callers should check them against a real catalog.

    Raises GeminiNotConfiguredError without an API key, and httpx.HTTPError
    if the request fails.
    """
    if not settings.GEMINI_API_KEY:
        raise GeminiNotConfiguredError("GEMINI_API_KEY is not set")

    response = httpx.post(
        f"{GEMINI_API_URL}/{settings.GEMINI_MODEL}:generateContent",
        headers={"x-goog-api-key": settings.GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": _build_prompt(songs, exclude)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _RESPONSE_SCHEMA,
            },
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return _parse_suggestions(response.json())


def _build_prompt(songs: Sequence[tuple[str, str]], exclude: Sequence[tuple[str, str]]) -> str:
    def as_lines(pairs: Sequence[tuple[str, str]]) -> str:
        return "\n".join(f"{artist} - {title}" for artist, title in pairs)

    prompt = (
        "These songs make up a musical setlist, one per line as 'Artist - Title':\n"
        f"{as_lines(songs)}\n\n"
        f"Suggest {SUGGESTION_COUNT} other real, existing songs that would fit well "
        "in this setlist. Do not suggest any song that is already in it."
    )
    if exclude:
        prompt += f" Also do not suggest any of these:\n{as_lines(exclude)}"
    return prompt


def _parse_suggestions(body: dict) -> list[tuple[str, str]]:
    """Pull (artist, title) pairs out of a generateContent response, skipping junk."""
    try:
        items = json.loads(body["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return []
    if not isinstance(items, list):
        return []

    suggestions = []
    for item in items:
        if not isinstance(item, dict):
            continue
        artist = str(item.get("artist") or "").strip()
        title = str(item.get("title") or "").strip()
        if artist and title:
            suggestions.append((artist, title))
    return suggestions[:SUGGESTION_COUNT]
