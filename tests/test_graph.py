"""Tests for the relationship graph implementation."""

import pytest
from server.code_understanding.graph import (
    RelationType, Node, Edge, RelationshipGraph
)

@pytest.fixture
def sample_nodes():
    """Create sample nodes for testing."""
    return [
        Node(
            id="class1",
            type="class",
            name="MyClass",
            file="test.py",
            start=(1, 0),
            end=(10, 0)
        ),
        Node(
            id="method1",
            type="method",
            name="my_method",
            file="test.py",
            start=(2, 4),
            end=(4, 4)
        ),
        Node(
            id="func1",
            type="function",
            name="helper_func",
            file="test.py",
            start=(12, 0),
            end=(15, 0)
        )
    ]

@pytest.fixture
def sample_graph(sample_nodes):
    """Create a sample graph for testing."""
    graph = RelationshipGraph()
    
    # Add nodes
    for node in sample_nodes:
        graph.add_node(node)
    
    # Add edges
    graph.add_edge(Edge(
        source=sample_nodes[0],  # class1
        target=sample_nodes[1],  # method1
        type=RelationType.CONTAINS
    ))
    graph.add_edge(Edge(
        source=sample_nodes[1],  # method1
        target=sample_nodes[2],  # func1
        type=RelationType.CALLS
    ))
    
    return graph

def test_node_creation():
    """Test node creation and properties."""
    node = Node(
        id="test1",
        type="class",
        name="TestClass",
        file="test.py",
        start=(1, 0),
        end=(10, 0),
        properties={"visibility": "public"}
    )
    
    assert node.id == "test1"
    assert node.type == "class"
    assert node.name == "TestClass"
    assert node.file == "test.py"
    assert node.start == (1, 0)
    assert node.end == (10, 0)
    assert node.properties["visibility"] == "public"

def test_edge_creation():
    """Test edge creation and properties."""
    source = Node(
        id="source",
        type="class",
        name="Source",
        file="test.py",
        start=(1, 0),
        end=(5, 0)
    )
    target = Node(
        id="target",
        type="class",
        name="Target",
        file="test.py",
        start=(7, 0),
        end=(12, 0)
    )
    edge = Edge(
        source=source,
        target=target,
        type=RelationType.INHERITS,
        properties={"visibility": "public"}
    )
    
    assert edge.source == source
    assert edge.target == target
    assert edge.type == RelationType.INHERITS
    assert edge.properties["visibility"] == "public"

def test_graph_add_node(sample_nodes):
    """Test adding nodes to the graph."""
    graph = RelationshipGraph()
    
    # Add first node
    graph.add_node(sample_nodes[0])
    assert sample_nodes[0].id in graph.nodes
    assert len(graph.nodes) == 1
    
    # Add same node again (should update)
    graph.add_node(sample_nodes[0])
    assert len(graph.nodes) == 1
    
    # Add second node
    graph.add_node(sample_nodes[1])
    assert len(graph.nodes) == 2

def test_graph_add_edge(sample_nodes):
    """Test adding edges to the graph."""
    graph = RelationshipGraph()
    
    edge = Edge(
        source=sample_nodes[0],
        target=sample_nodes[1],
        type=RelationType.CONTAINS
    )
    
    # Add edge (should also add nodes)
    graph.add_edge(edge)
    assert edge in graph.edges
    assert len(graph.edges) == 1
    assert len(graph.nodes) == 2
    assert edge in graph.outgoing[sample_nodes[0].id]
    assert edge in graph.incoming[sample_nodes[1].id]

def test_graph_remove_node(sample_graph, sample_nodes):
    """Test removing nodes from the graph."""
    # Remove middle node (method1)
    sample_graph.remove_node(sample_nodes[1].id)
    
    assert sample_nodes[1].id not in sample_graph.nodes
    assert len(sample_graph.edges) == 0  # Both edges should be removed
    assert len(sample_graph.nodes) == 2

def test_graph_get_edges(sample_graph, sample_nodes):
    """Test getting edges from the graph."""
    # Get edges by source
    edges = sample_graph.get_edges(source_id=sample_nodes[0].id)
    assert len(edges) == 1
    assert next(iter(edges)).type == RelationType.CONTAINS
    
    # Get edges by target
    edges = sample_graph.get_edges(target_id=sample_nodes[2].id)
    assert len(edges) == 1
    assert next(iter(edges)).type == RelationType.CALLS
    
    # Get edges by type
    edges = sample_graph.get_edges(rel_type=RelationType.CONTAINS)
    assert len(edges) == 1
    assert next(iter(edges)).source == sample_nodes[0]

def test_graph_get_neighbors(sample_graph, sample_nodes):
    """Test getting neighboring nodes."""
    # Get outgoing neighbors
    neighbors = sample_graph.get_neighbors(sample_nodes[0].id, direction='out')
    assert len(neighbors) == 1
    assert next(iter(neighbors)) == sample_nodes[1]
    
    # Get incoming neighbors
    neighbors = sample_graph.get_neighbors(sample_nodes[2].id, direction='in')
    assert len(neighbors) == 1
    assert next(iter(neighbors)) == sample_nodes[1]
    
    # Get both directions
    neighbors = sample_graph.get_neighbors(sample_nodes[1].id, direction='both')
    assert len(neighbors) == 2

def test_graph_get_subgraph(sample_graph, sample_nodes):
    """Test extracting subgraphs."""
    # Get subgraph of first two nodes
    node_ids = {sample_nodes[0].id, sample_nodes[1].id}
    subgraph = sample_graph.get_subgraph(node_ids)
    
    assert len(subgraph.nodes) == 2
    assert len(subgraph.edges) == 1
    assert next(iter(subgraph.edges)).type == RelationType.CONTAINS

def test_graph_merge(sample_nodes):
    """Test merging graphs."""
    # Create two graphs
    graph1 = RelationshipGraph()
    graph1.add_node(sample_nodes[0])
    graph1.add_node(sample_nodes[1])
    graph1.add_edge(Edge(
        source=sample_nodes[0],
        target=sample_nodes[1],
        type=RelationType.CONTAINS
    ))
    
    graph2 = RelationshipGraph()
    graph2.add_node(sample_nodes[1])
    graph2.add_node(sample_nodes[2])
    graph2.add_edge(Edge(
        source=sample_nodes[1],
        target=sample_nodes[2],
        type=RelationType.CALLS
    ))
    
    # Merge graphs
    graph1.merge(graph2)
    assert len(graph1.nodes) == 3
    assert len(graph1.edges) == 2

def test_graph_serialization(sample_graph):
    """Test graph serialization to/from dict."""
    # Convert to dict
    data = sample_graph.to_dict()
    
    # Check dict structure
    assert 'nodes' in data
    assert 'edges' in data
    assert len(data['nodes']) == 3
    assert len(data['edges']) == 2
    
    # Convert back to graph
    new_graph = RelationshipGraph.from_dict(data)
    
    # Check graph structure
    assert len(new_graph.nodes) == len(sample_graph.nodes)
    assert len(new_graph.edges) == len(sample_graph.edges)
    
    # Check node equality
    for node_id, node in sample_graph.nodes.items():
        assert node_id in new_graph.nodes
        new_node = new_graph.nodes[node_id]
        assert new_node.type == node.type
        assert new_node.name == node.name
        assert new_node.file == node.file
        
    # Check edge equality
    assert len(new_graph.edges) == len(sample_graph.edges)
    for edge in sample_graph.edges:
        matching = [e for e in new_graph.edges
                   if e.source.id == edge.source.id and
                   e.target.id == edge.target.id and
                   e.type == edge.type]
        assert len(matching) == 1 