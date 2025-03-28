"""Tests for the code parser module."""

import pytest
from server.code_understanding.parser import CodeParser, TREE_SITTER_AVAILABLE

@pytest.fixture
def parser():
    """Create a code parser instance."""
    return CodeParser()

def test_parser_initialization(parser):
    """Test parser initialization."""
    assert parser is not None
    if TREE_SITTER_AVAILABLE:
        assert parser.parser is not None
        assert parser.language is not None
    else:
        assert parser.parser is not None
        assert parser.language is None

def test_parse_simple_code(parser):
    """Test parsing simple Python code."""
    code = """
def hello():
    print("Hello, world!")
"""
    tree = parser.parse(code)
    assert tree is not None
    root = parser.get_root_node(tree)
    assert root is not None
    assert root.type == "module"

def test_parse_imports(parser):
    """Test parsing import statements."""
    code = """
import os
from sys import path
"""
    tree = parser.parse(code)
    assert tree is not None
    root = parser.get_root_node(tree)
    assert root is not None
    
    # Convert to dict for easier inspection
    root_dict = parser.node_to_dict(root)
    assert root_dict['type'] == "module"
    
    # Check children
    children = root_dict['children']
    assert len(children) > 0
    
    # In tree-sitter mode, we should have import nodes
    # In mock mode, we should have import_statement nodes
    for child in children:
        assert child['type'] in ('import_statement', 'import_statement')

def test_parse_function_definition(parser):
    """Test parsing function definitions."""
    code = """
def greet(name: str) -> str:
    return f"Hello, {name}!"
"""
    tree = parser.parse(code)
    assert tree is not None
    root = parser.get_root_node(tree)
    assert root is not None
    
    # Convert to dict for easier inspection
    root_dict = parser.node_to_dict(root)
    assert root_dict['type'] == "module"
    
    # Check children
    children = root_dict['children']
    assert len(children) > 0
    
    # In tree-sitter mode, we should have function_definition nodes
    # In mock mode, we should have function_definition nodes
    for child in children:
        assert child['type'] in ('function_definition', 'function_definition')

def test_parse_class_definition(parser):
    """Test parsing class definitions."""
    code = """
class Person:
    def __init__(self, name: str):
        self.name = name
"""
    tree = parser.parse(code)
    assert tree is not None
    root = parser.get_root_node(tree)
    assert root is not None
    
    # Convert to dict for easier inspection
    root_dict = parser.node_to_dict(root)
    assert root_dict['type'] == "module"
    
    # Check children
    children = root_dict['children']
    assert len(children) > 0
    
    # In tree-sitter mode, we should have class_definition nodes
    # In mock mode, we should have class_definition nodes
    for child in children:
        assert child['type'] in ('class_definition', 'class_definition')

def test_parse_invalid_code(parser):
    """Test parsing invalid Python code."""
    code = """
def invalid(
    missing closing parenthesis
"""
    with pytest.raises(ValueError):
        parser.parse(code)

def test_node_to_dict_empty(parser):
    """Test converting None node to dict."""
    result = parser.node_to_dict(None)
    assert result == {} 