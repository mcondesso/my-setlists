"""Tests for the Gemini song-suggestion client."""

import json

import httpx
import pytest

from src.services import gemini


def _response(items, status_code: int = 200) -> httpx.Response:
    body = {"candidates": [{"content": {"parts": [{"text": json.dumps(items)}]}}]}
    request = httpx.Request("POST", gemini.GEMINI_API_URL)
    return httpx.Response(status_code, json=body, request=request)


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setattr(gemini.settings, "GEMINI_API_KEY", "test-key")


def test_raises_without_an_api_key(monkeypatch) -> None:
    monkeypatch.setattr(gemini.settings, "GEMINI_API_KEY", None)

    with pytest.raises(gemini.GeminiNotConfiguredError):
        gemini.suggest_songs([("Queen", "We Will Rock You")])


def test_sends_the_setlist_and_parses_suggestions(monkeypatch, api_key) -> None:
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, body=json)
        return _response([{"artist": "ABBA", "title": "Dancing Queen"}])

    monkeypatch.setattr(gemini.httpx, "post", fake_post)

    suggestions = gemini.suggest_songs(
        [("Queen", "We Will Rock You")], exclude=[("Michael Jackson", "Billie Jean")]
    )

    assert suggestions == [("ABBA", "Dancing Queen")]
    assert captured["headers"] == {"x-goog-api-key": "test-key"}
    assert captured["url"].endswith(f"/{gemini.settings.GEMINI_MODEL}:generateContent")
    prompt = captured["body"]["contents"][0]["parts"][0]["text"]
    assert "Queen - We Will Rock You" in prompt
    assert "Michael Jackson - Billie Jean" in prompt
    assert captured["body"]["generationConfig"]["responseMimeType"] == "application/json"


def test_skips_malformed_items_and_caps_at_three(monkeypatch, api_key) -> None:
    items = [
        {"artist": "A", "title": "1"},
        {"artist": "", "title": "no artist"},
        "not an object",
        {"artist": "B", "title": "2"},
        {"artist": "C", "title": "3"},
        {"artist": "D", "title": "4"},
    ]
    monkeypatch.setattr(gemini.httpx, "post", lambda *a, **kw: _response(items))

    assert gemini.suggest_songs([("X", "Y")]) == [("A", "1"), ("B", "2"), ("C", "3")]


def test_unexpected_response_shape_yields_no_suggestions(monkeypatch, api_key) -> None:
    request = httpx.Request("POST", gemini.GEMINI_API_URL)
    monkeypatch.setattr(
        gemini.httpx,
        "post",
        lambda *a, **kw: httpx.Response(200, json={"candidates": []}, request=request),
    )

    assert gemini.suggest_songs([("X", "Y")]) == []


def test_raises_on_an_http_error(monkeypatch, api_key) -> None:
    monkeypatch.setattr(gemini.httpx, "post", lambda *a, **kw: _response([], status_code=429))

    with pytest.raises(httpx.HTTPStatusError):
        gemini.suggest_songs([("X", "Y")])
