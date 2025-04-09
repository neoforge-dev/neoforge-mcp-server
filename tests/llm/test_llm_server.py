"""Tests for the LLMServer."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import logging

# Assuming config structure is similar to BaseServer test
from server.utils.config import ServerConfig

# Import the class to test
from server.llm.server import LLMServer

# --- Fixtures ---

@pytest.fixture(scope="module")
def mock_llm_config():
    """Provides a ServerConfig instance tailored for LLM tests."""
    # Adapt mock_config from BaseServer tests if needed
    return ServerConfig(
        name="llm_server",
        port=7444, # Default LLM port
        log_level="DEBUG",
        log_file="logs/llm_server_test.log",
        enable_metrics=False, # Disable for simpler testing initially
        enable_tracing=False,
        auth_token="test_llm_token",
        allowed_origins=["*"],
        api_keys={"test-api-key": {"permissions": ["*:*"]}}, # Add API keys
        # Add LLM specific config fields if ModelManager requires them
        # Example:
        # enable_local_models=True,
        # model_path="test_models",
    )

@pytest.fixture
def test_llm_server(mock_llm_config):
    """Creates an instance of LLMServer with mocked dependencies."""
    # Patch dependencies: Config loading, underlying managers used by BaseServer, and ModelManager used by LLMServer
    with patch('server.utils.config.ConfigManager.load_config') as MockLoadConfig, \
         patch('server.utils.base_server.LogManager') as MockLogManager, \
         patch('server.utils.base_server.MonitoringManager') as MockMonitoringManager, \
         patch('server.utils.base_server.SecurityManager') as MockSecurity, \
         patch('server.llm.server.ModelManager') as MockModelManager: # Correct target for ModelManager

        # Configure mocks
        MockLoadConfig.return_value = mock_llm_config
        mock_logger_instance = MagicMock(spec=logging.Logger)
        MockLogManager.return_value.get_logger.return_value = mock_logger_instance
        # MockMonitoringManager (if needed, BaseServer handles None if disabled)
        MockMonitoringManager.return_value = None
        mock_security_instance = MagicMock()
        MockSecurity.return_value = mock_security_instance
        mock_model_manager_instance = MagicMock()
        MockModelManager.return_value = mock_model_manager_instance # Mock for LLMServer init

        # Instantiate the server
        server = LLMServer()

        # Verify mocks were called as expected during init
        MockLoadConfig.assert_called_once_with("llm_server")
        MockLogManager.assert_called_once()
        MockSecurity.assert_called_once()
        MockModelManager.assert_called_once_with(config=mock_llm_config)

        # Add mocks to instance for potential use in tests
        server._test_mocks = {
            "logger": mock_logger_instance,
            "monitor": None,
            "security": mock_security_instance,
            "model_manager": mock_model_manager_instance,
            "LoadConfig": MockLoadConfig,
            "LogManager": MockLogManager,
            "MonitoringManager": MockMonitoringManager,
            "SecurityManager": MockSecurity,
            "ModelManager": MockModelManager
        }
        yield server # Yield the server instance for the test

        # --- Teardown / Reset Mocks --- (Runs after each test using the fixture)
        # Reset call counts for mocks that might be called in multiple tests
        # Check if the mocks were actually created before trying to reset
        if "ModelManager" in server._test_mocks:
            server._test_mocks["ModelManager"].reset_mock()
        # If specific methods were configured (like get_model):
        if "model_manager" in server._test_mocks and hasattr(server._test_mocks["model_manager"], "get_model"):
             server._test_mocks["model_manager"].get_model.reset_mock()

        # Reset nested mocks if necessary (example)
        # if "model_manager" in server._test_mocks and hasattr(server._test_mocks["model_manager"].get_model.return_value, "generate"):
        #     server._test_mocks["model_manager"].get_model.return_value.generate.reset_mock()
        # if "model_manager" in server._test_mocks and hasattr(server._test_mocks["model_manager"].get_model.return_value, "tokenizer") \
        #    and hasattr(server._test_mocks["model_manager"].get_model.return_value.tokenizer, "encode"):
        #     server._test_mocks["model_manager"].get_model.return_value.tokenizer.encode.reset_mock()

@pytest.fixture
def client(test_llm_server):
    """Provides a TestClient for the LLMServer instance."""
    return TestClient(test_llm_server.app)

# --- Test Cases ---

def test_llm_server_init(test_llm_server):
    """Test if LLMServer initializes correctly."""
    assert isinstance(test_llm_server, LLMServer)
    assert test_llm_server.app.title == "llm_server"
    # Check if ModelManager was initialized and assigned
    assert test_llm_server.model_manager is not None
    assert isinstance(test_llm_server.model_manager, MagicMock)

def test_llm_health_endpoint(client, test_llm_server):
    """Test the inherited /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    expected_config = test_llm_server.config
    expected_response = {
        "status": "healthy",
        "service": expected_config.name, # Should be "llm_server"
        "version": expected_config.version,
        "monitoring": {
            "metrics": expected_config.enable_metrics,
            "tracing": expected_config.enable_tracing
        }
    }
    assert response.json() == expected_response

