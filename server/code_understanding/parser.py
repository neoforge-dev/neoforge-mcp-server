"""Module for parsing Python code."""

import ast
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any, Iterator

logger = logging.getLogger(__name__)

# Names to ignore when processing symbols
IGNORED_NAMES = {'self', 'cls', 'None', 'True', 'False'}

@dataclass
class MockNode:
    """Mock AST node for testing."""
    type: str
    text: str = ""
    children: List["MockNode"] = field(default_factory=list)
    start_point: Tuple[int, int] = (0, 0)
    end_point: Tuple[int, int] = (0, 0)
    parent: Optional['MockNode'] = None
    fields: Dict[str, Any] = field(default_factory=dict)

    def children_by_field_name(self, field_name: str) -> List["MockNode"]:
        """Get children by field name."""
        if field_name == 'body':
            if 'body' in self.fields:
                return self.fields['body']
            # For function and class definitions, return children
            if self.type in ('function_definition', 'class_definition', 'module'):
                return self.children
        elif field_name == 'parameters' and self.type == 'function_definition':
            params = [child for child in self.children if child.type == 'parameters']
            return params[0].children if params else []
        elif field_name == 'bases' and self.type == 'class_definition':
            bases = [child for child in self.children if child.type == 'bases']
            return bases[0].children if bases else []
        return []

    def child_by_field_name(self, field_name: str) -> Optional["MockNode"]:
        """Get child by field name."""
        if field_name in self.fields:
            return self.fields[field_name]
        return None

    def walk(self) -> Iterator["MockNode"]:
        """Walk through the node and its children."""
        yield self
        for child in self.children:
            yield from child.walk()

class MockTree:
    """Mock syntax tree for testing."""
    def __init__(self, root: MockNode):
        self.root_node = root

    def walk(self):
        """Walk through the tree."""
        return self.root_node.walk()

