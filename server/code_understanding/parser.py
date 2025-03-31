"""Module for parsing Python code."""

import ast
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any, Iterator
from pathlib import Path
from .language_adapters import JavaScriptParserAdapter, SwiftParserAdapter
from .common_types import MockNode, MockTree

logger = logging.getLogger(__name__)

# Names to ignore when processing symbols
IGNORED_NAMES = {'self', 'cls', 'None', 'True', 'False'}

class CodeParser:
    """Parser for Python code."""

    def __init__(self):
        """Initialize the parser and load language support."""
        # Initialize ALL attributes first
        self.py_language = None
        self.py_parser = None
        self.adapters: Dict[str, Any] = {}
        self.mock_parser = None # Initialize mock_parser early
        
        # Now load parsers and adapters
        self._try_load_py_parser()
        self._try_load_adapters()
        
        # Ensure mock is set up if Python parser failed during _try_load_py_parser
        # This check might now be redundant if _try_load_py_parser handles it,
        # but it's safe to leave for robustness or remove if confident.
        if not self.py_parser or not self.py_language:
             self._setup_mock_parser_fallback()

    def _try_load_py_parser(self):
        """Try to load the Tree-sitter Python parser."""
        try:
            from tree_sitter import Parser, Language
            self.py_parser = Parser()
            # Assuming build_languages put python.so in the right place
            try:
                # Adjust path as needed, e.g., using build/python.so or vendor
                py_lang_path = Path(__file__).parent / 'build' / 'python.so' 
                if py_lang_path.exists():
                    self.py_language = Language(str(py_lang_path), 'python')
                    self.py_parser.set_language(self.py_language)
                    logger.info("Tree-sitter Python parser loaded successfully.")
                else:
                    logger.warning("Python tree-sitter grammar not found at expected location.")
                    self._setup_mock_parser_fallback() # Setup mock if python fails
            except Exception as e:
                logger.warning(f"Failed to load Python Tree-sitter grammar: {e}")
                self._setup_mock_parser_fallback()
        except ImportError:
            logger.warning("tree_sitter library not found.")
            self._setup_mock_parser_fallback()
        except Exception as e:
            logger.warning(f"Error initializing Python parser: {e}")
            self._setup_mock_parser_fallback()
            
    def _try_load_adapters(self):
        """Try to load adapters for other languages."""
        try:
            js_adapter = JavaScriptParserAdapter()
            if js_adapter.language: # Check if language loaded successfully
                 self.adapters['javascript'] = js_adapter
                 logger.info("JavaScriptParserAdapter loaded successfully.")
            else:
                 logger.warning("JavaScriptParserAdapter initialized but language failed to load.")
        except Exception as e:
            logger.error(f"Failed to initialize JavaScriptParserAdapter: {e}")
            
        try:
            # Add Swift or other adapters similarly
            # swift_adapter = SwiftParserAdapter()
            # self.adapters['swift'] = swift_adapter
            # logger.info("SwiftParserAdapter loaded.")
            pass
        except Exception as e:
            logger.error(f"Failed to initialize other language adapters: {e}")

    def _setup_mock_parser_fallback(self):
        """Use a mock parser for testing or when tree-sitter fails."""
        if not self.mock_parser:
             try:
                 from .mock_parser import MockParser
                 self.mock_parser = MockParser()
                 logger.info("Initialized MockParser fallback.")
             except ImportError:
                  logger.error("Failed to import MockParser for fallback.")
                  self.mock_parser = None # Ensure it's None

    def parse(self, code: str, language: str = 'python') -> Optional[MockTree]:
        """Parse code using the appropriate parser based on language.

        Args:
            code: Source code string.
            language: The programming language (e.g., 'python', 'javascript').

        Returns:
            MockTree: A unified abstract syntax tree representation, or None on failure.
        """
        selected_parser = None
        is_adapter = False
        
        if language == 'python':
            if self.py_parser and self.py_language:
                 selected_parser = self.py_parser
            elif self.mock_parser: # Use mock parser if Python tree-sitter failed
                 logger.warning("Using MockParser for Python due to Tree-sitter load failure.")
                 selected_parser = self.mock_parser
                 is_adapter = True # MockParser has a parse() -> MockTree method
            else:
                 logger.error("No Python parser (Tree-sitter or Mock) available.")
                 return None
        elif language in self.adapters:
            selected_parser = self.adapters[language]
            is_adapter = True # Adapters (and MockParser) return MockTree directly
            logger.info(f"Using {type(selected_parser).__name__} for language: {language}")
        else:
             # Optional: Fallback to mock parser for unsupported languages if desired?
             # if self.mock_parser:
             #    logger.warning(f"Language '{language}' not supported by specific adapters, attempting MockParser fallback.")
             #    selected_parser = self.mock_parser
             #    is_adapter = True
             # else:
             logger.error(f"No parser adapter found for language: {language}")
             return None

        if not selected_parser:
             logger.error(f"Parser selection failed for language: {language}")
             return None

        # Pre-parsing validation block
        try:
            # Validate syntax using Python's ast (ONLY for Python)
            if language == 'python':
                ast.parse(code)
            # No pre-validation for other languages currently
        except SyntaxError as e:
            logger.error(f"Syntax error detected by pre-parser validation for {language}: {e}")
            raise ValueError(f"Invalid {language} code: {e}") # Reraise for analyzer
        except Exception as e:
            logger.warning(f"Pre-parse validation step failed for {language}: {e}")
            # Proceeding, assuming the actual parser might handle it

        # Actual parsing block
        try:
            if is_adapter:
                # Ensure the selected parser (adapter) is actually called
                logger.debug(f"Calling {type(selected_parser).__name__}.parse() for {language}")
                return selected_parser.parse(code)
            else: # Assume Tree-sitter parser for Python
                 # This block should only execute if language == 'python' and py_parser is valid
                 logger.debug(f"Calling tree-sitter parse() for {language}")
                 if isinstance(code, str):
                     code_bytes = bytes(code, 'utf8')
                 else:
                      code_bytes = code # Assume bytes if not str
                 tree = selected_parser.parse(code_bytes)
                 # Convert tree-sitter tree to MockTree
                 mock_root = self._tree_sitter_to_mock_tree(tree)
                 return MockTree(root=mock_root)

        except Exception as e:
            logger.exception(f"Parsing failed with {type(selected_parser).__name__} for {language}: {e}")
            return None # Return None on parsing failure

    def _tree_sitter_to_mock_tree(self, tree: Any) -> Any:
         """Convert tree-sitter tree to mock node structure (root)."""
         # This needs careful implementation to map TS nodes to MockNodes
         # It was previously returning the root node directly, ensure it returns MockNode
         # Placeholder - reuse the recursive helper concept
         return self._convert_ts_node_recursive(tree.root_node)
         
    def _convert_ts_node_recursive(self, node):
        """Recursive helper to convert tree-sitter node to MockNode."""
        if not node:
            return None
            
        text = node.text.decode('utf8') if hasattr(node.text, 'decode') else str(node.text)
        
        # Basic type mapping - should be language specific? Adapter handles this now.
        # Keep a generic mapping here?
        mock_type = node.type

        mock_node = MockNode(
            type=mock_type,
            text=text,
            start_point=node.start_point,
            end_point=node.end_point,
            children=[],
            fields={}
        )
        
        # Process children recursively
        for field_name, child_node in node.children_by_field_name().items():
             # How Tree-sitter handles fields vs children needs clarification
             # Assuming children_by_field_name gives named children
             mock_child = self._convert_ts_node_recursive(child_node)
             if mock_child:
                  mock_node.fields[field_name] = mock_child
                  # Should they also be in children list? Depends on MockNode usage.
                  # mock_node.children.append(mock_child) 
                  
        for child_node in node.children: # Iterate unnamed children? Check tree-sitter API
             mock_child = self._convert_ts_node_recursive(child_node)
             if mock_child:
                 # Avoid duplicating named children if they are also in .children
                 if field_name not in mock_node.fields or mock_node.fields[field_name] != mock_child:
                      mock_node.children.append(mock_child)
                        
        return mock_node

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