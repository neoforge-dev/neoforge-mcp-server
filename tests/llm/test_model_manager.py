"""Tests for the LLM Model Manager."""

import pytest
import logging
import os
from unittest.mock import MagicMock, patch, DEFAULT

# Import the class to test and its dependencies
from server.llm.manager import ModelManager, PROVIDER_CONFIG_MAP
from server.llm.models import (
    BaseLanguageModel, PlaceholderModel, OpenAIModel, LocalModel, # Model Classes
    BaseModelConfig, PlaceholderModelConfig, OpenAIModelConfig, LocalModelConfig # Config Classes
)
from server.utils.config import ServerConfig # Needed for manager init
from server.utils.error_handling import ConfigurationError

# --- Fixtures ---

@pytest.fixture
def mock_llm_models_config():
    """Provides a sample list of model definitions for ServerConfig."""
    return [
        # Valid Placeholder
        {"provider": "placeholder", "model_id": "test-placeholder-1"},
        # Valid OpenAI (will require mocking its init)
        {"provider": "openai", "model_id": "gpt-4", "api_key_env_var": "TEST_OPENAI_KEY"},
        # Valid Local (will require mocking its init)
        {"provider": "local", "model_id": "llama-7b", "model_path": "/path/to/llama"},
        # Invalid - Unknown provider
        {"provider": "unknown", "model_id": "invalid-provider"},
        # Invalid - Missing model_id
        {"provider": "placeholder"},
        # Invalid - Not a dict
        "not-a-dict",
        # Valid Placeholder - Duplicate ID (should be skipped)
        {"provider": "placeholder", "model_id": "test-placeholder-1"},
        # Valid OpenAI - Different ID (should load)
        {"provider": "openai", "model_id": "gpt-3.5-turbo"},
    ]

@pytest.fixture
def mock_server_config(mock_llm_models_config):
    """Provides a ServerConfig mock with sample llm_models."""
    config = MagicMock(spec=ServerConfig)
    config.llm_models = mock_llm_models_config
    # Mock other potentially accessed config attributes if necessary
    config.log_level = "DEBUG"
    config.name = "mock_llm_server"
    return config

# --- Helper for Patching --- 
# Use context manager for patching model initializers to prevent actual external interactions
@pytest.fixture
def patch_model_initializers():
    # We need the base class to run its __init__
    from server.llm.models import BaseLanguageModel

    def mock_init_side_effect(self, config):
        """Manually call BaseLanguageModel.__init__ and skip the rest."""
        BaseLanguageModel.__init__(self, config)
        # Do nothing else to prevent external calls
        return None

    # Patch __init__ for external models, using autospec=True
    with patch('server.llm.models.OpenAIModel.__init__', side_effect=mock_init_side_effect, autospec=True) as mock_openai_init, \
         patch('server.llm.models.LocalModel.__init__', side_effect=mock_init_side_effect, autospec=True) as mock_local_init:
        yield mock_openai_init, mock_local_init


# --- Test Cases ---

def test_model_manager_init_and_loading(mock_server_config, caplog, patch_model_initializers):
    """Test ModelManager initialization and model loading logic from config."""
    caplog.set_level(logging.INFO)
    
    manager = ModelManager(config=mock_server_config)

    assert isinstance(manager, ModelManager)
    assert manager.config == mock_server_config
    assert manager.logger is not None

    # Check loaded models based on mock_llm_models_config
    # Expected loaded: test-placeholder-1, gpt-4, llama-7b, gpt-3.5-turbo
    assert len(manager.models) == 5 # 4 models + 1 'default' alias
    assert "default" in manager.models
    assert manager.models["default"] == manager.models["test-placeholder-1"] # Default is first loaded

    # Check specific models and their types
    assert "test-placeholder-1" in manager.models
    assert isinstance(manager.models["test-placeholder-1"], PlaceholderModel)
    assert manager.models["test-placeholder-1"].config.model_id == "test-placeholder-1"

    assert "gpt-4" in manager.models
    assert isinstance(manager.models["gpt-4"], OpenAIModel)
    assert manager.models["gpt-4"].config.model_id == "gpt-4"
    assert manager.models["gpt-4"].config.api_key_env_var == "TEST_OPENAI_KEY"

    assert "llama-7b" in manager.models
    assert isinstance(manager.models["llama-7b"], LocalModel)
    assert manager.models["llama-7b"].config.model_id == "llama-7b"
    assert manager.models["llama-7b"].config.model_path == "/path/to/llama"

    assert "gpt-3.5-turbo" in manager.models
    assert isinstance(manager.models["gpt-3.5-turbo"], OpenAIModel)
    assert manager.models["gpt-3.5-turbo"].config.model_id == "gpt-3.5-turbo"

    # Check logs for skipped models
    assert "Skipping model definition at index 3: Missing or unknown provider 'unknown'" in caplog.text
    assert "Skipping model definition at index 4 due to validation error" in caplog.text # Missing model_id
    assert "Skipping invalid model definition at index 5: Expected dict" in caplog.text
    assert "Skipping duplicate model_id 'test-placeholder-1' defined at index 6." in caplog.text
    assert "Set default model to: 'test-placeholder-1'" in caplog.text

