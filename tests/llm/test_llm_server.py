"""Tests for the LLMServer."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import logging
import time
import hashlib
from typing import Dict, List, Any

# Assuming config structure is similar to BaseServer test
from server.utils.config import ServerConfig, ConfigManager
from server.utils.error_handling import (
    ValidationError, AuthenticationError, AuthorizationError, NotFoundError, ConfigurationError
)
from server.utils.security import ApiKey, SecurityManager

# Import the class to test
from server.llm.server import LLMServer
# Import ModelManager and models for the refined fixture
from server.llm.manager import ModelManager
from server.llm.models import (
    BaseLanguageModel, PlaceholderModel, PlaceholderModelConfig,
    Tokenizer
)

# --- Fixtures ---

@pytest.fixture(scope="module")
def llm_server_config():
    """Provides a ServerConfig instance for LLM integration tests.
    Uses the updated ServerConfig definition with llm_models and correct api_keys type.
    """
    api_keys_dict: Dict[str, Dict[str, Any]] = {
        "test-api-key": {
            # "key" is the outer dict key, not part of the value structure
            "roles": ["llm_user"],
            "scopes": ["llm:list_models", "llm:tokenize", "llm:generate"],
            "description": "Test API Key for LLM tests"
            # Add created_at, expires_at if needed by SecurityManager init from config
        },
        "no-perms-key": {
            "roles": ["other"],
            "scopes": ["other:scope"],
            "description": "Key without LLM permissions"
        }
    }
    llm_models_list: List[Dict[str, Any]] = [
        {"provider": "placeholder", "model_id": "test-model-1"},
        {"provider": "placeholder", "model_id": "test-model-2", "max_tokens": 1024},
    ]

    # Ensure all required fields for ServerConfig are provided, even if default
    return ServerConfig(
        name="llm_server",
        port=7444, # Example port for tests
        log_level="DEBUG",
        log_file="logs/llm_server_integration_test.log", # Example log file
        enable_metrics=False,
        enable_tracing=False,
        auth_token=None,
        allowed_origins=["*"],
        # Pass the correctly typed dictionaries/lists
        api_keys=api_keys_dict,
        llm_models=llm_models_list,
        # Add other required fields with defaults if ServerConfig requires them
        # e.g., enable_auth=True if SecurityManager depends on it
        enable_auth=True
    )

@pytest.fixture
def mocked_security_manager(llm_server_config: ServerConfig):
    """Provides a mocked SecurityManager based on llm_server_config.
       Mocks validate_api_key based on the structure in ServerConfig.
    """
    security_manager_instance = MagicMock(spec=SecurityManager)

    api_key_objects = {}
    # Create ApiKey objects expected by the validation logic
    for key_id, key_info in llm_server_config.api_keys.items():
         api_key_objects[key_id] = ApiKey(
             key_id=key_id,
             key_hash=hashlib.sha256(key_id.encode()).hexdigest(), # Example hash
             name=key_id, # Use key_id as name for simplicity
             created_at=time.time(),
             roles=set(key_info.get("roles", [])),
             scopes=set(key_info.get("scopes", []))
             # description=key_info.get("description"), # Add if needed
         )

    def mock_validate(key_to_validate):
        if key_to_validate in api_key_objects:
            return api_key_objects[key_to_validate]
        else:
            # Ensure error message detail matches what the code might expect
            raise AuthenticationError(message="Invalid API key provided.", details={"api_key": key_to_validate})

    security_manager_instance.validate_api_key.side_effect = mock_validate

    # Note: SecurityManager init expects api_keys dict directly
    temp_real_manager = SecurityManager(api_keys=llm_server_config.api_keys, enable_auth=llm_server_config.enable_auth)

    security_manager_instance.check_permission.side_effect = temp_real_manager.check_permission # Assign real method directly

    # Mock load_keys if it's called separately during init or elsewhere
    security_manager_instance.load_keys = MagicMock()

    return security_manager_instance

@pytest.fixture
def configured_model_manager(llm_server_config: ServerConfig):
    """Provides a real ModelManager initialized with llm_server_config,
       but mocks the generate/tokenize methods of the loaded models.
    """
    # Use the actual ModelManager, relying on its tested loading logic
    manager = ModelManager(config=llm_server_config)
    # Verify models loaded from config list
    # Expecting 2 models + 1 'default' alias
    assert len(manager.models) == 3
    assert "test-model-1" in manager.models
    assert "test-model-2" in manager.models
    assert "default" in manager.models
    assert manager.get_model("default").name == "test-model-1"

    # Mock methods on the *loaded* model instances
    for model_id, model_instance in manager.models.items():
        if model_id == 'default': continue # Alias points to already mocked instance

        # Ensure we have an actual model instance before mocking
        assert isinstance(model_instance, BaseLanguageModel)
        # Ensure the model has a tokenizer attribute (as expected by endpoint code)
        if not hasattr(model_instance, 'tokenizer') or model_instance.tokenizer is None:
            # If the placeholder doesn't have one, add a mock tokenizer
            model_instance.tokenizer = MagicMock(spec=Tokenizer)

        # Mock generate method
        model_instance.generate = MagicMock(spec=model_instance.generate)
        # Use a side_effect function to provide dynamic mock responses
        def mock_gen_side_effect(prompt, model_name=model_instance.name, **kwargs):
            # Use closure to capture model_instance specific name correctly
            m_name = model_name # Use captured name
            # Use a consistent default token count if max_tokens not provided in call
            tkns = kwargs.get('max_tokens')
            if tkns is None:
                tkns = 5 # Default for mock testing if not specified
            else:
                tkns = int(tkns)
            # Simulate response based on args
            return f"Mock response from {m_name} for '{prompt[:10]}...' ({tkns} tokens)"
        model_instance.generate.side_effect = mock_gen_side_effect

        # Mock tokenizer's encode method (this is what the endpoint uses)
        model_instance.tokenizer.encode = MagicMock(spec=model_instance.tokenizer.encode)
        def mock_tok_encode_side_effect(text):
             # Simple mock tokenization based on word split returning list of ints
            return list(range(len(text.split())))
        model_instance.tokenizer.encode.side_effect = mock_tok_encode_side_effect

    return manager

@pytest.fixture
def test_llm_server_integrated(llm_server_config, mocked_security_manager, configured_model_manager):
    """Creates an LLMServer instance with integration-ready mocks/instances."""
    # Mock the ConfigManager class within base_server to control config loading
    mock_config_manager_instance = MagicMock()
    mock_config_manager_instance.load_config.return_value = llm_server_config
    
    # Patch dependencies at the point of use, using parentheses for multi-line context managers
    with (
        patch('server.utils.base_server.ConfigManager', return_value=mock_config_manager_instance) as MockConfigManager,
        patch('server.utils.base_server.LogManager') as MockLogManager,
        patch('server.utils.base_server.MonitoringManager') as MockMonitoringManager,
        patch('server.utils.base_server.SecurityManager', return_value=mocked_security_manager) as MockSecurityConstructor,
        patch('server.llm.server.ModelManager', return_value=configured_model_manager) as MockModelManagerConstructor,
        patch('server.utils.error_handling.logger') as MockErrorHandlingLogger
    ):

        # <<< Add Debug Prints Here >>>
        print(f"\nDEBUG: Inside test_llm_server_integrated fixture")
        print(f"DEBUG: llm_server_config: {llm_server_config.name}") # Verify config name
        print(f"DEBUG: MockConfigManager patch active: {MockConfigManager}")
        print(f"DEBUG: Mock config instance to use: {mock_config_manager_instance}")
        print(f"DEBUG: MockSecurityConstructor patch active: {MockSecurityConstructor}")
        print(f"DEBUG: Mock security instance to use: {mocked_security_manager}")
        print(f"DEBUG: MockModelManagerConstructor patch active: {MockModelManagerConstructor}")
        print(f"DEBUG: Mock model manager instance to use: {configured_model_manager}\n")

        # Configure logger mock
        mock_logger_instance = MagicMock(spec=logging.Logger)
        mock_logger_instance.bind = MagicMock(return_value=mock_logger_instance)
        MockLogManager.return_value.get_logger.return_value = mock_logger_instance
        MockErrorHandlingLogger.bind = MagicMock(return_value=MockErrorHandlingLogger)

        MockMonitoringManager.return_value = None

        # Instantiate the server
        server = LLMServer()

        # Verify mocks were called as expected during init
        # Check that ConfigManager was instantiated (implicitly, via return_value) and load_config called
        MockConfigManager.assert_called_once_with() # Check instantiation
        mock_config_manager_instance.load_config.assert_called_once_with(server_name="llm_server")
        
        # Verify SecurityManager constructor called with arguments extracted from config
        MockSecurityConstructor.assert_called_once_with(
            api_keys=llm_server_config.api_keys, 
            enable_auth=llm_server_config.enable_auth,
            auth_token=llm_server_config.auth_token
        )
        MockModelManagerConstructor.assert_called_once_with(config=llm_server_config)

        # Store actual managers
        server._test_security_manager = mocked_security_manager
        server._test_model_manager = configured_model_manager

        yield server

@pytest.fixture
def client(test_llm_server_integrated: LLMServer):
    """Provides a TestClient for the integrated LLMServer instance."""
    # Raise exceptions during client requests to simplify debugging
    return TestClient(test_llm_server_integrated.app, raise_server_exceptions=True)

@pytest.fixture
def test_llm_server_minimal_patches(llm_server_config, mocked_security_manager, configured_model_manager):
    """Creates an LLMServer instance with minimal, focused patches.
       Yields the server instance along with a TestClient configured for it.
    """
    # Use a real ConfigManager, but override its load_config method result
    # Note: We patch the *class* instantiation in BaseServer to return this specific instance
    real_config_manager_modified = ConfigManager()
    real_config_manager_modified.load_config = MagicMock(return_value=llm_server_config)

    # Patch only ModelManager and SecurityManager at their point of use
    # Also patch ConfigManager instantiation to return our modified real one
    # Also patch the logger used by the error handler
    # ALSO patch LogManager used by BaseServer (NEW)
    with (
        patch('server.utils.base_server.ConfigManager', return_value=real_config_manager_modified) as MockConfigManager,
        patch('server.utils.base_server.SecurityManager', return_value=mocked_security_manager) as MockSecurityConstructor,
        patch('server.llm.server.ModelManager', return_value=configured_model_manager) as MockModelManagerConstructor,
        patch('server.utils.error_handling.logger') as MockErrorHandlingLogger, # Add logger patch
        patch('server.utils.base_server.LogManager') as MockLogManager, # <<< ADDED THIS PATCH
    ):
        # Configure the error handler logger mock
        MockErrorHandlingLogger.bind = MagicMock(return_value=MockErrorHandlingLogger)

        # Configure logger mock used by BaseServer
        mock_logger_instance = MagicMock(spec=logging.Logger)
        mock_logger_instance.bind = MagicMock(return_value=mock_logger_instance)
        MockLogManager.return_value.get_logger.return_value = mock_logger_instance

        # Instantiate the server *inside* the patch context
        # This will use the patched ConfigManager, SecurityManager, and ModelManager
        server = LLMServer()

        # Verify mocks/overrides were hit
        real_config_manager_modified.load_config.assert_called_once_with(server_name="llm_server")
        MockSecurityConstructor.assert_called_once_with(
             api_keys=llm_server_config.api_keys,
             enable_auth=llm_server_config.enable_auth,
             auth_token=llm_server_config.auth_token
         )
        MockModelManagerConstructor.assert_called_once_with(config=llm_server_config)
        MockLogManager.assert_called_once() # Check LogManager was instantiated

        # Attach managers for test access if needed (optional)
        server._test_security_manager = mocked_security_manager
        server._test_model_manager = configured_model_manager

        # Yield the server and a client for testing
        # Set raise_server_exceptions=False so that FastAPI's exception handlers
        # can process exceptions like AuthorizationError into proper HTTP responses.
        yield server, TestClient(server.app, raise_server_exceptions=False)

    # Teardown: clean up mocked SecurityManager if needed (though patch handles it)
    # ... (no explicit teardown needed here as patch manages context)

# --- Test Cases ---

def test_llm_server_init(test_llm_server_integrated: LLMServer):
    """Test if LLMServer initializes correctly with integrated managers."""
    assert isinstance(test_llm_server_integrated, LLMServer)
    assert test_llm_server_integrated.app.title == "llm_server" # Name from config
    # Check if the *correct* (configured) ModelManager instance is assigned
    assert test_llm_server_integrated.model_manager is not None
    # Check the instance we manually attached matches the one on the server
    assert test_llm_server_integrated.model_manager == test_llm_server_integrated._test_model_manager
    # Verify it's the actual ModelManager instance, not just a mock object
    assert isinstance(test_llm_server_integrated.model_manager, ModelManager)
    # Verify the security manager is also the correct instance
    assert test_llm_server_integrated.security == test_llm_server_integrated._test_security_manager
    assert isinstance(test_llm_server_integrated.security, MagicMock) # Security Manager is mocked

def test_llm_health_endpoint(client: TestClient, test_llm_server_integrated: LLMServer):
    """Test the inherited /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    fixture_config = test_llm_server_integrated.config # Get config from the server instance
    expected_response = {
        "status": "healthy",
        "service": "llm_server", # Match the name used in LLMServer.__init__
        "version": fixture_config.version,
        "monitoring": {
            "metrics": fixture_config.enable_metrics,
            "tracing": fixture_config.enable_tracing
        }
    }
    assert response.json() == expected_response

