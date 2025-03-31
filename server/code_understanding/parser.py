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

    def __post_init__(self):
        """Initialize optional fields."""
        if self.children is None:
            self.children = []
        if self.fields is None:
            self.fields = {}

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
        return self.fields.get(field_name)

    def walk(self) -> Iterator["MockNode"]:
        """Walk through the node and its children."""
        yield self
        for child in self.children:
            yield from child.walk()

class MockTree:
    """Mock tree for testing."""

    def __init__(self, root: Optional[MockNode] = None):
        """Initialize mock tree.

        Args:
            root: Root node
        """
        self.root_node = root
        self.type = 'mock_tree'

    def walk(self):
        """Walk through the tree."""
        if self.root_node:
            return self.root_node.walk()
        else:
            return iter([])

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
                    try:
                        self.parser.set_language(self.language)
                    except ValueError as e:
                        if "Incompatible Language version" in str(e):
                            logger.warning("Tree-sitter language version mismatch, falling back to mock parser")
                            self._use_mock_parser()
                            return
                        raise
            except ImportError:
                logger.warning("Tree-sitter language library not found, falling back to mock parser")
                self._use_mock_parser()
        except Exception as e:
            logger.warning(f"Failed to load tree-sitter parser: {e}, falling back to mock parser")
            self._use_mock_parser()

    def _use_mock_parser(self):
        """Use a mock parser for testing."""
        from .mock_parser import MockParser
        self.parser = MockParser()
        self.language = None

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
            # If tree-sitter is available and configured
            if self.parser and self.language: 
                tree = self.parser.parse(bytes(code, 'utf8'))
                # Convert tree-sitter tree to a compatible MockTree structure
                # NOTE: We might want a different return type if tree-sitter succeeds,
                # but for now, let's assume we want a consistent MockTree output.
                # If _tree_sitter_to_mock_tree exists and works, use it.
                # Otherwise, maybe fall back or raise an error?
                # For now, let's assume _tree_sitter_to_mock_tree is desired path.
                # This conversion might need review later.
                mock_root = self._tree_sitter_to_mock_tree(tree)
                return MockTree(root=mock_root) # Wrap in MockTree
            
            # If tree-sitter is NOT available (language is None), 
            # but self.parser is set (it should be MockParser instance)
            elif self.parser and not self.language:
                logger.info("CodeParser: Using self.parser (MockParser instance) to parse.")
                # Call the parse method of the MockParser instance
                return self.parser.parse(code) 
            else:
                 # This case should ideally not happen if try_load_parser is robust
                 logger.error("CodeParser: Parser state inconsistent (parser or language missing without fallback). Falling back to basic AST parse.")
                 return self._mock_parse(code) # Keep internal AST parse as last resort

        except Exception as e:
            logger.warning(f"CodeParser: Parsing failed with {type(self.parser).__name__}, falling back to internal mock parse: {e}")
            # Fallback to the internal basic AST parse if the primary/mock parser fails
            return self._mock_parse(code)

    def _tree_sitter_to_mock_tree(self, tree: Any) -> Any:
        """Convert tree-sitter tree to mock tree.
        
        Args:
            tree: Tree-sitter tree
            
        Returns:
            Mock tree
        """
        def convert_node(node):
            """Convert a single node."""
            if not node:
                return None
                
            # Get node text
            text = node.text.decode('utf8') if hasattr(node.text, 'decode') else str(node.text)
            
            # Create mock node
            mock_node = MockNode(
                type=node.type,
                text=text,
                start_point=node.start_point,
                end_point=node.end_point
            )
            
            # Process children
            for child in node.children:
                child_mock = convert_node(child)
                if child_mock:
                    child_mock.parent = mock_node
                    mock_node.children.append(child_mock)
                    
                    # Handle special fields
                    if child.type == 'identifier':
                        if child.parent.type == 'function_definition':
                            mock_node.fields['name'] = child_mock
                        elif child.parent.type == 'class_definition':
                            mock_node.fields['name'] = child_mock
                        elif child.parent.type == 'argument_list':
                            # This is a base class
                            if 'bases' not in mock_node.fields:
                                mock_node.fields['bases'] = MockNode(type='bases', children=[])
                            mock_node.fields['bases'].children.append(child_mock)
                    elif child.type == 'parameters':
                        mock_node.fields['parameters'] = child_mock
                    elif child.type == 'body':
                        mock_node.fields['body'] = child_mock
                    elif child.type == 'bases':
                        mock_node.fields['bases'] = child_mock
                    elif child.type == 'left':
                        mock_node.fields['left'] = child_mock
                    elif child.type == 'right':
                        mock_node.fields['right'] = child_mock
                        
            return mock_node
            
        return convert_node(tree.root_node)

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

    def _ast_to_mock_node(self, node: ast.AST) -> Union[MockNode, List[MockNode]]:
        """Convert AST node to mock node.

        Args:
            node: AST node

        Returns:
            MockNode object or list of MockNode objects
        """
        if isinstance(node, ast.Module):
            children = []
            for child in node.body:
                child_node = self._ast_to_mock_node(child)
                if isinstance(child_node, list):
                    children.extend(child_node)
                else:
                    children.append(child_node)
            return MockNode(type='module', children=children)
        elif isinstance(node, ast.FunctionDef):
            name_node = MockNode(type='identifier', text=node.name)
            return MockNode(
                type='function_definition',
                text=node.name,
                fields={'name': name_node},
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno or node.lineno, node.end_col_offset or 0)
            )
        elif isinstance(node, ast.ClassDef):
            name_node = MockNode(type='identifier', text=node.name)
            return MockNode(
                type='class_definition',
                text=node.name,
                fields={'name': name_node},
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno or node.lineno, node.end_col_offset or 0)
            )
        elif isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                left_node = MockNode(type='identifier', text=node.targets[0].id)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    right_text = repr(node.value.value)
                else:
                    right_text = repr(node.value)
                right_node = MockNode(type='string', text=right_text)
                return MockNode(
                    type='assignment',
                    text=f"{node.targets[0].id} = {right_text}",
                    fields={'left': left_node, 'right': right_node},
                    start_point=(node.lineno - 1, node.col_offset),
                    end_point=(node.end_lineno or node.lineno, node.end_col_offset or 0)
                )
        elif isinstance(node, ast.Import):
            return MockNode(
                type='import',
                text=f"import {', '.join(name.name for name in node.names)}",
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno or node.lineno, node.end_col_offset or 0)
            )
        elif isinstance(node, ast.ImportFrom):
            imports = []
            for name in node.names:
                imports.append(MockNode(
                    type='import',
                    text=f"from {node.module} import {name.name}",
                    start_point=(node.lineno - 1, node.col_offset),
                    end_point=(node.end_lineno or node.lineno, node.end_col_offset or 0)
                ))
            return imports
        return MockNode(type='unknown')

    def _value_to_mock_node(self, node: ast.AST) -> MockNode:
        """Convert value node to mock node.

        Args:
            node: AST node

        Returns:
            MockNode object
        """
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                node_type = 'string'
            elif isinstance(node.value, int):
                node_type = 'integer'
            elif isinstance(node.value, float):
                node_type = 'float'
            elif isinstance(node.value, bool):
                node_type = 'true' if node.value else 'false'
            elif node.value is None:
                node_type = 'none'
            else:
                node_type = 'unknown'
        elif isinstance(node, ast.List):
            node_type = 'list'
        elif isinstance(node, ast.Dict):
            node_type = 'dictionary'
        elif isinstance(node, ast.Tuple):
            node_type = 'tuple'
        else:
            node_type = 'unknown'

        return MockNode(
            type=node_type,
            text=ast.unparse(node) if hasattr(ast, 'unparse') else str(node),
            start_point=(node.lineno - 1, node.col_offset),
            end_point=(node.end_lineno - 1, node.end_col_offset)
        )

    def extract_symbols(self, tree: Union[Any, MockTree]) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
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
            if node.type == 'import_statement':
                # Get the module name and alias from the children
                module_name = None
                alias_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        if not module_name:
                            module_name = child.text
                        else:
                            alias_name = child.text
                if module_name:
                    symbols['imports'].append({
                        'module': module_name,
                        'symbol': '',
                        'alias': alias_name,
                        'start_line': node.start_point[0],
                        'end_line': node.end_point[0]
                    })
            elif node.type == 'import_from_statement':
                # Get the module name and symbols from the children
                module_name = None
                for child in node.children:
                    if child.type == 'dotted_name':
                        module_name = child.text
                        break
                if module_name:
                    for child in node.children:
                        if child.type == 'identifier':
                            symbols['imports'].append({
                                'module': module_name,
                                'symbol': child.text,
                                'alias': None,
                                'start_line': node.start_point[0],
                                'end_line': node.end_point[0]
                            })

            # Process functions and methods
            elif node.type == 'function_definition':
                # Get the function name from the identifier
                func_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = child.text
                        break
                if func_name:
                    # Get parameters
                    parameters = []
                    for child in node.children:
                        if child.type == 'parameters':
                            for param_node in child.children:
                                if param_node.type == 'identifier':
                                    parameters.append({
                                        'name': param_node.text,
                                        'start_line': param_node.start_point[0],
                                        'end_line': param_node.end_point[0]
                                    })

                    # Check if this is a method (inside a class)
                    parent = node.parent
                    while parent:
                        if parent.type == 'class_definition':
                            # Skip processing here since it will be handled in class_definition
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
            elif node.type == 'class_definition':
                # Get the class name from the name field
                name_node = node.fields.get('name')
                class_name = name_node.text if name_node else None
                if class_name:
                    # Get base classes from the bases field
                    bases = []
                    bases_node = node.fields.get('bases')
                    if bases_node:
                        for base_node in bases_node.children:
                            if base_node.type == 'identifier':
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

                    # Process all methods in the class
                    body_node = node.fields.get('body')
                    if body_node:
                        for method_node in body_node.children:
                            if method_node.type == 'function_definition':
                                method_name_node = method_node.fields.get('name')
                                method_name = method_name_node.text if method_name_node else None
                                if method_name:
                                    parameters = []
                                    params_node = method_node.fields.get('parameters')
                                    if params_node:
                                        for param_node in params_node.children:
                                            if param_node.type == 'identifier':
                                                parameters.append({
                                                    'name': param_node.text,
                                                    'start_line': param_node.start_point[0],
                                                    'end_line': param_node.end_point[0]
                                                })
                                    class_info['methods'].append({
                                        'name': method_name,
                                        'parameters': parameters,
                                        'start_line': method_node.start_point[0],
                                        'end_line': method_node.end_point[0]
                                    })

            # Process function calls
            elif node.type == 'call':
                # Get the function name from the identifier
                func_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = child.text
                        break
                if func_name:
                    references['calls'].append({
                        'name': func_name,
                        'start_line': node.start_point[0],
                        'end_line': node.end_point[0]
                    })

            # Process variable references
            elif node.type == 'assignment':
                left_node = node.fields.get('left')
                right_node = node.fields.get('right')
                if left_node:
                    var_name = left_node.text
                    value_type = right_node.type if right_node else 'unknown'
                    if value_type == 'string':
                        value_type = 'str'
                    symbols['variables'].append({
                        'name': var_name,
                        'type': value_type,
                        'start_line': node.start_point[0],
                        'end_line': node.end_point[0]
                    })
            elif node.type == 'identifier':
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
            raise

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