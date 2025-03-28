"""Tests for the CodeAnalyzer class."""

import pytest
from server.code_understanding.analyzer import CodeAnalyzer
from server.code_understanding.parser import MockNode, MockTree

@pytest.fixture
def analyzer():
    """Create a CodeAnalyzer instance for testing."""
    return CodeAnalyzer()

def test_analyze_tree(analyzer):
    """Test analyzing a complete syntax tree."""
    # Create mock nodes
    mock_import = MockNode(
        type="import",
        text="import os",
        start_point=(1, 0),
        end_point=(1, 9)
    )
    mock_function = MockNode(
        type="function_definition",
        text="test_func",
        start_point=(2, 0),
        end_point=(4, 0),
        fields={"name": MockNode(type="identifier", text="test_func")}
    )
    mock_class = MockNode(
        type="class_definition",
        text="TestClass",
        start_point=(5, 0),
        end_point=(7, 0),
        fields={"name": MockNode(type="identifier", text="TestClass")}
    )
    mock_var = MockNode(
        type="assignment",
        text="test_var = 'hello'",
        start_point=(8, 0),
        end_point=(8, 10),
        fields={
            "left": MockNode(type="identifier", text="test_var"),
            "right": MockNode(type="string", text="'hello'")
        }
    )

    # Create root node with all nodes as children
    root = MockNode(
        type="module",
        children=[mock_import, mock_function, mock_class, mock_var]
    )

    # Create tree
    tree = MockTree(root)

    result = analyzer.analyze_tree(tree)

    assert result == {
        'imports': [{'type': 'import', 'name': 'import os', 'start_line': 2, 'end_line': 2}],
        'functions': [{'name': 'test_func', 'start_line': 3, 'end_line': 5, 'parameters': []}],
        'classes': [{'name': 'TestClass', 'start_line': 6, 'end_line': 8, 'methods': [], 'bases': []}],
        'variables': [{'name': 'test_var', 'start_line': 9, 'end_line': 9, 'type': 'str'}]
    }

def test_analyze_tree_error(analyzer):
    """Test error handling during tree analysis."""
    # Create a tree that will raise an exception
    root = MockNode(type="module")  # Empty node will cause error
    tree = MockTree(root)

    result = analyzer.analyze_tree(tree)

    assert result == {
        'imports': [],
        'functions': [],
        'classes': [],
        'variables': []
    }

def test_extract_imports(analyzer):
    """Test extracting import statements."""
    mock_import = MockNode(
        type="import",
        text="import os",
        start_point=(1, 0),
        end_point=(1, 9)
    )
    root = MockNode(type="module", children=[mock_import])

    result = analyzer._extract_imports(root)

    assert result == [{
        'type': 'import',
        'name': 'import os',
        'start_line': 2,
        'end_line': 2
    }]

def test_extract_functions(analyzer):
    """Test extracting function definitions."""
    mock_function = MockNode(
        type="function_definition",
        text="test_func",
        start_point=(1, 0),
        end_point=(3, 0),
        fields={
            "name": MockNode(type="identifier", text="test_func"),
            "parameters": MockNode(type="parameters", children=[])
        }
    )
    root = MockNode(type="module", children=[mock_function])

    result = analyzer._extract_functions(root)

    assert result == [{
        'name': 'test_func',
        'start_line': 2,
        'end_line': 4,
        'parameters': []
    }]

def test_extract_classes(analyzer):
    """Test extracting class definitions."""
    mock_class = MockNode(
        type="class_definition",
        text="TestClass",
        start_point=(1, 0),
        end_point=(5, 0),
        fields={
            "name": MockNode(type="identifier", text="TestClass"),
            "bases": MockNode(type="bases", children=[])
        }
    )
    root = MockNode(type="module", children=[mock_class])

    result = analyzer._extract_classes(root)

    assert result == [{
        'name': 'TestClass',
        'start_line': 2,
        'end_line': 6,
        'methods': [],
        'bases': []
    }]

