from fastapi import status
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Check if webserver is running"""
    response = client.get("/health")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ok"
