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
    HAS_ATTRIBUTE = 'has_attribute'

@dataclass
class Node:
    """A node in the graph."""
    id: str
    name: str
    type: NodeType
    properties: Dict[str, Any]
    
    def __post_init__(self):
        """Initialize additional attributes after dataclass initialization."""
        self.file_path = self.properties.get('file_path', '')
        self.start_line = self.properties.get('start_line', 0)
        self.end_line = self.properties.get('end_line', 0)

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

    def add_node(self, name: str, type: Union[str, NodeType], file_path: str, start_line: int = 0, end_line: int = 0, properties: Optional[Dict[str, Any]] = None) -> Node:
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
        # Convert NodeType enum to string if needed
        node_type = type.value if isinstance(type, NodeType) else type
        node_id = f"{file_path}:{node_type}:{name}"
        if node_id not in self.nodes:
            self.nodes[node_id] = Node(
                id=node_id,
                name=name,
                type=node_type,
                properties=properties or {}
            )
        return self.nodes[node_id]

    def add_edge(self, from_node: str, to_node: str, type: Union[str, RelationType], properties: Optional[Dict[str, Any]] = None) -> None:
        """Add an edge to the graph.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            type: Edge type
            properties: Optional edge properties
        """
        if not properties:
            properties = {}

        # Convert RelationType enum to string if needed
        edge_type = type.value if isinstance(type, RelationType) else type
        edge = Edge(from_node=from_node, to_node=to_node, type=edge_type, properties=properties)
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

    def get_edges(self, source_id: Optional[str] = None, target_id: Optional[str] = None, rel_type: Optional[Union[str, RelationType]] = None) -> List[Edge]:
        """Get edges matching the given criteria.

        Args:
            source_id: Optional source node ID to filter by
            target_id: Optional target node ID to filter by
            rel_type: Optional relationship type to filter by

        Returns:
            List of matching edges
        """
        result = []
        # Convert RelationType enum to string if needed
        edge_type = rel_type.value if isinstance(rel_type, RelationType) else rel_type
        for edge in self.edges:
            matches = True
            if source_id is not None and edge.from_node != source_id:
                matches = False
            if target_id is not None and edge.to_node != target_id:
                matches = False
            if edge_type is not None and edge.type != edge_type:
                matches = False
            if matches:
                result.append(edge)
        return result

    def get_nodes_by_type(self, node_type: Union[str, NodeType]) -> List[Node]:
        """Get nodes of a specific type.

        Args:
            node_type: Node type

        Returns:
            List of matching nodes
        """
        # Convert NodeType enum to string if needed
        type_str = node_type.value if isinstance(node_type, NodeType) else node_type
        return [node for node in self.nodes.values() if node.type == type_str]

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
            Node object
        """
        # Create a unique ID for the node
        file_path = properties.get('file_path', '') if properties else ''
        
        # If name already includes file path (e.g. "file.py:ClassName"), extract it
        if ':' in name:
            file_path, name = name.split(':', 1)
            if not properties:
                properties = {}
            properties['file_path'] = file_path
            
        # First try to find an existing node with the same name and file path
        for node in self.nodes.values():
            if node.type == type.value:
                # Try exact match first
                if node.name == name and node.properties.get('file_path') == file_path:
                    return node
                # Try with file path in name
                if node.name == f"{file_path}:{name}":
                    return node
                # Try just the name part if it matches
                if ':' in node.name:
                    node_file_path, node_name = node.name.split(':', 1)
                    if node_name == name and node_file_path == file_path:
                        return node
            
        # If not found, create a new node
        node_id = f"{file_path}:{type.value}:{name}"
        if not properties:
            properties = {}
        if file_path and 'file_path' not in properties:
            properties['file_path'] = file_path
            
        # For class nodes, include file path in name for better cross-file matching
        full_name = f"{file_path}:{name}" if file_path and type == NodeType.CLASS else name
        
        self.nodes[node_id] = Node(
            id=node_id,
            name=full_name,
            type=type.value,
            properties=properties
        )
        return self.nodes[node_id]

    def find_node(self, name: str) -> Optional[Node]:
        """Find a node by its name.

        Args:
            name: The name of the node to find

        Returns:
            The node if found, None otherwise
        """
        for node in self.nodes.values():
            if node.name == name:
                return node
        return None 