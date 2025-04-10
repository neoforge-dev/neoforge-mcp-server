"""Common test fixtures for Terminal Command Runner MCP tests."""

import os
import sys
import pytest
import tempfile
import shutil
from contextlib import contextmanager
from typing import Generator, Dict, Any
import threading
import time
import asyncio
import logging
from fastapi.testclient import TestClient
from server.core import create_app as create_core_app
from server.llm import create_app as create_llm_app
from server.neod import create_app as create_neod_app
from server.neoo import create_app as create_neoo_app
from server.neolocal import create_app as create_neolocal_app
from server.neollm.server import app as neollm_app
from server.neodo import create_app as create_neodo_app
from server.utils.config import ConfigManager, ServerConfig
from server.utils.logging import LogManager
from server.utils.monitoring import MonitoringManager
from server.utils.security import SecurityManager, ApiKey
from server.llm.manager import ModelManager
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from slowapi import Limiter
from slowapi.util import get_remote_address
from server.utils.error_handling import ErrorHandlerMiddleware
from loguru import logger as Logger

# Add the parent directory to path to import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for file operation tests."""
    test_dir = tempfile.mkdtemp()
    yield test_dir
    # Clean up after tests
    shutil.rmtree(test_dir)


@pytest.fixture
def sample_text_file(temp_dir: str) -> Generator[str, None, None]:
    """Create a sample text file for testing file operations."""
    file_path = os.path.join(temp_dir, "sample.txt")
    with open(file_path, "w") as f:
        f.write("This is a sample test file.\nIt has multiple lines.\nThird line.")
    yield file_path


@pytest.fixture
def long_running_process() -> Generator[Dict[str, Any], None, None]:
    """Start a long-running process for testing process management."""
    if sys.platform == "win32":
        cmd = "ping -t localhost"
        proc = None
    else:
        cmd = "sleep 30"
        proc = None
    
    # Use subprocess to start a process, but do it in a way that can be imported elsewhere
    # We'll implement this in the test functions
    
    yield {"command": cmd, "process": proc}
    
    # Cleanup will be handled in the tests


@contextmanager
def mock_active_sessions() -> Generator[Dict[int, Dict[str, Any]], None, None]:
    """Context manager to mock the active_sessions global variable."""
    # This is a placeholder - in actual tests, we'll need to mock the server's global state
    mock_sessions = {}
    yield mock_sessions


@contextmanager
def mock_output_queues() -> Generator[Dict[int, Any], None, None]:
    """Context manager to mock the output_queues global variable."""
    # This is a placeholder - in actual tests, we'll need to mock the server's global state
    mock_queues = {}
    yield mock_queues


@pytest.fixture
def blacklisted_commands() -> Generator[set, None, None]:
    """Fixture to provide and restore the blacklisted_commands set."""
    # This is a placeholder - in actual tests, we'll need to mock the server's global state
    original_blacklist = {'rm -rf /', 'mkfs'}
    mock_blacklist = original_blacklist.copy()
    yield mock_blacklist
    # Reset blacklist in cleanup 


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def core_client(mock_dependencies):
    """Create a test client for the Core MCP Server."""
    app = create_core_app()
    # Attach mocks/config to app state if tests need them
    app.state.config = mock_dependencies["config"]
    app.state.monitor = mock_dependencies["monitor"]
    app.state.security = mock_dependencies["security"]
    app.state.logger = mock_dependencies["logger"]
    # Assuming core doesn't need limiter state attached directly for tests

    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def _unused_llm_client(mock_dependencies):
    """Create a test client for the LLM MCP Server."""
    # REMOVED: Patch ModelManager specifically for LLM server *before* app creation
    # with patch('server.llm.server.ModelManager') as MockModelManager:
    # Configure a generic mock if needed, but don't patch globally here
    mock_model_manager_instance = MagicMock()
    mock_model_manager_instance.list_models.return_value = [{"id": "generic-mock-model", "name": "generic-mock-model"}]
    mock_model_manager_instance.get_model.return_value = MagicMock( 
        tokenizer=MagicMock(encode=lambda x: [0]),
        generate=lambda prompt, **kwargs: f"Generic Generated: {prompt}"
    )
    # MockModelManager.return_value = mock_model_manager_instance # Don't assign to a patch

    # Create app 
    llm_app = create_llm_app()

    # Attach mocks/config to app state for tests to access if needed
    llm_app.state.config = mock_dependencies["config"]
    llm_app.state.monitor = mock_dependencies["monitor"]
    llm_app.state.security = mock_dependencies["security"]
    llm_app.state.logger = mock_dependencies["logger"]
    llm_app.state.limiter = mock_dependencies.get("Limiter") # Safely get if exists
    # llm_app.state.model_manager = mock_model_manager_instance # Avoid attaching this generic one

    with TestClient(llm_app) as client:
        yield client


