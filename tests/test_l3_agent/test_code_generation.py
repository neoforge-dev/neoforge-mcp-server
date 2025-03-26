import pytest
from unittest.mock import Mock, patch
import server

@pytest.fixture
def mock_anthropic():
    with patch('server.anthropic') as mock:
        mock.messages.create.return_value = Mock(
            content="def test_function():\n    return True",
            usage=Mock(total_tokens=50)
        )
        yield mock

@pytest.fixture
def mock_openai():
    with patch('server.openai.ChatCompletion') as mock:
        mock.create.return_value = Mock(
            choices=[Mock(message=Mock(content="def test_function():\n    return True"))],
            usage=Mock(total_tokens=50)
        )
        yield mock

def test_generate_code_with_claude(mock_anthropic):
    result = server.generate_code(
        prompt="Write a test function",
        model="claude-3-sonnet"
    )
    
    assert result['status'] == 'success'
    assert 'def test_function()' in result['code']
    assert result['tokens_used'] == 50
    assert 'generation_time' in result
    mock_anthropic.messages.create.assert_called_once()

def test_generate_code_with_gpt4(mock_openai):
    result = server.generate_code(
        prompt="Write a test function",
        model="gpt-4"
    )
    
    assert result['status'] == 'success'
    assert 'def test_function()' in result['code']
    assert result['tokens_used'] == 50
    assert 'generation_time' in result
    mock_openai.create.assert_called_once()

@pytest.mark.parametrize("model", ["code-llama", "starcoder"])
def test_generate_code_with_local_model(model):
    with patch('server.pipeline') as mock_pipeline:
        mock_pipeline.return_value = lambda **kwargs: [
            {'generated_text': "def test_function():\n    return True"}
        ]
        
        result = server.generate_code(
            prompt="Write a test function",
            model=model
        )
        
        assert result['status'] == 'success'
        assert 'def test_function()' in result['code']
        assert 'tokens_used' in result
        assert 'generation_time' in result
        mock_pipeline.assert_called_once()

def test_generate_code_with_invalid_model():
    result = server.generate_code(
        prompt="Write a test function",
        model="invalid-model"
    )
    
    assert result['status'] == 'error'
    assert 'error' in result
    assert 'Invalid model' in result['error']

def test_generate_code_with_empty_prompt():
    result = server.generate_code(prompt="")
    
    assert result['status'] == 'error'
    assert 'error' in result
    assert 'Empty prompt' in result['error']

def test_generate_code_with_context():
    with patch('server._get_workspace_info') as mock_workspace:
        mock_workspace.return_value = {'workspace': 'test'}
        with patch('server._generate_with_api_model') as mock_generate:
            mock_generate.return_value = {
                'status': 'success',
                'code': 'def test_function():\n    return True',
                'tokens_used': 50,
                'generation_time': 0.5
            }
            
            result = server.generate_code(
                prompt="Write a test function",
                context={'file': 'test.py'}
            )
            
            assert result['status'] == 'success'
            assert 'workspace' in result['context']
            assert 'file' in result['context']

def test_generate_code_with_custom_system_prompt():
    custom_prompt = "You are a Python expert"
    with patch('server._generate_with_api_model') as mock_generate:
        server.generate_code(
            prompt="Write a test function",
            system_prompt=custom_prompt
        )
        
        mock_generate.assert_called_with(
            prompt="Write a test function",
            model="claude-3-sonnet",
            system_prompt=custom_prompt,
            max_tokens=None,
            temperature=0.7
        )

def test_generate_code_metrics_tracking():
    with patch('server._track_generation_metrics') as mock_track:
        with patch('server._generate_with_api_model') as mock_generate:
            mock_generate.return_value = {
                'status': 'success',
                'code': 'def test():\n    pass',
                'tokens_used': 50,
                'generation_time': 0.5
            }
            
            server.generate_code(
                prompt="Write a test function",
                model="claude-3-sonnet"
            )
            
            mock_track.assert_called_with(
                model="claude-3-sonnet",
                language="python",
                tokens_used=50,
                success=True
            )