def test_extract_variables(analyzer):
    """Test extracting variable assignments."""
    mock_var = MockNode(
        type="assignment",
        text="test_var = 'hello'",
        start_point=(1, 0),
        end_point=(1, 10),
        fields={
            "left": MockNode(type="identifier", text="test_var"),
            "right": MockNode(type="string", text="'hello'")
        }
    )
    root = MockNode(type="module", children=[mock_var])

    result = analyzer._extract_variables(root)

    assert result == [{
        'name': 'test_var',
        'start_line': 2,
        'end_line': 2,
        'type': 'str'
    }]

def test_infer_type(analyzer):
    """Test type inference from value nodes."""
    type_tests = [
        ('string', 'str'),
        ('integer', 'int'),
        ('float', 'float'),
        ('true', 'bool'),
        ('false', 'bool'),
        ('none', 'None'),
        ('list', 'list'),
        ('dictionary', 'dict'),
        ('unknown_type', 'unknown')
    ]

    for node_type, expected_type in type_tests:
        node = MockNode(type=node_type)
        result = analyzer._infer_type(node)
        assert result == expected_type

def test_analyze_code_basic(analyzer):
    """Test analyzing basic Python code."""
    code = """
def greet(name: str) -> str:
    return f"Hello, {name}!"
"""
    result = analyzer.analyze_code(code)

    assert 'imports' in result
    assert 'functions' in result
    assert 'classes' in result
    assert 'variables' in result

    # Check function
    functions = result['functions']
    assert len(functions) == 1
    assert functions[0]['name'] == 'greet'

def test_analyze_code_with_imports(analyzer):
    """Test analyzing code with imports."""
    code = """
import os
from typing import List, Optional

def get_files() -> List[str]:
    return os.listdir('.')
"""
    result = analyzer.analyze_code(code)

    # Check imports
    imports = result['imports']
    assert len(imports) == 3
    assert any(imp['name'] == 'import os' for imp in imports)

def test_analyze_code_with_classes(analyzer):
    """Test analyzing code with class definitions."""
    code = """
class Animal:
    def __init__(self, name: str):
        self.name = name

    def speak(self) -> str:
        return "..."

class Dog(Animal):
    def speak(self) -> str:
        return "Woof!"
"""
    result = analyzer.analyze_code(code)

    # Check classes
    classes = result['classes']
    assert len(classes) == 2
    assert any(cls['name'] == 'Animal' for cls in classes)
    assert any(cls['name'] == 'Dog' for cls in classes)

def test_analyze_code_with_references(analyzer):
    """Test analyzing code with various references."""
    code = """
from math import sqrt

def calculate_distance(x: float, y: float) -> float:
    return sqrt(x*x + y*y)

def main():
    result = calculate_distance(3.0, 4.0)
    print(f"Distance: {result}")
"""
    result = analyzer.analyze_code(code)

    # Check functions
    functions = result['functions']
    assert len(functions) == 2
    assert any(func['name'] == 'calculate_distance' for func in functions)
    assert any(func['name'] == 'main' for func in functions)

def test_analyze_code_error_handling(analyzer):
    """Test error handling in code analysis."""
    # Test with invalid syntax
    code = "def invalid_syntax("
    result = analyzer.analyze_code(code)

    assert result == {
        'imports': [],
        'functions': [],
        'classes': [],
        'variables': []
    }

def test_analyze_file(analyzer, tmp_path):
    """Test analyzing a Python file."""
    # Create a test file
    test_file = tmp_path / "test.py"
    code = """
def test_function():
    return "Hello, World!"
"""
    test_file.write_text(code)

    # Analyze the file
    result = analyzer.analyze_file(str(test_file))

    # Check results
    assert len(result['functions']) == 1
    assert result['functions'][0]['name'] == 'test_function'

def test_analyze_file_error(analyzer, tmp_path):
    """Test error handling when analyzing a file."""
    # Test with non-existent file
    result = analyzer.analyze_file(str(tmp_path / "nonexistent.py"))

    assert result == {
        'imports': [],
        'functions': [],
        'classes': [],
        'variables': []
    } 