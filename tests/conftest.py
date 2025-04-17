"""Common test fixtures for Terminal Command Runner MCP tests."""

import os
import sys
import copy # <-- Add import for copy module
print('DEBUG sys.path:', sys.path)

# Add vendor directory to sys.path for test discovery
# _VENDOR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server', 'vendor'))
# if _VENDOR_DIR not in sys.path:
#     sys.path.insert(0, _VENDOR_DIR)

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
# Import factory functions instead of directly importing app instances
from server.core import create_app as create_core_app
from server.llm import create_app as create_llm_app
from server.neod import create_app as create_neod_app
from server.neoo import create_app as create_neoo_app
from server.neolocal import create_app as create_neolocal_app
from server.neollm.main import create_app as create_neollm_app
from server.neodo.main import NeoDOServer, create_app as create_neodo_app
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
import digitalocean
from digitalocean import Manager as DOManager_spec
from server.llm.models import BaseModelConfig, PlaceholderModelConfig, OpenAIModelConfig, LocalModelConfig
from server.utils.base_server import BaseServer

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
def core_client(mock_dependencies, base_test_config):
    """Create a test client for the Core MCP Server."""
    from server.core import create_app as create_core_app

    # Access mocks
    mock_log_manager = mock_dependencies["LogManager"]
    mock_security_manager = mock_dependencies["SecurityManager"]
    mock_error_handler_logger = mock_dependencies["ErrorHandlingLogger"]
    mock_monitor_constructor = mock_dependencies["MonitorConstructor"]

    config_to_use = base_test_config

    with patch("server.utils.config.ConfigManager.load_config", return_value=config_to_use) as MockLoadConfig, \
         patch("server.utils.logging.LogManager", return_value=mock_log_manager) as MockLogMgr, \
         patch("server.utils.security.SecurityManager", return_value=mock_security_manager) as MockSecMgr, \
         patch("server.utils.monitoring.MonitoringManager", mock_monitor_constructor) as MockMonitorMgr, \
         patch("server.utils.error_handling.logger", mock_error_handler_logger) as MockErrLogger, \
         patch("slowapi.extension.Limiter._check_request_limit", lambda *args, **kwargs: None):

        app = create_core_app()

        # Attach necessary mocks to app state (mirroring BaseServer)
        app.state.config = config_to_use
        app.state.logger = mock_log_manager.return_value.get_logger.return_value
        app.state.security = mock_security_manager
        app.state.monitor = mock_monitor_constructor.return_value
        app.state.limiter = mock_dependencies.get("Limiter")

        with TestClient(app) as client:
            yield client


@pytest.fixture(scope="function")
def llm_client(mock_dependencies, mock_server_config_llm):
    """Create a test client for the LLM MCP Server."""
    from server.llm import create_app as create_llm_app
    from server.llm.manager import ModelManager
    from unittest.mock import MagicMock, patch

    # Access mocks
    mock_log_manager = mock_dependencies["LogManager"]
    mock_security_manager = mock_dependencies["SecurityManager"]
    mock_error_handler_logger = mock_dependencies["ErrorHandlingLogger"]
    mock_monitor_constructor = mock_dependencies["MonitorConstructor"]

    # Specific LLM mock
    mock_model_manager_instance = MagicMock(spec=ModelManager)
    mock_model_manager_instance.list_models.return_value = [{"id": "mock-llm-model", "name": "Mock LLM"}]
    # Configure other model manager methods if tests require them

    with patch("server.utils.config.ConfigManager.load_config", return_value=mock_server_config_llm) as MockLoadConfig, \
         patch("server.utils.logging.LogManager", return_value=mock_log_manager) as MockLogMgr, \
         patch("server.utils.security.SecurityManager", return_value=mock_security_manager) as MockSecMgr, \
         patch("server.utils.monitoring.MonitoringManager", mock_monitor_constructor) as MockMonitorMgr, \
         patch("server.utils.error_handling.logger", mock_error_handler_logger) as MockErrLogger, \
         patch("server.llm.manager.ModelManager", return_value=mock_model_manager_instance) as MockModelMgr, \
         patch("slowapi.extension.Limiter._check_request_limit", lambda *args, **kwargs: None):

        llm_app = create_llm_app()

        # Attach state
        llm_app.state.config = mock_server_config_llm
        llm_app.state.logger = mock_log_manager.return_value.get_logger.return_value
        llm_app.state.security = mock_security_manager
        llm_app.state.monitor = mock_monitor_constructor.return_value
        llm_app.state.limiter = mock_dependencies.get("Limiter")
        llm_app.state.model_manager = mock_model_manager_instance

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


