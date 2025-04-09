"""Tests for the NeoOpsServer."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import logging

# Assuming config structure is similar to BaseServer test
from server.utils.config import ServerConfig

# Import the class to test
from server.neoo.server import NeoOpsServer

# --- Fixtures ---

@pytest.fixture
def mock_neoo_config():
    """Provides a ServerConfig instance tailored for NeoOps tests."""
    return ServerConfig(
        name="neoo_server",
        port=7446, # Default NeoOps port
        log_level="DEBUG",
        log_file="logs/neoo_server_test.log",
        enable_metrics=False,
        enable_tracing=False,
        auth_token="test_neoo_token",
        allowed_origins=["*"],
        # Add NeoOps specific config fields if needed later
    )

@pytest.fixture
def test_neoo_server(mock_neoo_config):
    """Creates an instance of NeoOpsServer with mocked dependencies."""
    with patch('server.utils.config.ConfigManager.load_config') as MockLoadConfig, \
         patch('server.utils.base_server.LogManager') as MockLogManager, \
         patch('server.utils.base_server.MonitoringManager') as MockMonitoringManager, \
         patch('server.utils.base_server.SecurityManager') as MockSecurity, \
         patch('server.utils.error_handling.logger') as MockDecoratorLogger:
         # No need to patch NeoOps specific managers yet

        # Configure mocks
        MockLoadConfig.return_value = mock_neoo_config
        mock_logger_instance = MagicMock() # Use a general MagicMock
        # Explicitly add the 'bind' method and make it return the mock instance
        mock_logger_instance.bind = MagicMock(return_value=mock_logger_instance)
        MockLogManager.return_value.get_logger.return_value = mock_logger_instance

        # Mock logger used by the decorator (needs bind method too)
        MockDecoratorLogger.bind.return_value = MockDecoratorLogger

        MockMonitoringManager.return_value = None
        mock_security_instance = MagicMock()
        MockSecurity.return_value = mock_security_instance

        # Instantiate the server
        server = NeoOpsServer()

        # Verify mocks were called as expected during init
        MockLoadConfig.assert_called_once_with(server_name="neoo_server")
        MockLogManager.assert_called_once()
        MockSecurity.assert_called_once()

        # Add mocks to instance for potential use in tests
        server._test_mocks = {
            "logger": mock_logger_instance,
            "decorator_logger": MockDecoratorLogger,
            "monitor": None,
            "security": mock_security_instance,
            "LoadConfig": MockLoadConfig,
            "LogManager": MockLogManager,
            "MonitoringManager": MockMonitoringManager,
            "SecurityManager": MockSecurity
        }
        yield server

@pytest.fixture
def client(test_neoo_server):
    """Provides a TestClient for the NeoOpsServer instance."""
    return TestClient(test_neoo_server.app)

# --- Test Cases ---

def test_neoo_server_init(test_neoo_server):
    """Test if NeoOpsServer initializes correctly."""
    assert isinstance(test_neoo_server, NeoOpsServer)
    assert test_neoo_server.app.title == "neoo_server"

def test_neoo_health_endpoint(client, test_neoo_server):
    """Test the inherited /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    expected_config = test_neoo_server.config
    expected_response = {
        "status": "healthy",
        "service": expected_config.name, # Should be "neoo_server"
        "version": expected_config.version,
        "monitoring": {
            "metrics": expected_config.enable_metrics,
            "tracing": expected_config.enable_tracing
        }
    }
    assert response.json() == expected_response

def test_list_processes_endpoint(client):
    """Test the placeholder /api/v1/processes endpoint."""
    response = client.get("/api/v1/processes")
    assert response.status_code == 200
    response_data = response.json()
    assert "processes" in response_data
    assert isinstance(response_data["processes"], list)
    # Optional: Check placeholder data
    assert len(response_data["processes"]) == 2
    assert response_data["processes"][0]["pid"] == 123

def test_get_resource_usage_endpoint(client):
    """Test the placeholder /api/v1/resources endpoint."""
    response = client.get("/api/v1/resources")
    assert response.status_code == 200
    response_data = response.json()
    assert "cpu_total_percent" in response_data
    assert "memory_total_percent" in response_data
    assert "disk_usage_percent" in response_data
    assert isinstance(response_data["disk_usage_percent"], dict)

# TODO: Add tests for NeoOps specific endpoints (/processes, /resources)
# Replace these basic tests when real logic is implemented 