@pytest.fixture(scope="function")
def neod_client():
    """Create a TestClient for the Neo Dev Server with rate limiting patched out."""
    from server.neod import create_app  # Local import within fixture

    # Define mocks for dependencies
    # Explicitly disable rate limiting in mock config, though patching is the primary mechanism
    mock_config = ServerConfig(enable_rate_limiting=False)
    mock_logger = MagicMock(spec=Logger)
    mock_logger.bind.return_value = mock_logger # Ensure bind returns the mock logger
    mock_log_manager = MagicMock()
    mock_log_manager.get_logger.return_value = mock_logger
    mock_security_manager = MagicMock()
    mock_security_manager.verify_api_key = AsyncMock(return_value=True) # Mock API key verification
    mock_analyzer = MagicMock()
    mock_analyzer.analyze_directory = AsyncMock(return_value={"analysis": "mock directory analysis"})
    mock_analyzer.analyze_file = AsyncMock(return_value={"analysis": "mock file analysis"})

    # Patch necessary dependencies and the core rate limiter check
    with patch("server.utils.config.load_config", return_value=mock_config), \
         patch("server.utils.logging.LogManager", return_value=mock_log_manager), \
         patch("server.utils.security.SecurityManager", return_value=mock_security_manager), \
         patch("server.neod.server.CodeAnalyzer", return_value=mock_analyzer), \
         patch("slowapi.extension.Limiter._check_request_limit", lambda *args, **kwargs: None): # Correct patch target

        # Create the app *inside* the patch context to ensure mocks are used
        app = create_app()

        # Optionally attach mocks to app state if tests need to access them directly
        # Example: app.state.analyzer = mock_analyzer

        # Create and yield the TestClient
        with TestClient(app) as client:
            yield client


@pytest.fixture(scope="session")
def neoo_client(mock_dependencies):
    """Create a test client for the Neo Operations Server."""
    neoo_app = create_neoo_app()
    # Attach mocks/config to app state if tests need them
    neoo_app.state.config = mock_dependencies["config"]
    neoo_app.state.monitor = mock_dependencies["monitor"]
    neoo_app.state.security = mock_dependencies["security"]
    neoo_app.state.logger = mock_dependencies["logger"]
    neoo_app.state.limiter = mock_dependencies["Limiter"]

    with TestClient(neoo_app) as client:
        yield client


@pytest.fixture(scope="session")
def neollm_client():
    """Create a test client for the Neo Local LLM Server."""
    return TestClient(neollm_app)


@pytest.fixture(scope="session")
def neodo_test_config():
    """Load config for testing, potentially from a test-specific file or env."""
    # Initialize ConfigManager with test config directory
    config_manager = ConfigManager(config_dir="config")
    # Load config for neodo server, will use default.yaml if test.yaml doesn't exist
    return config_manager.load_config("neodo")


@pytest.fixture(scope="session")
def valid_api_key(neodo_test_config):
    """Provide a valid API key from the loaded test config."""
    # Assumes the test config has API keys defined
    if not neodo_test_config.api_keys:
        pytest.skip("No API keys found in the loaded configuration.")
    # Return the first key found
    return list(neodo_test_config.api_keys.keys())[0]


