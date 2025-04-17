"""Module for parsing Python code."""

import ast
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any, Iterator
from pathlib import Path

# Import the helper function
from tree_sitter_languages import get_language

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
            from tree_sitter import Parser, Language # Keep Language import for type hint
            # Import platform module to determine OS <-- REMOVE THIS
            #import platform <-- REMOVE THIS
            self.py_parser = Parser()
            
            try:
                # Use the get_language helper
                self.py_language = get_language('python')
                self.py_parser.set_language(self.py_language)
                logger.info("Tree-sitter Python parser loaded successfully via tree-sitter-languages.")
            
            # Keep the original exception handling for Language loading issues
            except Exception as e:
                logger.warning(f"Failed to load Python Tree-sitter grammar via tree-sitter-languages: {e}", exc_info=True) # Add exc_info for details
                self._setup_mock_parser_fallback()
        except ImportError:
            logger.warning("tree_sitter or tree-sitter-languages library not found.")
            self._setup_mock_parser_fallback()
        except Exception as e:
            logger.warning(f"Error initializing Python parser: {e}", exc_info=True) # Add exc_info for details
            self._setup_mock_parser_fallback()
            
    def _try_load_adapters(self):
        """Try to load adapters for other languages. (Temporarily disabled)"""
        logger.info("Skipping _try_load_adapters during troubleshooting.")
        pass # Skip loading JS/Swift adapters for now
        #try:
        #    # Import adapters here to avoid circular imports
        #    from .language_adapters import JavaScriptParserAdapter, SwiftParserAdapter
        #    
        #    # Try loading JS via tree-sitter-languages first
        #except Exception as e:
        #    logger.error(f"Failed to initialize other language adapters: {e}")

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
                 return MockTree(root_node=mock_root)

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
        for child in node.children:
            child_mock = self._convert_ts_node_recursive(child)
            if child_mock:
                mock_node.children.append(child_mock)
                #child_mock.parent = mock_node # Optional: Set parent link if needed
            
            # Convert named fields (Temporarily disabled due to API mismatch)
            # logger.debug(f"Processing fields for node type {node.type}")
            # try:
            #     # Attempting to iterate fields - API might differ across versions
            #     # This line caused TypeError: function takes exactly 1 argument (0 given)
            #     # for field_name, field_value in node.children_by_field_name().items():
            #     # Instead, try accessing known fields if applicable, or just skip
            #     pass # Skip field processing for now
            # except Exception as field_error:
            #      logger.warning(f"Could not process fields for node {node.type}: {field_error}")

            # NEW: Process named fields using child_by_field_name
            # We need to know the possible field names for the node type.
            # Since tree-sitter doesn't provide a direct way to list all fields,
            # we'll try common ones or rely on the analyzer knowing which fields to check.
            # For now, let's add a mechanism but recognize it might be incomplete.
            # The analyzer logic will look for specific fields (e.g., 'name', 'left', 'right').
            # It's crucial that the MockNode has the fields populated if they exist.
            try:
                 # The tree-sitter Python grammar uses specific field names.
                 # We can check for common ones here.
                 common_fields = ['name', 'body', 'parameters', 'return_type', 'left', 'right', 'value', 'module', 'alias', 'condition', 'consequence', 'alternative', 'argument', 'function']
                 for field_name in common_fields:
                     field_node = node.child_by_field_name(field_name)
                     if field_node:
                          field_mock_node = self._convert_ts_node_recursive(field_node)
                          if field_mock_node:
                              mock_node.fields[field_name] = field_mock_node
            except Exception as field_error:
                 # Log if field access fails unexpectedly, but continue
                 logger.debug(f"Error accessing fields for node {node.type}: {field_error}")

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
            # Convert parameters
            params_list = []
            for arg in node.args.args:
                param_node = MockNode(
                    type='identifier',
                    text=arg.arg,
                    start_point=(arg.lineno - 1, arg.col_offset),
                    end_point=(arg.end_lineno - 1 if arg.end_lineno else arg.lineno - 1, arg.end_col_offset if arg.end_col_offset else 0)
                )
                params_list.append(param_node)
            parameters_node = MockNode(type='parameters', children=params_list)

            # Convert body
            body_children = []
            for stmt in node.body:
                child_node = self._convert_ast_node_recursive(stmt)
                if isinstance(child_node, list):
                    body_children.extend(child_node)
                elif child_node:
                    body_children.append(child_node)

            # Create FunctionDef MockNode
            func_def_node = MockNode(
                type='function_definition',
                text=node.name,
                fields={
                    'name': name_node,
                    'parameters': parameters_node,
                    'body': MockNode(type='block', children=body_children) # Store body in fields as well
                },
                children=body_children, # Children for recursive processing
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1 if node.end_lineno else node.lineno - 1, node.end_col_offset if node.end_col_offset else 0)
            )
            # Set parent for children
            for child in body_children:
                 child.parent = func_def_node
            return func_def_node

        elif isinstance(node, ast.ClassDef):
            name_node = MockNode(type='identifier', text=node.name)

            # Convert bases
            bases_list = []
            for base in node.bases:
                 # Assuming bases are simple names for now
                 if isinstance(base, ast.Name):
                     base_node = MockNode(
                         type='identifier',
                         text=base.id,
                         start_point=(base.lineno - 1, base.col_offset),
                         end_point=(base.end_lineno - 1 if base.end_lineno else base.lineno - 1, base.end_col_offset if base.end_col_offset else 0)
                     )
                     bases_list.append(base_node)
                 # TODO: Handle more complex base types if needed
            bases_node = MockNode(type='base_classes', children=bases_list)

            # Convert body
            body_children = []
            for stmt in node.body:
                child_node = self._convert_ast_node_recursive(stmt)
                if isinstance(child_node, list):
                    body_children.extend(child_node)
                elif child_node:
                    body_children.append(child_node)

            # Create ClassDef MockNode
            class_def_node = MockNode(
                type='class_definition',
                text=node.name,
                fields={
                    'name': name_node,
                    'bases': bases_node,
                    'body': MockNode(type='block', children=body_children) # Store body in fields
                },
                children=body_children, # Children for recursive processing
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1 if node.end_lineno else node.lineno - 1, node.end_col_offset if node.end_col_offset else 0)
            )
             # Set parent for children
            for child in body_children:
                 child.parent = class_def_node
            return class_def_node

        elif isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                left_node = MockNode(type='identifier', text=node.targets[0].id)
                # Use _value_to_mock_node for the right side
                right_node = self._value_to_mock_node(node.value)
                # Update text representation if necessary
                assign_text = f"{left_node.text} = {right_node.text}"

                assign_node = MockNode(
                    type='assignment',
                    text=assign_text,
                    fields={'left': left_node, 'right': right_node},
                    start_point=(node.lineno - 1, node.col_offset),
                    end_point=(node.end_lineno - 1 if node.end_lineno else node.lineno - 1, node.end_col_offset if node.end_col_offset else 0)
                )
                return assign_node
        elif isinstance(node, ast.Import):
             # Convert Import nodes
             import_children = []
             for alias in node.names:
                 name_node = MockNode(type='identifier', text=alias.name)
                 alias_node = MockNode(type='identifier', text=alias.asname) if alias.asname else None
                 import_children.append(MockNode(
                     type='aliased_import',
                     fields={'name': name_node, 'alias': alias_node} if alias_node else {'name': name_node}
                 ))
             import_node = MockNode(
                 type='import_statement', # Changed type
                 text=f"import {', '.join(name.name + (f' as {name.asname}' if name.asname else '') for name in node.names)}",
                 children=import_children,
                 start_point=(node.lineno - 1, node.col_offset),
                 end_point=(node.end_lineno - 1 if node.end_lineno else node.lineno - 1, node.end_col_offset if node.end_col_offset else 0)
             )
             return import_node
        elif isinstance(node, ast.ImportFrom):
             # Convert ImportFrom nodes
             module_node = MockNode(type='dotted_name', text=node.module) if node.module else None
             import_children = []
             for alias in node.names:
                 name_node = MockNode(type='identifier', text=alias.name)
                 alias_node = MockNode(type='identifier', text=alias.asname) if alias.asname else None
                 import_children.append(MockNode(
                     type='aliased_import',
                     fields={'name': name_node, 'alias': alias_node} if alias_node else {'name': name_node}
                 ))

             import_from_node = MockNode(
                 type='import_from_statement', # Changed type
                 text=f"from {node.module or '.'*node.level} import {', '.join(name.name + (f' as {name.asname}' if name.asname else '') for name in node.names)}",
                 fields={'module': module_node},
                 children=import_children,
                 start_point=(node.lineno - 1, node.col_offset),
                 end_point=(node.end_lineno - 1 if node.end_lineno else node.lineno - 1, node.end_col_offset if node.end_col_offset else 0)
             )
             # This function should return a single node, not a list
             return import_from_node
        # Handle Call nodes
        elif isinstance(node, ast.Call):
            func_node = self._convert_ast_node_recursive(node.func)
            arg_nodes = [self._convert_ast_node_recursive(arg) for arg in node.args]
            # TODO: Handle keywords if necessary

            call_node = MockNode(
                type='call',
                fields={'function': func_node, 'arguments': MockNode(type='argument_list', children=arg_nodes)},
                children=[func_node] + arg_nodes, # Combine function and args for children
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1 if node.end_lineno else node.lineno - 1, node.end_col_offset if node.end_col_offset else 0)
            )
            # Set parent for children
            func_node.parent = call_node
            for arg_child in arg_nodes:
                 arg_child.parent = call_node
            return call_node

        # Handle Attribute access (e.g., obj.attr)
        elif isinstance(node, ast.Attribute):
            value_node = self._convert_ast_node_recursive(node.value)
            attr_node = MockNode(type='identifier', text=node.attr)

            attribute_node = MockNode(
                type='attribute',
                text=f"{value_node.text}.{attr_node.text}",
                fields={'object': value_node, 'attribute': attr_node},
                children=[value_node, attr_node], # Include both parts as children?
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1 if node.end_lineno else node.lineno - 1, node.end_col_offset if node.end_col_offset else 0)
            )
            value_node.parent = attribute_node
            attr_node.parent = attribute_node
            return attribute_node

        # Handle simple names/identifiers
        elif isinstance(node, ast.Name):
            return MockNode(
                type='identifier',
                text=node.id,
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno - 1 if node.end_lineno else node.lineno - 1, node.end_col_offset if node.end_col_offset else 0)
            )

        # Fallback for unhandled AST node types
        logger.debug(f"Unhandled AST node type: {type(node).__name__}")
        return MockNode(
             type='unknown',
             text=f"<{type(node).__name__}>",
             start_point=(node.lineno - 1, node.col_offset) if hasattr(node, 'lineno') else (0,0),
             end_point=(node.end_lineno - 1, node.end_col_offset) if hasattr(node, 'end_lineno') and node.end_lineno is not None else ((node.lineno - 1) if hasattr(node, 'lineno') else 0, 0)
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
                # Get the module name and alias from the children (aliased_import)
                for child in node.children:
                    if child.type == 'aliased_import':
                         name_node = child.fields.get('name')
                         alias_node = child.fields.get('alias')
                         module_name = name_node.text if name_node else None
                         alias_name = alias_node.text if alias_node else None
                         if module_name:
                             symbols['imports'].append({
                                 'module': module_name,
                                 'symbol': '', # Standard import imports the module itself
                                 'alias': alias_name,
                                 'start_line': node.start_point[0],
                                 'end_line': node.end_point[0]
                             })
            elif node.type == 'import_from_statement':
                # Get the module name from fields and symbols from children (aliased_import)
                module_node = node.fields.get('module')
                module_name = module_node.text if module_node else None
                if module_name:
                    for child in node.children:
                         if child.type == 'aliased_import':
                            name_node = child.fields.get('name')
                            alias_node = child.fields.get('alias')
                            symbol_name = name_node.text if name_node else None
                            alias_name = alias_node.text if alias_node else None
                            if symbol_name:
                                symbols['imports'].append({
                                    'module': module_name,
                                    'symbol': symbol_name,
                                    'alias': alias_name,
                                    'start_line': node.start_point[0], # Use main import node lines
                                    'end_line': node.end_point[0]
                                })

            # Process functions and methods
            elif node.type == 'function_definition':
                # Get the function name from the 'name' field
                name_node = node.fields.get('name')
                func_name = name_node.text if name_node else None
                if func_name:
                    # Get parameters from the 'parameters' field
                    parameters = []
                    params_node = node.fields.get('parameters')
                    if params_node and params_node.type == 'parameters':
                        for param_node in params_node.children:
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
                    if bases_node and bases_node.type == 'base_classes':
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
                    if body_node and body_node.type == 'block':
                        # Iterate through children of the body block for methods
                        for method_node in body_node.children:
                            if method_node.type == 'function_definition':
                                method_name_node = method_node.fields.get('name')
                                method_name = method_name_node.text if method_name_node else None
                                if method_name:
                                    parameters = []
                                    params_node = method_node.fields.get('parameters')
                                    if params_node and params_node.type == 'parameters':
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
                # Get the function name from the 'function' field
                func_field_node = node.fields.get('function')
                # The function could be an identifier or an attribute access
                func_name = None
                if func_field_node:
                     if func_field_node.type == 'identifier':
                         func_name = func_field_node.text
                     elif func_field_node.type == 'attribute':
                         # For obj.method(), use the full attribute text
                         func_name = func_field_node.text


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
                    elif value_type == 'integer':
                         value_type = 'int'
                    elif value_type == 'float':
                         value_type = 'float'
                    elif value_type == 'true' or value_type == 'false':
                         value_type = 'bool'
                    elif value_type == 'none':
                         value_type = 'NoneType' # Or just 'none'
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