def test_list_models_endpoint(test_llm_server_minimal_patches):
    """Test the /api/v1/models endpoint using integrated ModelManager (minimal patches)."""
    server, client = test_llm_server_minimal_patches # Use the new fixture
    valid_api_key = "test-api-key"
    headers = {"X-API-Key": valid_api_key}

    # Get the actual model manager instance used by the server fixture
    model_manager = server._test_model_manager
    # Get the expected list of models directly from the manager (excluding 'default')
    expected_models = [m for m in model_manager.list_models() if m.name != 'default']
    assert len(expected_models) == 2
    assert expected_models[0].name == "test-model-1"
    assert expected_models[1].name == "test-model-2"

    response = client.get("/api/v1/models", headers=headers)

    assert response.status_code == 200
    response_data = response.json()
    # The endpoint returns a dictionary with a 'models' key
    assert isinstance(response_data, dict)
    assert "models" in response_data
    models_list = response_data["models"]
    assert isinstance(models_list, list)
    assert len(models_list) == len(expected_models)
    # Further checks can be added to validate the content of the list items

def test_list_models_unauthorized(test_llm_server_minimal_patches):
    """Test unauthorized access to /api/v1/models endpoint."""
    server, client = test_llm_server_minimal_patches # Unpack server and client

    # No API Key -> Expect 403 Forbidden (due to dependency requiring API key)
    response = client.get("/api/v1/models")
    assert response.status_code == 403, f"Expected 403 without API key, got {response.status_code}"
    # Check detail if possible, might vary based on FastAPI/Starlette version
    # assert "Not authenticated" in response.json().get("detail", "") # Example check

    # Invalid API Key -> Expect 401 Unauthorized (from mocked SecurityManager, handled by middleware)
    # Note: raise_server_exceptions=False means we check the response status code
    response = client.get("/api/v1/models", headers={"X-API-Key": "invalid-key"})
    assert response.status_code == 401, f"Expected 401 with invalid key, got {response.status_code}"
    # Check the error response structure from ErrorHandlerMiddleware
    error_data = response.json().get("error", {})
    assert error_data.get("code") == "AUTHENTICATION_ERROR"
    assert "Invalid API key" in error_data.get("message", "")

    # Key without permissions -> Expect 403 Forbidden (from require_scope check handled by middleware)
    response = client.get("/api/v1/models", headers={"X-API-Key": "no-perms-key"})
    assert response.status_code == 403, f"Expected 403 with key lacking scope, got {response.status_code}"
    # Check the error response structure from ErrorHandlerMiddleware
    error_data = response.json().get("error", {})
    assert error_data.get("code") == "AUTHORIZATION_ERROR"
    assert "Insufficient permissions" in error_data.get("message", "")

