"""Integration tests for code understanding components."""

import pytest
from server.code_understanding.parser import MockNode as Node, MockTree as Tree, CodeParser
from server.code_understanding.analyzer import CodeAnalyzer
from server.code_understanding.extractor import SymbolExtractor

@pytest.fixture
def sample_code():
    """Sample Python code for testing."""
    return """
import os
from typing import List, Optional

class BaseClass:
    def base_method(self) -> None:
        pass

class TestClass(BaseClass):
    def __init__(self, name: str) -> None:
        self.name = name
        
    def test_method(self, value: int) -> None:
        pass

def helper_function(items: List[int]) -> int:
    return sum(items)

test_variable = "Hello World"
numbers = [1, 2, 3]
result = helper_function(numbers)
"""

def create_mock_node(mocker, type_name, text, start_point, end_point):
    """Create a mock node with the given properties."""
    return Node(type=type_name, text=text, start_point=start_point, end_point=end_point)

def create_mock_function_node(mocker, name, start_point, end_point, params):
    """Create a mock function node."""
    param_nodes = []
    for param in params:
        param_node = Node(type="identifier", text=param['name'])
        param_nodes.append(param_node)
    
    name_node = Node(type="identifier", text=name)
    params_node = Node(type="parameters", children=param_nodes)
    
    return Node(
        type="function_definition",
        start_point=start_point,
        end_point=end_point,
        fields={
            'name': name_node,
            'parameters': params_node
        }
    )

def create_mock_class_node(mocker, name, start_point, end_point, methods, bases=None):
    """Create a mock class node."""
    name_node = Node(type="identifier", text=name)
    
    base_nodes = []
    if bases:
        for base in bases:
            base_node = Node(type="identifier", text=base)
            base_nodes.append(base_node)
    bases_node = Node(type="bases", children=base_nodes)
    
    return Node(
        type="class_definition",
        start_point=start_point,
        end_point=end_point,
        children=methods,
        fields={
            'name': name_node,
            'bases': bases_node
        }
    )

def create_mock_variable_node(mocker, name, start_point, end_point, type_name):
    """Create a mock variable node."""
    name_node = Node(type="identifier", text=name)
    return Node(
        type="assignment",
        start_point=start_point,
        end_point=end_point,
        fields={
            'left': name_node
        }
    )

def test_end_to_end_analysis(mocker, sample_code):
    """Test the complete code analysis pipeline."""
    # Create instances of our components
    parser = CodeParser()
    analyzer = CodeAnalyzer()
    extractor = SymbolExtractor()
    
    # Configure mock nodes for imports
    mock_import_nodes = [
        create_mock_node(mocker, "import", b"import os", (1, 0), (1, 9)),
        create_mock_node(mocker, "import", b"from typing import List, Optional", (2, 0), (2, 32))
    ]
    
    # Configure mock nodes for classes
    mock_class_nodes = [
        create_mock_class_node(mocker, "BaseClass", (4, 0), (6, 8), [
            create_mock_function_node(mocker, "base_method", (5, 4), (6, 8), [])
        ]),
        create_mock_class_node(mocker, "TestClass", (8, 0), (14, 8), [
            create_mock_function_node(mocker, "__init__", (9, 4), (10, 8), [
                {'name': 'name', 'type': 'str'}
            ]),
            create_mock_function_node(mocker, "test_method", (12, 4), (14, 8), [
                {'name': 'value', 'type': 'int'}
            ])
        ], ["BaseClass"])
    ]
    
    # Configure mock nodes for functions
    mock_function_nodes = [
        create_mock_function_node(mocker, "helper_function", (16, 0), (17, 16), [
            {'name': 'items', 'type': 'List[int]'}
        ])
    ]
    
    # Configure mock nodes for variables
    mock_variable_nodes = [
        create_mock_variable_node(mocker, "test_variable", (19, 0), (19, 24), "str"),
        create_mock_variable_node(mocker, "numbers", (20, 0), (20, 14), "list"),
        create_mock_variable_node(mocker, "result", (21, 0), (21, 31), "int")
    ]
    
    # Configure root node to return our mock nodes
    def mock_children_by_field_name(field):
        if field == 'body':  # Changed from specific fields to 'body'
            return mock_import_nodes + mock_class_nodes + mock_function_nodes + mock_variable_nodes
        return []
    
    # Create a mock tree using our Node and Tree classes
    mock_root = Node('module')
    mock_root.children = mock_import_nodes + mock_class_nodes + mock_function_nodes + mock_variable_nodes
    mock_root._fields = {'body': mock_root.children}
    mock_tree = Tree(mock_root)
    
    # Run the analysis pipeline
    tree = mock_tree  # Use our mock tree directly
    analysis_result = analyzer.analyze_tree(tree)
    result = extractor.extract_symbols(tree)  # Pass tree instead of analysis_result
    
    # Verify the results
    assert len(result['symbols']) > 0
    
    # Check imports
    assert 'os' in result['symbols']
    assert 'List' in result['symbols']
    assert 'Optional' in result['symbols']
    
    # Check classes
    assert 'BaseClass' in result['symbols']
    assert 'TestClass' in result['symbols']
    
    # Check functions
    assert 'base_method' in result['symbols']
    assert '__init__' in result['symbols']
    assert 'test_method' in result['symbols']
    assert 'helper_function' in result['symbols']
    
    # Check variables
    assert 'test_variable' in result['symbols']
    assert 'numbers' in result['symbols']
    assert 'result' in result['symbols'] 