class CodeParser:
    """Parser for Python code."""

    def __init__(self):
        """Initialize the parser."""
        self.language = None
        self.parser = None
        self.try_load_parser()

    def try_load_parser(self):
        """Try to load the parser."""
        try:
            from tree_sitter import Parser, Language
            self.parser = Parser()
            try:
                from . import LANGUAGE_LIB_PATH
                if LANGUAGE_LIB_PATH:
                    self.language = Language(LANGUAGE_LIB_PATH, 'python')
                    self.parser.set_language(self.language)
            except ImportError:
                logger.warning("Language library not found, using mock parser")
        except ImportError:
            logger.warning("tree-sitter not available, using mock parser")

    def parse(self, code: str) -> Union[Any, MockTree]:
        """Parse Python code.

        Args:
            code: Python source code

        Returns:
            Syntax tree (either tree-sitter Tree or MockTree)

        Raises:
            ValueError: If code is invalid
        """
        try:
            # First validate syntax
            ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python code: {e}")

        try:
            if self.parser and self.language:
                tree = self.parser.parse(bytes(code, 'utf8'))
                return tree
            else:
                return self._mock_parse(code)
        except Exception as e:
            logger.warning(f"Tree-sitter parsing failed, falling back to mock parser: {e}")
            return self._mock_parse(code)

    def _mock_parse(self, code: str) -> MockTree:
        """Create a mock syntax tree for testing.

        Args:
            code: Python source code

        Returns:
            MockTree object
        """
        tree = ast.parse(code)
        root = self._ast_to_mock_node(tree)
        return MockTree(root)

    def _ast_to_mock_node(self, node: ast.AST) -> MockNode:
        """Convert AST node to mock node.

        Args:
            node: AST node

        Returns:
            MockNode object
        """
        children = []
        fields = {}

        # Handle module nodes
        if isinstance(node, ast.Module):
            mock_node = MockNode(
                type='module',
                text='',
                start_point=(0, 0),
                end_point=(0, 0)
            )
            body_children = [self._ast_to_mock_node(child) for child in node.body]
            for child in body_children:
                child.parent = mock_node
            mock_node.children = body_children
            return mock_node

        # Handle import nodes
        if isinstance(node, ast.Import):
            text = 'import ' + ', '.join(name.name for name in node.names)
            return MockNode(
                type='import',
                text=text,
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )
        
        if isinstance(node, ast.ImportFrom):
            names = ', '.join(name.name for name in node.names)
            text = f'from {node.module} import {names}'
            return MockNode(
                type='import',
                text=text,
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )

        # Handle function definitions
        if isinstance(node, ast.FunctionDef):
            text = node.name
            # Add parameters node
            params_node = MockNode(
                type='parameters',
                children=[],
                text='',
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )
            for arg in node.args.args:
                param_node = MockNode(
                    type='identifier',
                    text=arg.arg,
                    start_point=(arg.lineno - 1, arg.col_offset),
                    end_point=(arg.end_lineno - 1, arg.end_col_offset)
                )
                param_node.parent = params_node
                params_node.children.append(param_node)
            children.append(params_node)
            
            # Add body node
            body_children = [self._ast_to_mock_node(stmt) for stmt in node.body]
            body_node = MockNode(
                type='body',
                children=body_children,
                text='',
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )
            for child in body_children:
                child.parent = body_node
            children.append(body_node)
            
            mock_node = MockNode(
                type='function_definition',
                text=text,
                children=children,
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset),
                fields={'name': MockNode(type='identifier', text=text)}
            )
            for child in children:
                child.parent = mock_node
            return mock_node

        # Handle class definitions
        if isinstance(node, ast.ClassDef):
            text = node.name
            # Add bases node
            bases_node = MockNode(
                type='bases',
                children=[],
                text='',
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )
            for base in node.bases:
                if isinstance(base, ast.Name):
                    base_node = MockNode(
                        type='identifier',
                        text=base.id,
                        start_point=(base.lineno - 1, base.col_offset),
                        end_point=(base.end_lineno - 1, base.end_col_offset)
                    )
                    base_node.parent = bases_node
                    bases_node.children.append(base_node)
            children.append(bases_node)
            
            # Add body node
            body_children = [self._ast_to_mock_node(stmt) for stmt in node.body]
            body_node = MockNode(
                type='body',
                children=body_children,
                text='',
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )
            for child in body_children:
                child.parent = body_node
            children.append(body_node)
            
            mock_node = MockNode(
                type='class_definition',
                text=text,
                children=children,
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset),
                fields={'name': MockNode(type='identifier', text=text)}
            )
            for child in children:
                child.parent = mock_node
            return mock_node

        # Handle assignments
        if isinstance(node, ast.Assign):
            if len(node.targets) > 0:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    left = MockNode(
                        type='identifier',
                        text=target.id,
                        start_point=(target.lineno - 1, target.col_offset),
                        end_point=(target.end_lineno - 1, target.end_col_offset)
                    )
                    right = self._ast_to_mock_node(node.value)
                    mock_node = MockNode(
                        type='assignment',
                        text='',
                        start_point=(node.lineno - 1, node.col_offset),
                        end_point=(node.end_lineno - 1, node.end_col_offset),
                        fields={'left': left, 'right': right}
                    )
                    left.parent = mock_node
                    right.parent = mock_node
                    return mock_node

        # Handle basic nodes
        if isinstance(node, ast.Name):
            text = node.id
        elif isinstance(node, ast.Str):
            text = node.s
        elif isinstance(node, ast.Num):
            text = str(node.n)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                text = node.func.id
            elif isinstance(node.func, ast.Attribute):
                text = node.func.attr
            else:
                text = ''
        else:
            text = ''

        # Create mock node for other types
        mock_node = MockNode(
            type=node.__class__.__name__.lower(),
            text=text,
            children=children,
            start_point=(getattr(node, 'lineno', 1) - 1, getattr(node, 'col_offset', 0)),
            end_point=(getattr(node, 'end_lineno', 1) - 1, getattr(node, 'end_col_offset', 0)),
            fields=fields
        )

        # Set parent for all children
        for child in children:
            child.parent = mock_node

        return mock_node

    def extract_symbols(self, tree: Union[Any, MockTree]) -> Tuple[Dict[str, List[dict]], Dict[str, List[dict]]]:
        """Extract symbols and references from a syntax tree.

        Args:
            tree: Syntax tree

        Returns:
            Tuple of (symbols, references)
        """
        symbols = {
            'imports': [],
            'functions': [],
            'classes': [],
            'variables': []
        }
        references = {
            'imports': [],
            'calls': [],
            'attributes': [],
            'variables': []
        }

        if isinstance(tree, MockTree):
            self._extract_from_mock_tree(tree.root_node, symbols, references)
        else:
            self._extract_from_tree_sitter(tree, symbols, references)

        return symbols, references

    def _extract_from_mock_tree(self, node: MockNode, symbols: Dict[str, List[Dict[str, Any]]], references: Dict[str, List[Dict[str, Any]]]):
        """Extract symbols and references from a mock tree.

        Args:
            node: The root node
            symbols: Dictionary to store symbol information
            references: Dictionary to store reference information
        """
        if not node:
            return

        try:
            # Process imports
            if node.type == 'Import':
                for name in ast.parse(node.text).body[0].names:
                    symbols['imports'].append({
                        'module': name.name,
                        'symbol': '',
                        'start_line': node.start_point[0],
                        'end_line': node.end_point[0]
                    })
            elif node.type == 'ImportFrom':
                module = ast.parse(node.text).body[0].module
                for name in ast.parse(node.text).body[0].names:
                    symbols['imports'].append({
                        'module': module,
                        'symbol': name.name,
                        'start_line': node.start_point[0],
                        'end_line': node.end_point[0]
                    })

            # Process functions and methods
            elif node.type == 'FunctionDef':
                func_name = node.text.split('(')[0].strip()
                if func_name:
                    # Get parameters
                    parameters = []
                    for child in node.children:
                        if child.type == 'parameters':
                            for param_node in child.children:
                                if param_node.text:
                                    parameters.append({
                                        'name': param_node.text,
                                        'start_line': param_node.start_point[0],
                                        'end_line': param_node.end_point[0]
                                    })

                    # Check if this is a method (inside a class)
                    parent = node.parent
                    while parent:
                        if parent.type == 'ClassDef':
                            # Skip processing here since it will be handled in ClassDef
                            break
                        parent = parent.parent
                    else:
                        # Only add as a function if not inside a class
                        symbols['functions'].append({
                            'name': func_name,
                            'parameters': parameters,
                            'start_line': node.start_point[0],
                            'end_line': node.end_point[0]
                        })

            # Process classes
            elif node.type == 'ClassDef':
                class_name = node.text.split('(')[0].strip()  # Extract just the class name
                if class_name:
                    # Get base classes
                    bases = []
                    for child in node.children:
                        if child.type == 'bases':
                            for base_node in child.children:
                                if base_node.text:
                                    bases.append(base_node.text)

                    # Create class info
                    class_info = {
                        'name': class_name,
                        'bases': bases,
                        'methods': [],
                        'start_line': node.start_point[0],
                        'end_line': node.end_point[0]
                    }
                    symbols['classes'].append(class_info)
                    print(f"Added class {class_name} with bases {bases}")

                    # Process all methods in the class
                    for child in node.children:
                        if child.type == 'FunctionDef':
                            method_name = child.text.split('(')[0].strip()
                            if method_name:
                                parameters = []
                                for param_child in child.children:
                                    if param_child.type == 'parameters':
                                        for param_node in param_child.children:
                                            if param_node.text:
                                                parameters.append({
                                                    'name': param_node.text,
                                                    'start_line': param_node.start_point[0],
                                                    'end_line': param_node.end_point[0]
                                                })
                                class_info['methods'].append({
                                    'name': method_name,
                                    'parameters': parameters,
                                    'start_line': child.start_point[0],
                                    'end_line': child.end_point[0]
                                })
                                print(f"Added method {method_name} to class {class_name} with parameters {parameters}")

            # Process function calls
            elif node.type == 'Call':
                if node.text:
                    references['calls'].append({
                        'name': node.text,
                        'start_line': node.start_point[0],
                        'end_line': node.end_point[0]
                    })

            # Process variable references
            elif node.type == 'Name':
                if node.text and node.text not in IGNORED_NAMES:
                    # Skip type hints
                    if node.text not in ('str', 'int', 'float', 'bool', 'list', 'dict', 'tuple', 'set', 'Optional', 'List', 'Dict', 'Tuple', 'Set'):
                        references['variables'].append({
                            'name': node.text,
                            'start_line': node.start_point[0],
                            'end_line': node.end_point[0]
                        })

            # Process children
            for child in node.children:
                self._extract_from_mock_tree(child, symbols, references)

        except Exception as e:
            logger.warning(f"Error extracting symbols from node {node.type}: {e}")

    def _extract_from_tree_sitter(self, tree: Any, symbols: Dict[str, List[dict]], references: Dict[str, List[dict]]) -> None:
        """Extract symbols from tree-sitter tree.

        Args:
            tree: Tree-sitter tree
            symbols: Dictionary to store symbols
            references: Dictionary to store references
        """
        # Similar to _extract_from_mock_tree but using tree-sitter nodes
        # This will be implemented when tree-sitter is properly integrated
        pass

    def get_root_node(self, tree: Union[Any, MockTree]) -> Union[Any, MockNode]:
        """Get the root node of a tree.
        
        Args:
            tree: Syntax tree
            
        Returns:
            Root node of the tree
            
        Raises:
            ValueError: If tree is None
        """
        if tree is None:
            return None
        return tree.root_node

    def node_to_dict(self, node: Union[Any, MockNode]) -> Dict[str, Any]:
        """Convert a node to a dictionary representation."""
        if node is None:
            return {}

        result = {
            'type': node.type,
            'text': node.text.decode('utf-8') if isinstance(node.text, bytes) else str(node.text),
            'start_point': node.start_point,
            'end_point': node.end_point,
            'children': []
        }

        for child in node.children:
            result['children'].append(self.node_to_dict(child))

        return result