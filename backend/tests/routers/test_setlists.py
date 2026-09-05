"""TestClient coverage for the setlist routes and their response shape."""

from fastapi import status
from fastapi.testclient import TestClient


def _create_setlist(client: TestClient, name: str = "Live Set", **fields) -> dict:
    response = client.post("/setlists/", json={"name": name, **fields})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def _create_song(client: TestClient, title: str) -> str:
    response = client.post("/songs/", json={"title": title, "artist": "Artist"})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def test_create_setlist(authenticated_client: TestClient) -> None:
    body = _create_setlist(authenticated_client, "Encore", description="last songs")

    assert body["name"] == "Encore"
    assert body["owner_display_name"] == "Test User"
    assert body["is_library"] is False


def test_list_omits_entries(authenticated_client: TestClient) -> None:
    _create_setlist(authenticated_client)

    listed = authenticated_client.get("/setlists/")

    assert listed.status_code == status.HTTP_200_OK
    assert listed.json()
    assert all("entries" not in item for item in listed.json())


def test_list_is_paginated(authenticated_client: TestClient) -> None:
    for i in range(3):
        _create_setlist(authenticated_client, f"Set {i}")

    page = authenticated_client.get("/setlists/", params={"limit": 2})

    assert len(page.json()) == 2


def test_setlist_songs_are_returned_in_position_order(
    authenticated_client: TestClient,
) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]
    song_ids = [_create_song(authenticated_client, t) for t in ("First", "Second", "Third")]
    for song_id in song_ids:
        added = authenticated_client.post(f"/setlists/{setlist_id}/songs/{song_id}")
        assert added.status_code == status.HTTP_201_CREATED

    detail = authenticated_client.get(f"/setlists/{setlist_id}")
    assert [entry["position"] for entry in detail.json()["entries"]] == [1, 2, 3]

    by_position = authenticated_client.get(f"/setlists/{setlist_id}/songs")
    assert [e["song"]["title"] for e in by_position.json()] == ["First", "Second", "Third"]

    by_recent = authenticated_client.get(
        f"/setlists/{setlist_id}/songs", params={"order": "recent"}
    )
    assert by_recent.status_code == status.HTTP_200_OK
    assert {e["song"]["title"] for e in by_recent.json()} == {"First", "Second", "Third"}


def test_adding_the_same_song_twice_is_rejected(authenticated_client: TestClient) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]
    song_id = _create_song(authenticated_client, "Once")

    authenticated_client.post(f"/setlists/{setlist_id}/songs/{song_id}")
    again = authenticated_client.post(f"/setlists/{setlist_id}/songs/{song_id}")

    assert again.status_code == status.HTTP_400_BAD_REQUEST


def test_library_setlist_cannot_be_deleted(authenticated_client: TestClient) -> None:
    library = next(s for s in authenticated_client.get("/setlists/").json() if s["is_library"])

    response = authenticated_client.delete(f"/setlists/{library['id']}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_setlists_require_authentication(client: TestClient) -> None:
    assert client.get("/setlists/").status_code == status.HTTP_401_UNAUTHORIZED


def test_update_setlist_name_and_description(authenticated_client: TestClient) -> None:
    setlist = _create_setlist(authenticated_client, "Draft", description="wip")

    response = authenticated_client.patch(
        f"/setlists/{setlist['id']}",
        json={"name": "Final", "description": "ready to play"},
    )

    # Regression test: this 500ed with a ResponseValidationError — the
    # handler returned the bare ORM object instead of building a SetlistRead
    # (which needs owner_display_name, not a column on the model), and
    # nothing but a real HTTP round-trip could catch it.
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["name"] == "Final"
    assert body["description"] == "ready to play"
    assert body["owner_display_name"] == "Test User"

    refetched = authenticated_client.get(f"/setlists/{setlist['id']}")
    assert refetched.json()["name"] == "Final"


def test_update_setlist_clears_description_with_null(authenticated_client: TestClient) -> None:
    setlist = _create_setlist(authenticated_client, "Draft", description="wip")

    response = authenticated_client.patch(f"/setlists/{setlist['id']}", json={"description": None})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["description"] is None


def test_update_library_setlist_name_is_rejected(authenticated_client: TestClient) -> None:
    library = next(s for s in authenticated_client.get("/setlists/").json() if s["is_library"])

    response = authenticated_client.patch(f"/setlists/{library['id']}", json={"name": "Renamed"})

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_missing_setlist_returns_404(authenticated_client: TestClient) -> None:
    response = authenticated_client.patch(
        "/setlists/00000000-0000-0000-0000-000000000000", json={"name": "X"}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
