"""Shared fixtures for code understanding tests."""

import pytest
from server.code_understanding import CodeParser, CodeAnalyzer, SymbolExtractor

@pytest.fixture
def mock_tree_sitter(mocker):
    """Mock tree-sitter components."""
    mock_language = mocker.MagicMock()
    mock_parser = mocker.MagicMock()
    mock_tree = mocker.MagicMock()
    mock_root = mocker.MagicMock()
    
    mocker.patch('tree_sitter.Language', return_value=mock_language)
    mocker.patch('tree_sitter.Parser', return_value=mock_parser)
    mock_parser.parse.return_value = mock_tree
    mock_tree.root_node = mock_root
    
    return {
        'language': mock_language,
        'parser': mock_parser,
        'tree': mock_tree,
        'root': mock_root
    }

@pytest.fixture
def mock_node_factory(mocker):
    """Factory for creating mock nodes."""
    def create_node(node_type, text, start_point, end_point):
        node = mocker.MagicMock()
        node.type = node_type
        node.text = text if isinstance(text, bytes) else text.encode()
        node.start_point = start_point
        node.end_point = end_point
        return node
    return create_node

@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return '''
import os
from typing import List, Optional

class BaseClass:
    def base_method(self) -> None:
        pass

class TestClass(BaseClass):
    def __init__(self, name: str):
        self.name = name
        
    def test_method(self, value: int) -> Optional[str]:
        result = f"Processing {value}"
        return result if value > 0 else None

def helper_function(items: List[int]) -> int:
    return sum(items)

test_variable = "Hello World"
numbers = [1, 2, 3]
result = helper_function(numbers)
'''

@pytest.fixture
def mock_analysis_result():
    """Sample analysis result for testing."""
    return {
        'imports': [{
            'name': 'os',
            'type': 'import',
            'start_line': 1,
            'end_line': 1
        }],
        'functions': [{
            'name': 'test_func',
            'start_line': 3,
            'end_line': 5,
            'parameters': [{'name': 'x', 'type': 'int'}]
        }],
        'classes': [{
            'name': 'TestClass',
            'start_line': 7,
            'end_line': 12,
            'methods': [{
                'name': 'test_method',
                'start_line': 8,
                'end_line': 9,
                'parameters': []
            }],
            'bases': ['BaseClass']
        }],
        'variables': [{
            'name': 'test_var',
            'start_line': 14,
            'end_line': 14,
            'type': 'str'
        }]
    }

@pytest.fixture
def code_parser(mock_tree_sitter):
    """Create a CodeParser instance with mocked dependencies."""
    parser = CodeParser()
    parser.language = mock_tree_sitter['language']
    parser.parser = mock_tree_sitter['parser']
    return parser

@pytest.fixture
def code_analyzer():
    """Create a CodeAnalyzer instance."""
    return CodeAnalyzer()

@pytest.fixture
def symbol_extractor():
    """Create a SymbolExtractor instance."""
    return SymbolExtractor() 