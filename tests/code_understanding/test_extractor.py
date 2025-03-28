"""Tests for the symbol extractor module."""

import pytest
from server.code_understanding.extractor import SymbolExtractor
from server.code_understanding.parser import MockNode as Node, MockTree as Tree

@pytest.fixture
def extractor():
    """Create a symbol extractor instance."""
    return SymbolExtractor()

@pytest.fixture
def mock_tree():
    """Create a mock syntax tree."""
    # Create mock nodes
    import_node = Node(
        type="import",
        text="import os",
        start_point=(1, 0),
        end_point=(1, 9)
    )
    
    function_node = Node(
        type="function_definition",
        text="def test_func(x: int) -> str:",
        start_point=(3, 0),
        end_point=(4, 12),
        fields={
            'name': Node(type="identifier", text="test_func"),
            'parameters': Node(type="parameters", children=[
                Node(type="identifier", text="x: int")
            ])
        }
    )
    
    class_node = Node(
        type="class_definition",
        text="class TestClass(BaseClass):",
        start_point=(6, 0),
        end_point=(9, 12),
        fields={
            'name': Node(type="identifier", text="TestClass"),
            'bases': Node(type="bases", children=[
                Node(type="identifier", text="BaseClass")
            ])
        }
    )
    
    # Create root node
    root = Node(type="module")
    root.children = [import_node, function_node, class_node]
    
    return Tree(root)

def test_extract_symbols_basic(extractor, mock_tree):
    """Test basic symbol extraction."""
    result = extractor.extract_symbols(mock_tree)
    
    assert 'symbols' in result
    assert 'references' in result
    
    symbols = result['symbols']
    assert 'os' in symbols
    assert 'test_func' in symbols
    assert 'TestClass' in symbols
    
    # Check symbol types
    assert symbols['os']['type'] == 'import'
    assert symbols['test_func']['type'] == 'function'
    assert symbols['TestClass']['type'] == 'class'

def test_process_import(extractor):
    """Test processing import statements."""
    # Test simple import
    node = Node(type="import", text="import os")
    extractor._process_import(node)
    
    assert 'os' in extractor.symbols
    assert extractor.symbols['os']['type'] == 'import'
    
    # Test from import
    node = Node(type="import", text="from typing import List, Optional")
    extractor._process_import(node)
    
    assert 'List' in extractor.symbols
    assert 'Optional' in extractor.symbols
    assert extractor.symbols['List']['type'] == 'import'
    assert extractor.symbols['Optional']['type'] == 'import'

def test_process_function(extractor):
    """Test processing function definitions."""
    node = Node(
        type="function_definition",
        fields={
            'name': Node(type="identifier", text="test_func"),
            'parameters': Node(type="parameters", children=[
                Node(type="identifier", text="x: int"),
                Node(type="identifier", text="y: str")
            ])
        }
    )
    extractor._process_function(node)
    
    assert 'test_func' in extractor.symbols
    assert extractor.symbols['test_func']['type'] == 'function'
    assert len(extractor.symbols['test_func']['params']) == 2
    assert 'x' in extractor.symbols['test_func']['params']
    assert 'y' in extractor.symbols['test_func']['params']

def test_process_class(extractor):
    """Test processing class definitions."""
    node = Node(
        type="class_definition",
        fields={
            'name': Node(type="identifier", text="TestClass"),
            'bases': Node(type="bases", children=[
                Node(type="identifier", text="BaseClass")
            ])
        }
    )
    extractor._process_class(node)
    
    assert 'TestClass' in extractor.symbols
    assert extractor.symbols['TestClass']['type'] == 'class'
    assert len(extractor.symbols['TestClass']['bases']) == 1
    assert 'BaseClass' in extractor.symbols['TestClass']['bases']

def test_process_identifier(extractor):
    """Test processing identifiers."""
    node = Node(type="identifier", text="test_var")
    extractor._process_identifier(node)
    
    assert 'test_var' in extractor.references
    assert len(extractor.references['test_var']) == 1
    assert extractor.references['test_var'][0]['scope'] == 'global'

def test_process_assignment(extractor):
    """Test processing assignments."""
    node = Node(
        type="assignment",
        fields={
            'left': Node(type="identifier", text="test_var")
        }
    )
    extractor._process_assignment(node)
    
    assert 'test_var' in extractor.symbols
    assert extractor.symbols['test_var']['type'] == 'variable'

def test_scope_handling(extractor):
    """Test scope handling during symbol extraction."""
    # Create a class with a method
    class_node = Node(
        type="class_definition",
        fields={
            'name': Node(type="identifier", text="TestClass"),
            'body': Node(type="body", children=[
                Node(
                    type="function_definition",
                    fields={
                        'name': Node(type="identifier", text="test_method"),
                        'parameters': Node(type="parameters", children=[])
                    }
                )
            ])
        }
    )
    
    extractor._process_node(class_node)
    
    # Check that method is in class scope
    assert 'test_method' in extractor.symbols
    assert extractor.symbols['test_method']['scope'] == 'TestClass'

def test_error_handling(extractor):
    """Test error handling during symbol extraction."""
    # Test with invalid tree
    result = extractor.extract_symbols(None)
    assert result == {'symbols': {}, 'references': {}}
    
    # Test with invalid node
    extractor._process_node(None)
    assert extractor.symbols == {}
    assert extractor.references == {} 