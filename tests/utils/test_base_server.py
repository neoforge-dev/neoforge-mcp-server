"""Tests for the BaseServer utility."""

import pytest
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.utils.base_server import BaseServer
from server.utils.config import ServerConfig

# --- Fixtures ---

@pytest.fixture
def mock_config():
    # Provides a ServerConfig instance with basic test settings
    return ServerConfig(
        name="test_server",
        port=8001,
        log_level="DEBUG",
        log_file="logs/test_server.log",
        enable_metrics=True,
        enable_tracing=True,
        tracing_endpoint="http://localhost:4317",
        auth_token="test_token",
        allowed_origins=["*"],
    )

@pytest.fixture
def concrete_server(mock_config):
    # Patch dependencies including ConfigManager.load_config
    with patch('server.utils.logging.LogManager') as MockLogManager, \
         patch('server.utils.base_server.MonitoringManager') as MockMonitoringManager, \
         patch('server.utils.base_server.SecurityManager') as MockSecurity, \
         patch('server.utils.config.ConfigManager.load_config') as MockLoadConfig:

        # Configure mocks
        MockLoadConfig.return_value = mock_config # Return the fixture's config
        mock_logger_instance = MagicMock(spec=logging.Logger)
        MockLogManager.return_value.get_logger.return_value = mock_logger_instance
        mock_monitor_instance = MagicMock()
        MockMonitoringManager.return_value = mock_monitor_instance
        mock_security_instance = MagicMock()
        MockSecurity.return_value = mock_security_instance

        class ConcreteServer(BaseServer):
            def __init__(self):
                # Only pass app_name, BaseServer loads config via mocked load_config
                super().__init__(app_name=mock_config.name)

            def _setup_routes(self):
                @self.app.get("/dummy")
                async def dummy_route():
                    return {"message": "dummy"}

        server = ConcreteServer()
        # Verify load_config was called correctly by BaseServer.__init__
        MockLoadConfig.assert_called_once_with(mock_config.name)
        # Add mocks if needed
        server._test_mocks = {
            "logger": mock_logger_instance,
            "monitor": mock_monitor_instance,
            "security": mock_security_instance,
            "LogManager": MockLogManager,
            "MonitoringManager": MockMonitoringManager,
            "SecurityManager": MockSecurity,
            "LoadConfig": MockLoadConfig
        }
        return server

@pytest.fixture
def client(concrete_server):
    # Provides a TestClient for the concrete server instance
    return TestClient(concrete_server.app)

# --- Test Cases ---

def test_initialization(mock_config):
    # Patch dependencies including ConfigManager.load_config
    # Patch managers where they are used (in base_server)
    with patch('server.utils.base_server.LogManager') as MockLogManager, \
         patch('server.utils.base_server.MonitoringManager') as MockMonitoringManager, \
         patch('server.utils.base_server.SecurityManager') as MockSecurity, \
         patch('server.utils.config.ConfigManager.load_config') as MockLoadConfig:

        # Configure mocks
        MockLoadConfig.return_value = mock_config # Return the fixture's config
        mock_logger_instance = MagicMock(spec=logging.Logger)
        MockLogManager.return_value.get_logger.return_value = mock_logger_instance
        mock_monitor_instance = MagicMock()
        MockMonitoringManager.return_value = mock_monitor_instance
        mock_security_instance = MagicMock()
        MockSecurity.return_value = mock_security_instance

        class TestServer(BaseServer):
            def __init__(self):
                # Only pass app_name
                super().__init__(app_name=mock_config.name)
            def _setup_routes(self): pass

        server = TestServer()
        # Verify load_config was called
        MockLoadConfig.assert_called_once_with(mock_config.name)

        # Assert server uses the mocked config
        assert server.config == mock_config
        assert isinstance(server.app, FastAPI)

        # Check manager initializations with the mocked config
        MockLogManager.assert_called_once_with(
            mock_config.name,
            log_dir=mock_config.log_file,
            log_level=mock_config.log_level
        )
        assert server.logger == mock_logger_instance

        if mock_config.enable_metrics or mock_config.enable_tracing:
            MockMonitoringManager.assert_called_once_with(
                service_name=mock_config.name,
                service_version=mock_config.version,
                tracing_endpoint=mock_config.tracing_endpoint if mock_config.enable_tracing else None,
                enable_tracing=mock_config.enable_tracing,
                enable_metrics=mock_config.enable_metrics
            )
            assert server.monitor == mock_monitor_instance
        else:
            MockMonitoringManager.assert_not_called()
            assert server.monitor is None

        MockSecurity.assert_called_once_with(
            secret_key=mock_config.auth_token
        )
        assert server.security == mock_security_instance

# TODO: Add test for config loading (if BaseServer handles it directly)
# TODO: Add test for initialization failure (e.g., invalid config)

def test_health_endpoint(client, concrete_server):
    # Test the /health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    # Get expected values from the server's config (which should be the mocked one)
    expected_config = concrete_server.config
    expected_response = {
        "status": "healthy",
        "service": expected_config.name,
        "version": expected_config.version,
        "monitoring": {
            "metrics": expected_config.enable_metrics,
            "tracing": expected_config.enable_tracing
        }
    }
    assert response.json() == expected_response

def test_middleware_presence(concrete_server):
     # Test if standard and custom middleware are added
     app = concrete_server.app # Access app from the fixture
     assert any(middleware.cls.__name__ == 'CORSMiddleware' for middleware in app.user_middleware)
     # TrustedHostMiddleware might be added conditionally based on config
     # GZipMiddleware might be added conditionally based on config

     # Check for custom middleware added in BaseServer._setup_middleware
     # ErrorHandlerMiddleware is not added here; handled via decorator?
     assert any(middleware.cls.__name__ == 'RequestLoggingMiddleware' for middleware in app.user_middleware)
     # RateLimitingMiddleware is added conditionally
     # MonitoringMiddleware and SecurityMiddleware are not added as classes here

# Removed test_run_method as BaseServer does not have a .run() method.
# Server startup is handled externally (e.g., via uvicorn).

# TODO: Test middleware functionality (e.g., logging, error handling, security)
# TODO: Test server shutdown sequence (if applicable)
# TODO: Test integration points (Monitor calls, Security checks in routes - requires routes) 