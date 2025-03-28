"""Tests for the relationship builder."""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from server.code_understanding.relationships import (
    RelationshipBuilder,
    FileContext,
    IGNORED_NAMES
)
from server.code_understanding.graph import Graph, Node, Edge, RelationType

@pytest.fixture
def sample_code():
    """Sample Python code for testing."""
    return """
import os
from sys import path

def hello(name):
    print(f"Hello {name}")
    return path

class Greeter:
    def __init__(self, prefix="Hello"):
        self.prefix = prefix
        
    def greet(self, name):
        return f"{self.prefix} {name}"
        
    @staticmethod
    def say_hi():
        return "Hi there!"

def main():
    g = Greeter("Hey")
    hello("World")
    print(g.greet("Universe"))
    print(Greeter.say_hi())
"""

@pytest.fixture
def mock_parser():
    """Create a mock parser for testing."""
    parser = Mock()
    parser.parse.return_value = Mock()  # Mock tree
    parser.extract_symbols.return_value = (
        {
            'imports': [
                {'module': 'os', 'start_line': 1, 'end_line': 1},
                {'module': 'sys', 'symbol': 'path', 'start_line': 2, 'end_line': 2}
            ],
            'functions': [
                {'name': 'hello', 'start_line': 4, 'end_line': 6},
                {'name': 'main', 'start_line': 20, 'end_line': 25}
            ],
            'classes': [
                {
                    'name': 'Greeter',
                    'start_line': 8, 'end_line': 18,
                    'methods': [
                        {'name': '__init__', 'start_line': 9, 'end_line': 10},
                        {'name': 'greet', 'start_line': 12, 'end_line': 13},
                        {'name': 'say_hi', 'start_line': 15, 'end_line': 16}
                    ]
                }
            ],
            'variables': []
        },
        {
            'calls': [
                {'name': 'print', 'scope': 'hello', 'start_line': 5, 'end_line': 5},
                {'name': 'Greeter', 'scope': 'main', 'start_line': 21, 'end_line': 21},
                {'name': 'hello', 'scope': 'main', 'start_line': 22, 'end_line': 22},
                {'name': 'greet', 'scope': 'g', 'start_line': 23, 'end_line': 23},
                {'name': 'say_hi', 'scope': 'Greeter', 'start_line': 24, 'end_line': 24},
                {'name': 'print', 'scope': 'main', 'start_line': 23, 'end_line': 23},
                {'name': 'print', 'scope': 'main', 'start_line': 24, 'end_line': 24}
            ],
            'attributes': [
                {'name': 'prefix', 'scope': 'self', 'start_line': 10, 'end_line': 10}
            ],
            'variables': []
        }
    )
    return parser

@pytest.fixture
def builder(mock_parser):
    """Create a RelationshipBuilder instance with mock parser."""
    builder = RelationshipBuilder()
    builder.parser = mock_parser
    return builder

def test_analyze_file(tmp_path, builder, sample_code):
    """Test analyzing a single file."""
    # Create test file
    file_path = tmp_path / "test.py"
    file_path.write_text(sample_code)
    
    # Analyze file
    builder.analyze_file(str(file_path))
    
    # Verify file context was created
    assert str(file_path) in builder.file_contexts
    context = builder.file_contexts[str(file_path)]
    assert context.path == str(file_path)
    assert context.code == sample_code
    
    # Verify relationships were built
    graph = builder.get_relationships()
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

def test_analyze_directory(tmp_path, builder, sample_code):
    """Test analyzing a directory of Python files."""
    # Create test directory structure
    module1 = tmp_path / "module1.py"
    module1.write_text("def func1(): return 'Hello'")
    
    module2 = tmp_path / "module2.py"
    module2.write_text("from module1 import func1\ndef func2(): return func1()")
    
    # Create a subdirectory with another file
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    module3 = subdir / "module3.py"
    module3.write_text("from ..module2 import func2\ndef func3(): return func2()")
    
    # Analyze directory
    builder.analyze_directory(str(tmp_path))
    
    # Verify all files were analyzed
    assert str(module1) in builder.file_contexts
    assert str(module2) in builder.file_contexts
    assert str(module3) in builder.file_contexts

def test_analyze_file_with_code(builder, sample_code):
    """Test analyzing a file with provided code string."""
    file_path = "test.py"
    builder.analyze_file(file_path, code=sample_code)
    
    # Verify file context was created
    assert file_path in builder.file_contexts
    context = builder.file_contexts[file_path]
    assert context.path == file_path
    assert context.code == sample_code

def test_analyze_file_not_found(builder):
    """Test handling of non-existent files."""
    with pytest.raises(FileNotFoundError):
        builder.analyze_file("non_existent_file.py")

def test_analyze_directory_not_found(builder):
    """Test handling of non-existent directories."""
    with pytest.raises(FileNotFoundError):
        builder.analyze_directory("non_existent_directory")