@pytest.fixture(scope="function")
def neoo_client(mock_dependencies, mock_neoo_config):
    """Create a test client for the Neo Operations Server."""
    from server.neoo import create_app as create_neoo_app
    from unittest.mock import MagicMock, patch

    # Access mocks
    mock_log_manager = mock_dependencies["LogManager"]
    mock_security_manager = mock_dependencies["SecurityManager"]
    mock_error_handler_logger = mock_dependencies["ErrorHandlingLogger"]
    mock_monitor_constructor = mock_dependencies["MonitorConstructor"]

    with patch("server.utils.config.ConfigManager.load_config", return_value=mock_neoo_config) as MockLoadConfig, \
         patch("server.utils.logging.LogManager", return_value=mock_log_manager) as MockLogMgr, \
         patch("server.utils.security.SecurityManager", return_value=mock_security_manager) as MockSecMgr, \
         patch("server.utils.monitoring.MonitoringManager", mock_monitor_constructor) as MockMonitorMgr, \
         patch("server.utils.error_handling.logger", mock_error_handler_logger) as MockErrLogger, \
         patch("slowapi.extension.Limiter._check_request_limit", lambda *args, **kwargs: None):
        # Add any neoo specific patches here (e.g., for K8s client if used)

        neoo_app = create_neoo_app()

        # Attach state
        neoo_app.state.config = mock_neoo_config
        neoo_app.state.logger = mock_log_manager.return_value.get_logger.return_value
        neoo_app.state.security = mock_security_manager
        neoo_app.state.monitor = mock_monitor_constructor.return_value
        neoo_app.state.limiter = mock_dependencies.get("Limiter")
        # Attach other neoo specific state mocks if needed

        with TestClient(neoo_app) as client:
            yield client


@pytest.fixture(scope="function")
def neollm_client(mock_dependencies, base_test_config):
    """Create a test client for the Neo Local LLM Server."""
    # Assuming neollm might be simple, fewer specific mocks needed initially
    from server.neollm.main import create_app as create_neollm_app
    from unittest.mock import MagicMock, patch

    mock_log_manager = mock_dependencies["LogManager"]
    mock_security_manager = mock_dependencies["SecurityManager"]
    mock_error_handler_logger = mock_dependencies["ErrorHandlingLogger"]
    mock_monitor_constructor = mock_dependencies["MonitorConstructor"]

    config_to_use = base_test_config

    with patch("server.utils.config.ConfigManager.load_config", return_value=config_to_use) as MockLoadConfig, \
         patch("server.utils.logging.LogManager", return_value=mock_log_manager) as MockLogMgr, \
         patch("server.utils.security.SecurityManager", return_value=mock_security_manager) as MockSecMgr, \
         patch("server.utils.monitoring.MonitoringManager", mock_monitor_constructor) as MockMonitorMgr, \
         patch("server.utils.error_handling.logger", mock_error_handler_logger) as MockErrLogger, \
         patch("slowapi.extension.Limiter._check_request_limit", lambda *args, **kwargs: None):

        app = create_neollm_app()

        # Attach state
        app.state.config = config_to_use
        app.state.logger = mock_log_manager.return_value.get_logger.return_value
        app.state.security = mock_security_manager
        app.state.monitor = mock_monitor_constructor.return_value
        app.state.limiter = mock_dependencies.get("Limiter")

        # If neollm has specific state, attach mocks here

        with TestClient(app) as client:
            yield client


