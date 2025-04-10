"""Tests for the LLM Model implementations (Placeholder, OpenAI, Local)."""

import pytest
from unittest.mock import MagicMock, patch
import os
import logging
from server.utils.error_handling import ConfigurationError
import sys

# Import models and configs to test
from server.llm.models import (
    PlaceholderModel, PlaceholderModelConfig,
    OpenAIModel, OpenAIModelConfig,
    LocalModel, LocalModelConfig,
    Tokenizer # Can test tokenizer separately if needed
)

# --- PlaceholderModel Tests ---

def test_placeholder_model_init():
    """Test PlaceholderModel initialization."""
    config = PlaceholderModelConfig(model_id="test-placeholder", max_tokens=100)
    model = PlaceholderModel(config=config)
    assert model.name == "test-placeholder"
    assert model.type == "placeholder"
    assert model.config == config
    assert isinstance(model.tokenizer, Tokenizer)

def test_placeholder_model_generate():
    """Test PlaceholderModel generate method."""
    config = PlaceholderModelConfig(model_id="test-ph-gen", max_tokens=50)
    model = PlaceholderModel(config=config)
    prompt = "This is a test prompt."
    
    # Test basic generation
    output = model.generate(prompt)
    assert f"[Placeholder: {config.model_id}]" in output
    assert f"'{prompt[:20]}...'" in output
    assert f"(max_tokens={config.max_tokens}," in output # Default max_tokens
    assert "temp=0.7" in output # Default temperature

    # Test generation with overridden parameters
    output_override = model.generate(prompt, max_tokens=10, temperature=0.9)
    assert f"(max_tokens=10," in output_override
    assert "temp=0.9" in output_override

# --- OpenAIModel Tests ---

@pytest.fixture
def openai_config():
    """Provides a basic OpenAIModelConfig."""
    return OpenAIModelConfig(model_id="gpt-test", api_key_env_var="TEST_OPENAI_KEY")

@pytest.fixture
def local_config():
    """Provides a basic LocalModelConfig."""
    return LocalModelConfig(model_id="test-local-model", model_path="/fake/path", device="cpu")

@patch.dict(os.environ, {"TEST_OPENAI_KEY": "fake-api-key"})
@patch('server.llm.models.openai') # Patch the imported openai module
def test_openai_model_init_success(mock_openai, openai_config):
    """Test successful OpenAIModel initialization with API key."""
    # Configure the mock openai library
    mock_openai.OpenAI = MagicMock()
    mock_client = mock_openai.OpenAI.return_value
    
    model = OpenAIModel(config=openai_config)
    
    assert model.name == "gpt-test"
    assert model.type == "openai"
    assert model.config == openai_config
    assert model.client is not None
    # Check that the client was initialized correctly
    mock_openai.OpenAI.assert_called_once_with(
        api_key="fake-api-key",
        base_url=None # Default in fixture
    )

@patch.dict(os.environ, {}, clear=True) # Ensure TEST_OPENAI_KEY is not set
def test_openai_model_init_missing_key(openai_config):
    """Test OpenAIModel init fails if API key env var is not set."""
    with pytest.raises(ConfigurationError) as excinfo:
        OpenAIModel(config=openai_config)
    assert "TEST_OPENAI_KEY' not found" in str(excinfo.value)

@patch.dict(os.environ, {"TEST_OPENAI_KEY": "fake-api-key"})
@patch('server.llm.models.openai')
def test_openai_model_init_client_error(mock_openai, openai_config):
    """Test handling errors during OpenAI client initialization."""
    # Simulate an error during client creation
    mock_openai.OpenAI.side_effect = Exception("Connection refused")
    
    with pytest.raises(ConfigurationError) as excinfo:
        OpenAIModel(config=openai_config)
    assert "Failed to initialize OpenAI client" in str(excinfo.value)
    assert "Connection refused" in str(excinfo.value)

# Test the case where the openai package itself is not installed
@patch('server.llm.models.openai', None) # Simulate openai being None after import attempt
def test_openai_model_init_package_not_installed(openai_config):
    """Test OpenAIModel init fails if openai package is not installed."""
    with pytest.raises(ImportError) as excinfo:
         OpenAIModel(config=openai_config)
    assert "'openai' package is not installed" in str(excinfo.value)

