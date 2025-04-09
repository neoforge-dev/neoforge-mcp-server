"""
Tests for server initialization.
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

# Import BaseServer for testing middleware
from server.utils.base_server import BaseServer

# Import servers
from server.core.server import server as core_server
from server.neod.server import server as neod_server
from server.neoo.server import server as neoo_server
from server.neolocal.server import server as neolocal_server

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

# --- Specific Server Initialization Tests (Existing) ---

def test_core_server_init():
    """Test Core MCP Server initialization."""
    app = core_server.get_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "core_mcp"

def test_neod_server_init():
    """Test Neo Development Server initialization."""
    app = neod_server.get_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "neod_mcp"

def test_neoo_server_init():
    """Test Neo Operations Server initialization."""
    app = neoo_server.get_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "neoo_mcp"

def test_neolocal_server_init():
    """Test Neo Local Server initialization."""
    app = neolocal_server.get_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "neolocal_mcp"

@pytest.mark.skipif(
    not os.environ.get("TEST_LOCAL_LLM"),
    reason="Local LLM tests are disabled"
)
def test_neollm_server_init():
    """Test Neo Local LLM Server initialization."""
    # Dynamically import to avoid loading the model during test collection
    from server.neollm.server import server as neollm_server
    
    app = neollm_server.get_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "neollm_mcp" 