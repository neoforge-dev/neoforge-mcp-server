"""Tests for the symbols module."""

import pytest
from server.code_understanding.symbols import SymbolExtractor
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

def test_symbol_table_management(extractor):
    """Test symbol table management."""
    # Add symbols
    extractor._add_symbol('test_var', {
        'type': 'variable',
        'scope': 'global',
        'start': (1, 0),
        'end': (1, 10)
    })
    
    extractor._add_symbol('test_func', {
        'type': 'function',
        'scope': 'global',
        'start': (3, 0),
        'end': (5, 0),
        'params': ['x', 'y']
    })
    
    # Check symbols
    assert 'test_var' in extractor.symbols
    assert extractor.symbols['test_var']['type'] == 'variable'
    assert extractor.symbols['test_var']['scope'] == 'global'
    
    assert 'test_func' in extractor.symbols
    assert extractor.symbols['test_func']['type'] == 'function'
    assert len(extractor.symbols['test_func']['params']) == 2

def test_scope_resolution(extractor):
    """Test scope resolution."""
    # Create nested scopes
    extractor.current_scope = 'global'
    
    # Add class
    extractor._add_symbol('TestClass', {
        'type': 'class',
        'scope': 'global',
        'start': (1, 0),
        'end': (10, 0)
    })
    
    # Add method in class scope
    extractor.current_scope = 'TestClass'
    extractor._add_symbol('test_method', {
        'type': 'method',
        'scope': 'TestClass',
        'start': (2, 4),
        'end': (4, 4)
    })
    
    # Add variable in method scope
    extractor.current_scope = 'TestClass.test_method'
    extractor._add_symbol('local_var', {
        'type': 'variable',
        'scope': 'TestClass.test_method',
        'start': (3, 8),
        'end': (3, 20)
    })
    
    # Check scopes
    assert extractor.symbols['TestClass']['scope'] == 'global'
    assert extractor.symbols['test_method']['scope'] == 'TestClass'
    assert extractor.symbols['local_var']['scope'] == 'TestClass.test_method'

def test_reference_tracking(extractor):
    """Test reference tracking."""
    # Add references
    extractor._add_reference('test_var', {
        'scope': 'global',
        'start': (1, 0),
        'end': (1, 10)
    })
    
    extractor._add_reference('test_var', {
        'scope': 'test_func',
        'start': (3, 4),
        'end': (3, 14)
    })
    
    # Check references
    assert 'test_var' in extractor.references
    assert len(extractor.references['test_var']) == 2
    assert extractor.references['test_var'][0]['scope'] == 'global'
    assert extractor.references['test_var'][1]['scope'] == 'test_func'

def test_type_handling(extractor):
    """Test type handling."""
    # Test basic types
    node = Node(type="identifier", text="x: int")
    type_info = extractor._get_type_info(node)
    assert type_info == 'int'
    
    # Test complex types
    node = Node(type="identifier", text="x: List[str]")
    type_info = extractor._get_type_info(node)
    assert type_info == 'List[str]'
    
    # Test optional types
    node = Node(type="identifier", text="x: Optional[int]")
    type_info = extractor._get_type_info(node)
    assert type_info == 'Optional[int]'

def test_node_text_handling(extractor):
    """Test node text handling."""
    # Test string text
    node = Node(type="identifier", text="test_var")
    text = extractor._get_node_text(node)
    assert text == "test_var"
    
    # Test bytes text
    node = Node(type="identifier", text=b"test_var")
    text = extractor._get_node_text(node)
    assert text == "test_var"
    
    # Test invalid text
    node = Node(type="identifier", text=None)
    text = extractor._get_node_text(node)
    assert text == ""

def test_error_handling(extractor):
    """Test error handling."""
    # Test with None tree
    result = extractor.extract_symbols(None)
    expected_result = {
        'functions': [],
        'classes': [],
        'variables': []
    }
    assert result == expected_result
    
    # Test with invalid node
    extractor._process_node(None)
    assert extractor.symbols == {}
    assert extractor.references == {}
    
    # Test with invalid node text
    node = Node(type="identifier", text=123)  # Invalid text type
    text = extractor._get_node_text(node)
    assert text == "" 