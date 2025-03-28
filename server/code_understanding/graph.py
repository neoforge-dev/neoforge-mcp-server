"""Module for graph data structures."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Union

logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Node types."""
    MODULE = 'module'
    FUNCTION = 'function'
    CLASS = 'class'
    METHOD = 'method'
    PARAMETER = 'parameter'
    VARIABLE = 'variable'
    ATTRIBUTE = 'attribute'
    SYMBOL = 'symbol'

class RelationType(Enum):
    """Edge types."""
    IMPORTS = 'imports'
    CONTAINS = 'contains'
    CALLS = 'calls'
    REFERENCES = 'references'
    INHERITS = 'inherits'

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
    from_node: str
    to_node: str
    type: str
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

    def add_edge(self, from_node: str, to_node: str, type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Add an edge to the graph.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            type: Edge type
            properties: Optional edge properties
        """
        if not properties:
            properties = {}

        edge = Edge(from_node=from_node, to_node=to_node, type=type, properties=properties)
        self.edges.append(edge)

    def create_edge(self, from_node: Node, to_node: Node, type: RelationType, properties: Optional[Dict[str, Any]] = None) -> None:
        """Create an edge between two nodes.

        Args:
            from_node: Source node
            to_node: Target node
            type: Edge type
            properties: Optional edge properties
        """
        if not properties:
            properties = {}

        if from_node.id not in self.nodes or to_node.id not in self.nodes:
            raise ValueError("Both nodes must exist in the graph")

        edge = Edge(from_node=from_node.id, to_node=to_node.id, type=type.value, properties=properties)
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID.

        Args:
            node_id: Node ID

        Returns:
            Node if found, None otherwise
        """
        return self.nodes.get(node_id)

    def get_edges(self, source_id: Optional[str] = None, target_id: Optional[str] = None, rel_type: Optional[str] = None) -> List[Edge]:
        """Get edges matching the given criteria.

        Args:
            source_id: Optional source node ID to filter by
            target_id: Optional target node ID to filter by
            rel_type: Optional relationship type to filter by

        Returns:
            List of matching edges
        """
        result = []
        for edge in self.edges:
            matches = True
            if source_id is not None and edge.from_node != source_id:
                matches = False
            if target_id is not None and edge.to_node != target_id:
                matches = False
            if rel_type is not None and edge.type != rel_type:
                matches = False
            if matches:
                result.append(edge)
        return result

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

    def find_or_create_node(self, name: str, type: NodeType, properties: Optional[Dict[str, Any]] = None) -> Node:
        """Find an existing node or create a new one.

        Args:
            name: Node name
            type: Node type
            properties: Optional node properties

        Returns:
            The found or created node
        """
        # Create a unique ID for the node
        node_id = f"{name}:{type.value}"

        # Check if node already exists
        if node_id in self.nodes:
            return self.nodes[node_id]

        # Get file path from properties or use empty string
        file_path = properties.get('file_path', '') if properties else ''

        # Create new node
        node = Node(
            id=node_id,
            name=name,
            type=type.value,
            file_path=file_path,
            properties=properties or {}
        )
        self.nodes[node_id] = node
        return node 