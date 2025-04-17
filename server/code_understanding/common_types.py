"""Common data structures for code understanding."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Iterator
import logging

logger = logging.getLogger(__name__)

# Moved from parser.py to break circular import
@dataclass
class MockNode:
    """Mock AST node for testing and unified representation."""
    type: str
    text: str = ""
    children: List["MockNode"] = field(default_factory=list)
    start_point: Tuple[int, int] = (0, 0)
    end_point: Tuple[int, int] = (0, 0)
    parent: Optional['MockNode'] = None # Optional parent link
    fields: Dict[str, Any] = field(default_factory=dict) # For named children/attributes
    metadata: Dict[str, Any] = field(default_factory=dict) # For language-specific metadata
    has_error: bool = False  # Flag to indicate if node has errors
    is_missing: bool = False  # Flag to indicate if node is missing

    def __post_init__(self):
        """Initialize optional fields."""
        # Ensure children/fields are mutable defaults
        if self.children is None:
            self.children = []
        if self.fields is None:
            self.fields = {}
        if self.metadata is None:
            self.metadata = {}

    @property
    def child_count(self) -> int:
        """Get total number of children."""
        return len(self.children)

    @property
    def named_child_count(self) -> int:
        """Get number of named children."""
        return len([child for child in self.children if child.type != 'unknown'])

    def child(self, index: int) -> Optional["MockNode"]:
        """Get child at index."""
        try:
            return self.children[index]
        except IndexError:
            return None

    def named_child(self, index: int) -> Optional["MockNode"]:
        """Get named child at index."""
        named_children = [child for child in self.children if child.type != 'unknown']
        try:
            return named_children[index]
        except IndexError:
            return None

    def field_name_for_child(self, index: int) -> Optional[str]:
        """Get field name for child at index."""
        try:
            child = self.children[index]
            for field_name, field_value in self.fields.items():
                if isinstance(field_value, list):
                    if child in field_value:
                        return field_name
                elif field_value == child:
                    return field_name
            return None
        except IndexError:
            return None

    def children_by_field_name(self, field_name: str) -> List["MockNode"]:
        """Get children associated with a specific field name."""
        field_value = self.fields.get(field_name)
        if isinstance(field_value, list):
            return field_value
        elif isinstance(field_value, MockNode):
            return [field_value]
        return []

    def child_by_field_name(self, field_name: str) -> Optional["MockNode"]:
        """Get a single child node associated with a field name."""
        field_value = self.fields.get(field_name)
        if isinstance(field_value, MockNode):
             return field_value
        elif isinstance(field_value, list) and field_value:
             # Return first element if it's a list
             if isinstance(field_value[0], MockNode):
                  return field_value[0]
        return None

    def walk(self) -> Iterator["MockNode"]:
        """Walk through the node and its children (depth-first)."""
        yield self
        for child in self.children:
            yield from child.walk()

# Moved from parser.py to break circular import
class MockTree:
    """A unified abstract syntax tree representation."""
    def __init__(self, root_node: Optional[MockNode] = None, has_errors: bool = False, error_details: Optional[List[Dict]] = None, features: Optional[Dict] = None):
        """Initialize a MockTree.
        
        Args:
            root_node: The root node of the tree.
            has_errors: Whether the tree contains syntax errors.
            error_details: List of error details if any.
            features: Dictionary of language-specific features (functions, classes, exports, etc.).
        """
        # Only default to 'program' node if root_node is not explicitly provided (i.e., uses default None)
        # If None is explicitly passed, keep it None.
        self.root_node = root_node if root_node is not None else MockNode(type='program', text='program')
        # A simpler way, assuming the default should be None if not provided:
        # self.root_node = root_node 

        # Let's adjust to keep None if None is passed
        self.root_node = root_node # Keep root_node as passed, allows None

        self.has_errors = has_errors
        self.error_details = error_details or []
        self.features = features or {}
        
        # Add compatibility with tree-sitter
        # These seem redundant with has_errors and error_details above?
        # self.has_error = has_errors 
        # self.errors = error_details or []

    @property
    def type(self) -> str:
        """Get the type of the root node."""
        return self.root_node.type if self.root_node else 'program'

    def get(self, field_name: str) -> Optional[MockNode]:
        """Get a field from the root node."""
        return self.root_node.fields.get(field_name) if self.root_node else None

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access to features."""
        return self.features.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style setting of features."""
        self.features[key] = value

    def __contains__(self, key: str) -> bool:
        """Check if a feature exists."""
        return key in self.features

    def __str__(self) -> str:
        """String representation of the tree."""
        return f"MockTree(type={self.type}, has_errors={self.has_errors}, error_count={len(self.error_details)})"

    def __repr__(self) -> str:
        """Get a detailed string representation of the tree."""
        return str(self)

    def walk(self) -> Iterator[MockNode]:
        """Walk through all nodes in the tree (depth-first)."""
        if self.root_node:
            return self.root_node.walk()
        else:
            return iter([]) # Return empty iterator if no root

    def add_error(self, error: Dict) -> None:
        """Add an error to the tree."""
        self.has_errors = True
        self.error_details.append(error)

    def add_feature(self, feature_type: str, feature_data: Any) -> None:
        """Add a feature to the tree.
        
        Args:
            feature_type: The type of feature (e.g., 'function', 'class', 'import').
            feature_data: The feature data to add.
        """
        if feature_type not in self.features:
            self.features[feature_type] = []
        self.features[feature_type].append(feature_data)

    def get_features(self, feature_type: str) -> List[Any]:
        """Get all features of a specific type."""
        return self.features.get(feature_type, [])

    def clear_features(self) -> None:
        """Clear all features."""
        self.features.clear()

    def clear_errors(self) -> None:
        """Clear all errors."""
        self.has_errors = False
        self.error_details.clear() 