@pytest.fixture(scope="function")
def neodo_client(neodo_test_config, mock_dependencies):
    """Create a TestClient for NeoDO with rate limiting patched out."""
    from server.neodo import create_app # Local import

    # Access mocks by key from the dictionary
    mock_log_manager = mock_dependencies["LogManager"]
    mock_do_manager = mock_dependencies["DOManager"] # Assuming DOMAnager is added to mock_dependencies
    mock_security_manager = mock_dependencies["SecurityManager"]
    mock_error_handler_logger = mock_dependencies["ErrorHandlingLogger"]

    # Patch limiter check and error handler logger initialization
    with patch("server.utils.config.load_config", return_value=neodo_test_config), \
         patch("server.utils.logging.LogManager", return_value=mock_log_manager), \
         patch("digitalocean.Manager", return_value=mock_do_manager), \
         patch("server.utils.security.SecurityManager", return_value=mock_security_manager), \
         patch("server.utils.error_handling.logger", mock_error_handler_logger), \
         patch("slowapi.extension.Limiter._check_request_limit", lambda *args, **kwargs: None): # Patch Limiter check

        # Create the app *inside* the patch context
        app = create_app()

        # Attach the DO manager mock to the app state
        app.state.do_manager = mock_do_manager

        # Create and yield TestClient
        with TestClient(app) as client:
            yield client


@pytest.fixture(scope="session")
def all_clients(core_client, _unused_llm_client, neod_client, neoo_client, neollm_client, neodo_client):
    """Return a dictionary of all test clients."""
    return {
        "core": core_client,
        "llm": _unused_llm_client,
        "neod": neod_client,
        "neoo": neoo_client,
        "neollm": neollm_client,
        "neodo": neodo_client
    }


@pytest.fixture(scope="session")
def test_environment():
    """Set up test environment variables."""
    os.environ["MCP_PORT"] = "7443"
    os.environ["LLM_PORT"] = "7444"
    os.environ["NEOD_PORT"] = "7445"
    os.environ["NEOO_PORT"] = "7446"
    os.environ["NEOLOCAL_PORT"] = "7447"
    os.environ["NEOLM_PORT"] = "7448"
    os.environ["NEODO_PORT"] = "7449"
    os.environ["DO_TOKEN"] = "test_token"
    yield
    # Clean up environment variables if needed 


@pytest.fixture
def mock_log_manager(monkeypatch):
    """Fixture to mock the LogManager."""
    mock_logger_instance = MagicMock(spec=logging.Logger)
    # Add the 'bind' method to the mock logger instance
    # It should return itself to allow method chaining if needed.
    mock_logger_instance.bind = MagicMock(return_value=mock_logger_instance)

    mock_manager = MagicMock(spec=LogManager)
    mock_manager.return_value.get_logger.return_value = mock_logger_instance
    monkeypatch.setattr("server.utils.logging.LogManager", mock_manager)
    return mock_manager


@pytest.fixture
def mock_monitoring_manager(monkeypatch):
    """Fixture to mock the MonitoringManager."""
    mock_instance = MagicMock(spec=MonitoringManager)
    # Mock methods that might be called
    mock_instance.record_request_metrics = MagicMock()
    mock_instance.record_error = MagicMock()
    mock_instance.create_span = MagicMock()
    mock_instance.span_in_context = MagicMock()

    # Configure span_in_context to return a context manager mock
    span_mock = MagicMock()
    span_context_manager_mock = MagicMock()
    span_context_manager_mock.__enter__.return_value = span_mock
    span_context_manager_mock.__exit__.return_value = None
    mock_instance.span_in_context.return_value = span_context_manager_mock

    # Patch the class to return this mock instance upon instantiation
    mock_constructor = MagicMock(return_value=mock_instance)
    monkeypatch.setattr("server.utils.monitoring.MonitoringManager", mock_constructor)
    return mock_constructor  # Return the mock constructor


@pytest.fixture
def mock_config_manager(monkeypatch):
    """Fixture to mock the ConfigManager."""
    mock_instance = MagicMock(spec=ConfigManager)
    mock_instance.load_config = MagicMock(return_value=ServerConfig())
    # Configure the mock constructor to return the instance
    mock_constructor = MagicMock(return_value=mock_instance)
    monkeypatch.setattr("server.utils.config.ConfigManager", mock_constructor)
    return mock_constructor  # Return the mock constructor


