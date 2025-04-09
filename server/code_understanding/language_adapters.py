"""Language-specific parser adapters for JavaScript and Swift."""

import os
import logging
import sys
import time
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple, Callable
import ctypes # Add ctypes import at the top

# Import tree-sitter components
try:
    from tree_sitter import Language, Parser, Node, Tree
except ImportError as e:
    print(f"Failed to import tree-sitter: {e}")
    print(f"Python path: {sys.path}")
    raise

# Import common types
from .common_types import MockTree, MockNode

# Import build paths
from .build_languages import JAVASCRIPT_LANGUAGE_PATH

logger = logging.getLogger(__name__)

class ParserError(Exception):
    """Custom error class for parser-related errors."""
    def __init__(self, message: str, error_type: str, node: Optional[Node] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_type = error_type
        self.node = node
        self.context = context or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            'type': self.error_type,
            'message': str(self),
            'context': self.context
        }

class BaseParserAdapter:
    """Base class for language-specific parser adapters."""
    
    def __init__(self):
        """Initialize the base parser adapter."""
        self.parser = None
        self.language = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self._error_recovery_attempts = 3
        
    def _check_memory_usage(self):
        """Check if memory usage is within acceptable limits."""
        process = psutil.Process(os.getpid())
        memory_percent = process.memory_percent()
        if memory_percent > 90:
            raise MemoryError(f"Memory usage too high: {memory_percent}%")
            
    def _handle_tree_errors(self, node: Node, mock_tree: MockTree):
        """Handle errors in the parse tree."""
        errors = []
        
        # Check if the node itself has an error
        if node.has_error:
            error_info = {
                'type': 'syntax_error',
                'node_type': node.type,
                'start_point': node.start_point,
                'end_point': node.end_point,
                'text': self._get_node_text(node, mock_tree.code) if hasattr(mock_tree, 'code') else None
            }
            errors.append(error_info)
            
        # Check for ERROR nodes in children
        for child in node.children:
            if child.type == 'ERROR':
                error_info = {
                    'type': 'syntax_error',
                    'node_type': 'ERROR',
                    'start_point': child.start_point,
                    'end_point': child.end_point,
                    'text': self._get_node_text(child, mock_tree.code) if hasattr(mock_tree, 'code') else None
                }
                errors.append(error_info)
            elif child.has_error:
                error_info = {
                    'type': 'syntax_error',
                    'node_type': child.type,
                    'start_point': child.start_point,
                    'end_point': child.end_point,
                    'text': self._get_node_text(child, mock_tree.code) if hasattr(mock_tree, 'code') else None
                }
                errors.append(error_info)
            if child.children:
                child_errors = self._handle_tree_errors(child, mock_tree)
                if child_errors:
                    errors.extend(child_errors)
                    
        if errors:
            if not hasattr(mock_tree, 'errors'):
                mock_tree.errors = []
            mock_tree.errors.extend(errors)
            mock_tree.has_errors = True
            
        return errors

