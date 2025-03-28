"""Tests for the relationship builder."""

import pytest
from pathlib import Path
from server.code_understanding.relationships import RelationshipBuilder
from server.code_understanding.graph import RelationType

@pytest.fixture
def builder():
    """Create a relationship builder for testing."""
    return RelationshipBuilder()

def test_analyze_simple_code(builder):
    """Test analyzing simple Python code."""
    code = """
def greet(name: str) -> str:
    return f"Hello, {name}!"

def main():
    greet("World")
"""
    builder.analyze_file("test.py", code)
    graph = builder.get_relationships()
    
    # Check nodes
    assert len(graph.nodes) == 3  # Two functions and one reference
    
    # Find function nodes
    greet_node = None
    main_node = None
    for node in graph.nodes.values():
        if node.name == "greet":
            greet_node = node
        elif node.name == "main":
            main_node = node
            
    assert greet_node is not None
    assert main_node is not None
    
    # Check call relationship
    edges = graph.get_edges(source_id=main_node.id)
    assert len(edges) == 1
    edge = next(iter(edges))
    assert edge.type == RelationType.CALLS
    assert edge.target.name == "greet"

def test_analyze_class_code(builder):
    """Test analyzing code with classes."""
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
    builder.analyze_file("test.py", code)
    graph = builder.get_relationships()
    
    # Find class nodes
    animal_node = None
    dog_node = None
    for node in graph.nodes.values():
        if node.name == "Animal" and node.type == "class":
            animal_node = node
        elif node.name == "Dog" and node.type == "class":
            dog_node = node
            
    assert animal_node is not None
    assert dog_node is not None
    
    # Check inheritance
    edges = graph.get_edges(source_id=dog_node.id, rel_type=RelationType.INHERITS)
    assert len(edges) == 1
    edge = next(iter(edges))
    assert edge.target.name == "Animal"
    
    # Check methods
    edges = graph.get_edges(source_id=animal_node.id, rel_type=RelationType.CONTAINS)
    assert len(edges) == 2  # __init__ and speak
    
    edges = graph.get_edges(source_id=dog_node.id, rel_type=RelationType.CONTAINS)
    assert len(edges) == 1  # speak

def test_analyze_imports(builder):
    """Test analyzing import statements."""
    code = """
import os
from sys import path
from typing import List, Optional

def get_files() -> List[str]:
    return os.listdir(path[0])
"""
    builder.analyze_file("test.py", code)
    graph = builder.get_relationships()
    
    # Check import nodes
    import_nodes = [node for node in graph.nodes.values() if node.type == 'import']
    assert len(import_nodes) == 4  # os, sys.path, typing.List, typing.Optional
    
    # Check import relationships
    edges = graph.get_edges(rel_type=RelationType.IMPORTS)
    assert len(edges) == 4
    
    # Check module targets
    modules = {edge.target.name for edge in edges}
    assert 'os' in modules
    assert 'sys' in modules
    assert 'typing' in modules

def test_analyze_references(builder):
    """Test analyzing symbol references."""
    code = """
from math import sqrt

def calculate_distance(x: float, y: float) -> float:
    return sqrt(x*x + y*y)

def main():
    dist = calculate_distance(3.0, 4.0)
    print(f"Distance: {dist}")
"""
    builder.analyze_file("test.py", code)
    graph = builder.get_relationships()
    
    # Find function nodes
    calc_node = None
    for node in graph.nodes.values():
        if node.name == "calculate_distance":
            calc_node = node
            break
            
    assert calc_node is not None
    
    # Check function call
    edges = graph.get_edges(target_id=calc_node.id, rel_type=RelationType.CALLS)
    assert len(edges) == 1
    
    # Check sqrt reference
    edges = graph.get_edges(rel_type=RelationType.REFERENCES)
    sqrt_refs = [edge for edge in edges if edge.target.name == 'sqrt']
    assert len(sqrt_refs) == 1

def test_analyze_directory(builder, tmp_path):
    """Test analyzing a directory of files."""
    # Create test files
    module1 = tmp_path / "module1.py"
    module1.write_text("""
def func1():
    return "Hello"
""")
    
    module2 = tmp_path / "module2.py"
    module2.write_text("""
from module1 import func1

def func2():
    return func1()
""")
    
    # Analyze directory
    builder.analyze_directory(str(tmp_path))
    graph = builder.get_relationships()
    
    # Check nodes
    assert len(graph.nodes) >= 4  # Two functions, one import, one module
    
    # Check relationships
    edges = graph.get_edges(rel_type=RelationType.IMPORTS)
    assert len(edges) == 1
    
    edges = graph.get_edges(rel_type=RelationType.CALLS)
    assert len(edges) == 1

def test_clear(builder):
    """Test clearing analysis data."""
    code = "def test(): pass"
    builder.analyze_file("test.py", code)
    assert len(builder.get_relationships().nodes) > 0
    
    builder.clear()
    assert len(builder.get_relationships().nodes) == 0 