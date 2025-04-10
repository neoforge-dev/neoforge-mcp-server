import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import uuid
import json
import time

# Assuming paths based on project structure
from server.core.server import CoreMCPServer, create_app
from server.utils.security import ApiKey, SecurityManager
from server.utils.command_execution import CommandExecutor # Corrected path
from server.utils.error_handling import MCPError, AuthorizationError, ErrorHandlerMiddleware
from server.utils.config import ServerConfig # Import for spec
from server.utils.base_server import BaseServer # Import for patching

# --- Fixtures ---

@pytest.fixture
def mock_security_manager():
    """Provides a mock SecurityManager."""
    mock = MagicMock(spec=SecurityManager)
    # Ensure the mock has the methods expected by BaseServer/CoreMCPServer
    mock.validate_api_key = MagicMock()
    mock.check_permission = MagicMock()
    mock.check_rate_limit = MagicMock(return_value=True)
    return mock

@pytest.fixture
def mock_command_executor():
    """Provides a mock CommandExecutor."""
    mock = MagicMock(spec=CommandExecutor)
    # Ensure the mock has the methods/attributes expected by CoreMCPServer
    mock.execute = MagicMock()
    mock.terminate = MagicMock()
    mock.get_output = MagicMock()
    mock.list_processes = MagicMock()
    mock.blacklist = MagicMock() # Mock the blacklist object itself
    mock.blacklist.add = MagicMock()
    mock.blacklist.discard = MagicMock()
    return mock

@pytest.fixture
def sample_api_key():
    """Provides a sample valid ApiKey object."""
    # Match the ApiKey dataclass definition in server/utils/security.py
    return ApiKey(
        key_id="test-key-id",
        key_hash="dummy_hash",  # Corrected from hashed_key
        name="Test Key",
        created_at=time.time(), # Added required created_at
        expires_at=None,
        roles={"admin"},       # Corrected from role, using a set
        scopes={"*"}          # Assuming '*' scope for admin based on previous intent
    )

@pytest.fixture(scope="function")
def test_app(mock_security_manager, mock_command_executor):
    """Creates a FastAPI app instance with mocked dependencies for testing."""

    # Import necessary components here for patching
    from server.core.server import CoreMCPServer, create_app
    from server.utils.config import ServerConfig # Import for spec

    # Mocks for other managers (simplified)
    mock_config = MagicMock(spec=ServerConfig)
    # Set necessary config attributes used by BaseServer/CoreServer
    mock_config.log_level = "INFO"
    mock_config.log_file = None # Don't write logs to file in tests
    mock_config.enable_metrics = False
    mock_config.enable_tracing = False
    mock_config.api_keys = {"test-key": {}} # Minimal config for SecurityManager init
    mock_config.enable_auth = True
    mock_config.auth_token = None
    mock_config.enable_docs = False
    mock_config.enable_health_checks = True
    mock_config.version = "test-v0.1"
    mock_config.allowed_origins = ["*"]
    mock_config.enable_compression = False
    mock_config.trusted_proxies = None
    mock_config.enable_sessions = False
    mock_config.session_secret = "test-secret"
    mock_config.enable_rate_limiting = True # Enable rate limiting
    mock_config.default_rate_limit = "10000/minute" # High limit for tests
    mock_config.metrics_port = 9091 # Dummy port

    # Enhance mock_logger to support methods used by middleware
    mock_logger = MagicMock()
    mock_logger.bind.return_value = mock_logger # Return self for chained calls
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.error = MagicMock()
    mock_logger.exception = MagicMock()

    mock_monitor = MagicMock() # Simple mock

    # Patch manager constructors/methods used in BaseServer._init_managers
    # Target the import location within base_server.py
    with patch('server.utils.base_server.ConfigManager') as MockConfigMgr, \
         patch('server.utils.base_server.LogManager') as MockLogMgr, \
         patch('server.utils.base_server.MonitoringManager', return_value=mock_monitor) as MockMonitorMgr, \
         patch('server.utils.base_server.SecurityManager', return_value=mock_security_manager) as MockSecMgr:

        # Configure the mocks created by patching the classes/methods
        MockConfigMgr.return_value.load_config.return_value = mock_config
        MockLogMgr.return_value.get_logger.return_value = mock_logger

        # Patch CoreMCPServer to inject the executor AFTER BaseServer init runs
        original_core_init = CoreMCPServer.__init__
        def mocked_core_init_for_executor(instance, *args, **kwargs):
             # Call the original CoreMCPServer init (which calls BaseServer init)
             original_core_init(instance, *args, **kwargs)
             # Manually add the missing executor attribute to the instance
             instance.executor = mock_command_executor

        # Apply the __init__ patch (add autospec=True back)
        with patch.object(CoreMCPServer, '__init__', side_effect=mocked_core_init_for_executor, autospec=True):
             # Create the app - this triggers the patched __init__ sequence
             app = create_app()

        yield app