@pytest.fixture
def loaded_manager(mock_server_config, patch_model_initializers):
    """Provides a ModelManager instance after loading models from mock_server_config."""
    # Suppress logging during fixture setup if desired, or use caplog
    return ModelManager(config=mock_server_config)

def test_list_models(loaded_manager):
    """Test listing available models after loading from config."""
    model_list = loaded_manager.list_models()

    assert isinstance(model_list, list)
    # Should contain the 4 successfully loaded models
    assert len(model_list) == 4
    model_ids = {model.config.model_id for model in model_list}
    assert model_ids == {"test-placeholder-1", "gpt-4", "llama-7b", "gpt-3.5-turbo"}

    # Check types
    assert any(isinstance(m, PlaceholderModel) for m in model_list)
    assert sum(isinstance(m, OpenAIModel) for m in model_list) == 2
    assert any(isinstance(m, LocalModel) for m in model_list)

def test_list_model_names(loaded_manager):
    """Test listing available model names."""
    model_names = loaded_manager.list_model_names()
    assert isinstance(model_names, list)
    assert len(model_names) == 4
    assert set(model_names) == {"test-placeholder-1", "gpt-4", "llama-7b", "gpt-3.5-turbo"}

# --- get_model Tests (using loaded_manager) ---

def test_get_model_specific(loaded_manager):
    """Test getting specific models by name."""
    model_p = loaded_manager.get_model("test-placeholder-1")
    assert isinstance(model_p, PlaceholderModel)
    assert model_p.name == "test-placeholder-1"

    model_oai = loaded_manager.get_model("gpt-4")
    assert isinstance(model_oai, OpenAIModel)
    assert model_oai.name == "gpt-4"

    model_local = loaded_manager.get_model("llama-7b")
    assert isinstance(model_local, LocalModel)
    assert model_local.name == "llama-7b"

def test_get_model_default_implicit(loaded_manager):
    """Test getting the default model implicitly."""
    model = loaded_manager.get_model() # Default is first loaded: test-placeholder-1
    assert isinstance(model, PlaceholderModel)
    assert model.name == "test-placeholder-1"

def test_get_model_default_explicit(loaded_manager):
    """Test getting the default model explicitly."""
    model = loaded_manager.get_model("default")
    assert isinstance(model, PlaceholderModel)
    assert model.name == "test-placeholder-1"

def test_get_model_not_found(loaded_manager):
    """Test getting a model that was not loaded or doesn't exist."""
    with pytest.raises(ValueError) as excinfo:
        loaded_manager.get_model("invalid-provider") # Defined but not loaded
    assert "Model 'invalid-provider' not found." in str(excinfo.value)
    assert "Available models: " in str(excinfo.value) # Check help message

    with pytest.raises(ValueError) as excinfo:
        loaded_manager.get_model("completely-unknown-model")
    assert "Model 'completely-unknown-model' not found." in str(excinfo.value)

# --- _load_models Specific Edge Case Tests ---

def test_load_models_empty_config(caplog):
    """Test loading when config.llm_models is empty or missing."""
    caplog.set_level(logging.WARNING)
    config_empty = MagicMock(spec=ServerConfig)
    config_empty.llm_models = []
    config_empty.name = "empty_config_server"
    manager_empty = ModelManager(config=config_empty)
    assert len(manager_empty.models) == 0
    assert "No language models defined in configuration" in caplog.text
    with pytest.raises(ConfigurationError, match="No default language model available."):
         manager_empty.get_model() # Cannot get default if none loaded

    caplog.clear()
    config_missing = MagicMock(spec=ServerConfig)
    config_missing.name = "missing_config_server"
    # Simulate missing attribute by setting to None instead of deleting
    config_missing.llm_models = None 
    # Re-check attribute existence for safety
    assert hasattr(config_missing, 'llm_models') 
    manager_missing = ModelManager(config=config_missing)
    assert len(manager_missing.models) == 0
    assert "No language models defined in configuration" in caplog.text
    with pytest.raises(ConfigurationError, match="No default language model available."):
         manager_missing.get_model()