@pytest.fixture(scope="session")
def neodo_test_config(base_test_config: ServerConfig) -> ServerConfig:
    """Generate a ServerConfig for NeoDO tests."""
    # Start with base config and override/add NeoDO specifics if needed
    config = copy.deepcopy(base_test_config) # Use copy.deepcopy for dataclass
    config.service_name = "neodo_mcp" # Correct service name for NeoDO
    config.api_prefix = "/api/v1/do" # Example if NeoDO uses a specific prefix
    # Add any other NeoDO specific config defaults here if necessary
    return config


@pytest.fixture(scope="session")
def valid_api_key(neodo_test_config):
    """Provide a valid API key from the loaded test config."""
    # Assumes the test config has API keys defined
    if not neodo_test_config.api_keys:
        pytest.skip("No API keys found in the loaded configuration.")
    # Return the first key found
    return list(neodo_test_config.api_keys.keys())[0]


@pytest.fixture(scope="function")
def neodo_client(mock_dependencies, neodo_test_config: ServerConfig, mock_do_manager: MagicMock):
    """Create a test client for the NeoDO Server."""
    from server.neodo.main import create_app as create_neodo_app
    from unittest.mock import MagicMock, patch, AsyncMock

    # Access mocks from shared fixture
    mock_log_manager = mock_dependencies["LogManager"]
    mock_security_manager = mock_dependencies["SecurityManager"]
    mock_error_handler_logger = mock_dependencies["ErrorHandlingLogger"]
    mock_monitor_constructor = mock_dependencies["MonitorConstructor"]
    mock_limiter = mock_dependencies["Limiter"] # Get the limiter mock

    # Mock DigitalOcean manager (already provided by mock_do_manager fixture)

    with patch("server.utils.config.ConfigManager.load_config", return_value=neodo_test_config) as MockLoadConfig, \
         patch("server.utils.logging.LogManager", return_value=mock_log_manager) as MockLogMgr, \
         patch("server.utils.security.SecurityManager", return_value=mock_security_manager) as MockSecMgr, \
         patch("server.utils.monitoring.MonitoringManager", mock_monitor_constructor) as MockMonitorMgr, \
         patch("server.utils.error_handling.logger", mock_error_handler_logger) as MockErrLogger, \
         patch("digitalocean.Manager", return_value=mock_do_manager) as MockDOClient, \
         patch("slowapi.extension.Limiter._check_request_limit", lambda *args, **kwargs: None): # Correct patch target and ensure colon is present

        neodo_app = create_neodo_app()

        # Attach state mirroring BaseServer and NeoDOServer setup
        neodo_app.state.config = neodo_test_config
        neodo_app.state.logger = mock_log_manager.get_logger.return_value
        neodo_app.state.security = mock_security_manager
        neodo_app.state.monitor = mock_monitor_constructor.return_value
        neodo_app.state.limiter = mock_limiter # Attach limiter mock
        neodo_app.state.do_manager = mock_do_manager # Attach DO manager mock

        with TestClient(neodo_app) as client:
            yield client


