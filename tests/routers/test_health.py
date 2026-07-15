"""Tests for the health check endpoint."""

from fastapi import status
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Check that the health endpoint returns ok status."""
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ok"