# TODO: Add tests for OpenAIModel generate (mocking API calls and responses)

# --- LocalModel Tests (Initial Structure - To be expanded) ---
# TODO: Add tests for LocalModel init (path validation, pipeline creation)
# TODO: Add tests for LocalModel generate (mocking pipeline calls) 

# Test missing packages
@patch.dict('sys.modules', {'transformers': None, 'torch': None})
def test_local_model_init_missing_packages(local_config):
    """Test LocalModel init fails if transformers or torch package is not installed."""
    with pytest.raises(ImportError) as excinfo:
         LocalModel(config=local_config)
    assert "'transformers' or 'torch' package is not installed" in str(excinfo.value)

# --- LocalModel Init with Actual Loading (Mocked) ---

@pytest.fixture
def mock_transformers_objects():
    """Provides mocks for tokenizer, model, and pipeline objects."""
    mock_tokenizer = MagicMock(name="MockTokenizer")
    mock_model = MagicMock(name="MockModel")
    # Ensure the mock model has a .config attribute (needed by some pipeline internals/logs potentially)
    mock_model.config = MagicMock()
    mock_model.to = MagicMock(return_value=mock_model) # Mock the .to() method
    mock_pipeline = MagicMock(name="MockPipeline")
    # Mock pipeline device if needed, although device is passed during creation
    # mock_pipeline.device = torch.device("cpu") 
    return mock_tokenizer, mock_model, mock_pipeline

@pytest.mark.usefixtures("caplog") # Apply caplog fixture
@patch.dict('sys.modules', {'torch': MagicMock(), 'transformers': MagicMock()})
def test_local_model_init_actual_load_success_cpu(
    local_config, mock_transformers_objects, caplog
):
    """Test successful LocalModel init with mocked actual loading on CPU."""
    import sys
    transformers = sys.modules['transformers']
    torch = sys.modules['torch']
    
    caplog.set_level(logging.INFO)
    mock_tokenizer, mock_model, mock_pipeline = mock_transformers_objects
    
    # Configure mocks for CPU
    transformers.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
    transformers.AutoModelForCausalLM.from_pretrained.return_value = mock_model
    transformers.pipeline.return_value = mock_pipeline
    torch.cuda.is_available.return_value = False
    torch.backends.mps.is_available.return_value = False

    # Action
    # Use a config specifying cpu explicitly or defaulting to it
    cpu_config = LocalModelConfig(model_id="test-cpu", model_path="/fake/cpu/path", device="cpu")
    model = LocalModel(config=cpu_config)

    # Assertions
    assert model.pipeline is mock_pipeline
    transformers.AutoTokenizer.from_pretrained.assert_called_once_with(cpu_config.model_path)
    transformers.AutoModelForCausalLM.from_pretrained.assert_called_once_with(cpu_config.model_path)
    mock_model.to.assert_called_once_with("cpu")
    transformers.pipeline.assert_called_once_with(
        "text-generation",
        model=mock_model,
        tokenizer=mock_tokenizer,
        device=-1 # CPU for pipeline
    )
    assert f"Successfully loaded local model '{model.name}'" in caplog.text
    assert "Moved model test-cpu to device 'cpu'" in caplog.text

