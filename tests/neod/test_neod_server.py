"""Tests for the NeoDevServer."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import logging

# Assuming config structure is similar to BaseServer test
from server.utils.config import ServerConfig

# Import the class to test
from server.neod.server import NeoDevServer

# --- Fixtures ---

@pytest.fixture
def mock_neod_config():
    """Provides a ServerConfig instance tailored for NeoDev tests."""
    return ServerConfig(
        name="neod_server",
        port=7445, # Default NeoDev port
        log_level="DEBUG",
        log_file="logs/neod_server_test.log",
        enable_metrics=False,
        enable_tracing=False,
        auth_token="test_neod_token",
        allowed_origins=["*"],
        # Add NeoDev specific config fields if needed later
    )

@pytest.fixture
def test_neod_server(mock_neod_config):
    """Creates an instance of NeoDevServer with mocked dependencies."""
    with patch('server.utils.config.ConfigManager.load_config') as MockLoadConfig, \
         patch('server.utils.base_server.LogManager') as MockLogManager, \
         patch('server.utils.base_server.MonitoringManager') as MockMonitoringManager, \
         patch('server.utils.base_server.SecurityManager') as MockSecurity:
         # No need to patch NeoDev specific managers yet (e.g., WorkspaceManager)

        # Configure mocks
        MockLoadConfig.return_value = mock_neod_config
        mock_logger_instance = MagicMock(spec=logging.Logger)
        MockLogManager.return_value.get_logger.return_value = mock_logger_instance
        MockMonitoringManager.return_value = None
        mock_security_instance = MagicMock()
        MockSecurity.return_value = mock_security_instance

        # Instantiate the server
        server = NeoDevServer()

        # Verify mocks were called as expected during BaseServer init
        MockLoadConfig.assert_called_once_with("neod_server")
        MockLogManager.assert_called_once()
        MockSecurity.assert_called_once()

        # Add mocks to instance for potential use in tests
        server._test_mocks = {
            "logger": mock_logger_instance,
            "monitor": None,
            "security": mock_security_instance,
            "LoadConfig": MockLoadConfig,
            "LogManager": MockLogManager,
            "MonitoringManager": MockMonitoringManager,
            "SecurityManager": MockSecurity
        }
        yield server

        # Optional: Add mock resets here if needed later

@pytest.fixture
def client(test_neod_server):
    """Provides a TestClient for the NeoDevServer instance."""
    return TestClient(test_neod_server.app)

# --- Test Cases ---

def test_neod_server_init(test_neod_server):
    """Test if NeoDevServer initializes correctly."""
    assert isinstance(test_neod_server, NeoDevServer)
    assert test_neod_server.app.title == "neod_server"
    # Add assertions for NeoDev specific components if they are added

def test_neod_health_endpoint(client, test_neod_server):
    """Test the inherited /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    expected_config = test_neod_server.config
    expected_response = {
        "status": "healthy",
        "service": expected_config.name, # Should be "neod_server"
        "version": expected_config.version,
        "monitoring": {
            "metrics": expected_config.enable_metrics,
            "tracing": expected_config.enable_tracing
        }
    }
    assert response.json() == expected_response

def test_list_workspaces_endpoint(client):
    """Test the placeholder /api/v1/workspaces endpoint."""
    # No mocking needed yet as the endpoint uses hardcoded data
    response = client.get("/api/v1/workspaces")
    assert response.status_code == 200

    # Check basic response structure
    response_data = response.json()
    assert "workspaces" in response_data
    assert isinstance(response_data["workspaces"], list)
    # Check placeholder data (optional, but good for confirming endpoint hit)
    assert len(response_data["workspaces"]) == 2
    assert response_data["workspaces"][0]["name"] == "project-a"

def test_analyze_feature_endpoint(client):
    """Test the placeholder /api/v1/analyze/{feature} endpoint."""
    feature_name = "test-feature"
    # No mocking needed yet
    response = client.post(f"/api/v1/analyze/{feature_name}")
    assert response.status_code == 200

    # Check basic response structure and placeholder data
    response_data = response.json()
    assert response_data["status"] == "ok"
    assert response_data["feature"] == feature_name
    assert "complexity" in response_data

# TODO: Add tests for NeoDev specific endpoints (/workspaces, /analyze)
# Replace these basic tests when real logic is implemented 