class JavaScriptParserAdapter(BaseParserAdapter):
    """Parser adapter for JavaScript code using tree-sitter."""
    
    def __init__(self):
        """Initialize the JavaScript parser adapter."""
        super().__init__()
        self.initialize()
        
    def initialize(self):
        """Initialize the parser and language."""
        try:
            # Build the language library if it doesn't exist
            if not os.path.exists(JAVASCRIPT_LANGUAGE_PATH):
                self.logger.info(f"Building tree-sitter JavaScript language library at {JAVASCRIPT_LANGUAGE_PATH}")
                # Provide the directory containing the tree-sitter-javascript repository
                # Adjust this path if your tree-sitter grammar source is located elsewhere
                grammar_src_dir = './tree-sitter-javascript' 
                if not os.path.isdir(grammar_src_dir):
                     # Try finding it relative to this file if not in root
                     base_dir = os.path.dirname(__file__)
                     grammar_src_dir = os.path.join(base_dir, 'tree-sitter-javascript')
                     if not os.path.isdir(grammar_src_dir):
                         self.logger.error(f"Tree-sitter JavaScript grammar source directory not found at expected locations ('./tree-sitter-javascript' or adjacent). Cannot build library.")
                         return # Cannot proceed
                         
                Language.build_library(
                    # The output path for the compiled library
                    JAVASCRIPT_LANGUAGE_PATH,
                    # List of grammar source directories
                    [grammar_src_dir]
                )
                self.logger.info("Successfully built JavaScript language library.")
            
            # --- Attempt alternative loading --- 
            # Explicitly load the shared library
            library = ctypes.cdll.LoadLibrary(JAVASCRIPT_LANGUAGE_PATH)
            
            # Get the language function pointer (usually named tree_sitter_<language_name>)
            language_func = getattr(library, "tree_sitter_javascript")
            language_func.restype = ctypes.c_void_p # Specify return type as pointer
            
            # Call the function to get the language pointer
            language_ptr = language_func()
            
            # Create the Language object from the pointer
            self.language = Language(language_ptr) # Use the single-argument constructor
            # --- End alternative loading ---
            
            self.parser = Parser()
            # Assign the language directly instead of calling set_language
            self.parser.language = self.language 
            self.logger.info("JavaScript language initialized successfully using ctypes pointer and direct assignment.")
        except Exception as e:
            # Log the full traceback for detailed debugging
            self.logger.exception(f"Failed to initialize JavaScript language: {e}")
            self.language = None # Ensure language is None on failure
            self.parser = None   # Ensure parser is None on failure
            
    def parse(self, code: Union[str, bytes]) -> Tree:
        """Parse JavaScript code and return a tree-sitter Tree.
        
        Args:
            code: JavaScript code as string or bytes
            
        Returns:
            Tree: Parsed tree-sitter tree
            
        Raises:
            ValueError: If parsing fails
        """
        if not code:
            raise ValueError("Empty code string provided")
            
        # Ensure we have a parser and language
        if not self.parser or not self.language:
            self.logger.error("JavaScript parser not initialized.")
            raise RuntimeError("JavaScript parser not initialized.") # Raise proper error
            
        # Convert to bytes if not already
        if isinstance(code, str):
            code_bytes = code.encode('utf8')
        else:
            code_bytes = code
            
        # Parse the code
        try:
            self._check_memory_usage()
            tree = self.parser.parse(code_bytes)
            
            # Store code in tree for error handling
            tree.code = code
            
            # Check for syntax errors
            if tree.root_node.has_error:
                self.logger.warning("Syntax errors found in JavaScript code")
                # Create a mock tree to store errors
                mock_tree = MockTree()
                mock_tree.root_node = self._tree_sitter_to_mock_node(tree.root_node)
                mock_tree.code = code
                # Handle errors
                self._handle_tree_errors(tree.root_node, mock_tree)
                # Transfer errors to the original tree
                if hasattr(mock_tree, 'errors'):
                    tree.errors = mock_tree.errors
            
            return tree # Return the actual tree-sitter tree
        except Exception as e:
            self.logger.exception(f"Failed to parse JavaScript: {e}")
            # Re-raise or raise a specific parsing error
            raise ValueError(f"JavaScript parsing failed: {e}") from e
            
    def _tree_sitter_to_mock_node(self, node: Node) -> MockNode:
        """Convert a tree-sitter node to a MockNode.
        
        Args:
            node: Tree-sitter node
            
        Returns:
            MockNode: Converted mock node
        """
        if not node:
            return None
            
        # Convert the text to string if it's bytes
        if hasattr(node, 'text'):
            if isinstance(node.text, bytes):
                text = node.text.decode('utf8')
            else:
                text = str(node.text)
        else:
            text = ""
            
        # Create the mock node
        mock_node = MockNode(
            type=node.type,
            text=text,
            start_point=node.start_point,
            end_point=node.end_point,
            children=[],
            fields={}
        )
        
        # Process children
        for child in node.children:
            child_mock = self._tree_sitter_to_mock_node(child)
            if child_mock:
                mock_node.children.append(child_mock)
                child_mock.parent = mock_node
                
        # Process named fields (using API compatible with tree-sitter ~0.20+)
        # NOTE: This assumes field names are known or need to be handled differently.
        # If specific field names need to be processed, they should be accessed directly.
        # For a generic approach, iterating named_children might be needed, 
        # but mapping them back to field names is complex without grammar knowledge.
        # This example simplifies by omitting the generic field processing loop
        # If specific fields ARE needed, they must be added explicitly like:
        # try:
        #     name_field = node.child_by_field_name('name')
        #     if name_field:
        #         mock_node.fields['name'] = self._tree_sitter_to_mock_node(name_field)
        # except Exception:
        #     pass # Field might not exist
            
        # Clear the fields dict for now as the old method is incompatible
        mock_node.fields = {} 

        return mock_node
        
    def analyze(self, code: Union[str, bytes]) -> Dict[str, List[Dict]]:
        """Parse the code and extract features.
        
        Args:
            code: JavaScript code string or bytes.
        
        Returns:
            Dictionary containing lists of extracted features (functions, classes, etc.).
        
        Raises:
            ValueError: If parsing fails or parser is not initialized.
            RuntimeError: If parser is not initialized.
        """
        if not self.parser:
            raise RuntimeError("JavaScript parser not initialized.")
            
        try:
            tree = self.parse(code)
            if not tree or not tree.root_node:
                raise ValueError("Parsing resulted in an empty tree.")
                
            # Use the internal feature extraction method
            features = self._extract_features(tree.root_node, code)

            # Check for syntax errors
            errors = []
            if hasattr(tree, 'errors'):
                errors.extend(tree.errors)
            if tree.root_node.has_error:
                self._handle_tree_errors(tree.root_node, tree)
                if hasattr(tree, 'errors'):
                    errors.extend(tree.errors)

            # Add error information to the features
            if errors:
                features['has_errors'] = True
                features['errors'] = errors

            return features
        except Exception as e:
            self.logger.exception(f"JavaScript analysis failed: {e}")
            # Re-raise to ensure the caller knows analysis failed
            raise
            
    def _extract_features(self, node: Node, code: Union[str, bytes]) -> Dict[str, List[Dict]]:
        features = {
            'functions': [],
            'classes': [],
            'variables': [],
            'imports': [],
            'exports': []
        }

        # Keep track of parent node during traversal for context (like catch clause)
        parent_map = {node: None}
        queue = [node]
        while queue:
            n = queue.pop(0)
            for child in n.children:
                parent_map[child] = n
                queue.append(child)

        def traverse(current_node: Node):
            # Process the current node based on its type
            if current_node.type == 'function_declaration':
                func_info = self._extract_function(current_node, code)
                if func_info: features['functions'].append(func_info)
            elif current_node.type == 'class_declaration':
                class_info = self._extract_class(current_node, code)
                if class_info: features['classes'].append(class_info)
            elif current_node.type == 'catch_clause':
                param_node = current_node.child_by_field_name('parameter')
                if param_node:
                    # Extract the catch variable name
                    var_name = self._get_node_text(param_node, code)
                    var_info = {
                        'name': var_name,
                        'type': 'variable',
                        'is_catch_variable': True,
                        'line': param_node.start_point[0] + 1,
                        'column': param_node.start_point[1],
                        'end_line': param_node.end_point[0] + 1,
                        'end_column': param_node.end_point[1]
                    }
                    features['variables'].append(var_info)

                # Find the parent function and mark it as having a try-catch block
                current = current_node
                while current and current.type not in ('function_declaration', 'method_definition', 'arrow_function'):
                    current = parent_map.get(current)
                if current:
                    # Find the corresponding function info in our features list
                    for func in features['functions']:
                        if func.get('line') == current.start_point[0] + 1:
                            func['has_try_catch'] = True
                            break
            elif current_node.type == 'try_statement':
                # Find the parent function and mark it as having a try-catch block
                current = current_node
                while current and current.type not in ('function_declaration', 'method_definition', 'arrow_function'):
                    current = parent_map.get(current)
                if current:
                    # Find the corresponding function info in our features list
                    for func in features['functions']:
                        if func.get('line') == current.start_point[0] + 1:
                            func['has_try_catch'] = True
                            break
            elif current_node.type in ('variable_declaration', 'lexical_declaration'):
                vars_extracted = self._extract_variables(current_node, code)
                parent_node = parent_map.get(current_node)
                is_catch_var = parent_node and parent_node.type == 'catch_clause'
                for var in vars_extracted:
                    var['is_catch_variable'] = is_catch_var
                features['variables'].extend(vars_extracted)
            elif current_node.type == 'import_statement':
                import_info = self._extract_import(current_node, code)
                if import_info: features['imports'].append(import_info)
            elif current_node.type == 'export_statement':
                 # Process exports, but also recurse into its children 
                 # (e.g., to find class/func defined within the export)
                export_info = self._extract_export(current_node, code)
                if export_info:
                    # Handle cases where one export statement might yield multiple logical exports (e.g., re-exports)
                    # _extract_export should return a list in such cases if needed
                    if isinstance(export_info, list):
                        features['exports'].extend(export_info)
                    else:
                        features['exports'].append(export_info)
            
            # Recursively process children
            for child in current_node.children:
                traverse(child)

        # Start traversal from the provided node (usually the root)
        traverse(node)

        # Deduplicate functions based on name and line number just in case
        # Simple deduplication - might need refinement for complex cases
        seen_functions = set()
        deduped_functions = []
        for func in features['functions']:
            key = (func.get('name'), func.get('line'))
            if key not in seen_functions:
                seen_functions.add(key)
                deduped_functions.append(func)
        features['functions'] = deduped_functions

        return features
        
    def _extract_function(self, node: Node, code: Union[str, bytes]) -> Dict:
        """Extract function details (name, parameters, async status)."""
        name_node = node.child_by_field_name('name')
        name = self._get_node_text(name_node, code) if name_node else "<anonymous>"
        
        # Check for async modifier
        is_async = any(child.type == 'async' for child in node.children)
        
        # Extract parameters
        params = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type == 'identifier':
                    params.append(self._get_node_text(child, code))
                elif child.type == 'rest_parameter':
                    param_name = self._get_node_text(child, code)
                    params.append(f"...{param_name}")
        
        # Check for arrow function
        is_arrow = node.type == 'arrow_function'
        
        # Check for try-catch blocks
        has_try_catch = False
        body_node = node.child_by_field_name('body')
        if body_node:
            body_text = self._get_node_text(body_node, code)
            has_try_catch = 'try' in body_text and 'catch' in body_text
        
        return {
            'name': name,
            'type': 'function',
            'is_async': is_async,
            'is_arrow': is_arrow,
            'parameters': params,
            'has_try_catch': has_try_catch,
            'line': node.start_point[0] + 1,
            'column': node.start_point[1],
            'end_line': node.end_point[0] + 1,
            'end_column': node.end_point[1]
        }
        
    def _extract_class(self, node: Node, code: Union[str, bytes]) -> Dict:
        """Extract class details (name, parent, methods)."""
        name = self._get_node_text(node.child_by_field_name('name'), code) if node.child_by_field_name('name') else "<anonymous>"
        # Add checks for inheritance (extends clause)
        parent = None
        # CORRECTED AGAIN: Use the 'superclass' field name as per tree-sitter grammar
        superclass_node = node.child_by_field_name('superclass')
        if superclass_node:
             parent = self._get_node_text(superclass_node, code)

        # Extract methods and fields
        methods = []
        fields = [] # Initialize fields list
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'method_definition':
                    method_info = self._extract_function(child, code)
                    if method_info:
                        # Additional checks for method properties (static, private, getter/setter)
                        modifiers = [m.type for m in child.children if m.type in ['static', 'get', 'set']] # Add 'get', 'set'
                        if 'static' in modifiers:
                            method_info['is_static'] = True
                        # Check if name starts with # for private
                        if method_info['name'].startswith('#'):
                             method_info['is_private'] = True
                        # Check for getter/setter
                        if 'get' in modifiers:
                             method_info['is_getter'] = True
                        if 'set' in modifiers:
                             method_info['is_setter'] = True

                        # Check for super() call within constructor
                        if method_info['name'] == 'constructor':
                            body_node = child.child_by_field_name('body')
                            if body_node:
                                body_text = self._get_node_text(body_node, code)
                                if 'super(' in body_text: # Simple check
                                    method_info['calls_super'] = True

                        methods.append(method_info)
                elif child.type in ['field_definition', 'public_field_definition']: # Handle fields
                     is_static = any(m.type == 'static' for m in child.children)
                     name_node = child.child_by_field_name('name') \
                                 or next((n for n in child.children if n.type in ['property_identifier', 'private_property_identifier']), None)
                     value_node = child.child_by_field_name('value')

                     if name_node:
                         field_name = self._get_node_text(name_node, code)
                         field_info = {
                             'name': field_name,
                             'type': 'field', # Distinguish fields from methods
                             'is_static': is_static,
                             'is_private': field_name.startswith('#'),
                        'line': child.start_point[0] + 1,
                        'column': child.start_point[1],
                        'end_line': child.end_point[0] + 1,
                             'end_column': child.end_point[1],
                             'value': self._get_node_text(value_node, code) if value_node else None
                         }
                         fields.append(field_info) # Add to fields list

        class_info = {
            'name': name,
            'type': 'class',
            'extends': parent, # Renamed from 'parent'
            'methods': methods,
            'fields': fields, # Include fields in the class info
            'line': node.start_point[0] + 1,
            'column': node.start_point[1],
            'end_line': node.end_point[0] + 1,
            'end_column': node.end_point[1]
        }
        return class_info
        
    def _extract_variables(self, node: Node, code: Union[str, bytes]) -> List[Dict]:
        """Extract variable details from declarations (const, let, var). Handles destructuring."""
        variables = []
        
        # Helper function to recursively extract from patterns
        # Pass the main features dict to potentially add functions directly? No, let traverse handle it.
        def extract_pattern(pattern_node: Node, value_node: Optional[Node] = None) -> List[Dict]:
            extracted = []
            node_type = pattern_node.type

            if node_type == 'identifier':
                var_info = {
                    'name': self._get_node_text(pattern_node, code),
                    'type': 'variable',
                    'line': pattern_node.start_point[0] + 1,
                    'column': pattern_node.start_point[1],
                    'end_line': pattern_node.end_point[0] + 1,
                    'end_column': pattern_node.end_point[1],
                    'is_destructured': False, # Default, might be updated by caller if inside pattern
                    'destructure_type': None, # array or object
                    'alias': None, # For renamed destructured variables
                    'default_value': None, # For destructured variables with defaults
                    'value': self._get_node_text(value_node, code) if value_node else None,
                    # Add flags for specific value types
                    'value_is_async_arrow': False,
                    'is_template_literal': False,
                    'is_tagged_template': False,
                }
                
                 # Check value node type
                if value_node:
                     if value_node.type == 'arrow_function':
                         # Check if the arrow function itself is async
                         if any(c.type == 'async' for c in value_node.children):
                             var_info['value_is_async_arrow'] = True
                             # Extract params for potential use in function list
                             params = []
                             has_destructured_params = False
                             param_node = value_node.child_by_field_name('parameters')
                             if param_node:
                                 params_text = self._get_node_text(param_node, code)
                                 params = [p.strip() for p in params_text.strip('()').split(',') if p.strip()]
                                 if any(pat in params_text for pat in ['{', '[', '...']):
                                      has_destructured_params = True
                             elif len(value_node.children) > 0 and value_node.children[0].type == 'identifier' and value_node.children[1].type == '=>':
                                 param_node = value_node.children[0]
                                 params_text = self._get_node_text(param_node, code)
                                 params = [params_text.strip()]
                             var_info['arrow_params'] = params
                             var_info['arrow_has_destructured_params'] = has_destructured_params
                             
                     elif value_node.type == 'template_string':
                          var_info['is_template_literal'] = True
                     elif value_node.type == 'tagged_template_string': # This might not be the type for const x = tag`...`
                          var_info['is_tagged_template'] = True
                     # Check for tagged template pattern: call_expression with template_string argument
                     elif value_node.type == 'call_expression': 
                         # The tree structure is typically call_expression(function=identifier, arguments=template_string)
                         # or call_expression(function=member_expression, arguments=template_string)
                         function_node = value_node.child_by_field_name('function')
                         arguments_node = value_node.child_by_field_name('arguments') # This node contains the template string
                         
                         # Check if arguments node itself is a template_string (common tree-sitter structure)
                         if arguments_node and arguments_node.type == 'template_string':
                             var_info['is_tagged_template'] = True
                         # Fallback: Sometimes arguments is a list containing the template string
                         elif arguments_node and arguments_node.child_count > 0:
                              first_arg_child = next((c for c in arguments_node.children if c.is_named), None)
                              if first_arg_child and first_arg_child.type == 'template_string':
                                  var_info['is_tagged_template'] = True

                extracted.append(var_info)

            elif node_type == 'variable_declarator':
                name_node = pattern_node.child_by_field_name('name')
                value_node = pattern_node.child_by_field_name('value')

                if name_node:
                    # If the name node itself is a pattern, recurse
                    if name_node.type in ['object_pattern', 'array_pattern']:
                        pattern_vars = extract_pattern(name_node, value_node)
                        for var in pattern_vars:
                             var['is_destructured'] = True # Mark as destructured
                             var['destructure_type'] = 'object' if name_node.type == 'object_pattern' else 'array'
                        extracted.extend(pattern_vars)
                    elif name_node.type == 'identifier':
                        # Simple variable declaration - extract_pattern handles value checking
                        pattern_result = extract_pattern(name_node, value_node)
                        if pattern_result: # Should return one var_info dict
                            extracted.append(pattern_result[0])

            elif node_type == 'object_pattern':
                for child in pattern_node.children:
                    # Handle different pattern types within an object pattern
                    if child.type == 'pair_pattern': # { key: pattern } or { key: pattern = default }
                        # Extract the pattern on the value side
                        value_pattern_node = child.child_by_field_name('value')
                        key_node = child.child_by_field_name('key') # Original key name
                        if value_pattern_node:
                             pattern_vars = extract_pattern(value_pattern_node, value_node) # value_node from original declarator if needed? No, value comes from object.
                             for var in pattern_vars:
                                 var['is_destructured'] = True
                                 var['destructure_type'] = 'object'
                                 if key_node: var['alias'] = self._get_node_text(key_node, code) # The key acts as the alias source
                                 # Default value handled within assignment_pattern if present
                             extracted.extend(pattern_vars)

                    elif child.type == 'shorthand_property_identifier_pattern': # { prop } or { prop = default }
                        # Pass the shorthand identifier node itself to extract_pattern
                        extracted.extend(extract_pattern(child, value_node)) # Value comes from object

                    elif child.type == 'rest_pattern': # { ...rest }
                        # Extract the identifier within the rest pattern
                         identifier_node = next((c for c in child.children if c.type == 'identifier'), None)
                         if identifier_node:
                            pattern_vars = extract_pattern(identifier_node, value_node) # Value from object
                            for var in pattern_vars:
                                 var['is_destructured'] = True
                                 var['destructure_type'] = 'object'
                                 var['is_rest'] = True
                            extracted.extend(pattern_vars)
                            
                    elif child.type == 'assignment_pattern': # { prop = default } - shorthand default
                         # Pass the assignment pattern to extract_pattern
                         extracted.extend(extract_pattern(child, value_node))


            elif node_type == 'array_pattern':
                array_index = 0
                for child in pattern_node.children:
                    # Handle elements, skipped elements, and rest pattern
                    if child.type == ',':
                         array_index += 1
                    elif child.type == 'rest_pattern':
                        identifier_node = next((c for c in child.children if c.type == 'identifier'), None)
                        if identifier_node:
                             pattern_vars = extract_pattern(identifier_node, value_node) # Value from array
                             for var in pattern_vars:
                                 var['is_destructured'] = True
                                 var['destructure_type'] = 'array'
                                 var['is_rest'] = True
                             extracted.extend(pattern_vars)
                    elif child.is_named: # Includes identifier, object_pattern, array_pattern, assignment_pattern
                        pattern_vars = extract_pattern(child, value_node) # Value from array
                        for var in pattern_vars:
                            var['is_destructured'] = True
                            var['destructure_type'] = 'array'
                            # Assign index if not a rest element (rest handled above)
                            if not var.get('is_rest', False):
                                var['array_index'] = array_index
                        extracted.extend(pattern_vars)
                        # Increment index only if it wasn't a rest element itself
                        # Need to reliably check if pattern_vars corresponds to non-rest
                        is_rest_in_vars = any(v.get('is_rest', False) for v in pattern_vars)
                        if not is_rest_in_vars:
                             array_index += 1


            # Removed pair_pattern, shorthand_property_identifier_pattern, rest_pattern, assignment_pattern logic
            # from here as they are handled within the object/array pattern loops by calling extract_pattern recursively.

            # Handling shorthand identifier directly (for { prop } case, called from object_pattern loop)
            elif node_type == 'shorthand_property_identifier_pattern':
                 identifier_node = pattern_node
                 var_info = {
                    'name': self._get_node_text(identifier_node, code),
                            'type': 'variable',
                    'line': identifier_node.start_point[0] + 1, 'column': identifier_node.start_point[1],
                    'end_line': identifier_node.end_point[0] + 1, 'end_column': identifier_node.end_point[1],
                    'is_destructured': True, # Set by caller (object_pattern loop) but good default
                    'destructure_type': 'object', # Set by caller
                    'alias': None, # Shorthand doesn't have alias here
                    'default_value': None, # Default handled if parent is assignment_pattern
                    'value': None # Value comes from the source object
                 }
                 # Default value handled by assignment_pattern case below if applicable
                 extracted.append(var_info)

            # Handling assignment pattern (for default values in destructuring)
            elif node_type == 'assignment_pattern':
                 left_pattern = pattern_node.child_by_field_name('left')
                 right_node = pattern_node.child_by_field_name('right') # Default value node
                 if left_pattern:
                      # Recursively call extract_pattern on the left side (the actual variable pattern)
                      pattern_vars = extract_pattern(left_pattern, None) # Don't pass value_node here
                      default_value_text = self._get_node_text(right_node, code) if right_node else None
                      for var in pattern_vars:
                           # The is_destructured/destructure_type flags are set by the containing pattern (object/array)
                           var['default_value'] = default_value_text
                      extracted.extend(pattern_vars)


            return extracted

        # Iterate through variable declarators in the declaration (e.g., const a = 1, b = 2;)
        for declarator in node.children:
            if declarator.type == 'variable_declarator':
                 variables.extend(extract_pattern(declarator))
            # Handle cases like 'for (const x of y)' - the pattern is directly under lexical_declaration
            elif declarator.type in ['object_pattern', 'array_pattern'] and node.type == 'lexical_declaration':
                 # Don't pass a value_node here, value comes from iteration
                 pattern_vars = extract_pattern(declarator, None)
                 for var in pattern_vars:
                     var['is_destructured'] = True
                     var['destructure_type'] = 'object' if declarator.type == 'object_pattern' else 'array'
                 variables.extend(pattern_vars)

                    
        return variables
        
    def _extract_import(self, node: Node, code: Union[str, bytes]) -> Dict:
        """Extract import details (names, source)."""
        source_node = node.child_by_field_name('source')
        source = self._get_node_text(source_node, code) if source_node else ""
        
        # Remove quotes from source
        if source.startswith('"') and source.endswith('"'):
            source = source[1:-1]
        elif source.startswith("'") and source.endswith("'"):
            source = source[1:-1]
            
        # Get imported symbols
        specifiers = []
        clause_node = node.child_by_field_name('clause')
        if clause_node:
            for child in clause_node.children:
                if child.type == 'import_specifier':
                    local_node = child.child_by_field_name('local')
                    imported_node = child.child_by_field_name('imported')
                    
                    local = self._get_node_text(local_node, code) if local_node else ""
                    imported = self._get_node_text(imported_node, code) if imported_node else local
                    
                    specifiers.append({
                        'local': local,
                        'imported': imported
                    })
                    
        # Handle default import
        default_node = node.child_by_field_name('default')
        if default_node:
            default = self._get_node_text(default_node, code)
            specifiers.append({
                'local': default,
                'imported': 'default'
            })
            
        return {
            'type': 'import',
            'source': source,
            'specifiers': specifiers,
            'line': node.start_point[0] + 1,
            'column': node.start_point[1]
        }
        
    def _extract_export(self, node: Node, code: Union[str, bytes]) -> Union[Dict, List[Dict]]:
        """Extract export details based on AST structure.

        Args:
            node: The AST node representing the export statement
            code: The source code string or bytes
            
        Returns:
            A dictionary or list of dictionaries containing export information.
            For named exports with multiple specifiers, returns a list of export info dicts.
            For other cases, returns a single export info dict.
            
        The export info dict contains:
            - type: 'default' | 'named' | 're-export' | 'namespace' | 'direct'
            - is_default: bool
            - names: List of exported names with their details
            - source: Source module for re-exports
            - namespace: Namespace info for namespace exports
            - exported_type: Type of the exported entity (function, class, variable)
            - line, column, end_line, end_column: Location information
        """
        # Find key components of the export statement
        default_keyword = next((child for child in node.children if child.type == 'default'), None)
        star_keyword = next((child for child in node.children if child.type == '*'), None)
        clause_node = node.child_by_field_name('clause')
        declaration_node = node.child_by_field_name('declaration')
        source_node = node.child_by_field_name('source')
        namespace_export_node = next((child for child in node.children if child.type == 'namespace_export'), None)

        # Initialize base export info
        base_info = {
            'line': node.start_point[0] + 1,
            'column': node.start_point[1],
            'end_line': node.end_point[0] + 1,
            'end_column': node.end_point[1],
            'is_default': False,
            'names': [],
            'source': self._get_node_text(source_node, code).strip('\'\"') if source_node else None,
            'namespace': None,
            'exported_type': None
        }

        # 1. Default Export: export default ...
        if default_keyword:
            return self._handle_default_export(node, code, default_keyword, base_info)

        # 2. Namespace/All Re-export: export * from ... or export * as ns from ...
        elif star_keyword and source_node:
            return self._handle_namespace_export(node, code, namespace_export_node, base_info)

        # 3. Named Exports: export { name1, name2 as alias } [from ...]
        elif clause_node:
            return self._handle_named_exports(node, code, clause_node, source_node, base_info)

        # 4. Direct Export: export [async] function/class/let/const/var ...
        elif declaration_node:
            return self._handle_direct_export(node, code, declaration_node, base_info)

        # 5. Unknown Export Structure
        else:
            base_info['type'] = 'unknown'
            children_types = [child.type for child in node.children]
            self.logger.warning(
                f"Unrecognized export statement structure at line {base_info['line']}. "
                f"Node type: {node.type}, Children types: {children_types}"
            )
            base_info['raw_text'] = self._get_node_text(node, code)
            return base_info

    def _handle_default_export(self, node: Node, code: Union[str, bytes], default_keyword: Node, base_info: Dict) -> Dict:
        """Handle default export statements."""
        base_info['type'] = 'default'
        base_info['is_default'] = True
        
        # Find the node being exported (immediately follows 'default')
            actual_exported_node = None
            found_default = False
            for child in node.children:
            if found_default and child.is_named:
                    actual_exported_node = child
                    break
                if child == default_keyword:
                    found_default = True
            
        if not actual_exported_node:
            return base_info

        name = "<anonymous>"
        name_info_node = actual_exported_node
        exported_type = 'value'
                
                if actual_exported_node.type in ('function_declaration', 'class_declaration'):
            exported_type = 'function' if actual_exported_node.type == 'function_declaration' else 'class'
            name_node = actual_exported_node.child_by_field_name('name')
            if name_node:
                name = self._get_node_text(name_node, code)
                name_info_node = name_node
                elif actual_exported_node.type == 'identifier':
                    name = self._get_node_text(actual_exported_node, code)
            exported_type = 'identifier'
        elif actual_exported_node.type in ('number', 'string', 'object', 'array', 'arrow_function'):
            exported_type = actual_exported_node.type
            name = self._get_node_text(actual_exported_node, code) if actual_exported_node.type not in ('object', 'array') else 'anonymous'
            if actual_exported_node.type == 'arrow_function':
                     name = 'anonymous'

        base_info['exported_type'] = exported_type
        base_info['names'].append({
                        'name': name,
                        'alias': None,
            'line': name_info_node.start_point[0] + 1,
            'column': name_info_node.start_point[1],
            'end_line': name_info_node.end_point[0] + 1,
            'end_column': name_info_node.end_point[1]
        })
        return base_info

    def _handle_namespace_export(self, node: Node, code: Union[str, bytes], namespace_export_node: Optional[Node], base_info: Dict) -> Dict:
        """Handle namespace and re-export statements."""
        if namespace_export_node:  # export * as ns from './mod'
            base_info['type'] = 'namespace'
            alias_node = namespace_export_node.child_by_field_name('alias')
            if alias_node:
                ns_name = self._get_node_text(alias_node, code)
                base_info['namespace'] = {
                    'name': ns_name,
                    'line': alias_node.start_point[0] + 1,
                    'column': alias_node.start_point[1],
                    'end_line': alias_node.end_point[0] + 1,
                    'end_column': alias_node.end_point[1]
                }
        else:  # export * from './mod'
            base_info['type'] = 're-export'
            base_info['is_namespace'] = True
        return base_info

    def _handle_named_exports(self, node: Node, code: Union[str, bytes], clause_node: Node, source_node: Optional[Node], base_info: Dict) -> Union[Dict, List[Dict]]:
        """Handle named exports and re-exports."""
        current_export_type = 're-export' if source_node else 'named'
        base_info['type'] = current_export_type
        exports_list = []

        # Check for default re-export case
        default_reexport_spec = None
        specifier_count = 0
        for spec in clause_node.children:
            if spec.type == 'export_specifier':
                specifier_count += 1
                name_node = spec.child_by_field_name('name')
                if name_node and self._get_node_text(name_node, code) == 'default':
                    default_reexport_spec = spec

        is_default_reexport_only = source_node and default_reexport_spec and specifier_count == 1

        if is_default_reexport_only:
            return self._handle_default_reexport(default_reexport_spec, code, base_info)

        # Process all specifiers
            for spec in clause_node.children:
                if spec.type == 'export_specifier':
                    name_node = spec.child_by_field_name('name')
                    alias_node = spec.child_by_field_name('alias')
                    
                original_name = self._get_node_text(name_node, code) if name_node else None
                    alias = self._get_node_text(alias_node, code) if alias_node else None
                exported_as = alias if alias else original_name
                loc_node = alias_node if alias_node else name_node

                if original_name and loc_node:
                    single_export = base_info.copy()
                    single_export['type'] = 're-export' if source_node else 'named'
                    single_export['is_default_reexport'] = (original_name == 'default' and source_node)
                    single_export['names'] = [{
                        'name': exported_as,
                        'alias': alias,
                        'original_name': original_name,
                        'line': loc_node.start_point[0] + 1,
                        'column': loc_node.start_point[1],
                        'end_line': loc_node.end_point[0] + 1,
                        'end_column': loc_node.end_point[1]
                    }]
                    exports_list.append(single_export)

        if not exports_list:
            base_info['type'] = current_export_type
            return base_info
        return exports_list if len(exports_list) > 1 else exports_list[0]

    def _handle_default_reexport(self, spec: Node, code: Union[str, bytes], base_info: Dict) -> Dict:
        """Handle the case of re-exporting only the default export."""
        alias_node = spec.child_by_field_name('alias')
        exported_as = self._get_node_text(alias_node, code) if alias_node else 'default'
        alias = self._get_node_text(alias_node, code) if alias_node else None
        loc_node = alias_node or spec.child_by_field_name('name')

        single_export = base_info.copy()
        single_export['type'] = 're-export'
        single_export['is_default_reexport'] = True
        single_export['names'] = [{
            'name': exported_as,
            'alias': alias,
            'original_name': 'default',
            'line': loc_node.start_point[0] + 1,
            'column': loc_node.start_point[1],
            'end_line': loc_node.end_point[0] + 1,
            'end_column': loc_node.end_point[1]
        }]
        return single_export

    def _handle_direct_export(self, node: Node, code: Union[str, bytes], declaration_node: Node, base_info: Dict) -> Union[Dict, List[Dict]]:
        """Handle direct exports of functions, classes, and variables."""
        base_info['type'] = 'direct'
        name_node = None
        name = "<anonymous>"

            if declaration_node.type == 'function_declaration':
            base_info['exported_type'] = 'function'
                name_node = declaration_node.child_by_field_name('name')
            if name_node:
                name = self._get_node_text(name_node, code)
            elif declaration_node.type == 'class_declaration':
            base_info['exported_type'] = 'class'
                name_node = declaration_node.child_by_field_name('name')
            if name_node:
                name = self._get_node_text(name_node, code)
            elif declaration_node.type in ('lexical_declaration', 'variable_declaration'):
            base_info['exported_type'] = 'variable'
            vars_in_decl = self._extract_variables(declaration_node, code)
            if vars_in_decl:
                exports_list = []
                for var_info in vars_in_decl:
                    single_export = base_info.copy()
                    single_export['exported_type'] = 'variable'
                    single_export['names'] = [{
                        'name': var_info.get('name', '<anonymous>'),  # Ensure name is always present
                        'alias': None,
                        'line': var_info.get('line', node.start_point[0] + 1),
                        'column': var_info.get('column', node.start_point[1]),
                        'end_line': var_info.get('end_line', node.end_point[0] + 1),
                        'end_column': var_info.get('end_column', node.end_point[1])
                    }]
                    exports_list.append(single_export)
                return exports_list if len(exports_list) > 1 else exports_list[0]

        # Ensure name is always present in base_info
            if name_node:
            base_info['names'].append({
                    'name': name,
                    'alias': None,
                    'line': name_node.start_point[0] + 1,
                    'column': name_node.start_point[1],
                    'end_line': name_node.end_point[0] + 1,
                    'end_column': name_node.end_point[1]
                })
        else:
            # Add a default name if none was found
            base_info['names'].append({
                'name': name,
                'alias': None,
                'line': node.start_point[0] + 1,
                'column': node.start_point[1],
                'end_line': node.end_point[0] + 1,
                'end_column': node.end_point[1]
            })

        return base_info
        
    def _get_node_text(self, node: Node, code: Union[str, bytes]) -> str:
        """Safely extract text from a node, decoding if necessary."""
        if not node:
            return ""
            
        if isinstance(code, bytes):
            try:
                code_str = code.decode('utf8')
            except UnicodeDecodeError:
                # Return node.text if available, otherwise empty string
                return node.text.decode('utf8', errors='replace') if hasattr(node, 'text') else ""
        else:
            code_str = code
            
        # Get the node's start and end positions
        start_row, start_col = node.start_point
        end_row, end_col = node.end_point
        
        # Split the code into lines
        lines = code_str.splitlines()
        
        # Handle single-line node
        if start_row == end_row:
            if start_row < len(lines):
                return lines[start_row][start_col:end_col]
            return ""
            
        # Handle multi-line node
        result = []
        for i in range(start_row, end_row + 1):
            if i < len(lines):
                if i == start_row:
                    result.append(lines[i][start_col:])
                elif i == end_row:
                    result.append(lines[i][:end_col])
                else:
                    result.append(lines[i])
                    
        return "\n".join(result)