def test_load_models_init_error(mock_server_config, patch_model_initializers, caplog):
    """Test handling of errors during model initialization."""
    caplog.set_level(logging.INFO)
    mock_openai_init, mock_local_init = patch_model_initializers

    # Simulate error during OpenAIModel("gpt-4") init
    # Find the config for gpt-4
    gpt4_config_dict = next(m for m in mock_server_config.llm_models if isinstance(m, dict) and m.get("model_id") == "gpt-4")
    gpt4_config_obj = OpenAIModelConfig(**gpt4_config_dict)

    # Define the side effect specifically for OpenAIModel
    def openai_side_effect(self, config):
        if config.model_id == "gpt-4": # Check config object directly
            print(f"Simulating init error for {config.model_id}") # Debug print
            raise ConnectionError("Failed to connect to OpenAI API")
        else:
            # Call the original base class init logic for other OpenAI models
            BaseLanguageModel.__init__(self, config)
            return None

    mock_openai_init.side_effect = openai_side_effect
    # Reset side effect for LocalModel (use the default one from the fixture)
    # This is important if the fixture's side effect was modified elsewhere implicitly
    def local_side_effect(self, config):
         BaseLanguageModel.__init__(self, config)
         return None
    mock_local_init.side_effect = local_side_effect

    # Re-create manager to trigger loading with the failing init
    manager = ModelManager(config=mock_server_config)

    # Check loaded models: gpt-4 should be missing
    loaded_ids = manager.list_model_names()
    assert "gpt-4" not in loaded_ids
    # Should load: placeholder-1, llama-7b, gpt-3.5-turbo
    assert set(loaded_ids) == {"test-placeholder-1", "llama-7b", "gpt-3.5-turbo"}

    # Check log for the error - check start and relevant part of message
    expected_log_start = "ERROR    server.llm.manager:manager.py:85 Failed to initialize model 'gpt-4':"
    expected_error_part = "ConnectionError(\"Failed to connect to OpenAI API\")"
    assert expected_log_start in caplog.text
    assert expected_error_part in caplog.text
    
    # Check that default is still the first *successfully* loaded model
    assert manager.get_model().name == "test-placeholder-1"

def test_load_models_all_fail(caplog):
    """Test scenario where all defined models fail to load."""
    # DO NOT add patch_model_initializers here - we want real init/validation
    caplog.set_level(logging.INFO) # Use INFO to capture the expected ConfigurationError log
    failing_config = MagicMock(spec=ServerConfig)
    failing_config.name = "failing_config_server" 
    # Define models that will fail validation or init
    failing_config.llm_models = [
        # Fails in OpenAIModel.__init__ because env var not set (hopefully!)
        {"provider": "openai", "model_id": "fail-1", "api_key_env_var": "TEST_FAIL_OPENAI_KEY"}, # Use a specific var name
        # Fails pydantic validation because model_path is required
        {"provider": "local", "model_id": "fail-2"}, 
    ]
    
    # Ensure the target env var is unset for this test
    with patch.dict(os.environ, {"TEST_FAIL_OPENAI_KEY": ""}, clear=True):
         # Clear the specific var if it exists, ensures os.getenv returns None or empty
         # The real __init__ will be called
        manager = ModelManager(config=failing_config)
    
    # Assert no models were added
    assert len(manager.models) == 0 # No models loaded, no default alias
    
    # Check logs for BOTH failures
    # 1. OpenAIModel init failure (check manager's log message)
    assert "Failed to initialize model 'fail-1': OpenAI API key environment variable 'TEST_FAIL_OPENAI_KEY' not found or is empty." in caplog.text
    # 2. LocalModel validation failure (Pydantic ValidationError for missing model_path)
    assert "Skipping model definition at index 1 due to validation error: 1 validation error for LocalModelConfig\nmodel_path" in caplog.text
    
    assert "No models were loaded successfully. No default model set." in caplog.text
    
    # Getting default should fail
    with pytest.raises(ConfigurationError, match="No default language model available."):
        manager.get_model()
    # Getting a specific (failed) model should also fail
    with pytest.raises(ValueError, match="Model 'fail-1' not found."):
        manager.get_model("fail-1")

# TODO: Test _load_models with more complex configurations (requires mocking config/filesystem)
# TODO: Test get_model (specific model, default model, model not found) 