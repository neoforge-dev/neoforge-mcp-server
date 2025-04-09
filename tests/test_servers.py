"""
Tests for server initialization.
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from fastapi import FastAPI

# Import BaseServer for testing middleware
from server.utils.base_server import BaseServer

# Remove direct server imports - use factories or clients
# from server.core.server import server as core_server
# from server.neod.server import server as neod_server
# from server.neoo.server import server as neoo_server
# from server.neolocal.server import server as neolocal_server

# Import the factory functions
from server.core import create_app as create_core_app
from server.llm import create_app as create_llm_app
from server.neod import create_app as create_neod_app
from server.neoo import create_app as create_neoo_app
from server.neolocal import create_app as create_neolocal_app
# from server.neollm import create_app as create_neollm_app # Assuming this exists
from server.neodo import create_app as create_neodo_app

# --- BaseServer Middleware Tests ---

def test_base_server_cors_enabled():
    """Test CORS middleware is added when allowed_origins is set."""
    with patch('server.utils.config.ConfigManager.load_config') as mock_load:
        mock_config = Mock()
        mock_config.allowed_origins = ["http://localhost:3000"]
        mock_config.enable_compression = False
        mock_config.enable_proxy = False
        mock_config.enable_auth = False
        mock_config.enable_rate_limiting = False
        mock_config.enable_docs = False
        mock_config.enable_health_checks = True 
        mock_config.log_file = "/tmp/test.log" # Provide required attributes
        mock_config.log_level = "INFO"
        mock_config.auth_token = "test-token"
        mock_config.version = "1.0"
        mock_config.enable_metrics = False
        mock_config.enable_tracing = False
        mock_load.return_value = mock_config
        
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
    with patch('server.utils.config.ConfigManager.load_config') as mock_load:
        mock_config = Mock()
        mock_config.allowed_origins = [] # Disabled
        mock_config.enable_compression = False
        mock_config.enable_proxy = False
        mock_config.enable_auth = False
        mock_config.enable_rate_limiting = False
        mock_config.enable_docs = False
        mock_config.enable_health_checks = True
        mock_config.log_file = "/tmp/test.log"
        mock_config.log_level = "INFO"
        mock_config.auth_token = "test-token"
        mock_config.version = "1.0"
        mock_config.enable_metrics = False
        mock_config.enable_tracing = False
        mock_load.return_value = mock_config
        
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
    with patch('server.utils.config.ConfigManager.load_config') as mock_load:
        mock_config = Mock()
        mock_config.allowed_origins = []
        mock_config.enable_compression = True # Enabled
        mock_config.compression_level = 6 # Set a level
        mock_config.enable_proxy = False
        mock_config.enable_auth = False
        mock_config.enable_rate_limiting = False
        mock_config.enable_docs = False
        mock_config.enable_health_checks = True
        mock_config.log_file = "/tmp/test.log"
        mock_config.log_level = "INFO"
        mock_config.auth_token = "test-token"
        mock_config.version = "1.0"
        mock_config.enable_metrics = False
        mock_config.enable_tracing = False
        mock_load.return_value = mock_config
        
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
    # Setup mocks
    mock_logger = Mock()
    mock_get_logger.return_value = mock_logger
    
    # Mock config for BaseServer
    with patch('server.utils.config.ConfigManager.load_config') as mock_load:
        mock_config = Mock()
        # Set necessary config attributes for BaseServer init
        mock_config.allowed_origins = []
        mock_config.enable_compression = False
        mock_config.enable_proxy = False
        mock_config.enable_auth = False
        mock_config.enable_rate_limiting = False
        mock_config.enable_docs = False
        mock_config.enable_health_checks = True
        mock_config.log_file = "/tmp/test.log"
        mock_config.log_level = "INFO"
        mock_config.auth_token = "test-token"
        mock_config.version = "1.0"
        mock_config.enable_metrics = False
        mock_config.enable_tracing = False
        mock_load.return_value = mock_config

        server = BaseServer("test_logging_info")
        client = TestClient(server.app)
        
        # Make a successful request
        response = client.get("/health")
        assert response.status_code == 200
        
        # Verify logger call
        mock_logger.info.assert_called_once()
        args, kwargs = mock_logger.info.call_args
        assert args[0] == "Request processed"
        assert "extra" in kwargs
        assert kwargs["extra"]["status_code"] == 200
        assert kwargs["extra"]["method"] == "GET"
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

@patch('server.utils.logging.LogManager.get_logger')
def test_request_logging_middleware_warning(mock_get_logger):
    """Test RequestLoggingMiddleware logs WARNING for 4xx client errors."""
    mock_logger = Mock()
    mock_get_logger.return_value = mock_logger
    
    with patch('server.utils.config.ConfigManager.load_config') as mock_load:
        # ... (similar config mocking as above) ...
        mock_config = Mock()
        mock_config.allowed_origins = []
        mock_config.enable_compression = False
        mock_config.enable_proxy = False
        mock_config.enable_auth = False
        mock_config.enable_rate_limiting = False
        mock_config.enable_docs = False
        mock_config.enable_health_checks = True 
        mock_config.log_file = "/tmp/test.log"
        mock_config.log_level = "INFO"
        mock_config.auth_token = "test-token"
        mock_config.version = "1.0"
        mock_config.enable_metrics = False
        mock_config.enable_tracing = False
        mock_load.return_value = mock_config

        server = BaseServer("test_logging_warning")
        client = TestClient(server.app)
        
        # Make a request to a non-existent path
        response = client.get("/not/a/real/path")
        assert response.status_code == 404
        
        # Verify logger call
        mock_logger.warning.assert_called_once()
        args, kwargs = mock_logger.warning.call_args
        assert args[0] == "Client error"
        assert "extra" in kwargs
        assert kwargs["extra"]["status_code"] == 404
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()

@patch('server.utils.logging.LogManager.get_logger')
def test_request_logging_middleware_skip_sse(mock_get_logger):
    """Test RequestLoggingMiddleware skips logging for /sse endpoint."""
    mock_logger = Mock()
    mock_get_logger.return_value = mock_logger
    
    with patch('server.utils.config.ConfigManager.load_config') as mock_load:
        # ... (similar config mocking as above) ...
        mock_config = Mock()
        mock_config.allowed_origins = []
        mock_config.enable_compression = False
        mock_config.enable_proxy = False
        mock_config.enable_auth = False
        mock_config.enable_rate_limiting = False
        mock_config.enable_docs = False
        mock_config.enable_health_checks = True
        mock_config.log_file = "/tmp/test.log"
        mock_config.log_level = "INFO"
        mock_config.auth_token = "test-token"
        mock_config.version = "1.0"
        mock_config.enable_metrics = False
        mock_config.enable_tracing = False
        mock_load.return_value = mock_config

        # Need a server that actually *has* an SSE endpoint
        # Using CoreMCPServer as it defines /sse
        server = core_server # Use the actual core server instance
        client = TestClient(server.app)

        # Make a request to the SSE endpoint
        # Note: TestClient doesn't fully support SSE, 
        # but we only need to check if logging middleware is skipped.
        # A simple GET should suffice to trigger the middleware check.
        try:
            # This request might fail depending on TestClient/SSE setup,
            # but the logging middleware runs before the endpoint logic.
            client.get("/sse") 
        except Exception: 
            # Ignore exceptions from the endpoint itself for this test
            pass 

        # Verify logger was NOT called
        mock_logger.info.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

# Test basic app creation for each server using the factory
def test_core_server_creation():
    app = create_core_app()
    assert isinstance(app, FastAPI)

def test_llm_server_creation():
    app = create_llm_app()
    assert isinstance(app, FastAPI)

def test_neod_server_creation():
    app = create_neod_app()
    assert isinstance(app, FastAPI)

def test_neoo_server_creation():
    app = create_neoo_app()
    assert isinstance(app, FastAPI)

def test_neolocal_server_creation():
    app = create_neolocal_app()
    assert isinstance(app, FastAPI)

# def test_neollm_server_creation():
#     app = create_neollm_app()
#     assert isinstance(app, FastAPI)

def test_neodo_server_creation():
    app = create_neodo_app()
    assert isinstance(app, FastAPI)

# --- Test health endpoints via TestClient --- 
# (More robust than just creation)

def test_core_health(core_client: TestClient):
    response = core_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "core_mcp"

def test_llm_health(llm_client: TestClient):
    response = llm_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "llm_server"

def test_neod_health(neod_client: TestClient):
    response = neod_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "neod_mcp"

def test_neoo_health(neoo_client: TestClient):
    response = neoo_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "neoo_mcp"

def test_neolocal_health(neolocal_client: TestClient):
    response = neolocal_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "neolocal_mcp"

# def test_neollm_health(neollm_client: TestClient):
#     response = neollm_client.get("/health")
#     assert response.status_code == 200
#     assert response.json()["status"] == "healthy"
#     assert response.json()["service"] == "neollm_mcp"

def test_neodo_health(neodo_client: TestClient):
    response = neodo_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "neodo_mcp"

# TODO: Add more specific server initialization tests if needed,
# but prefer testing via TestClient and fixtures where possible. 