@pytest.fixture
def client(test_app):
    """Provides a TestClient for the FastAPI app."""
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c

# --- Simplified Fixture for Health Check ---
@pytest.fixture(scope="function")
def health_test_app():
    """Creates a minimal app instance specifically for the health check."""
    
    # Create minimal mocks needed ONLY for health check
    mock_config_health = MagicMock(spec=ServerConfig)
    mock_config_health.enable_health_checks = True
    mock_config_health.version = "health-test-v0.1"
    mock_config_health.enable_metrics = False
    mock_config_health.enable_tracing = False
    mock_config_health.log_level = "INFO"
    mock_config_health.log_file = None
    mock_config_health.allowed_origins = []
    mock_config_health.enable_compression = False
    mock_config_health.trusted_proxies = None
    mock_config_health.enable_sessions = False
    mock_config_health.session_secret = "test-secret"
    mock_config_health.enable_rate_limiting = False # Disable rate limiting completely for health check test
    mock_config_health.default_rate_limit = "10000/minute"
    mock_config_health.api_keys = {}
    mock_config_health.enable_auth = False
    mock_config_health.auth_token = None
    mock_config_health.enable_docs = False
    mock_config_health.metrics_port = 9091

    mock_logger_health = MagicMock()
    mock_logger_health.bind.return_value = mock_logger_health
    mock_logger_health.info = MagicMock()
    mock_logger_health.warning = MagicMock()
    mock_logger_health.error = MagicMock()
    mock_logger_health.exception = MagicMock()

    mock_monitor_health = None
    mock_security_health = MagicMock()
    mock_limiter_health = MagicMock()
    
    # Patch the manager constructors and limiter instance used in BaseServer
    with patch('server.utils.base_server.ConfigManager') as MockConfigMgr, \
         patch('server.utils.base_server.LogManager') as MockLogMgr, \
         patch('server.utils.base_server.MonitoringManager') as MockMonitorMgr, \
         patch('server.utils.base_server.SecurityManager', return_value=mock_security_health) as MockSecMgr, \
         patch('server.utils.base_server.limiter', mock_limiter_health) as PatchedLimiter:
         
        MockConfigMgr.return_value.load_config.return_value = mock_config_health
        MockLogMgr.return_value.get_logger.return_value = mock_logger_health

        # Patch CoreMCPServer __init__ to inject dummy executor
        original_core_init = CoreMCPServer.__init__
        mock_executor_health = MagicMock()
        def mocked_core_init_minimal(instance, *args, **kwargs):
             original_core_init(instance, *args, **kwargs)
             instance.executor = mock_executor_health

        # Apply the __init__ patch (add autospec=True back)
        with patch.object(CoreMCPServer, '__init__', side_effect=mocked_core_init_minimal, autospec=True):
             app = create_app()

        # Ensure necessary state is set AFTER app creation 
        app.state.logger = mock_logger_health
        app.state.limiter = mock_limiter_health 
        app.state.security = mock_security_health

        yield app

@pytest.fixture
def health_client(health_test_app):
    """Provides a TestClient specifically for the health check app."""
    app = health_test_app
    # Explicitly ensure state is set BEFORE TestClient runs startup
    # Get the mocks used within health_test_app (this assumes they are accessible
    # or we recreate minimal versions here if scope prevents access)
    # Recreating might be safer if fixture scoping is complex
    mock_logger_health = MagicMock()
    mock_logger_health.bind.return_value = mock_logger_health
    mock_logger_health.info = MagicMock()
    mock_logger_health.warning = MagicMock()
    mock_logger_health.error = MagicMock()
    mock_logger_health.exception = MagicMock()
    mock_limiter_health = MagicMock()
    mock_security_health = MagicMock()
    
    app.state.logger = mock_logger_health
    app.state.limiter = mock_limiter_health 
    app.state.security = mock_security_health
    
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