@pytest.fixture(scope="session")
def all_clients(core_client, llm_client, neod_client, neoo_client, neollm_client, neodo_client):
    """Return a dictionary of all test clients."""
    return {
        "core": core_client,
        "llm": llm_client,
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
    """Provides a mock LLM configuration (using PlaceholderModelConfig)."""
    # Use PlaceholderModelConfig as it's simpler
    return PlaceholderModelConfig(
        provider="placeholder", # Required by BaseModelConfig
        model_id="test-mock-llm-model", # Required by BaseModelConfig
        max_tokens=1024 # Optional, included for completeness
        # Removed fields not present in PlaceholderModelConfig:
        # model_name="test-model",
        # api_key="test-api-key",
        # base_url="http://localhost:8080",
        # permissions=["llm:read", "llm:tokenize", "llm:generate"],
    )


@pytest.fixture
def mock_server_config_llm(mock_llm_config):
    """Provides a mock ServerConfig specifically for LLM server tests."""
    return ServerConfig(
        name="llm_server",
        host="127.0.0.1",
        port=8001,
        log_level="INFO",
        api_keys={"test-key": {"key_id": "test-key", "hashed_key": "test-key-hash", "name": "Test Key", "roles": ["llm:*"], "rate_limit": "100/minute", "created_at": datetime.now(timezone.utc)}}, # Updated ApiKey format
        enable_metrics=False,
        enable_tracing=False, # <-- Ensure tracing is disabled
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
        enable_tracing=False, # <-- Ensure tracing is disabled
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
        enable_tracing=False, # <-- Ensure tracing is disabled
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
        enable_tracing=False, # <-- Ensure tracing is disabled
        # Add any neod specific config here
        workspaces={"default": "/path/to/workspace"},
    )


@pytest.fixture(scope="session")
def mock_neolocal_config():
    """Provides a specific mock NeoLocalConfig for testing."""
    return LocalModelConfig(
        model_id="mock-local-model", # Add required field
        model_path="/path/to/mock/model", # Add required field
        server_name="neolocal_test_server",
        host="0.0.0.0",
        port=8082,
        log_level="DEBUG",
        api_key_file="tests/fixtures/test_api_keys.json", # Use test keys
        allowed_hosts=["testserver", "localhost"],
        enable_cors=True,
        enable_gzip=True,
        enable_session=False, # Typically False for API servers
        session_secret="test-secret-neolocal",
        enable_metrics=True,
        enable_tracing=False, # <-- Ensure tracing is disabled
        prometheus_port=9093,
        otlp_endpoint="http://localhost:4317",
        enable_rate_limiting=False, # Using correct name
        enable_local_development=True, # Ensure local dev is enabled for tests
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
        enable_tracing=False, # <-- Ensure tracing is disabled
        enable_rate_limiting=False, # Disable rate limiting explicitly for tests
        default_rate_limit="1000/second" # Use a high limit even if enabled
    )

# Common mock patches used by multiple server fixtures
@pytest.fixture(scope="session")
def mock_dependencies(mock_server_config):
    """Provides mocked instances of common dependencies."""
    mock_log_manager_instance = MagicMock(spec=LogManager)
    mock_logger = MagicMock(spec=Logger)
    mock_logger.bind.return_value = mock_logger # Ensure bind returns the mock logger
    mock_log_manager_instance.get_logger.return_value = mock_logger

    mock_security_manager_instance = MagicMock(spec=SecurityManager)
    # Configure common security manager mocks if needed, e.g., API key verification
    valid_key = ApiKey(
        key_id="test-key-id",
        hashed_key="hashed_test_key", # Use a placeholder hash
        name="Test Key",              # Added required name field
        roles=["admin"],            # Added required roles field (using admin for broad permissions)
        rate_limit="1000/minute",    # Added required rate_limit field
        expires_at=None,
        created_at=datetime.now(timezone.utc)
        # is_active is implicitly True by default
    )
    mock_security_manager_instance.verify_api_key = AsyncMock(return_value=valid_key)
    mock_security_manager_instance.get_key_by_id = MagicMock(return_value=valid_key)
    mock_security_manager_instance.hash_api_key = MagicMock(return_value="hashed_test_key") # Consistent hash

    # Mock MonitoringManager constructor and instance
    mock_monitor_instance = MagicMock(spec=MonitoringManager)
    mock_monitor_constructor = MagicMock(return_value=mock_monitor_instance)

    mock_error_handler_logger = MagicMock(spec=Logger)

    # Mock Limiter (important for testing rate-limited endpoints)
    mock_limiter_instance = MagicMock(spec=Limiter)
    mock_limiter_instance.limit = lambda func: func # No-op decorator

    return {
        "LogManager": mock_log_manager_instance,
        "SecurityManager": mock_security_manager_instance,
        "MonitoringManager": mock_monitor_instance, # Return the instance
        "MonitorConstructor": mock_monitor_constructor, # Return the constructor mock
        "ErrorHandlingLogger": mock_error_handler_logger,
        "Limiter": mock_limiter_instance # Provide the limiter mock
    }

@pytest.fixture(scope="session")
def mock_server_config():
    """Mock server configuration for tests."""
    return ServerConfig(enable_rate_limiting=False, api_prefix="/api/v1")

@pytest.fixture(scope="function")
def neolocal_client(mock_neolocal_config, mock_dependencies):
    """Create a TestClient for NeoLocal with relevant mocks."""
    from server.neolocal import create_app # Local import

    # Access necessary mocks
    mock_log_manager = mock_dependencies["LogManager"]
    mock_security_manager = mock_dependencies["SecurityManager"]
    mock_error_handler_logger = mock_dependencies["ErrorHandlingLogger"]
    # Assume a mock monitor might be needed if config enables it
    mock_monitor_constructor = MagicMock(return_value=None) # Default to None unless config enables
    if mock_neolocal_config.enable_metrics or mock_neolocal_config.enable_tracing:
        mock_monitor_instance = MagicMock(spec=MonitoringManager) # Create a proper mock if needed
        # Configure the mock instance as needed (e.g., span_in_context)
        mock_monitor_constructor = MagicMock(return_value=mock_monitor_instance)

    # Use the specific mock_neolocal_config for this client
    with patch("server.utils.config.ConfigManager.load_config", return_value=mock_neolocal_config) as MockLoadConfig, \
         patch("server.utils.logging.LogManager", return_value=mock_log_manager) as MockLogMgr, \
         patch("server.utils.security.SecurityManager", return_value=mock_security_manager) as MockSecMgr, \
         patch("server.utils.monitoring.MonitoringManager", mock_monitor_constructor) as MockMonitorMgr, \
         patch("server.utils.error_handling.logger", mock_error_handler_logger) as MockErrLogger, \
         patch("slowapi.extension.Limiter._check_request_limit", lambda *args, **kwargs: None): # Patch Limiter
         # Add patches for other neolocal dependencies here if needed

        app = create_app()

        # Attach mocks to app state (ensure these match what BaseServer init would do)
        app.state.config = mock_neolocal_config # Use the correct config
        app.state.logger = mock_log_manager.return_value.get_logger.return_value
        app.state.security = mock_security_manager # Use the mock security manager instance directly
        app.state.monitor = mock_monitor_constructor.return_value # Use the actual mock instance
        # Attach other necessary state mocks

        with TestClient(app) as client:
            yield client 

# Add mock for DigitalOcean Manager
@pytest.fixture(scope="function")
def mock_do_manager() -> MagicMock:
    """Fixture to provide a mocked DigitalOcean Manager."""
    mock_manager = MagicMock(spec=DOManager_spec) # Use the imported spec

    # Mock common DO objects and methods needed by tests
    mock_droplet = MagicMock(spec=digitalocean.Droplet)
    mock_droplet.id = 123
    mock_droplet.name = "test-droplet"
    # Mock action methods - use AsyncMock if the real methods are async
    mock_droplet.power_on = MagicMock(return_value=None) # Assuming sync for simplicity here
    mock_droplet.power_off = MagicMock(return_value=None)
    mock_droplet.reboot = MagicMock(return_value=None)

    mock_snapshot = MagicMock(spec=digitalocean.Snapshot)
    mock_snapshot.id = 456
    mock_snapshot.name = "test-snapshot"
    # Mock snapshot creation method
    mock_droplet.take_snapshot = MagicMock(return_value=mock_snapshot)

    # Configure the manager mock to return the droplet mock
    mock_manager.get_droplet = MagicMock(return_value=mock_droplet)

    # Add other mocked methods as needed (e.g., get_all_droplets, create_droplet)
    mock_manager.get_all_droplets = MagicMock(return_value=[mock_droplet])

    return mock_manager

@pytest.fixture
def valid_api_key() -> str:
    """Provides a dummy valid API key string for testing headers."""
    return "test-valid-api-key-string" # Just a placeholder string 