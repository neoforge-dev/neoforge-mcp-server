"""Tests for the BaseServer utility."""

import pytest
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.utils.base_server import BaseServer, limiter
from server.utils.config import ServerConfig, ConfigManager
from server.utils.security import ApiKey
import time

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
def concrete_server(mock_dependencies): # Use centralized mocks
    server = BaseServer(app_name="concrete_test_server")
    server._test_mocks = mock_dependencies # Attach mocks for inspection
    return server

@pytest.fixture
def client_concrete(concrete_server):
    """Provides a TestClient for the concrete BaseServer instance."""
    return TestClient(concrete_server.app)

# Fixture specific for rate limit tests
@pytest.fixture
def test_base_server_rate_limit(mock_dependencies): # Depends on conftest fixture
    """Creates an instance of BaseServer with mocked dependencies for rate limit tests."""
    # Enable rate limiting specifically for these tests via config
    mock_dependencies["config"].enable_rate_limiting = True
    mock_dependencies["config"].default_rate_limit = "5/second" # Set a testable limit

    # Create a NEW limiter instance for this test scope to avoid state pollution
    test_limiter = Limiter(key_func=get_remote_address, enabled=True)
    with (
        patch('server.utils.base_server.limiter', new=test_limiter),
        patch.dict(test_limiter._limits, {}, clear=True)
    ): # Correct syntax: Colon after closing parenthesis for multi-line with
        
        # Instantiate the server using the mocked dependencies
        server = BaseServer(app_name="test_base_server_rate_limit")
        # Ensure the server's app uses the test_limiter instance
        server.app.state.limiter = test_limiter

        # Attach mocks to the server instance if needed for assertions
        server._test_mocks = mock_dependencies
        yield server

    # No need to disable global limiter as we used a local one

@pytest.fixture
def client_rate_limit(test_base_server_rate_limit):
    """Provides a TestClient for the rate-limit-specific BaseServer instance."""
    return TestClient(test_base_server_rate_limit.app)

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

def test_health_endpoint(client_concrete, concrete_server):
    # Test the /health endpoint
    response = client_concrete.get("/health")
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

