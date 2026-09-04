"""Tests for the CORS middleware configuration."""

from fastapi.testclient import TestClient

ALLOWED_ORIGIN = "http://localhost:5173"


def test_preflight_allows_the_configured_origin(client: TestClient):
    """A preflight request from the frontend's dev origin is allowed."""
    response = client.options(
        "/health",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_preflight_omits_the_header_for_an_unlisted_origin(client: TestClient):
    """
    A preflight from an origin that isn't allow-listed gets no
    Access-Control-Allow-Origin header, which is what makes the browser
    block the real request — CORSMiddleware still answers with 200, the
    enforcement happens client-side based on the missing header.
    """
    response = client.options(
        "/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_actual_response_includes_the_allow_origin_header(client: TestClient):
    """A normal (non-preflight) response also carries the header for an allowed origin."""
    response = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


def test_actual_response_omits_the_header_for_an_unlisted_origin(client: TestClient):
    response = client.get("/health", headers={"Origin": "http://evil.example.com"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_no_credentials_are_allowed(client: TestClient):
    """
    Auth is a Bearer token, never a cookie, so allow_credentials must stay
    False — flipping it to True alongside a concrete origin list would let
    a malicious page make credentialed requests using the browser's
    cookie jar, if this API ever grew cookie-based auth without revisiting
    this setting.
    """
    response = client.options(
        "/health",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-credentials" not in response.headers