def test_tokenize_endpoint(client: TestClient, test_llm_server_integrated: LLMServer):
    """Test the /api/v1/tokenize endpoint using integrated ModelManager."""
    valid_api_key = "test-api-key"
    headers = {"X-API-Key": valid_api_key}

    model_manager = test_llm_server_integrated._test_model_manager
    target_model_name = "test-model-1"
    expected_model = model_manager.get_model(target_model_name)
    mock_tokenize_method = expected_model.tokenizer.encode
    assert isinstance(mock_tokenize_method, MagicMock)

    test_text = "Tokenize this text"
    request_data = {"text": test_text, "model_name": target_model_name}

    response = client.post("/api/v1/tokenize", json=request_data, headers=headers)

    assert response.status_code == 200
    # Verify the *specific model's* tokenize method was called
    mock_tokenize_method.assert_called_once_with(test_text)

    response_data = response.json()
    expected_tokens = list(range(len(test_text.split()))) # From mock side effect
    assert response_data["tokens"] == expected_tokens
    assert response_data["count"] == len(expected_tokens)
    assert response_data["model_name"] == target_model_name

def test_tokenize_endpoint_default_model(client: TestClient, test_llm_server_integrated: LLMServer):
    """Test the /api/v1/tokenize endpoint when using the default model."""
    valid_api_key = "test-api-key"
    headers = {"X-API-Key": valid_api_key}
    model_manager = test_llm_server_integrated._test_model_manager
    expected_model = model_manager.get_model("default") # Should resolve to test-model-1
    mock_tokenize_method = expected_model.tokenizer.encode
    assert expected_model.name == "test-model-1" # Verify default resolution

    test_text = "Another text to tokenize"
    request_data = {"text": test_text} # No model_name specified

    response = client.post("/api/v1/tokenize", json=request_data, headers=headers)

    assert response.status_code == 200
    mock_tokenize_method.assert_called_once_with(test_text)
    response_data = response.json()
    expected_tokens = list(range(len(test_text.split())))
    assert response_data["tokens"] == expected_tokens
    assert response_data["count"] == len(expected_tokens)
    assert response_data["model_name"] == expected_model.name # Returns actual model name

