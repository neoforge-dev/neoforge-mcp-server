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
                return self._tree_sitter_to_mock_tree(tree)
            else:
                return self._mock_parse(code)
        except Exception as e:
            logger.warning(f"Tree-sitter parsing failed, falling back to mock parser: {e}")
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
        if node is None:
            return MockNode(
                type='unknown',
                text='',
                start_point=(0, 0),
                end_point=(0, 0)
            )

        # Handle module nodes
        if isinstance(node, ast.Module):
            mock_node = MockNode(
                type='module',
                text='',
                start_point=(0, 0),
                end_point=(0, 0)
            )
            body_children = []
            for child in node.body:
                result = self._ast_to_mock_node(child)
                if isinstance(result, list):
                    for r in result:
                        r.parent = mock_node
                        body_children.append(r)
                else:
                    result.parent = mock_node
                    body_children.append(result)
            mock_node.children = body_children
            return mock_node

        # Handle import nodes
        if isinstance(node, ast.Import):
            imports = []
            for name in node.names:
                import_node = MockNode(
                    type='import_statement',
                    text=f'import {name.name}',
                    start_point=(node.lineno - 1, node.col_offset),
                    end_point=(node.end_lineno - 1, node.end_col_offset)
                )
                # Add dotted_name node
                dotted_name = MockNode(
                    type='dotted_name',
                    text=name.name,
                    start_point=(node.lineno - 1, node.col_offset + 7),  # After 'import '
                    end_point=(node.end_lineno - 1, node.end_col_offset)
                )
                dotted_name.parent = import_node
                import_node.children.append(dotted_name)

                # Add alias node if present
                if name.asname:
                    alias_node = MockNode(
                        type='identifier',
                        text=name.asname,
                        start_point=(node.lineno - 1, node.col_offset + 7 + len(name.name) + 4),  # After 'import name as '
                        end_point=(node.end_lineno - 1, node.end_col_offset)
                    )
                    alias_node.parent = import_node
                    import_node.children.append(alias_node)

                imports.append(import_node)
            return imports

        if isinstance(node, ast.ImportFrom):
            imports = []
            for name in node.names:
                import_node = MockNode(
                    type='import_from_statement',
                    text=f'from {node.module} import {name.name}',
                    start_point=(node.lineno - 1, node.col_offset),
                    end_point=(node.end_lineno - 1, node.end_col_offset)
                )
                # Add module dotted_name node
                module_name = MockNode(
                    type='dotted_name',
                    text=node.module,
                    start_point=(node.lineno - 1, node.col_offset + 5),  # After 'from '
                    end_point=(node.lineno - 1, node.col_offset + 5 + len(node.module))
                )
                module_name.parent = import_node
                import_node.children.append(module_name)

                # Add imported symbol dotted_name node
                symbol_name = MockNode(
                    type='dotted_name',
                    text=name.name,
                    start_point=(node.lineno - 1, node.col_offset + 5 + len(node.module) + 8),  # After 'from module import '
                    end_point=(node.lineno - 1, node.col_offset + 5 + len(node.module) + 8 + len(name.name))
                )
                symbol_name.parent = import_node
                import_node.children.append(symbol_name)

                # Add alias node if present
                if name.asname:
                    alias_node = MockNode(
                        type='identifier',
                        text=name.asname,
                        start_point=(node.lineno - 1, node.col_offset + 5 + len(node.module) + 8 + len(name.name) + 4),  # After 'from module import name as '
                        end_point=(node.lineno - 1, node.col_offset + 5 + len(node.module) + 8 + len(name.name) + 4 + len(name.asname))
                    )
                    alias_node.parent = import_node
                    import_node.children.append(alias_node)

                imports.append(import_node)
            return imports

        # Handle function definitions
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            mock_node = MockNode(
                type='function_definition',
                text=node.name,
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )
            # Add identifier node for function name
            name_node = MockNode(
                type='identifier',
                text=node.name,
                start_point=(node.lineno - 1, node.col_offset + 4),  # After 'def '
                end_point=(node.lineno - 1, node.col_offset + 4 + len(node.name))
            )
            name_node.parent = mock_node
            mock_node.children.append(name_node)

            # Add parameters node
            params_node = MockNode(
                type='parameters',
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
            
            # Add *args if present
            if node.args.vararg:
                param_node = MockNode(
                    type='identifier',
                    text=node.args.vararg.arg,
                    start_point=(node.args.vararg.lineno - 1, node.args.vararg.col_offset),
                    end_point=(node.args.vararg.end_lineno - 1, node.args.vararg.end_col_offset)
                )
                param_node.parent = params_node
                params_node.children.append(param_node)
            
            # Add **kwargs if present
            if node.args.kwarg:
                param_node = MockNode(
                    type='identifier',
                    text=node.args.kwarg.arg,
                    start_point=(node.args.kwarg.lineno - 1, node.args.kwarg.col_offset),
                    end_point=(node.args.kwarg.end_lineno - 1, node.args.kwarg.end_col_offset)
                )
                param_node.parent = params_node
                params_node.children.append(param_node)
            
            params_node.parent = mock_node
            mock_node.children.append(params_node)
            
            # Add decorators
            for decorator in node.decorator_list:
                decorator_node = MockNode(
                    type='decorator',
                    text=ast.unparse(decorator),
                    start_point=(decorator.lineno - 1, decorator.col_offset),
                    end_point=(decorator.end_lineno - 1, decorator.end_col_offset)
                )
                decorator_node.parent = mock_node
                mock_node.children.append(decorator_node)
            
            # Add async flag
            if isinstance(node, ast.AsyncFunctionDef):
                async_node = MockNode(
                    type='async',
                    text='async',
                    start_point=(node.lineno - 1, node.col_offset),
                    end_point=(node.end_lineno - 1, node.end_col_offset)
                )
                async_node.parent = mock_node
                mock_node.children.append(async_node)
            
            # Add body node
            body_node = MockNode(
                type='block',
                text='',
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )
            body_node.parent = mock_node
            mock_node.children.append(body_node)

            for stmt in node.body:
                result = self._ast_to_mock_node(stmt)
                if isinstance(result, list):
                    for r in result:
                        r.parent = body_node
                        body_node.children.append(r)
                else:
                    result.parent = body_node
                    body_node.children.append(result)
            return mock_node

        # Handle class definitions
        if isinstance(node, ast.ClassDef):
            mock_node = MockNode(
                type='class_definition',
                text=node.name,
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )
            # Add identifier node for class name
            name_node = MockNode(
                type='identifier',
                text=node.name,
                start_point=(node.lineno - 1, node.col_offset + 6),  # After 'class '
                end_point=(node.lineno - 1, node.col_offset + 6 + len(node.name))
            )
            name_node.parent = mock_node
            mock_node.children.append(name_node)

            # Add argument_list node for bases
            if node.bases:
                bases_node = MockNode(
                    type='argument_list',
                    text='',
                    start_point=(node.lineno - 1, node.col_offset),
                    end_point=(node.end_lineno - 1, node.end_col_offset)
                )
                for base in node.bases:
                    base_node = MockNode(
                        type='identifier',
                        text=ast.unparse(base),
                        start_point=(base.lineno - 1, base.col_offset),
                        end_point=(base.end_lineno - 1, base.end_col_offset)
                    )
                    base_node.parent = bases_node
                    bases_node.children.append(base_node)
                bases_node.parent = mock_node
                mock_node.children.append(bases_node)
            
            # Add body node
            body_node = MockNode(
                type='block',
                text='',
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )
            body_node.parent = mock_node
            mock_node.children.append(body_node)

            for stmt in node.body:
                result = self._ast_to_mock_node(stmt)
                if isinstance(result, list):
                    for r in result:
                        r.parent = body_node
                        body_node.children.append(r)
                else:
                    result.parent = body_node
                    body_node.children.append(result)
            return mock_node

        # Handle function calls
        if isinstance(node, ast.Call):
            mock_node = MockNode(
                type='call',
                text=ast.unparse(node.func),
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )
            # Add identifier node for function name
            name_node = MockNode(
                type='identifier',
                text=ast.unparse(node.func),
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.lineno - 1, node.col_offset + len(ast.unparse(node.func)))
            )
            name_node.parent = mock_node
            mock_node.children.append(name_node)

            # Add argument_list node
            args_node = MockNode(
                type='argument_list',
                text='',
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )
            for arg in node.args:
                arg_node = MockNode(
                    type='identifier',
                    text=ast.unparse(arg),
                    start_point=(arg.lineno - 1, arg.col_offset),
                    end_point=(arg.end_lineno - 1, arg.end_col_offset)
                )
                arg_node.parent = args_node
                args_node.children.append(arg_node)
            args_node.parent = mock_node
            mock_node.children.append(args_node)
            return mock_node

        # Handle variable names
        if isinstance(node, ast.Name):
            return MockNode(
                type='identifier',
                text=node.id,
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1, node.end_col_offset)
            )

        # Handle other nodes
        return MockNode(
            type='unknown',
            text=ast.unparse(node),
            start_point=(node.lineno - 1, node.col_offset),
            end_point=(node.end_lineno - 1, node.end_col_offset)
        )

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
                    if child.type == 'dotted_name':
                        module_name = child.text
                    elif child.type == 'identifier':
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
                # Get the module name from the dotted_name
                module_name = None
                symbol_name = None
                alias_name = None
                for child in node.children:
                    if child.type == 'dotted_name':
                        if not module_name:
                            module_name = child.text
                        elif not symbol_name:
                            symbol_name = child.text
                    elif child.type == 'identifier':
                        alias_name = child.text
                if module_name and symbol_name:
                    symbols['imports'].append({
                        'module': module_name,
                        'symbol': symbol_name,
                        'alias': alias_name,
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
                # Get the class name from the identifier
                class_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text
                        break
                if class_name:
                    # Get base classes
                    bases = []
                    for child in node.children:
                        if child.type == 'argument_list':
                            for base_node in child.children:
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
                    for child in node.children:
                        if child.type == 'block':
                            for method_node in child.children:
                                if method_node.type == 'function_definition':
                                    method_name = None
                                    for method_child in method_node.children:
                                        if method_child.type == 'identifier':
                                            method_name = method_child.text
                                            break
                                    if method_name:
                                        parameters = []
                                        for method_child in method_node.children:
                                            if method_child.type == 'parameters':
                                                for param_node in method_child.children:
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