# --- Test Cases ---

def test_health_check(health_client): # Use the specific client
    """Test the base /health endpoint."""
    response = health_client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    # Check for specific fields expected in the healthy response based on BaseServer
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "core_mcp"
    assert data["version"] == "health-test-v0.1"
    assert data["monitoring"]["metrics"] == False
    assert data["monitoring"]["tracing"] == False

# --- /api/v1/execute Tests ---

TEST_COMMAND = "echo 'hello world'"
TEST_PID = 12345

def test_execute_command_success(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test successful command execution."""
    # Arrange
    # Configure mock SecurityManager for dependency injection (get_api_key)
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    expected_result = {"status": "success", "pid": TEST_PID, "output": "hello world"}
    mock_command_executor.execute.return_value = expected_result
    
    # Act
    response = client.post(
        "/api/v1/execute",
        headers={"X-API-Key": "valid-key"},
        # Use correct JSON payload structure matching endpoint signature
        json={"command": TEST_COMMAND, "timeout": 10, "allow_background": False}
    )
    
    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    assert response.json() == expected_result
    mock_security_manager.validate_api_key.assert_called_once_with("valid-key")
    mock_security_manager.check_permission.assert_called_once_with(sample_api_key, "execute:command")
    mock_command_executor.execute.assert_called_once_with(
        TEST_COMMAND,
        timeout=10,
        allow_background=False
    )

def test_execute_command_unauthorized_missing_key(client):
    """Test execute command with missing API key."""
    response = client.post("/api/v1/execute", json={"command": TEST_COMMAND})
    # FastAPI's dependency injection handles missing Security dependency
    assert response.status_code == 403
    assert "Not authenticated" in response.json()["detail"]

def test_execute_command_unauthorized_invalid_key(
    client,
    mock_security_manager
):
    """Test execute command with an invalid API key."""
    # Arrange
    # Mock the validation function called by Depends(self.get_api_key)
    mock_security_manager.validate_api_key.side_effect = AuthorizationError("Invalid API Key")
    
    # Act
    response = client.post(
        "/api/v1/execute",
        headers={"X-API-Key": "invalid-key"},
        json={"command": TEST_COMMAND}
    )
    
    # Assert
    # The get_api_key dependency raises HTTPException(401)
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]
    mock_security_manager.validate_api_key.assert_called_once_with("invalid-key")

def test_execute_command_insufficient_permissions(
    client,
    mock_security_manager,
    mock_command_executor, # Add executor mock to prevent it from being called
    sample_api_key
):
    """Test execute command with insufficient permissions."""
    # Arrange
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = False # Simulate permission denied
    
    # Act
    response = client.post(
        "/api/v1/execute",
        headers={"X-API-Key": "valid-key-no-perm"},
        json={"command": TEST_COMMAND}
    )
    
    # Assert
    # Endpoint raises HTTPException(403)
    assert response.status_code == 403, f"Expected 403, got {response.status_code}. Response: {response.text}"
    assert response.json()["detail"] == "Insufficient permissions"
    mock_security_manager.validate_api_key.assert_called_once_with("valid-key-no-perm")
    mock_security_manager.check_permission.assert_called_once_with(sample_api_key, "execute:command")
    mock_command_executor.execute.assert_not_called() # Verify executor not called

def test_execute_command_executor_error(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test execute command when the command executor itself fails."""
    # Arrange
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    mock_command_executor.execute.side_effect = MCPError("Execution Failed")
    
    # Act
    response = client.post(
        "/api/v1/execute",
        headers={"X-API-Key": "valid-key"},
        json={"command": TEST_COMMAND}
    )
    
    # Assert
    # @handle_exceptions catches MCPError
    assert response.status_code == 500, f"Expected 500, got {response.status_code}. Response: {response.text}"
    assert "Execution Failed" in response.json()["detail"]
    mock_command_executor.execute.assert_called_once()

def test_execute_command_background(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test successful command execution in background mode."""
    # Arrange
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    expected_result = {"status": "running", "pid": TEST_PID} # Typical background response
    mock_command_executor.execute.return_value = expected_result
    
    # Act
    response = client.post(
        "/api/v1/execute",
        headers={"X-API-Key": "valid-key"},
        # Pass allow_background=True, timeout defaults to None
        json={"command": TEST_COMMAND, "allow_background": True}
    )
    
    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    assert response.json() == expected_result
    mock_command_executor.execute.assert_called_once_with(
        TEST_COMMAND,
        timeout=None,
        allow_background=True
    )

# --- /api/v1/terminate/{pid} Tests ---

def test_terminate_process_success(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test successful process termination."""
    # Arrange
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    expected_result = {"status": "success", "message": f"Process {TEST_PID} terminated."}
    mock_command_executor.terminate.return_value = expected_result

    # Act
    response = client.post(
        f"/api/v1/terminate/{TEST_PID}",
        headers={"X-API-Key": "valid-key"},
        json={"force": False} # force is passed via JSON body
    )

    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    assert response.json() == expected_result
    mock_security_manager.check_permission.assert_called_once_with(sample_api_key, "terminate:process")
    mock_command_executor.terminate.assert_called_once_with(TEST_PID, force=False)

def test_terminate_process_force(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test successful process termination with force=True."""
    # Arrange
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    expected_result = {"status": "success", "message": f"Process {TEST_PID} forcefully terminated."}
    mock_command_executor.terminate.return_value = expected_result

    # Act
    response = client.post(
        f"/api/v1/terminate/{TEST_PID}",
        headers={"X-API-Key": "valid-key"},
        json={"force": True} # Send force=True in body
    )

    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    assert response.json() == expected_result
    mock_command_executor.terminate.assert_called_once_with(TEST_PID, force=True)

def test_terminate_process_unauthorized(client, mock_security_manager):
    """Test terminate process with invalid API key."""
    mock_security_manager.validate_api_key.side_effect = AuthorizationError("Invalid Key")
    response = client.post(f"/api/v1/terminate/{TEST_PID}", headers={"X-API-Key": "invalid"}, json={})
    assert response.status_code == 401
    assert "Invalid Key" in response.json()["detail"]

def test_terminate_process_insufficient_permissions(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test terminate process with insufficient permissions."""
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = False
    response = client.post(f"/api/v1/terminate/{TEST_PID}", headers={"X-API-Key": "valid"}, json={})
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    mock_command_executor.terminate.assert_not_called()

def test_terminate_process_not_found(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test terminating a non-existent process."""
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    # Assuming executor raises NotFoundError (or MCPError mapped to 404)
    mock_command_executor.terminate.side_effect = MCPError(f"Process {TEST_PID} not found")
    response = client.post(f"/api/v1/terminate/{TEST_PID}", headers={"X-API-Key": "valid"}, json={})
    assert response.status_code == 404
    assert f"Process {TEST_PID} not found" in response.json()["detail"]

# --- /api/v1/output/{pid} Tests ---

def test_get_output_success(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test successfully getting process output."""
    # Arrange
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    expected_output = {"pid": TEST_PID, "stdout": "line1\nline2", "stderr": ""}
    mock_command_executor.get_output.return_value = expected_output

    # Act
    response = client.get(f"/api/v1/output/{TEST_PID}", headers={"X-API-Key": "valid-key"})

    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    assert response.json() == expected_output
    mock_security_manager.check_permission.assert_called_once_with(sample_api_key, "read:output")
    mock_command_executor.get_output.assert_called_once_with(TEST_PID)

def test_get_output_unauthorized(client, mock_security_manager):
    """Test get output with invalid API key."""
    mock_security_manager.validate_api_key.side_effect = AuthorizationError("Bad Key")
    response = client.get(f"/api/v1/output/{TEST_PID}", headers={"X-API-Key": "invalid"})
    assert response.status_code == 401
    assert "Bad Key" in response.json()["detail"]

def test_get_output_insufficient_permissions(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test get output with insufficient permissions."""
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = False
    response = client.get(f"/api/v1/output/{TEST_PID}", headers={"X-API-Key": "valid"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    mock_command_executor.get_output.assert_not_called()

def test_get_output_not_found(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test getting output for a non-existent process."""
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    mock_command_executor.get_output.side_effect = MCPError(f"Output for {TEST_PID} not found")
    response = client.get(f"/api/v1/output/{TEST_PID}", headers={"X-API-Key": "valid"})
    assert response.status_code == 404
    assert f"Output for {TEST_PID} not found" in response.json()["detail"]

# --- /api/v1/processes Tests ---

def test_list_processes_success(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test successfully listing active processes."""
    # Arrange
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    expected_processes = {"processes": [{"pid": TEST_PID, "command": TEST_COMMAND, "status": "running"}]}
    mock_command_executor.list_processes.return_value = expected_processes

    # Act
    response = client.get("/api/v1/processes", headers={"X-API-Key": "valid-key"})

    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    assert response.json() == expected_processes
    mock_security_manager.check_permission.assert_called_once_with(sample_api_key, "read:processes")
    mock_command_executor.list_processes.assert_called_once()

def test_list_processes_unauthorized(client, mock_security_manager):
    """Test list processes with invalid API key."""
    mock_security_manager.validate_api_key.side_effect = AuthorizationError("Key Invalid")
    response = client.get("/api/v1/processes", headers={"X-API-Key": "invalid"})
    assert response.status_code == 401
    assert "Key Invalid" in response.json()["detail"]

def test_list_processes_insufficient_permissions(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test list processes with insufficient permissions."""
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = False
    response = client.get("/api/v1/processes", headers={"X-API-Key": "valid"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    mock_command_executor.list_processes.assert_not_called()

def test_list_processes_executor_error(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test list processes when the executor raises an error."""
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    mock_command_executor.list_processes.side_effect = MCPError("Failed to list")
    response = client.get("/api/v1/processes", headers={"X-API-Key": "valid"})
    assert response.status_code == 500
    assert "Failed to list" in response.json()["detail"]

# --- /api/v1/block Tests ---

BLOCKED_COMMAND = "rm -rf /"

def test_block_command_success(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test successfully blocking a command pattern."""
    # Arrange
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    
    # Act
    response = client.post(
        "/api/v1/block",
        headers={"X-API-Key": "valid-key"},
        json={"command": BLOCKED_COMMAND}
    )
    
    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    assert response.json() == {
        "status": "success", 
        "message": f"Command pattern '{BLOCKED_COMMAND}' blocked"
    }
    mock_security_manager.check_permission.assert_called_once_with(sample_api_key, "manage:blacklist")
    # Verify the mock's blacklist.add was called
    mock_command_executor.blacklist.add.assert_called_once_with(BLOCKED_COMMAND)

def test_block_command_unauthorized(client, mock_security_manager):
    """Test block command with invalid API key."""
    mock_security_manager.validate_api_key.side_effect = AuthorizationError("Key Auth Failed")
    response = client.post("/api/v1/block", headers={"X-API-Key": "invalid"}, json={"command": BLOCKED_COMMAND})
    assert response.status_code == 401
    assert "Key Auth Failed" in response.json()["detail"]

def test_block_command_insufficient_permissions(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test block command with insufficient permissions."""
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = False
    response = client.post("/api/v1/block", headers={"X-API-Key": "valid"}, json={"command": BLOCKED_COMMAND})
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    mock_command_executor.blacklist.add.assert_not_called() # Ensure it wasn't called

# --- /api/v1/unblock Tests ---

def test_unblock_command_success(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test successfully unblocking a command pattern."""
    # Arrange
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = True
    
    # Act
    response = client.post(
        "/api/v1/unblock",
        headers={"X-API-Key": "valid-key"},
        json={"command": BLOCKED_COMMAND}
    )
    
    # Assert
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    assert response.json() == {
        "status": "success", 
        "message": f"Command pattern '{BLOCKED_COMMAND}' unblocked"
    }
    mock_security_manager.check_permission.assert_called_once_with(sample_api_key, "manage:blacklist")
    # Verify the mock's blacklist.discard was called
    mock_command_executor.blacklist.discard.assert_called_once_with(BLOCKED_COMMAND)

def test_unblock_command_unauthorized(client, mock_security_manager):
    """Test unblock command with invalid API key."""
    mock_security_manager.validate_api_key.side_effect = AuthorizationError("Invalid Credentials")
    response = client.post("/api/v1/unblock", headers={"X-API-Key": "invalid"}, json={"command": BLOCKED_COMMAND})
    assert response.status_code == 401
    assert "Invalid Credentials" in response.json()["detail"]

def test_unblock_command_insufficient_permissions(
    client,
    mock_security_manager,
    mock_command_executor,
    sample_api_key
):
    """Test unblock command with insufficient permissions."""
    mock_security_manager.validate_api_key.return_value = sample_api_key
    mock_security_manager.check_permission.return_value = False
    response = client.post("/api/v1/unblock", headers={"X-API-Key": "valid"}, json={"command": BLOCKED_COMMAND})
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    mock_command_executor.blacklist.discard.assert_not_called() # Ensure it wasn't called

# --- /sse Tests ---

# Note: Testing SSE with TestClient can be tricky.
# httpx (which TestClient uses) needs specific handling for streaming responses.

@pytest.mark.asyncio # SSE endpoint is async
async def test_sse_success(client, mock_security_manager):
    """Test successful SSE connection and receiving update events."""
    # Arrange
    # Note: check_rate_limit is mocked in mock_security_manager fixture
    # It needs to be configured per-test if specific behavior is needed
    mock_security_manager.check_rate_limit.return_value = True # Ensure rate limit allows
    headers = {"X-API-Key": "valid-sse-key", "Accept": "text/event-stream"}
    
    # Act & Assert
    received_events = []
    try:
        # Need to use client.stream for SSE
        async with client.stream("GET", "/sse", headers=headers) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            
            event_count = 0
            # Read a limited number of events to avoid infinite loop in test
            async for line in response.aiter_lines():
                if line.startswith("event: update"): 
                    event_count += 1
                if line.startswith("data:"):
                    try:
                        data = json.loads(line.split("data:", 1)[1].strip())
                        received_events.append(data)
                    except json.JSONDecodeError:
                        pytest.fail(f"Failed to decode JSON data: {line}")
                        
                if event_count >= 2: # Check for at least two update events
                    break 
                    
    except Exception as e:
        pytest.fail(f"SSE streaming failed: {e}")

    # Further Assertions
    assert event_count >= 2
    assert len(received_events) >= 2
    for event in received_events:
        assert event["type"] == "update"
        assert "id" in event["data"]
        assert "timestamp" in event["data"]
        assert event["data"]["status"] == "ok"
    # Verify rate limit check occurred (using the specific key)
    mock_security_manager.check_rate_limit.assert_called_once_with("valid-sse-key")

@pytest.mark.asyncio
async def test_sse_rate_limited(client, mock_security_manager):
    """Test SSE connection denied due to rate limiting."""
    # Arrange
    mock_security_manager.check_rate_limit.return_value = False # Simulate rate limit hit
    headers = {"X-API-Key": "rate-limited-key", "Accept": "text/event-stream"}
    
    # Act & Assert
    received_error = None
    try:
        async with client.stream("GET", "/sse", headers=headers) as response:
            assert response.status_code == 200 # Connection established before error event
            assert response.headers["content-type"] == "text/event-stream"
            
            # The server should send an error event and close
            async for line in response.aiter_lines():
                if line.startswith("event: error"): 
                    pass # Expecting error event
                if line.startswith("data:"):
                    try:
                        data = json.loads(line.split("data:", 1)[1].strip())
                        if data.get("type") == "error" and data.get("data", {}).get("code") == "rate_limit_exceeded":
                            received_error = data
                            break # Found the expected error
                    except json.JSONDecodeError:
                        pass # Ignore non-JSON data lines
    except Exception as e:
        pytest.fail(f"SSE streaming failed during rate limit test: {e}")

    # Assert
    assert received_error is not None
    assert received_error["data"]["message"] == "Rate limit exceeded"
    mock_security_manager.check_rate_limit.assert_called_once_with("rate-limited-key")

# Note: Testing internal errors within the SSE generator is more complex
# as it requires mocking asyncio.sleep or request.is_disconnected 
# within the already running async generator. This often requires more 
# intricate patching or structuring the generator for testability.

# Placeholder for more tests
# e.g., Testing the get_api_key method directly if needed, although covered by endpoint tests.