def test_list_models_endpoint(client: TestClient, test_llm_server: LLMServer):
    """Test the /api/v1/models endpoint."""
    # Get a valid API key from the app config
    valid_api_key = list(client.app.state.config.api_keys.keys())[0]
    headers = {"X-API-Key": valid_api_key}

    # Get the mock ModelManager from the fixture
    mock_model_manager = test_llm_server._test_mocks["model_manager"]

    # Configure the mock ModelManager to return placeholder models
    # Use the actual placeholder model defined in server/llm/models.py
    from server.llm.models import LanguageModel, ModelConfig
    placeholder_config = ModelConfig(provider="placeholder", model_id="placeholder-v1")
    placeholder_model = LanguageModel(config=placeholder_config)
    mock_model_manager.list_models.return_value = [placeholder_model]

    # Make the request with headers
    response = client.get("/api/v1/models", headers=headers)

    # Assertions
    assert response.status_code == 200
    mock_model_manager.list_models.assert_called_once()

    # Check the response structure and data
    response_data = response.json()
    assert "models" in response_data
    assert isinstance(response_data["models"], list)
    assert len(response_data["models"]) == 1

    model_info = response_data["models"][0]
    assert model_info["name"] == placeholder_model.name
    assert model_info["type"] == placeholder_model.type
    # Check config - Pydantic model needs .dict()
    assert model_info["config"] == placeholder_config.dict()

def test_tokenize_endpoint(client: TestClient, test_llm_server: LLMServer):
    """Test the /api/v1/tokenize endpoint."""
    # Import placeholder classes needed for mocks
    from server.llm.models import LanguageModel, Tokenizer

    # Get a valid API key from the app config
    valid_api_key = list(client.app.state.config.api_keys.keys())[0]
    headers = {"X-API-Key": valid_api_key}

    # Get the mock ModelManager
    mock_model_manager = test_llm_server._test_mocks["model_manager"]

    # Configure a mock model and tokenizer
    mock_tokenizer = MagicMock(spec=Tokenizer)
    mock_tokenizer.encode.return_value = [0, 1, 2] # Example token IDs

    mock_model = MagicMock(spec=LanguageModel)
    mock_model.name = "mock-model-for-tokenize"
    mock_model.tokenizer = mock_tokenizer

    # Configure ModelManager.get_model to return the mock model
    mock_model_manager.get_model.return_value = mock_model

    # Input data
    test_text = "Tokenize this text"
    request_data = {"text": test_text, "model_name": "mock-model-for-tokenize"}

    # Make the request with headers
    response = client.post("/api/v1/tokenize", json=request_data, headers=headers)

    # Assertions
    assert response.status_code == 200
    mock_model_manager.get_model.assert_called_once_with("mock-model-for-tokenize")
    mock_tokenizer.encode.assert_called_once_with(test_text)

    # Check response data
    response_data = response.json()
    assert response_data["tokens"] == [0, 1, 2]
    assert response_data["count"] == 3
    assert response_data["model_name"] == "mock-model-for-tokenize"

    # Removed incorrect assertion leftover from copy-paste
    # assert model_info["config"] == placeholder_config.dict()

def test_generate_endpoint(client: TestClient, test_llm_server: LLMServer):
    """Test the /api/v1/generate endpoint."""
    # Import placeholder classes needed for mocks
    from server.llm.models import LanguageModel, Tokenizer, ModelConfig

    # Get a valid API key from the app config
    valid_api_key = list(client.app.state.config.api_keys.keys())[0]
    headers = {"X-API-Key": valid_api_key}

    # Get the mock ModelManager
    mock_model_manager = test_llm_server._test_mocks["model_manager"]

    # Configure mock model, tokenizer, and their methods
    mock_tokenizer = MagicMock(spec=Tokenizer)
    mock_tokenizer.encode.return_value = [0, 1, 2, 3, 4] # Example token IDs for generated text

    mock_model = MagicMock(spec=LanguageModel)
    mock_model.name = "mock-model-for-generate"
    mock_model.tokenizer = mock_tokenizer
    mock_model.generate.return_value = "Mock generated text response" # Expected output

    # Configure ModelManager.get_model to return the mock model
    mock_model_manager.get_model.return_value = mock_model

    # Input data
    test_prompt = "Generate something"
    request_data = {
        "prompt": test_prompt,
        "model_name": "mock-model-for-generate",
        "max_tokens": 50 # Example parameter
    }

    # Make the request with headers
    response = client.post("/api/v1/generate", json=request_data, headers=headers)

    # Assertions
    assert response.status_code == 200
    mock_model_manager.get_model.assert_called_once_with("mock-model-for-generate")
    # Check that model.generate was called with the prompt and overridden params
    mock_model.generate.assert_called_once_with(test_prompt, max_tokens=50)
    # Check that tokenizer.encode was called on the generated text
    mock_tokenizer.encode.assert_called_once_with("Mock generated text response")

    # Check response data
    response_data = response.json()
    assert response_data["text"] == "Mock generated text response"
    assert response_data["model_name"] == "mock-model-for-generate"
    assert response_data["tokens_generated"] == 5 # Based on mock_tokenizer.encode

# TODO: Add tests for ModelManager integration (mocking model calls)
# TODO: Add tests for security integration (once re-enabled) 