@pytest.mark.usefixtures("caplog")
@patch.dict('sys.modules', {'torch': MagicMock(), 'transformers': MagicMock()})
def test_local_model_init_actual_load_success_cuda(
    mock_transformers_objects, caplog
):
    """Test successful LocalModel init with mocked actual loading on CUDA."""
    import sys
    transformers = sys.modules['transformers']
    torch = sys.modules['torch']
    
    caplog.set_level(logging.INFO)
    mock_tokenizer, mock_model, mock_pipeline = mock_transformers_objects
    cuda_config = LocalModelConfig(model_id="test-cuda", model_path="/fake/cuda/path", device="cuda")
    
    # Configure mocks for CUDA
    transformers.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
    transformers.AutoModelForCausalLM.from_pretrained.return_value = mock_model
    transformers.pipeline.return_value = mock_pipeline
    torch.cuda.is_available.return_value = True # CUDA available
    torch.backends.mps.is_available.return_value = False

    model = LocalModel(config=cuda_config)

    assert model.pipeline is mock_pipeline
    mock_model.to.assert_called_once_with("cuda")
    transformers.pipeline.assert_called_once_with(
        "text-generation",
        model=mock_model,
        tokenizer=mock_tokenizer,
        device=0 # CUDA device 0 for pipeline
    )
    assert f"Successfully loaded local model '{model.name}'" in caplog.text
    assert f"Moved model {model.name} to device 'cuda'" in caplog.text

@pytest.mark.usefixtures("caplog")
@patch.dict('sys.modules', {'torch': MagicMock(), 'transformers': MagicMock()})
def test_local_model_init_load_tokenizer_error(
    local_config, caplog
):
    """Test error handling when tokenizer loading fails."""
    import sys
    transformers = sys.modules['transformers']
    torch = sys.modules['torch']
    
    caplog.set_level(logging.ERROR)
    # Simulate error during tokenizer loading
    load_error = OSError("Could not load tokenizer")
    transformers.AutoTokenizer.from_pretrained.side_effect = load_error
    torch.cuda.is_available.return_value = False
    torch.backends.mps.is_available.return_value = False

    with pytest.raises(ConfigurationError) as excinfo:
        LocalModel(config=local_config)
    
    assert "Failed to load local model" in str(excinfo.value)
    assert str(load_error) in str(excinfo.value)
    assert "Failed to load local model 'test-local-model'" in caplog.text

@pytest.mark.usefixtures("caplog")
@patch.dict('sys.modules', {'torch': MagicMock(), 'transformers': MagicMock()})
def test_local_model_init_load_model_error(
    local_config, mock_transformers_objects, caplog
):
    """Test error handling when model loading fails."""
    import sys
    transformers = sys.modules['transformers']
    torch = sys.modules['torch']
    
    caplog.set_level(logging.ERROR)
    mock_tokenizer, _, _ = mock_transformers_objects
    transformers.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
    # Simulate error during model loading
    load_error = ValueError("Invalid model architecture")
    transformers.AutoModelForCausalLM.from_pretrained.side_effect = load_error
    torch.cuda.is_available.return_value = False
    torch.backends.mps.is_available.return_value = False

    with pytest.raises(ConfigurationError) as excinfo:
        LocalModel(config=local_config)
    
    assert "Failed to load local model" in str(excinfo.value)
    assert str(load_error) in str(excinfo.value)
    assert "Failed to load local model 'test-local-model'" in caplog.text

@pytest.mark.usefixtures("caplog")
@patch.dict('sys.modules', {'torch': MagicMock(), 'transformers': MagicMock()})
def test_local_model_init_pipeline_error(
    local_config, mock_transformers_objects, caplog
):
    """Test error handling when pipeline creation fails."""
    import sys
    transformers = sys.modules['transformers']
    torch = sys.modules['torch']
    
    caplog.set_level(logging.ERROR)
    mock_tokenizer, mock_model, _ = mock_transformers_objects
    transformers.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
    transformers.AutoModelForCausalLM.from_pretrained.return_value = mock_model
    # Simulate error during pipeline creation
    load_error = RuntimeError("Pipeline creation failed")
    transformers.pipeline.side_effect = load_error
    torch.cuda.is_available.return_value = False
    torch.backends.mps.is_available.return_value = False

    with pytest.raises(ConfigurationError) as excinfo:
        LocalModel(config=local_config)
    
    assert "Failed to load local model" in str(excinfo.value)
    assert str(load_error) in str(excinfo.value)
    assert "Failed to load local model 'test-local-model'" in caplog.text

# Remove the previously postponed test placeholder
# @patch('server.llm.models.torch')
# @patch('server.llm.models.transformers')
# def test_local_model_init_loading_error(...):
#    pass