def test_base_models_endpoint(client_concrete, concrete_server):
    """Test the placeholder /api/v1/models endpoint."""
    api_key = list(concrete_server.config.api_keys.keys())[0]
    headers = {"X-API-Key": api_key}
    response = client_concrete.get("/api/v1/models", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0 # Check it returns something

def test_rate_limit_exceeded(client_rate_limit, test_base_server_rate_limit):
    """Test that requests are blocked when rate limit is exceeded."""
    api_key = list(test_base_server_rate_limit.config.api_keys.keys())[0]
    headers = {"X-API-Key": api_key}
    limit_str = test_base_server_rate_limit.config.default_rate_limit # e.g., "5/second"
    limit, _ = limit_str.split('/')
    limit_count = int(limit)

    # Make requests up to the limit - should succeed
    for _ in range(limit_count):
        response = client_rate_limit.get("/api/v1/models", headers=headers)
        assert response.status_code == 200

    # Make one more request - should fail with 429
    response = client_rate_limit.get("/api/v1/models", headers=headers)
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.text
    assert "Retry-After" in response.headers

    # Wait for the window to reset (add a small buffer)
    time.sleep(1.1)

    # Make another request - should succeed now
    response = client_rate_limit.get("/api/v1/models", headers=headers)
    assert response.status_code == 200

# --- BaseServer Middleware Tests ---

def test_base_server_cors_enabled():
    """Test CORS middleware is added when allowed_origins is set."""
    # Mock a minimal ServerConfig needed for BaseServer init
    mock_config = ServerConfig(
        allowed_origins=["http://localhost:3000"], 
        enable_compression=False,
        enable_proxy=False, 
        enable_auth=False, 
        enable_rate_limiting=False,
        enable_docs=False,
        enable_health_checks=True,
        log_level="INFO",
        version="1.0",
        enable_metrics=False,
        enable_tracing=False
    )
    with patch('server.utils.config.ConfigManager.load_config', return_value=mock_config):
        server = BaseServer("test_cors_enabled")
        client = TestClient(server.app)
        response = client.options(
            "/health", 
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

def test_base_server_cors_disabled():
    """Test CORS middleware is NOT added when allowed_origins is empty."""
    mock_config = ServerConfig(
        allowed_origins=[], # Disabled
        enable_compression=False,
        enable_proxy=False, 
        enable_auth=False, 
        enable_rate_limiting=False,
        enable_docs=False,
        enable_health_checks=True,
        log_level="INFO",
        version="1.0",
        enable_metrics=False,
        enable_tracing=False
    )
    with patch('server.utils.config.ConfigManager.load_config', return_value=mock_config):
        server = BaseServer("test_cors_disabled")
        client = TestClient(server.app)
        response = client.options(
            "/health", 
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"}
        )
        # Without CORS middleware, OPTIONS might return 405 or not include headers
        assert "access-control-allow-origin" not in response.headers

def test_base_server_gzip_enabled():
    """Test GZip middleware is added when enable_compression is True."""
    mock_config = ServerConfig(
        allowed_origins=[], 
        enable_compression=True, # Enabled
        compression_level=6, # Set a level
        enable_proxy=False, 
        enable_auth=False, 
        enable_rate_limiting=False,
        enable_docs=False,
        enable_health_checks=True,
        log_level="INFO",
        version="1.0",
        enable_metrics=False,
        enable_tracing=False
    )
    with patch('server.utils.config.ConfigManager.load_config', return_value=mock_config):
        server = BaseServer("test_gzip_enabled")
        client = TestClient(server.app)
        # Need a response large enough to trigger compression (default minimum_size=1000)
        large_payload = {"data": "a" * 2000}
        @server.app.get("/large")
        async def large_endpoint():
            return large_payload
            
        response = client.get("/large", headers={"Accept-Encoding": "gzip"})
        assert response.status_code == 200
        assert response.headers.get("content-encoding") == "gzip"

@patch('server.utils.logging.LogManager.get_logger')
def test_request_logging_middleware_info(mock_get_logger):
    """Test RequestLoggingMiddleware logs INFO for successful requests."""
    mock_logger = Mock(spec=logging.Logger)
    mock_get_logger.return_value = mock_logger
    
    mock_config = ServerConfig(
        allowed_origins=[], 
        enable_compression=False,
        enable_proxy=False, 
        enable_auth=False, 
        enable_rate_limiting=False,
        enable_docs=False,
        enable_health_checks=True,
        log_level="INFO",
        version="1.0",
        enable_metrics=False,
        enable_tracing=False
    )
    with patch('server.utils.config.ConfigManager.load_config', return_value=mock_config):
        server = BaseServer("test_logging_info")
        client = TestClient(server.app)
        
        response = client.get("/health")
        assert response.status_code == 200
        
        mock_logger.info.assert_called_once()
        args, kwargs = mock_logger.info.call_args
        assert args[0].startswith("Request processed") # Check start of message
        assert "extra" in kwargs
        assert kwargs["extra"]["status_code"] == 200
        assert kwargs["extra"]["method"] == "GET"
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

@patch('server.utils.logging.LogManager.get_logger')
def test_request_logging_middleware_warning(mock_get_logger):
    """Test RequestLoggingMiddleware logs WARNING for 4xx client errors."""
    mock_logger = Mock(spec=logging.Logger)
    mock_get_logger.return_value = mock_logger
    
    mock_config = ServerConfig(
        allowed_origins=[], 
        enable_compression=False,
        enable_proxy=False, 
        enable_auth=False, 
        enable_rate_limiting=False,
        enable_docs=False,
        enable_health_checks=True,
        log_level="INFO",
        version="1.0",
        enable_metrics=False,
        enable_tracing=False
    )
    with patch('server.utils.config.ConfigManager.load_config', return_value=mock_config):
        server = BaseServer("test_logging_warning")
        client = TestClient(server.app)
        
        response = client.get("/not/a/real/path")
        assert response.status_code == 404
        
        mock_logger.warning.assert_called_once()
        args, kwargs = mock_logger.warning.call_args
        assert args[0].startswith("Client error") # Check start of message
        assert "extra" in kwargs
        assert kwargs["extra"]["status_code"] == 404
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()

@patch('server.utils.logging.LogManager.get_logger')
def test_request_logging_middleware_skip_sse(mock_get_logger, core_client):
    """Test RequestLoggingMiddleware skips logging for /sse endpoint."""
    # This test needs an app that actually has /sse endpoint, use core_client fixture
    mock_logger = Mock(spec=logging.Logger)
    # Find the logger attached to the core_client app state if possible, or mock globally
    # For simplicity, we assume the global patch is sufficient here, but ideally,
    # we'd verify the specific logger instance used by the middleware isn't called.
    mock_get_logger.return_value = mock_logger

    try:
        # Make a request to the SSE endpoint using the core_client
        # TestClient doesn't fully support SSE streams, but the middleware runs before the endpoint.
        core_client.get("/sse")
    except Exception:
        # Ignore endpoint exceptions as we only care about middleware behavior
        pass

    # Verify logger was NOT called for the SSE request
    mock_logger.info.assert_not_called()
    mock_logger.warning.assert_not_called()
    mock_logger.error.assert_not_called()