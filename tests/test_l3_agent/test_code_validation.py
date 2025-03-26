import pytest
from unittest.mock import Mock, patch
import server

@pytest.fixture
def valid_python_code():
    return """
def test_function():
    x = 1
    y = 2
    return x + y
"""

@pytest.fixture
def invalid_python_code():
    return """
def test_function()
    x = 1
    y = 2
    return x + y
"""

def test_validate_code_quality_success(valid_python_code):
    with patch('server.lint_code') as mock_lint:
        mock_lint.return_value = {'status': 'success'}
        
        result = server.validate_code_quality(valid_python_code)
        
        assert result['status'] == 'success'
        assert result['language'] == 'python'
        assert 'results' in result
        assert 'summary' in result

def test_validate_code_quality_syntax_error(invalid_python_code):
    result = server.validate_code_quality(invalid_python_code)
    
    assert result['status'] == 'error'
    assert result['results']['syntax']['status'] == 'error'
    assert 'SyntaxError' in result['results']['syntax']['error']

def test_validate_code_quality_empty_code():
    result = server.validate_code_quality("")
    
    assert result['status'] == 'error'
    assert result['error'] == 'No code provided'

def test_validate_code_quality_specific_checks():
    code = "x = 1"
    checks = ['syntax', 'style']
    
    with patch('server.lint_code') as mock_lint:
        mock_lint.return_value = {'status': 'success'}
        
        result = server.validate_code_quality(code, checks=checks)
        
        assert set(result['results'].keys()) == set(checks)

def test_validate_code_quality_complexity():
    complex_code = """
def complex_function(x):
    if x > 0:
        if x < 10:
            for i in range(x):
                if i % 2 == 0:
                    while True:
                        try:
                            if i > 5:
                                return True
                        except:
                            pass
    return False
"""
    
    result = server.validate_code_quality(complex_code, checks=['complexity'])
    
    assert result['results']['complexity']['status'] == 'warning'
    assert result['results']['complexity']['complexity_score'] > 10

def test_validate_code_quality_security():
    insecure_code = """
import pickle
def process_data(data):
    return pickle.loads(data)
"""
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=1,
            stdout="Found security issue: Use of unsafe pickle.loads()"
        )
        
        result = server.validate_code_quality(insecure_code, checks=['security'])
        
        assert result['results']['security']['status'] == 'error'
        assert 'issues' in result['results']['security']

def test_validate_code_quality_performance():
    inefficient_code = """
def process_list(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
"""
    
    result = server.validate_code_quality(inefficient_code, checks=['performance'])
    
    assert 'performance' in result['results']
    assert 'recommendations' in result['results']['performance']
    assert any('list comprehension' in r.lower() 
              for r in result['results']['performance']['recommendations'])

def test_validate_code_quality_summary_generation():
    with patch('server.lint_code') as mock_lint:
        mock_lint.return_value = {'status': 'success'}
        
        result = server.validate_code_quality("x = 1")
        
        assert '✅' in result['summary']  # Success markers
        assert isinstance(result['summary'], str)
        assert len(result['summary'].split('\n')) >= 1  # At least one check

def test_validate_code_quality_all_checks_failed():
    with patch('server.lint_code') as mock_lint:
        mock_lint.return_value = {'status': 'error', 'error': 'Style error'}
        with patch('server._analyze_complexity') as mock_complexity:
            mock_complexity.return_value = {
                'status': 'error',
                'error': 'Too complex'
            }
            with patch('server._analyze_security') as mock_security:
                mock_security.return_value = {
                    'status': 'error',
                    'error': 'Security issue'
                }
                
                result = server.validate_code_quality("x = 1")
                
                assert result['status'] == 'error'
                assert '❌' in result['summary']  # Error markers

def test_validate_code_quality_exception_handling():
    with patch('ast.parse') as mock_parse:
        mock_parse.side_effect = Exception("Unexpected error")
        
        result = server.validate_code_quality("x = 1")
        
        assert result['status'] == 'error'
        assert 'error' in result