def test_clear(builder, tmp_path, sample_code):
    """Test clearing the relationship builder."""
    # Add some data
    file_path = tmp_path / "test.py"
    file_path.write_text(sample_code)
    builder.analyze_file(str(file_path))
    
    # Verify data exists
    assert len(builder.file_contexts) > 0
    assert len(builder.get_relationships().nodes) > 0
    
    # Clear the builder
    builder.clear()
    
    # Verify data was cleared
    assert len(builder.file_contexts) == 0
    assert len(builder.get_relationships().nodes) == 0
    assert len(builder.get_relationships().edges) == 0

def test_process_imports(builder):
    """Test processing import statements."""
    imports = [
        {'module': 'os', 'start_line': 1, 'end_line': 1},
        {'module': 'sys', 'symbol': 'path', 'start_line': 2, 'end_line': 2},
        {'module': 'typing', 'symbol': 'List', 'alias': 'ListType', 'start_line': 3, 'end_line': 3}
    ]
    
    builder._process_imports(imports)
    graph = builder.get_relationships()
    
    # Verify module nodes were created
    module_nodes = [n for n in graph.nodes.values() if n.type == 'module']
    assert len(module_nodes) == 3  # os, sys, typing
    
    # Verify import nodes were created
    import_nodes = [n for n in graph.nodes.values() if n.type == 'import']
    assert len(import_nodes) == 2  # path, ListType
    
    # Verify edges were created
    edges = graph.get_edges(rel_type=RelationType.IMPORTS)
    assert len(edges) == 4  # os->os, sys->path, typing->ListType

def test_process_classes(builder):
    """Test processing class definitions."""
    context = FileContext(
        path="test.py",
        code="",
        tree=Mock(),
        symbols={
            'classes': [
                {
                    'name': 'TestClass',
                    'start_line': 1,
                    'end_line': 10,
                    'methods': [
                        {'name': 'method1', 'start_line': 2, 'end_line': 3},
                        {'name': 'method2', 'start_line': 4, 'end_line': 5}
                    ]
                }
            ]
        }
    )
    
    builder._process_classes(context)
    graph = builder.get_relationships()
    
    # Verify class node was created
    class_nodes = graph.get_nodes_by_type('class')
    assert len(class_nodes) == 1
    assert class_nodes[0].name == 'TestClass'
    
    # Verify method nodes were created
    method_nodes = graph.get_nodes_by_type('method')
    assert len(method_nodes) == 2
    assert {n.name for n in method_nodes} == {'method1', 'method2'}
    
    # Verify contains edges were created
    edges = graph.get_edges(rel_type=RelationType.CONTAINS)
    assert len(edges) == 2  # TestClass contains each method

def test_process_functions(builder):
    """Test processing function definitions."""
    context = FileContext(
        path="test.py",
        code="",
        tree=Mock(),
        symbols={
            'functions': [
                {'name': 'func1', 'start_line': 1, 'end_line': 2},
                {'name': 'func2', 'start_line': 3, 'end_line': 4}
            ]
        }
    )
    
    builder._process_functions(context)
    graph = builder.get_relationships()
    
    # Verify function nodes were created
    function_nodes = graph.get_nodes_by_type('function')
    assert len(function_nodes) == 2
    assert {n.name for n in function_nodes} == {'func1', 'func2'}

def test_process_references(builder):
    """Test processing code references."""
    # Create some nodes first
    context = FileContext(
        path="test.py",
        code="",
        tree=Mock(),
        references={
            'calls': [
                {'name': 'func1', 'scope': 'main', 'start_line': 1, 'end_line': 1},
                {'name': 'func2', 'scope': 'main', 'start_line': 2, 'end_line': 2}
            ]
        }
    )
    
    # Add nodes that will be referenced
    builder.graph.add_node(name='main', type='function', file_path='test.py')
    builder.graph.add_node(name='func1', type='function', file_path='test.py')
    builder.graph.add_node(name='func2', type='function', file_path='test.py')
    
    builder._process_references(context)
    graph = builder.get_relationships()
    
    # Verify call edges were created
    edges = graph.get_edges(rel_type=RelationType.CALLS)
    assert len(edges) == 2  # main calls func1, main calls func2

def test_ignored_names():
    """Test that ignored names are properly defined."""
    assert 'self' in IGNORED_NAMES
    assert 'cls' in IGNORED_NAMES
    assert len(IGNORED_NAMES) == 2  # Only these two names should be ignored

def test_file_context_initialization():
    """Test FileContext initialization."""
    context = FileContext(
        path="test.py",
        code="test code",
        tree=Mock()
    )
    
    # Verify default dictionaries are empty
    assert context.symbols['imports'] == []
    assert context.symbols['functions'] == []
    assert context.symbols['classes'] == []
    assert context.symbols['variables'] == []
    
    assert context.references['imports'] == []
    assert context.references['calls'] == []
    assert context.references['attributes'] == []
    assert context.references['variables'] == [] 