def test_tokenize_unauthorized(test_llm_server_minimal_patches):
    """Test unauthorized access to the /api/v1/tokenize endpoint."""
    server, client = test_llm_server_minimal_patches # Use the fixture that sets raise_server_exceptions=False
    request_data = {"text": "test", "model_name": "test-model-1"}

    # No API Key
    response = client.post("/api/v1/tokenize", json=request_data)
    assert response.status_code == 403
    # Check detail if possible
    # assert "Not authenticated" in response.json().get("detail", "") # Detail might vary

    # Invalid API Key -> Expect 401
    response = client.post("/api/v1/tokenize", json=request_data, headers={"X-API-Key": "invalid-key"})
    assert response.status_code == 401
    error_data = response.json().get("error", {})
    assert error_data.get("code") == "AUTHENTICATION_ERROR"
    assert "Invalid API key" in error_data.get("message", "")

    # Key without permissions -> Expect 403
    response = client.post("/api/v1/tokenize", json=request_data, headers={"X-API-Key": "no-perms-key"})
    assert response.status_code == 403
    error_data = response.json().get("error", {})
    assert error_data.get("code") == "AUTHORIZATION_ERROR"
    assert "Insufficient permissions" in error_data.get("message", "")

def test_tokenize_model_not_found(client: TestClient, test_llm_server_integrated: LLMServer):
    """Test tokenize endpoint raises NotFoundError (404) when model doesn't exist."""
    valid_api_key = "test-api-key"
    headers = {"X-API-Key": valid_api_key}
    model_manager = test_llm_server_integrated._test_model_manager

    # Temporarily configure ModelManager.get_model to raise ValueError for this test
    original_get_model = model_manager.get_model
    model_manager.get_model = MagicMock(side_effect=ValueError("Model 'non-existent-model' not found."))

    request_data = {"text": "Test text", "model_name": "non-existent-model"}

    # Expect NotFoundError from the endpoint's exception handling
    with pytest.raises(NotFoundError) as exc_info:
        client.post("/api/v1/tokenize", json=request_data, headers=headers)
    assert f"Model not found: non-existent-model" in str(exc_info.value)
    assert exc_info.value.error_code == "NOT_FOUND"

    # Restore original method
    model_manager.get_model = original_get_model

