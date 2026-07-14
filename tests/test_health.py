def test_health_check(client):
    """Check if webserver is running"""
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