@pytest.fixture
def mock_security_manager(monkeypatch):
    """Fixture to mock the SecurityManager."""
    mock_instance = MagicMock(spec=SecurityManager)
    mock_instance.validate_api_key = MagicMock(return_value=True)  # Default to valid
    mock_instance.check_permission = MagicMock(return_value=True)  # Default to allowed
    mock_instance.get_api_key_info = MagicMock(
        return_value=ApiKey(
            key="test_key",
            permissions=["*"],
            description="Test Key",
            created_time=datetime.now(timezone.utc),
            expiration_time=None,
        )
    )
    # Configure the mock constructor to return the instance
    mock_constructor = MagicMock(return_value=mock_instance)
    monkeypatch.setattr("server.utils.security.SecurityManager", mock_constructor)
    return mock_constructor  # Return the mock constructor


@pytest.fixture
def mock_llm_config():
    """Provides a mock LLM configuration."""
    return ModelConfig(
        model_name="test-model",
        api_key="test-api-key",
        base_url="http://localhost:8080",
        permissions=["llm:read", "llm:tokenize", "llm:generate"],
    )


@pytest.fixture
def mock_server_config_llm(mock_llm_config):
    """Provides a mock ServerConfig specifically for LLM server tests."""
    return ServerConfig(
        server_name="llm_server",
        host="127.0.0.1",
        port=8001,
        log_level="INFO",
        api_keys={"test-key": ApiKey(key="test-key", permissions=["llm:*"])}, # Simplified for now
        enable_metrics=False,
        models={"test-model": mock_llm_config}, # Include the mock LLM config
    )


@pytest.fixture
def _unused_mock_model_manager(monkeypatch, mock_llm_config):
    """Fixture to mock the ModelManager."""
    mock_instance = MagicMock(spec=ModelManager)
    mock_instance.list_models.return_value = [mock_llm_config]
    mock_instance.get_model_config.side_effect = lambda name: (
        mock_llm_config if name == "test-model" else None
    )
    mock_instance.tokenize.return_value = {"tokens": [1, 2, 3], "count": 3}
    mock_instance.generate.return_value = {
        "text": "Generated text",
        "tokens_generated": 5,
        "tokens_input": 3,
    }

    # Patch the class to return this mock instance upon instantiation
    mock_constructor = MagicMock(return_value=mock_instance)
    monkeypatch.setattr("server.llm.manager.ModelManager", mock_constructor)
    return mock_constructor  # Return the mock constructor


@pytest.fixture
def mock_neoo_config():
    """Provides a mock ServerConfig for NeoOps server tests."""
    return ServerConfig(
        server_name="neoo_server",
        host="127.0.0.1",
        port=8004, # Example port for NeoOps
        log_level="INFO",
        api_keys={"ops-key": ApiKey(key="ops-key", permissions=["neoo:*"])},
        enable_metrics=True, # Example: NeoOps might enable metrics
        # Add any neoo specific config here if needed
    )


@pytest.fixture
def mock_neodo_config():
    """Provides a mock ServerConfig for NeoDO server tests."""
    return ServerConfig(
        server_name="neodo_server",
        host="127.0.0.1",
        port=8003, # Example port for NeoDO
        log_level="INFO",
        api_keys={"devops-key": ApiKey(key="devops-key", permissions=["neodo:*"])},
        enable_metrics=True,
        # Add any neodo specific config here
        resource_directories=["/path/to/resources"],
        backup_location="/path/to/backups",
    )


@pytest.fixture
def mock_neod_config():
    """Provides a mock ServerConfig for NeoD server tests."""
    # Assume WorkspaceManager is mocked elsewhere or not needed for basic config
    return ServerConfig(
        server_name="neod_server",
        host="127.0.0.1",
        port=8002, # Example port for NeoD
        log_level="INFO",
        api_keys={"dev-key": ApiKey(key="dev-key", permissions=["neod:*"])},
        enable_metrics=False,
        # Add any neod specific config here
        workspaces={"default": "/path/to/workspace"},
    )


@pytest.fixture
def mock_neolocal_config():
    """Provides a mock ServerConfig for NeoLocal server tests."""
    return ServerConfig(
        server_name="neolocal_server",
        host="127.0.0.1",
        port=8005, # Example port for NeoLocal
        log_level="INFO",
        api_keys={"local-key": ApiKey(key="local-key", permissions=["neolocal:*"])},
        enable_metrics=False,
        # Add any neolocal specific config here
        development_environment={"path": "/local/dev"},
        testing_framework={"type": "pytest", "path": "/local/tests"},
    )