def test_tokenize_model_config_error(client: TestClient, test_llm_server_integrated: LLMServer):
    """Test tokenize endpoint raises ConfigurationError (500) on manager config issue."""
    valid_api_key = "test-api-key"
    headers = {"X-API-Key": valid_api_key}
    model_manager = test_llm_server_integrated._test_model_manager

    # Temporarily configure ModelManager.get_model to raise ConfigurationError
    original_get_model = model_manager.get_model
    model_manager.get_model = MagicMock(side_effect=ConfigurationError("No default model configured."))

    request_data = {"text": "Test text"} # Request default model

    # Expect ConfigurationError from the endpoint's exception handling
    with pytest.raises(ConfigurationError) as exc_info:
        client.post("/api/v1/tokenize", json=request_data, headers=headers)
    assert "No default model configured" in str(exc_info.value)
    assert exc_info.value.error_code == "CONFIGURATION_ERROR"

    # Restore original method
    model_manager.get_model = original_get_model

def test_generate_endpoint(client: TestClient, test_llm_server_integrated: LLMServer):
    """Test the /api/v1/generate endpoint using integrated ModelManager."""
    valid_api_key = "test-api-key"
    headers = {"X-API-Key": valid_api_key}

    model_manager = test_llm_server_integrated._test_model_manager
    target_model_name = "test-model-2" # This one has max_tokens=1024 in config
    expected_model = model_manager.get_model(target_model_name)
    mock_generate_method = expected_model.generate
    mock_tokenize_method = expected_model.tokenizer.encode # Used for counting tokens in response
    assert isinstance(mock_generate_method, MagicMock)
    assert isinstance(mock_tokenize_method, MagicMock)

    test_prompt = "Generate something creative"
    request_data = {
        "prompt": test_prompt,
        "model_name": target_model_name,
        "max_tokens": 150, # Override model's default config
        "temperature": 0.9,
        # Add other valid parameters if needed by generate call
    }

    # Predict the output based on the mock's side effect
    expected_gen_output = f"Mock response from {target_model_name} for '{test_prompt[:10]}...' (150 tokens)"
    expected_tokens_list = list(range(len(expected_gen_output.split())))

    response = client.post("/api/v1/generate", json=request_data, headers=headers)

    assert response.status_code == 200
    # Verify model's generate method called with correct args from request
    # Note: The mock side effect captures kwargs, check those were passed
    mock_generate_method.assert_called_once()
    call_args, call_kwargs = mock_generate_method.call_args
    assert call_args[0] == test_prompt
    assert call_kwargs.get("max_tokens") == 150
    assert call_kwargs.get("temperature") == 0.9

    # Verify model's tokenize method called on the *result* of generate for token counting
    mock_tokenize_method.assert_called_once_with(expected_gen_output)

    # Check response data
    response_data = response.json()
    assert response_data["text"] == expected_gen_output
    assert response_data["model_name"] == target_model_name
    assert response_data["tokens_generated"] == len(expected_tokens_list)

