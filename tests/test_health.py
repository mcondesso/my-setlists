import requests

def test_health_check(base_url):
    """Check if webserver is running"""
    response = requests.get(f"{base_url}/health")

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
