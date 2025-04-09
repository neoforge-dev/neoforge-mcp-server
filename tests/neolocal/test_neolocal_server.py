"""Tests for the NeoLocal MCP Server."""

from fastapi.testclient import TestClient


def test_neolocal_health_endpoint(neolocal_client: TestClient) -> None:
    """Test the health check endpoint for NeoLocalServer."""
    response = neolocal_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "neolocal_mcp"
    assert "version" in data
    assert "monitoring" in data
    assert data["monitoring"]["metrics"] is True
    assert data["monitoring"]["tracing"] is True


def test_local_development_endpoint(neolocal_client: TestClient) -> None:
    """Test the placeholder local-development endpoint."""
    # Get a valid API key from the app config
    valid_api_key = list(neolocal_client.app.state.config.api_keys.keys())[0]
    
    response = neolocal_client.post(
        "/api/v1/local-development",
        params={"action": "setup", "project_path": "/tmp/project"},
        headers={"X-API-Key": valid_api_key} # Use valid key
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["action"] == "setup"
    assert data["project_path"] == "/tmp/project"
    assert "result" in data


def test_local_testing_endpoint(neolocal_client: TestClient) -> None:
    """Test the placeholder local-testing endpoint."""
    # Get a valid API key from the app config
    valid_api_key = list(neolocal_client.app.state.config.api_keys.keys())[0]
    
    response = neolocal_client.post(
        "/api/v1/local-testing",
        params={"action": "run", "test_path": "/tmp/project/tests"},
        headers={"X-API-Key": valid_api_key} # Use valid key
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["action"] == "run"
    assert data["test_path"] == "/tmp/project/tests"
    assert "result" in data 