# --- LocalModel Generate Tests ---

@pytest.fixture
def initialized_local_model(local_config, mock_transformers_objects):
    """Provides an initialized LocalModel with a mocked pipeline."""
    with patch.dict('sys.modules', {'torch': MagicMock(), 'transformers': MagicMock()}):
        import sys
        transformers = sys.modules['transformers']
        torch = sys.modules['torch']
        
        mock_tokenizer, mock_model, mock_pipeline = mock_transformers_objects
        
        # Configure mocks for successful loading
        transformers.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
        transformers.AutoModelForCausalLM.from_pretrained.return_value = mock_model
        transformers.pipeline.return_value = mock_pipeline
        torch.cuda.is_available.return_value = False
        torch.backends.mps.is_available.return_value = False
        mock_model.to.return_value = mock_model # Ensure .to() returns the mock model

        model = LocalModel(config=local_config)
        assert model.pipeline is mock_pipeline # Verify pipeline was set
        # Attach mock pipeline for easy access
        model._test_mocks = {"pipeline": mock_pipeline}
        yield model

def test_local_model_generate_success(initialized_local_model):
    """Test successful generation using the LocalModel pipeline."""
    model = initialized_local_model
    mock_pipeline = model._test_mocks["pipeline"]
    prompt = "Once upon a time"
    expected_output = " there was a small cottage."
    pipeline_response = [{'generated_text': prompt + expected_output}]
    
    # Configure mock pipeline response
    mock_pipeline.return_value = pipeline_response
    
    # Action
    result = model.generate(prompt, temperature=0.8, top_k=50)
    
    # Assertions
    assert result == expected_output.strip()
    mock_pipeline.assert_called_once_with(
        prompt,
        max_new_tokens=model.config.max_tokens,
        temperature=0.8,
        do_sample=True, # temp > 0
        num_return_sequences=1,
        top_k=50 # Passed from kwargs
    )

def test_local_model_generate_no_sample(initialized_local_model):
    """Test generation with temperature 0 (do_sample=False)."""
    model = initialized_local_model
    mock_pipeline = model._test_mocks["pipeline"]
    prompt = "Test prompt"
    expected_output = " deterministic output."
    pipeline_response = [{'generated_text': prompt + expected_output}]
    mock_pipeline.return_value = pipeline_response
    
    result = model.generate(prompt, temperature=0)
    
    assert result == expected_output.strip()
    mock_pipeline.assert_called_once_with(
        prompt,
        max_new_tokens=model.config.max_tokens,
        temperature=0,
        do_sample=False, # temp = 0
        num_return_sequences=1
    )

def test_local_model_generate_pipeline_error(initialized_local_model):
    """Test error handling when the pipeline call fails."""
    model = initialized_local_model
    mock_pipeline = model._test_mocks["pipeline"]
    prompt = "Test prompt"
    error_message = "CUDA out of memory"
    
    # Configure mock pipeline to raise an error
    mock_pipeline.side_effect = RuntimeError(error_message)
    
    with pytest.raises(RuntimeError) as excinfo:
        model.generate(prompt)
        
    assert f"Error generating text with local model '{model.name}'" in str(excinfo.value)
    assert error_message in str(excinfo.value)

def test_local_model_generate_invalid_response(initialized_local_model):
    """Test handling of invalid response structures from the pipeline."""
    model = initialized_local_model
    mock_pipeline = model._test_mocks["pipeline"]
    prompt = "Test prompt"
    
    invalid_responses = [
        [], # Empty list
        [{"wrong_key": "..."}], # List with dict missing 'generated_text'
        "just a string", # Not a list
        None # None response
    ]
    
    for response in invalid_responses:
        mock_pipeline.return_value = response
        mock_pipeline.side_effect = None # Reset side effect
        with pytest.raises(RuntimeError) as excinfo:
            model.generate(prompt)
        assert "Unexpected response structure from local pipeline" in str(excinfo.value)
        mock_pipeline.reset_mock() # Reset calls for next iteration

# Remove TODO for generate tests
# TODO: Add tests for LocalModel generate when pipeline loading IS implemented