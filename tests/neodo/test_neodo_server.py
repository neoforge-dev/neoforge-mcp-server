"""Tests for the NeoDO MCP Server."""

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pytest
from unittest import mock
import digitalocean
from httpx import AsyncClient
from server.neodo.server import NeoDOServer
from server.utils.config import ServerConfig # Import for expected config

# Fixtures moved to conftest.py (removed local client fixture)

# --- Health Check Test ---

def test_health_endpoint(neodo_client: TestClient, neodo_test_config: ServerConfig): # Use fixtures from conftest.py
    """Test the standard health endpoint from BaseServer."""
    response = neodo_client.get("/health") # Target root /health
    assert response.status_code == 200

    # Assert the expected BaseServer health response structure
    expected_response = {
        "status": "healthy",
        "service": "neodo_mcp", # Corrected expected service name
        "version": neodo_test_config.version,
        "monitoring": {
            "metrics": neodo_test_config.enable_metrics,
            "tracing": neodo_test_config.enable_tracing
        }
    }
    assert response.json() == expected_response


# --- DigitalOcean Endpoint Tests ---

def test_manage_resources_endpoint(neodo_client: TestClient, valid_api_key: str):
    """Test the manage resources endpoint."""
    headers = {"X-API-Key": valid_api_key}

    # Access mocks from app state configured in the fixture
    mock_manager = neodo_client.app.state.do_manager
    mock_droplet = mock_manager.get_droplet.return_value

    # Reset mocks before calls (good practice)
    mock_manager.reset_mock()
    mock_manager.get_droplet.return_value.reset_mock()

    # Test power on
    response = neodo_client.post("/api/v1/do/management", json={
        "action": "power_on",
        "resource_type": "droplet",
        "resource_id": 123
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    # Assert mock calls
    mock_manager.get_droplet.assert_called_once_with(123)
    mock_droplet.power_on.assert_called_once()

    # Reset mocks for next action
    mock_manager.reset_mock()
    mock_manager.get_droplet.return_value.reset_mock()

    # Test power off
    response = neodo_client.post("/api/v1/do/management", json={
        "action": "power_off",
        "resource_type": "droplet",
        "resource_id": 123
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    # Assert mock calls
    mock_manager.get_droplet.assert_called_once_with(123)
    mock_droplet.power_off.assert_called_once()

    # Reset mocks for next action
    mock_manager.reset_mock()
    mock_manager.get_droplet.return_value.reset_mock()

    # Test reboot
    response = neodo_client.post("/api/v1/do/management", json={
        "action": "reboot",
        "resource_type": "droplet",
        "resource_id": 123
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    # Assert mock calls
    mock_manager.get_droplet.assert_called_once_with(123)
    mock_droplet.reboot.assert_called_once()

def test_backup_resources_endpoint(neodo_client: TestClient, valid_api_key: str):
    """Test the backup resources endpoint."""
    headers = {"X-API-Key": valid_api_key}

    # Access mocks from app state
    mock_manager = neodo_client.app.state.do_manager
    mock_droplet = mock_manager.get_droplet.return_value
    mock_snapshot = mock_droplet.take_snapshot.return_value
    mock_snapshot.id = 456

    # Reset mocks
    mock_manager.reset_mock()
    mock_manager.get_droplet.return_value.reset_mock()
    mock_manager.get_droplet.return_value.take_snapshot.return_value.reset_mock()

    response = neodo_client.post("/api/v1/do/backup", json={
        "resource_type": "droplet",
        "resource_id": 123,
        "backup_name": "test-snapshot"
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["message"] == "Snapshot created successfully"
    assert response.json()["snapshot_id"] == 456 # Check snapshot ID from mock
    # Assert mock calls
    mock_manager.get_droplet.assert_called_once_with(123)
    mock_droplet.take_snapshot.assert_called_once_with(name="test-snapshot", power_off=False)