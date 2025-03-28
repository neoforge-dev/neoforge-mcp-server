"""Module for graph data structures."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any

logger = logging.getLogger(__name__)

class RelationType(Enum):
    """Types of relationships between nodes."""
    IMPORTS = 'imports'
    INHERITS = 'inherits'
    CONTAINS = 'contains'
    CALLS = 'calls'
    REFERENCES = 'references'

@dataclass
class Node:
    """A node in the graph."""
    id: str
    name: str
    type: str
    file_path: str
    start_line: int = 0
    end_line: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Edge:
    """An edge in the graph."""
    source: Node
    target: Node
    type: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)

class Graph:
    """A graph data structure."""

    def __init__(self):
        """Initialize the graph."""
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []

    def add_node(self, name: str, type: str, file_path: str, start_line: int = 0, end_line: int = 0, properties: Optional[Dict[str, Any]] = None) -> Node:
        """Add a node to the graph.

        Args:
            name: Node name
            type: Node type
            file_path: File path
            start_line: Start line number
            end_line: End line number
            properties: Optional node properties

        Returns:
            Added node
        """
        node_id = f"{file_path}:{type}:{name}"
        if node_id not in self.nodes:
            self.nodes[node_id] = Node(
                id=node_id,
                name=name,
                type=type,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                properties=properties or {}
            )
        return self.nodes[node_id]

    def add_edge(self, source: Node, target: Node, type: RelationType, properties: Optional[Dict[str, Any]] = None) -> Edge:
        """Add an edge to the graph.

        Args:
            source: Source node
            target: Target node
            type: Edge type
            properties: Optional edge properties

        Returns:
            Added edge
        """
        edge = Edge(
            source=source,
            target=target,
            type=type,
            properties=properties or {}
        )
        self.edges.append(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID.

        Args:
            node_id: Node ID

        Returns:
            Node if found, None otherwise
        """
        return self.nodes.get(node_id)

    def get_edges(self, source_id: Optional[str] = None, target_id: Optional[str] = None, rel_type: Optional[RelationType] = None) -> List[Edge]:
        """Get edges matching criteria.

        Args:
            source_id: Optional source node ID
            target_id: Optional target node ID
            rel_type: Optional relationship type

        Returns:
            List of matching edges
        """
        print(f"Getting edges with source_id={source_id}, target_id={target_id}, rel_type={rel_type}")
        print(f"All edges: {self.edges}")
        edges = []
        for edge in self.edges:
            print(f"Checking edge: source={edge.source.id}, target={edge.target.id}, type={edge.type}")
            if source_id and edge.source.id != source_id:
                print(f"Skipping edge due to source_id mismatch: {edge.source.id} != {source_id}")
                continue
            if target_id and edge.target.id != target_id:
                print(f"Skipping edge due to target_id mismatch: {edge.target.id} != {target_id}")
                continue
            if rel_type and edge.type != rel_type:
                print(f"Skipping edge due to rel_type mismatch: {edge.type} != {rel_type}")
                continue
            print(f"Adding edge to result: {edge}")
            edges.append(edge)
        return edges

    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """Get nodes of a specific type.

        Args:
            node_type: Node type

        Returns:
            List of matching nodes
        """
        return [node for node in self.nodes.values() if node.type == node_type]

    def get_nodes_by_file(self, file_path: str) -> List[Node]:
        """Get nodes from a specific file.

        Args:
            file_path: File path

        Returns:
            List of matching nodes
        """
        return [node for node in self.nodes.values() if node.file_path == file_path]

    def clear(self) -> None:
        """Clear all nodes and edges."""
        self.nodes.clear()
        self.edges.clear() 