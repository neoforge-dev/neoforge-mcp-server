"""Tests for the graph data structure."""

import pytest
from server.code_understanding.graph import Graph, Node, Edge, RelationType

@pytest.fixture
def sample_graph():
    """Create a sample graph for testing."""
    graph = Graph()
    
    # Add some nodes
    node1 = graph.add_node(
        name="test_function",
        type="function",
        file_path="test.py",
        start_line=10,
        end_line=20,
        properties={"visibility": "public"}
    )
    
    node2 = graph.add_node(
        name="test_class",
        type="class",
        file_path="test.py",
        start_line=30,
        end_line=40,
        properties={"visibility": "public"}
    )
    
    # Add an edge
    graph.add_edge(
        source=node1,
        target=node2,
        type=RelationType.CALLS,
        properties={"line_number": 15}
    )
    
    return graph, node1, node2

def test_node_creation():
    """Test creating and retrieving nodes in the graph."""
    graph = Graph()
    
    # Test node creation
    node = graph.add_node(
        name="test_function",
        type="function",
        file_path="test.py",
        start_line=10,
        end_line=20,
        properties={"visibility": "public"}
    )
    
    # Verify node properties
    assert node.name == "test_function"
    assert node.type == "function"
    assert node.file_path == "test.py"
    assert node.start_line == 10
    assert node.end_line == 20
    assert node.properties == {"visibility": "public"}
    
    # Test node retrieval
    retrieved_node = graph.get_node(node.id)
    assert retrieved_node == node
    
    # Test retrieval by type
    nodes_by_type = graph.get_nodes_by_type("function")
    assert len(nodes_by_type) == 1
    assert nodes_by_type[0] == node

def test_edge_creation():
    """Test creating and retrieving edges in the graph."""
    graph = Graph()
    
    # Create nodes
    node1 = graph.add_node(name="source", type="function", file_path="test.py")
    node2 = graph.add_node(name="target", type="function", file_path="test.py")
    
    # Create edge
    edge = graph.add_edge(
        source=node1,
        target=node2,
        type=RelationType.CALLS,
        properties={"line_number": 15}
    )
    
    # Verify edge properties
    assert edge.source == node1
    assert edge.target == node2
    assert edge.type == RelationType.CALLS
    assert edge.properties == {"line_number": 15}
    
    # Test edge retrieval
    edges = graph.get_edges(source_id=node1.id)
    assert len(edges) == 1
    assert edges[0] == edge
    
    edges = graph.get_edges(target_id=node2.id)
    assert len(edges) == 1
    assert edges[0] == edge
    
    edges = graph.get_edges(rel_type=RelationType.CALLS)
    assert len(edges) == 1
    assert edges[0] == edge

def test_edge_filtering():
    """Test filtering edges with multiple criteria."""
    graph = Graph()
    
    # Create nodes
    node1 = graph.add_node(name="source", type="function", file_path="test.py")
    node2 = graph.add_node(name="target", type="function", file_path="test.py")
    node3 = graph.add_node(name="other", type="function", file_path="test.py")
    
    # Create edges
    edge1 = graph.add_edge(
        source=node1,
        target=node2,
        type=RelationType.CALLS,
        properties={"line_number": 15}
    )
    
    edge2 = graph.add_edge(
        source=node2,
        target=node3,
        type=RelationType.REFERENCES,
        properties={"line_number": 20}
    )
    
    # Test filtering by source and type
    edges = graph.get_edges(source_id=node1.id, rel_type=RelationType.CALLS)
    assert len(edges) == 1
    assert edges[0] == edge1
    
    # Test filtering by target and type
    edges = graph.get_edges(target_id=node2.id, rel_type=RelationType.CALLS)
    assert len(edges) == 1
    assert edges[0] == edge1
    
    # Test filtering with no matches
    edges = graph.get_edges(source_id=node1.id, rel_type=RelationType.REFERENCES)
    assert len(edges) == 0

def test_node_filtering():
    """Test filtering nodes by type and file."""
    graph = Graph()
    
    # Create nodes
    node1 = graph.add_node(name="func1", type="function", file_path="test.py")
    node2 = graph.add_node(name="func2", type="function", file_path="test.py")
    node3 = graph.add_node(name="class1", type="class", file_path="test.py")
    node4 = graph.add_node(name="func3", type="function", file_path="other.py")
    
    # Test filtering by type
    function_nodes = graph.get_nodes_by_type("function")
    assert len(function_nodes) == 3
    assert all(n.type == "function" for n in function_nodes)
    
    class_nodes = graph.get_nodes_by_type("class")
    assert len(class_nodes) == 1
    assert class_nodes[0] == node3
    
    # Test filtering by file
    test_nodes = graph.get_nodes_by_file("test.py")
    assert len(test_nodes) == 3
    assert all(n.file_path == "test.py" for n in test_nodes)
    
    other_nodes = graph.get_nodes_by_file("other.py")
    assert len(other_nodes) == 1
    assert other_nodes[0] == node4

def test_duplicate_node_handling():
    """Test handling of duplicate node creation."""
    graph = Graph()
    
    # Create initial node
    node1 = graph.add_node(
        name="test_function",
        type="function",
        file_path="test.py"
    )
    
    # Try to create duplicate node
    node2 = graph.add_node(
        name="test_function",
        type="function",
        file_path="test.py"
    )
    
    # Verify same node is returned
    assert node1 == node2
    assert len(graph.nodes) == 1

def test_clear_graph():
    """Test clearing the graph."""
    graph = Graph()
    
    # Add nodes and edges
    node1 = graph.add_node(name="source", type="function", file_path="test.py")
    node2 = graph.add_node(name="target", type="function", file_path="test.py")
    graph.add_edge(
        source=node1,
        target=node2,
        type=RelationType.CALLS
    )
    
    # Verify graph has content
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    
    # Clear graph
    graph.clear()
    
    # Verify graph is empty
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0

def test_edge_properties():
    """Test edge property handling."""
    graph = Graph()
    
    # Create nodes
    node1 = graph.add_node(name="source", type="function", file_path="test.py")
    node2 = graph.add_node(name="target", type="function", file_path="test.py")
    
    # Create edge with properties
    properties = {
        "line_number": 15,
        "scope": "local",
        "context": "function_call"
    }
    edge = graph.add_edge(
        source=node1,
        target=node2,
        type=RelationType.CALLS,
        properties=properties
    )
    
    # Verify properties
    assert edge.properties == properties
    assert edge.properties["line_number"] == 15
    assert edge.properties["scope"] == "local"
    assert edge.properties["context"] == "function_call"

def test_node_properties():
    """Test node property handling."""
    graph = Graph()
    
    # Create node with properties
    properties = {
        "visibility": "public",
        "async": True,
        "decorators": ["@property"]
    }
    node = graph.add_node(
        name="test_function",
        type="function",
        file_path="test.py",
        properties=properties
    )
    
    # Verify properties
    assert node.properties == properties
    assert node.properties["visibility"] == "public"
    assert node.properties["async"] is True
    assert node.properties["decorators"] == ["@property"]

def test_relation_types():
    """Test all relation types are properly defined."""
    # Verify all expected relation types exist
    assert RelationType.IMPORTS.value == "imports"
    assert RelationType.INHERITS.value == "inherits"
    assert RelationType.CONTAINS.value == "contains"
    assert RelationType.CALLS.value == "calls"
    assert RelationType.REFERENCES.value == "references"
    
    # Verify no unexpected relation types
    relation_types = {t.value for t in RelationType}
    expected_types = {"imports", "inherits", "contains", "calls", "references"}
    assert relation_types == expected_types 