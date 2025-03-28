"""Tests for the parser module."""

import pytest
from server.code_understanding.parser import CodeParser, MockNode, MockTree

def test_parse_valid_code():
    """Test parsing valid Python code."""
    parser = CodeParser()
    code = "x = 1"
    tree = parser.parse(code)
    assert isinstance(tree, MockTree)
    assert tree.root_node is not None

def test_parse_invalid_code():
    """Test parsing invalid Python code."""
    parser = CodeParser()
    code = "x ="
    with pytest.raises(ValueError):
        parser.parse(code)

def test_get_root_node():
    """Test getting the root node of a tree."""
    parser = CodeParser()
    tree = MockTree(MockNode('module'))
    root = parser.get_root_node(tree)
    assert root is not None
    assert root.type == 'module'

def test_get_root_node_error():
    """Test error handling when getting root node."""
    parser = CodeParser()
    root = parser.get_root_node(None)
    assert root is None

def test_node_to_dict():
    """Test converting a node to a dictionary."""
    parser = CodeParser()
    node = MockNode(
        type='test',
        text='test_text',
        start_point=(1, 0),
        end_point=(1, 10),
        children=[
            MockNode(type='child', text='child_text')
        ]
    )
    result = parser.node_to_dict(node)
    assert result['type'] == 'test'
    assert result['text'] == 'test_text'
    assert result['start_point'] == (1, 0)
    assert result['end_point'] == (1, 10)
    assert len(result['children']) == 1
    assert result['children'][0]['type'] == 'child'
    assert result['children'][0]['text'] == 'child_text' 