def test_generate_endpoint_default_model(test_llm_server_minimal_patches):
    """Test the /api/v1/generate endpoint using the default model."""
    server, client = test_llm_server_minimal_patches # Unpack server and client
    valid_api_key = "test-api-key"
    headers = {"X-API-Key": valid_api_key}
    model_manager = server._test_model_manager # Use server from fixture
    expected_model = model_manager.get_model("default") # test-model-1
    mock_generate_method = expected_model.generate
    mock_tokenize_method = expected_model.tokenizer.encode
    assert expected_model.name == "test-model-1"

    test_prompt = "Default model prompt"
    request_data = {"prompt": test_prompt} # No model_name, use default, no params

    # Predict output based on mock defaults (max_tokens=5, as fixed in fixture)
    expected_gen_output = f"Mock response from {expected_model.name} for '{test_prompt[:10]}...' (5 tokens)"
    expected_tokens_list = list(range(len(expected_gen_output.split())))

    response = client.post("/api/v1/generate", json=request_data, headers=headers)

    assert response.status_code == 200
    # Generate called with default params (max_tokens=None, temperature=None from endpoint perspective)
    # The mock side effect uses its default (5) if max_tokens is None or not provided
    mock_generate_method.assert_called_once()
    call_args, call_kwargs = mock_generate_method.call_args
    assert call_args[0] == test_prompt
    assert call_kwargs.get("max_tokens") is None # Endpoint doesn't override if not in request
    assert call_kwargs.get("temperature") is None

    mock_tokenize_method.assert_called_once_with(expected_gen_output)

    response_data = response.json()
    assert response_data["text"] == expected_gen_output
    assert response_data["model_name"] == expected_model.name
    assert response_data["tokens_generated"] == len(expected_tokens_list)

