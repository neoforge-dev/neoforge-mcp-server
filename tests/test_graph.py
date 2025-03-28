"""Tests for the graph data structure."""

import pytest
from server.code_understanding.graph import Graph, Node, Edge, RelationType

@pytest.fixture
def graph():
    """Create a test graph."""
    return Graph()

@pytest.fixture
def sample_nodes(graph):
    """Create sample nodes in the graph."""
    node1 = graph.add_node(
        name="test_function",
        type="function",
        file_path="test.py",
        start_line=1,
        end_line=10
    )
    node2 = graph.add_node(
        name="test_class",
        type="class",
        file_path="test.py",
        start_line=11,
        end_line=20
    )
    return node1, node2

def test_add_node(graph):
    """Test adding nodes to the graph."""
    # Test basic node addition
    node = graph.add_node(
        name="test",
        type="function",
        file_path="test.py"
    )
    assert node.name == "test"
    assert node.type == "function"
    assert node.file_path == "test.py"
    assert node.start_line == 0
    assert node.end_line == 0
    assert node.properties == {}
    
    # Test node with properties
    node_with_props = graph.add_node(
        name="test_with_props",
        type="class",
        file_path="test.py",
        start_line=1,
        end_line=10,
        properties={"key": "value"}
    )
    assert node_with_props.properties == {"key": "value"}
    
    # Test duplicate node (should return existing node)
    duplicate = graph.add_node(
        name="test",
        type="function",
        file_path="test.py"
    )
    assert duplicate.id == node.id

def test_add_edge(graph, sample_nodes):
    """Test adding edges to the graph."""
    node1, node2 = sample_nodes
    
    # Test basic edge addition
    edge = graph.add_edge(node1, node2, RelationType.CALLS)
    assert edge.source == node1
    assert edge.target == node2
    assert edge.type == RelationType.CALLS
    assert edge.properties == {}
    
    # Test edge with properties
    edge_with_props = graph.add_edge(
        node2,
        node1,
        RelationType.CONTAINS,
        properties={"line": 15}
    )
    assert edge_with_props.properties == {"line": 15}

def test_get_node(graph, sample_nodes):
    """Test getting nodes from the graph."""
    node1, node2 = sample_nodes
    
    # Test getting existing node
    found = graph.get_node(node1.id)
    assert found == node1
    
    # Test getting non-existent node
    not_found = graph.get_node("non_existent")
    assert not_found is None

def test_get_edges(graph, sample_nodes):
    """Test getting edges from the graph."""
    node1, node2 = sample_nodes
    
    # Add some edges
    edge1 = graph.add_edge(node1, node2, RelationType.CALLS)
    edge2 = graph.add_edge(node2, node1, RelationType.CONTAINS)
    
    # Test getting all edges
    all_edges = graph.get_edges()
    assert len(all_edges) == 2
    assert edge1 in all_edges
    assert edge2 in all_edges
    
    # Test filtering by source
    source_edges = graph.get_edges(source_id=node1.id)
    assert len(source_edges) == 1
    assert source_edges[0] == edge1
    
    # Test filtering by target
    target_edges = graph.get_edges(target_id=node2.id)
    assert len(target_edges) == 1
    assert target_edges[0] == edge1
    
    # Test filtering by relationship type
    calls_edges = graph.get_edges(rel_type=RelationType.CALLS)
    assert len(calls_edges) == 1
    assert calls_edges[0] == edge1
    
    # Test filtering with multiple criteria
    filtered_edges = graph.get_edges(
        source_id=node1.id,
        target_id=node2.id,
        rel_type=RelationType.CALLS
    )
    assert len(filtered_edges) == 1
    assert filtered_edges[0] == edge1

def test_get_nodes_by_type(graph, sample_nodes):
    """Test getting nodes by type."""
    node1, node2 = sample_nodes
    
    # Test getting function nodes
    function_nodes = graph.get_nodes_by_type("function")
    assert len(function_nodes) == 1
    assert function_nodes[0] == node1
    
    # Test getting class nodes
    class_nodes = graph.get_nodes_by_type("class")
    assert len(class_nodes) == 1
    assert class_nodes[0] == node2
    
    # Test getting non-existent type
    empty_nodes = graph.get_nodes_by_type("non_existent")
    assert len(empty_nodes) == 0

def test_get_nodes_by_file(graph, sample_nodes):
    """Test getting nodes by file path."""
    node1, node2 = sample_nodes
    
    # Test getting nodes from existing file
    file_nodes = graph.get_nodes_by_file("test.py")
    assert len(file_nodes) == 2
    assert node1 in file_nodes
    assert node2 in file_nodes
    
    # Test getting nodes from non-existent file
    empty_nodes = graph.get_nodes_by_file("non_existent.py")
    assert len(empty_nodes) == 0

def test_clear(graph, sample_nodes):
    """Test clearing the graph."""
    node1, node2 = sample_nodes
    graph.add_edge(node1, node2, RelationType.CALLS)
    
    # Verify graph has data
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    
    # Clear the graph
    graph.clear()
    
    # Verify graph is empty
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0

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