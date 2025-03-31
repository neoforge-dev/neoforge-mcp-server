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

    def __post_init__(self):
        """Initialize optional fields."""
        # Ensure children/fields are mutable defaults
        if self.children is None:
            self.children = []
        if self.fields is None:
            self.fields = {}

    def children_by_field_name(self, field_name: str) -> List["MockNode"]:
        """Get children associated with a specific field name."""
        # This might need adjustment based on how fields vs children are used
        field_value = self.fields.get(field_name)
        if isinstance(field_value, list):
            return field_value
        elif isinstance(field_value, MockNode):
            return [field_value]
        return []
        # # Alternative: check children based on a hypothetical 'field' attr?
        # return [child for child in self.children if getattr(child, 'field', None) == field_name]

    def child_by_field_name(self, field_name: str) -> Optional["MockNode"]:
        """Get a single child node associated with a field name."""
        field_value = self.fields.get(field_name)
        if isinstance(field_value, MockNode):
             return field_value
        elif isinstance(field_value, list) and field_value:
             # Return first element if it's a list?
             # Or should this only return non-list fields? Decide based on usage.
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
    """Mock tree structure holding the root MockNode."""

    def __init__(self, root: Optional[MockNode] = None):
        """Initialize mock tree.

        Args:
            root: Root MockNode
        """
        self.root_node = root
        self.type = 'mock_tree' # Keep a type identifier if useful

    def walk(self) -> Iterator[MockNode]:
        """Walk through all nodes in the tree (depth-first)."""
        if self.root_node:
            return self.root_node.walk()
        else:
            return iter([]) # Return empty iterator if no root 