def test_generate_model_not_found(test_llm_server_minimal_patches):
    """Test generate endpoint returns 404 when model doesn't exist."""
    server, client = test_llm_server_minimal_patches # Unpack server and client
    valid_api_key = "test-api-key"
    headers = {"X-API-Key": valid_api_key}
    model_manager = server._test_model_manager # Use server from fixture

    original_get_model = model_manager.get_model
    # Configure mock to raise ValueError as the endpoint expects
    model_manager.get_model = MagicMock(side_effect=ValueError("Model 'who-dis' not found."))

    request_data = {"prompt": "Test prompt", "model_name": "who-dis"}

    # Make the request and check the HTTP response
    response = client.post("/api/v1/generate", json=request_data, headers=headers)

    assert response.status_code == 404
    response_data = response.json()
    assert "error" in response_data
    error_details = response_data["error"]
    assert error_details["code"] == "NOT_FOUND"
    assert "Model not found: who-dis" in error_details["message"]
    # Check if details are present if needed
    # assert error_details["details"]["model_name"] == "who-dis"

    model_manager.get_model = original_get_model # Restore

def test_generate_model_config_error(client: TestClient, test_llm_server_integrated: LLMServer):
    """Test generate endpoint raises ConfigurationError (500) on manager config issue."""
    valid_api_key = "test-api-key"
    headers = {"X-API-Key": valid_api_key}
    model_manager = test_llm_server_integrated._test_model_manager

    original_get_model = model_manager.get_model
    model_manager.get_model = MagicMock(side_effect=ConfigurationError("Default model misconfigured"))

    request_data = {"prompt": "Test prompt"} # Request default

    with pytest.raises(ConfigurationError) as exc_info:
        client.post("/api/v1/generate", json=request_data, headers=headers)
    assert "Default model misconfigured" in str(exc_info.value)
    assert exc_info.value.error_code == "CONFIGURATION_ERROR"

    model_manager.get_model = original_get_model # Restore

def test_generate_unauthorized(test_llm_server_minimal_patches):
    """Test unauthorized access to /api/v1/generate endpoint."""
    server, client = test_llm_server_minimal_patches # Unpack server and client
    request_data = {"prompt": "Test prompt", "model_name": "test-model-1"}

    # No API Key
    response = client.post("/api/v1/generate", json=request_data)
    assert response.status_code == 403, f"Expected 403 without API key, got {response.status_code}"
    # assert "Not authenticated" in response.json().get("detail", "")

    # Invalid API Key
    response = client.post("/api/v1/generate", json=request_data, headers={"X-API-Key": "invalid-key"})
    assert response.status_code == 401, f"Expected 401 with invalid key, got {response.status_code}"
    error_data = response.json().get("error", {})
    assert error_data.get("code") == "AUTHENTICATION_ERROR"
    assert "Invalid API key" in error_data.get("message", "")

    # Key without permissions
    response = client.post("/api/v1/generate", json=request_data, headers={"X-API-Key": "no-perms-key"})
    assert response.status_code == 403, f"Expected 403 with key lacking scope, got {response.status_code}"
    error_data = response.json().get("error", {})
    assert error_data.get("code") == "AUTHORIZATION_ERROR"
    assert "Insufficient permissions" in error_data.get("message", "")