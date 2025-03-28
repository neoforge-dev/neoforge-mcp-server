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
from server.code_understanding.graph import Graph, Node, Edge, RelationType, NodeType

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
    return parser

@pytest.fixture
def mock_extractor():
    """Create a mock extractor for testing."""
    extractor = Mock()
    extractor.extract_symbols.return_value = (
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
    return extractor

@pytest.fixture
def builder(mock_parser, mock_extractor):
    """Create a RelationshipBuilder instance with mock parser."""
    builder = RelationshipBuilder()
    builder.parser = mock_parser
    builder.extractor = mock_extractor
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
    # Create a current file node
    builder.current_file_node = builder.graph.find_or_create_node(
        name="test.py",
        type=NodeType.MODULE,
        properties={
            'file_path': "test.py"
        }
    )

    imports = [
        {'module': 'os', 'start_line': 1, 'end_line': 1},
        {'module': 'sys', 'symbol': 'path', 'start_line': 2, 'end_line': 2},
        {'module': 'typing', 'symbol': 'List', 'alias': 'ListType', 'start_line': 3, 'end_line': 3}
    ]

    builder._process_imports(imports)

    # Verify nodes were created
    graph = builder.get_relationships()
    module_nodes = graph.get_nodes_by_type('module')
    assert len(module_nodes) == 3  # os, sys, typing
    assert {n.name for n in module_nodes} == {'os', 'sys', 'typing', 'test.py'}

    # Verify edges were created
    edges = graph.get_edges(rel_type=RelationType.IMPORTS)
    assert len(edges) == 4  # test.py -> os, test.py -> sys, test.py -> path, test.py -> List

def test_process_classes(builder):
    """Test processing class definitions."""
    # Create a current file node
    builder.current_file_node = builder.graph.find_or_create_node(
        name="test.py",
        type=NodeType.MODULE,
        properties={
            'file_path': "test.py"
        }
    )

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
    assert len(edges) == 3  # test.py -> TestClass, TestClass -> method1, TestClass -> method2

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

def test_process_classes_with_inheritance(builder):
    """Test processing class definitions with inheritance."""
    # Create a current file node
    builder.current_file_node = builder.graph.find_or_create_node(
        name="test.py",
        type=NodeType.MODULE,
        properties={
            'file_path': "test.py"
        }
    )

    context = FileContext(
        path="test.py",
        code="",
        tree=Mock(),
        symbols={
            'classes': [
                {
                    'name': 'BaseClass',
                    'start_line': 1,
                    'end_line': 5,
                    'methods': [
                        {'name': 'base_method', 'start_line': 2, 'end_line': 3}
                    ]
                },
                {
                    'name': 'DerivedClass',
                    'start_line': 7,
                    'end_line': 12,
                    'bases': ['BaseClass'],
                    'methods': [
                        {'name': 'derived_method', 'start_line': 8, 'end_line': 9}
                    ]
                }
            ]
        }
    )

    builder._process_classes(context)
    graph = builder.get_relationships()

    # Verify class nodes were created
    class_nodes = graph.get_nodes_by_type('class')
    assert len(class_nodes) == 2
    assert {n.name for n in class_nodes} == {'BaseClass', 'DerivedClass'}

    # Verify method nodes were created
    method_nodes = graph.get_nodes_by_type('method')
    assert len(method_nodes) == 2
    assert {n.name for n in method_nodes} == {'base_method', 'derived_method'}

    # Verify inheritance edge was created
    edges = graph.get_edges(rel_type=RelationType.INHERITS)
    assert len(edges) == 1  # DerivedClass -> BaseClass

def test_process_classes_with_multiple_inheritance(builder):
    """Test processing class definitions with multiple inheritance."""
    # Create a current file node
    builder.current_file_node = builder.graph.find_or_create_node(
        name="test.py",
        type=NodeType.MODULE,
        properties={
            'file_path': "test.py"
        }
    )

    context = FileContext(
        path="test.py",
        code="",
        tree=Mock(),
        symbols={
            'classes': [
                {
                    'name': 'ClassA',
                    'start_line': 1,
                    'end_line': 5,
                    'methods': [
                        {'name': 'method_a', 'start_line': 2, 'end_line': 3}
                    ]
                },
                {
                    'name': 'ClassB',
                    'start_line': 7,
                    'end_line': 11,
                    'methods': [
                        {'name': 'method_b', 'start_line': 8, 'end_line': 9}
                    ]
                },
                {
                    'name': 'ClassC',
                    'start_line': 13,
                    'end_line': 18,
                    'bases': ['ClassA', 'ClassB'],
                    'methods': [
                        {'name': 'method_c', 'start_line': 14, 'end_line': 15}
                    ]
                }
            ]
        }
    )

    builder._process_classes(context)
    graph = builder.get_relationships()

    # Verify class nodes were created
    class_nodes = graph.get_nodes_by_type('class')
    assert len(class_nodes) == 3
    assert {n.name for n in class_nodes} == {'ClassA', 'ClassB', 'ClassC'}

    # Verify method nodes were created
    method_nodes = graph.get_nodes_by_type('method')
    assert len(method_nodes) == 3
    assert {n.name for n in method_nodes} == {'method_a', 'method_b', 'method_c'}

    # Verify inheritance edges were created
    edges = graph.get_edges(rel_type=RelationType.INHERITS)
    assert len(edges) == 2  # ClassC -> ClassA, ClassC -> ClassB

def test_process_functions_with_parameters(builder):
    """Test processing function definitions with parameters."""
    # Create a current file node
    builder.current_file_node = builder.graph.find_or_create_node(
        name="test.py",
        type=NodeType.MODULE,
        properties={
            'file_path': "test.py"
        }
    )

    context = FileContext(
        path="test.py",
        code="",
        tree=Mock(),
        symbols={
            'functions': [
                {
                    'name': 'complex_function',
                    'start_line': 1,
                    'end_line': 10,
                    'parameters': [
                        {'name': 'param1', 'start_line': 1, 'end_line': 1},
                        {'name': 'param2: str', 'start_line': 1, 'end_line': 1},
                        {'name': 'param3: int = 42', 'start_line': 1, 'end_line': 1}
                    ]
                }
            ]
        }
    )

    builder._process_functions(context)
    graph = builder.get_relationships()

    # Verify function node was created
    function_nodes = graph.get_nodes_by_type('function')
    assert len(function_nodes) == 1
    assert function_nodes[0].name == 'complex_function'

    # Verify parameter nodes were created
    parameter_nodes = graph.get_nodes_by_type('parameter')
    assert len(parameter_nodes) == 3
    assert {n.name for n in parameter_nodes} == {'param1', 'param2: str', 'param3: int = 42'}

    # Verify contains edges were created
    edges = graph.get_edges(rel_type=RelationType.CONTAINS)
    assert len(edges) == 4  # test.py -> complex_function, complex_function -> param1, complex_function -> param2, complex_function -> param3

def test_process_references_with_complex_scopes(builder):
    """Test processing references with complex scopes."""
    # Create a current file node
    builder.current_file_node = builder.graph.find_or_create_node(
        name="test.py",
        type=NodeType.MODULE,
        properties={
            'file_path': "test.py"
        }
    )

    context = FileContext(
        path="test.py",
        code="",
        tree=Mock(),
        references={
            'calls': [
                {
                    'name': 'method1',
                    'scope': 'ClassA.method2',
                    'start_line': 1,
                    'end_line': 1
                },
                {
                    'name': 'method2',
                    'scope': 'ClassB.method3',
                    'start_line': 2,
                    'end_line': 2
                }
            ],
            'attributes': [
                {
                    'name': 'attr1',
                    'scope': 'ClassA.method1',
                    'start_line': 3,
                    'end_line': 3
                }
            ]
        }
    )

    # Add nodes that will be referenced
    builder.graph.add_node(name='ClassA', type='class', file_path='test.py')
    builder.graph.add_node(name='method1', type='method', file_path='test.py')
    builder.graph.add_node(name='method2', type='method', file_path='test.py')
    builder.graph.add_node(name='ClassB', type='class', file_path='test.py')
    builder.graph.add_node(name='method3', type='method', file_path='test.py')

    builder._process_references(context)
    graph = builder.get_relationships()

    # Verify call edges were created
    call_edges = graph.get_edges(rel_type=RelationType.CALLS)
    assert len(call_edges) == 2  # ClassA.method2 -> method1, ClassB.method3 -> method2

def test_process_references_with_external_symbols(builder):
    """Test processing references to external symbols."""
    # Create a current file node
    builder.current_file_node = builder.graph.find_or_create_node(
        name="test.py",
        type=NodeType.MODULE,
        properties={
            'file_path': "test.py"
        }
    )

    context = FileContext(
        path="test.py",
        code="",
        tree=Mock(),
        references={
            'calls': [
                {
                    'name': 'external_func',
                    'scope': 'local_func',
                    'start_line': 1,
                    'end_line': 1
                }
            ]
        }
    )

    # Add local function node
    builder.graph.add_node(name='local_func', type='function', file_path='test.py')

    builder._process_references(context)
    graph = builder.get_relationships()

    # Verify external function node was created
    function_nodes = graph.get_nodes_by_type('function')
    assert len(function_nodes) == 2  # local_func and external_func

def test_cross_file_references(tmp_path, builder):
    """Test handling of references across multiple files."""
    # Create test files
    file1 = tmp_path / "file1.py"
    file1.write_text("""
def func1():
    return "Hello"

class ClassA:
    def method1(self):
        return func1()
    """)

    file2 = tmp_path / "file2.py"
    file2.write_text("""
from file1 import func1, ClassA

def func2():
    return func1()

class ClassB(ClassA):
    def method2(self):
        return self.method1()
    """)

    # Analyze both files
    builder.analyze_file(str(file1))
    builder.analyze_file(str(file2))

    graph = builder.get_relationships()

    # Verify cross-file relationships
    edges = graph.get_edges(rel_type=RelationType.IMPORTS)
    assert len(edges) > 0  # file2 imports from file1

    # Verify inheritance edges
    edges = graph.get_edges(rel_type=RelationType.INHERITS)
    assert len(edges) == 1  # ClassB inherits from ClassA

    # Verify function calls
    edges = graph.get_edges(rel_type=RelationType.CALLS)
    assert len(edges) > 0  # func2 calls func1, method2 calls method1

def test_relationship_builder_with_empty_file(builder):
    """Test relationship builder with an empty file."""
    context = FileContext(
        path="empty.py",
        code="",
        tree=Mock(),
        symbols={
            'imports': [],
            'functions': [],
            'classes': [],
            'variables': []
        },
        references={
            'calls': [],
            'attributes': [],
            'variables': []
        }
    )
    
    # Process empty context
    builder._process_imports(context.symbols['imports'])
    builder._process_classes(context)
    builder._process_functions(context)
    builder._process_references(context)
    
    graph = builder.get_relationships()
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0 