# Fixture for a base config (used by multiple server tests)
@pytest.fixture(scope="session")
def base_test_config():
    return ServerConfig(
        name="test_server",
        port=8001,
        log_level="DEBUG",
        api_keys={"test-key": {"permissions": ["read", "write"], "description": "Test Key"}},
        enable_metrics=False,
        enable_tracing=False,
        enable_rate_limiting=False, # Disable rate limiting explicitly for tests
        default_rate_limit="1000/second" # Use a high limit even if enabled
    )

# Common mock patches used by multiple server fixtures
@pytest.fixture(scope="session")
def mock_dependencies(base_test_config):
    with patch('server.utils.config.ConfigManager.load_config') as MockLoadConfig, \
         patch('server.utils.base_server.LogManager') as MockLogManager, \
         patch('server.utils.base_server.MonitoringManager') as MockMonitoringManager, \
         patch('server.utils.base_server.SecurityManager') as MockSecurity, \
         patch('server.utils.error_handling.logger') as MockErrorHandlingLogger:

        MockLoadConfig.return_value = base_test_config

        mock_logger_instance = MagicMock(spec=logging.Logger)
        # Add bind method expected by ErrorHandlerMiddleware
        mock_logger_instance.bind = MagicMock(return_value=mock_logger_instance)
        MockLogManager.return_value.get_logger.return_value = mock_logger_instance
        # Add bind method to the error handling logger mock as well, just in case
        MockErrorHandlingLogger.bind = MagicMock(return_value=MockErrorHandlingLogger) 

        MockMonitoringManager.return_value = None

        mock_security_instance = MockSecurity.return_value
        # Use correct ApiKey fields for instantiation
        mock_api_key_obj = ApiKey(
            key_id="test-key-id-123", # Use key_id
            key_hash="dummyhash1234567890abcdef", # Use key_hash
            name="Test Key",
            created_at=time.time(),
            scopes={"read", "write"} # Use scopes
        )
        mock_security_instance.validate_api_key.return_value = mock_api_key_obj
        mock_security_instance.check_permission.return_value = True # Assume permission granted for tests

        # Create a mock limiter that allows all requests
        mock_limiter = MagicMock(spec=Limiter)
        mock_limiter.limit = MagicMock(return_value=lambda x: x)  # No-op decorator
        mock_limiter._check_request_limit = MagicMock()  # No-op method

        yield {
            "LoadConfig": MockLoadConfig,
            "LogManager": MockLogManager,
            "MonitoringManager": MockMonitoringManager,
            "SecurityManager": MockSecurity,
            "ErrorHandlingLogger": MockErrorHandlingLogger,
            "config": base_test_config,
            "logger": mock_logger_instance,
            "monitor": None,
            "security": mock_security_instance,
            "Limiter": mock_limiter
        }

@pytest.fixture(scope="session")
def mock_server_config():
    """Provides a base mock ServerConfig for testing."""
    # Ensure rate limiting is off by default for tests unless specifically enabled
    return ServerConfig(rate_limit_enabled=False) 

@pytest.fixture(scope="function")
def neolocal_client(neolocal_test_config, mock_dependencies):
    """Create a TestClient for NeoLocal with rate limiting patched out."""
    from server.neolocal import create_app # Local import

    # Unpack mocks from the shared fixture
    _, mock_log_manager, _, mock_security_manager, _ = mock_dependencies

    # Create a specific mock logger for ErrorHandlerMiddleware patch
    mock_error_handler_logger = MagicMock(spec=Logger)
    mock_error_handler_logger.bind.return_value = mock_error_handler_logger

    # Patch limiter check and error handler logger initialization
    with patch("server.utils.config.load_config", return_value=neolocal_test_config), \
         patch("server.utils.logging.LogManager", return_value=mock_log_manager), \
         patch("server.utils.security.SecurityManager", return_value=mock_security_manager), \
         patch("server.utils.error_handling.logger", mock_error_handler_logger), \
         patch("slowapi.extension.Limiter._check_request_limit", lambda *args, **kwargs: None): # Patch Limiter check

        # Create the app *inside* the patch context
        app = create_app()

        # Create and yield TestClient
        with TestClient(app) as client:
            yield client 