class SwiftParserAdapter(BaseParserAdapter):
    """Parser adapter for Swift code using tree-sitter."""
    
    def __init__(self):
        """Initialize the Swift parser adapter."""
        super().__init__()
        # TODO: Implement Swift language loading and parser initialization
        # self.initialize() 
        self.logger.warning("Swift parser adapter is not fully implemented.")
        
    def initialize(self):
        # Placeholder for Swift initialization logic
        # Needs tree-sitter-swift grammar and library built/loaded
        # Example (adjust paths as needed):
        # SWIFT_LANGUAGE_PATH = './build/swift-language.so'
        # if not os.path.exists(SWIFT_LANGUAGE_PATH):
        #     Language.build_library(SWIFT_LANGUAGE_PATH, ['./tree-sitter-swift'])
        # self.language = Language(SWIFT_LANGUAGE_PATH, 'swift')
        # self.parser = Parser()
        # self.parser.set_language(self.language)
        self.language = None
        self.parser = None
        self.logger.info("Swift parser initialization skipped (not implemented).")
            
    def parse(self, source_code: Union[str, bytes]) -> Optional[MockTree]:
        """
        Parses Swift source code using a mock parser.

        Args:
            source_code (Union[str, bytes]): The Swift source code to parse.

        Returns:
            Optional[MockTree]: A mock tree representing the parsed structure, 
                                or None if parsing fails or is not implemented.
        """
        if not self.parser:
            # Use MockParser if tree-sitter setup failed or is unavailable
            self.logger.warning("Using MockParser for Swift due to lack of real parser.")
            try:
                from .mock_parser import MockParser # Local import if needed
                mock_parser = MockParser(language='swift')
                mock_tree = mock_parser.parse(source_code)
                # Handle potential errors from mock parser
                if hasattr(mock_tree, 'errors') and mock_tree.errors:
                     self.logger.error(f"Mock parsing errors encountered: {mock_tree.errors}")
                return mock_tree
            except ImportError:
                 self.logger.error("MockParser not found, cannot parse Swift code.")
                 return None
            except Exception as e:
                 self.logger.exception(f"Error using MockParser for Swift: {e}")
        return None
        
        # --- If real tree-sitter parser was initialized (currently skipped) ---
        # try:
        #     code_bytes = source_code.encode('utf8') if isinstance(source_code, str) else source_code
        #     tree = self.parser.parse(code_bytes)
        #     mock_tree = MockTree() # Convert real tree to mock tree structure
        #     if tree.root_node:
        #         mock_tree.root_node = self._tree_sitter_to_mock_node(tree.root_node) # Need this conversion method
        #         self._handle_tree_errors(tree.root_node, mock_tree)
        #     return mock_tree
        # except Exception as e:
        #     self.logger.exception(f"Error parsing Swift code: {e}")
        #     return None
        return None # Should not be reached if parser is initialized
        
    def _extract_features(self, node: Node, mock_tree: MockTree) -> None:
        """Extract features from the Swift parse tree (Placeholder)."""
        # This method would traverse the tree (real or mock) and populate 
        # feature lists (functions, classes, imports, etc.) stored perhaps
        # within the mock_tree object or returned separately.
        
        # Example placeholder logic using mock tree:
        if not mock_tree or not mock_tree.root_node:
                return
                
        mock_tree.imports = []
        mock_tree.functions = []
        mock_tree.classes = []
        
        def traverse_mock(mock_node: MockNode):
            if not mock_node: return

            # Example: Extract based on mock node types (adjust based on MockParser's output)
            if mock_node.type == 'import_declaration':
                import_info = self._extract_import_info(mock_node)
                if import_info: mock_tree.imports.append(import_info)
            elif mock_node.type == 'function_declaration':
                func_info = self._extract_function_info(mock_node)
                if func_info: mock_tree.functions.append(func_info)
            elif mock_node.type == 'class_declaration':
                 class_info = self._extract_class_info(mock_node)
                 if class_info: mock_tree.classes.append(class_info)
                 
            for child in mock_node.children:
                traverse_mock(child)
                
        traverse_mock(mock_tree.root_node)
        self.logger.debug(f"Extracted Swift features: Imports={len(mock_tree.imports)}, Functions={len(mock_tree.functions)}, Classes={len(mock_tree.classes)}")
            
    def _extract_import_info(self, node: Node) -> Optional[Dict[str, Any]]:
         """Placeholder to extract import info from a Swift node."""
         # Requires knowledge of Swift grammar node structure
         # Example: Find the module name child
         module_name = node.text.split(' ')[-1] # Very basic guess
         return {'module': module_name, 'line': node.start_point[0] + 1} if module_name else None
        
    def _extract_function_info(self, node: Node) -> Optional[Dict[str, Any]]:
         """Placeholder to extract function info from a Swift node."""
         # Example: Find identifier for name, parameters list
         name_node = next((c for c in node.children if c.type == 'identifier'), None)
         name = name_node.text if name_node else None
         # ... extract params, return type etc. ...
         return {'name': name, 'line': node.start_point[0] + 1} if name else None
        
    def _extract_class_info(self, node: Node) -> Optional[Dict[str, Any]]:
         """Placeholder to extract class info from a Swift node."""
         name_node = next((c for c in node.children if c.type == 'identifier'), None)
         name = name_node.text if name_node else None
         # ... extract inheritance, members etc. ...
         return {'name': name, 'line': node.start_point[0] + 1} if name else None
         
    # --- Placeholder methods for processing specific node types (if using real tree-sitter) ---
    # These would be similar to the JavaScript ones but use Swift grammar node types/fields
        
    def _process_import_node(self, node: Node) -> Optional[Dict[str, Any]]:
         """Process a Swift import node (Placeholder)."""
         self.logger.debug("Processing Swift import node (not implemented).")
         return None # Replace with actual logic
        
    def _process_function_node(self, node: Node) -> Optional[Dict[str, Any]]:
         """Process a Swift function node (Placeholder)."""
         self.logger.debug("Processing Swift function node (not implemented).")
         # Example:
         # name = node.child_by_field_name('name').text.decode('utf8')
         # params = ...
         # return {'name': name, ...}
         return None
        
    def _process_class_node(self, node: Node) -> Optional[Dict[str, Any]]:
         """Process a Swift class node (Placeholder)."""
         self.logger.debug("Processing Swift class node (not implemented).")
         # Example:
         # name = node.child_by_field_name('name').text.decode('utf8')
         # inheritance = ...
         # members = ...
         # return {'name': name, ...}
            return None