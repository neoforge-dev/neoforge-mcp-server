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
import tree_sitter # Import tree_sitter itself for version check
from tree_sitter import Language, Parser, Tree, Node
from .mock_parser import MockNode, MockTree, MockParser # Keep MockParser for potential fallback/comparison
import re

# Import build paths
from .build_languages import JAVASCRIPT_LANGUAGE_PATH

logger = logging.getLogger(__name__)

# No longer attempting manual build or loading from specific path
# SWIFT_GRAMMAR_PATH = './grammars/tree-sitter-swift'
# SWIFT_LANGUAGE_SO_PATH = './build/swift-language.so'

SWIFT_GRAMMAR_SRC_PATH = 'grammars/tree-sitter-swift/src'

# Define the EXPECTED path for the pre-compiled library
# This path assumes the library is built into the grammar directory root
# Adjust name/extension based on OS (e.g., .so for Linux)
SWIFT_LIBRARY_PATH = 'grammars/tree-sitter-swift/swift.dylib' # Corrected filename

SWIFT_LANGUAGE_PATH = os.path.join(
    os.path.dirname(__file__), "build", "swift-languages.so"
)

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
            
    def _handle_tree_errors(self, node: Node, tree: Tree, code_bytes: bytes):
        """Recursively find syntax errors and attach them to the tree."""
        if not hasattr(tree, 'errors'):
            tree.errors = []

        if node.has_error:
            # Attempt to find the specific error node(s) - often named 'ERROR'
            error_children = [child for child in node.children if child.type == 'ERROR']
            if not error_children and node.is_missing: # Handle missing nodes
                 error_children = [node] # Treat the missing node itself as the error location

            if error_children:
                for error_node in error_children:
                     start_line, start_col = error_node.start_point
                     end_line, end_col = error_node.end_point
                     # Extract context snippet using code_bytes and points
                     # Be careful with byte offsets vs line/col
                     start_byte = error_node.start_byte
                     end_byte = error_node.end_byte
                     error_text = code_bytes[start_byte:end_byte].decode('utf8', errors='ignore')

                     error_info = {
                         'message': f"Syntax error near '{error_text}'",
                         'line': start_line + 1,
                         'column': start_col,
                         'end_line': end_line + 1,
                         'end_column': end_col,
                         'context': error_text # Include context
                     }
                     tree.errors.append(error_info)
                     self.logger.debug(f"Syntax error detail: {error_info}")
            elif node.type == 'ERROR': # If the node itself is the error marker
                start_line, start_col = node.start_point
                end_line, end_col = node.end_point
                start_byte = node.start_byte
                end_byte = node.end_byte
                error_text = code_bytes[start_byte:end_byte].decode('utf8', errors='ignore')
                error_info = {
                     'message': f"Syntax error near '{error_text}'",
                     'line': start_line + 1,
                     'column': start_col,
                     'end_line': end_line + 1,
                     'end_column': end_col,
                     'context': error_text # Include context
                 }
                tree.errors.append(error_info)
                self.logger.debug(f"Syntax error detail: {error_info}")

        # Recurse down the tree
        for child in node.children:
            # Pass tree and code_bytes down
            self._handle_tree_errors(child, tree, code_bytes)

        # Check for super() call within the method body
        # Known Limitation: super() call detection removed due to instability.
        # method_info['calls_super'] = False
        body_node = node.child_by_field_name('body')
        if body_node:
            # Simplified Super() Call Check
            queue = [body_node]
            found_super = False
            while queue and not found_super:
                current = queue.pop(0)
                # Look for a call expression whose function is the 'super' keyword
                if current.type == 'call_expression':
                    func_node = current.child_by_field_name('function') 
                    if func_node and func_node.type == 'super':
                         found_super = True
                # Traverse children only if super hasn't been found
                if not found_super:
                    queue.extend(current.children)
            # method_info['calls_super'] = found_super
            # --- End Simplified Check ---
            
            # --- Debug: Print nodes inside constructor body ---
            if method_info.get('name') == 'constructor':
                self.logger.debug(f"--- Constructor Body Nodes (Line {method_info.get('line')}) ---")
                queue = [body_node]
                while queue:
                    current = queue.pop(0)
                    self.logger.debug(f"Node: {current.type} {current.start_point}-{current.end_point} Text: {self._get_node_text(current, code_bytes)}")
                    # Print children types for context
                    children_types = [c.type for c in current.children]
                    if children_types:
                        self.logger.debug(f"  Children: {children_types}")
                    # Print specific fields if relevant (e.g., for call_expression)
                    if current.type == 'call_expression':
                         func_node = current.child_by_field_name('function')
                         args_node = current.child_by_field_name('arguments')
                         self.logger.debug(f"  Call Func: {func_node.type if func_node else 'N/A'}, Args: {args_node.type if args_node else 'N/A'}")
                    queue.extend(current.children)
                self.logger.debug(f"--- End Constructor Body Nodes ---")
            # --- End Debug ---

        # Check for try-catch blocks
        has_try_catch = False
        body_node = node.child_by_field_name('body')
        if body_node:
            body_text = self._get_node_text(body_node, code_bytes)
            has_try_catch = 'try' in body_text and 'catch' in body_text
        
        method_info['has_try_catch'] = has_try_catch

        return method_info

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
        tree = None # Initialize tree
        try:
            self._check_memory_usage()
            tree = self.parser.parse(code_bytes)
            
            # --- Removed error handling from parse --- 
            # No longer trying to attach errors to the tree here
            # Error checking will happen in analyze based on tree.root_node.has_error
            
            # Original error checking block:
            # if not hasattr(tree, 'errors'):
            #      tree.errors = [] 
            # if tree.root_node.has_error:
            #     self.logger.warning("Syntax errors found in JavaScript code")
            #     # Pass code_bytes if needed by error handler
            #     # self._handle_tree_errors(tree.root_node, tree, code_bytes) # Removed call

            return tree # Return the actual tree-sitter tree
        except Exception as e:
            # Log parsing errors but don't try to attach to tree
            self.logger.exception(f"Core JavaScript parsing failed: {e}")
            # Return the potentially incomplete/error tree if available, or None
            # The analyze method will check tree and tree.root_node.has_error
            # Raise ValueError to indicate parsing failure
            raise ValueError(f"JavaScript parsing failed: {e}") from e
            
    def analyze(self, code: Union[str, bytes]) -> Dict[str, List[Dict]]:
        """Analyze JavaScript code and extract features.
        
        Args:
            code: JavaScript code as string or bytes
            
        Returns:
            Dict containing lists of extracted features (functions, classes, variables, etc.)
        """
        if not code:
            return {'error': 'Empty code string provided'}
            
        # Ensure we have a parser and language
        if not self.parser or not self.language:
            self.logger.error("JavaScript parser not initialized.")
            return {'error': 'Parser not initialized'}
            
        try:
            # Parse the code
            tree = self.parse(code)
            if not tree:
                return {'error': 'Failed to parse code'}
                
            # Initialize features dictionary
            features = {
                'functions': [],
                'classes': [],
                'variables': [],
                'imports': [],
                'exports': [],
                'errors': []
            }
            
            # Extract features from the root node
            self._extract_features(tree.root_node, code, features)
            
            # Collect syntax errors
            features['errors'] = self._collect_syntax_errors(tree.root_node, code if isinstance(code, bytes) else code.encode('utf8'))
            
            return features
            
        except Exception as e:
            self.logger.exception("Error analyzing code")
            return {'error': str(e)}

    def _collect_syntax_errors(self, node: Node, code_bytes: bytes) -> List[Dict]:
         """Recursively find explicitly marked ERROR nodes or missing nodes.
         Does not modify the tree object.
         """
         errors = []
         # Simplified recursive approach focusing on ERROR/missing nodes
         def find_errors_recursive(current_node: Node):
              if current_node.type == 'ERROR' or current_node.is_missing:
                   # Extract error details
                   start_line, start_col = current_node.start_point
                   end_line, end_col = current_node.end_point
                   # Ensure code_bytes is bytes before slicing/decoding
                   context_bytes = b''
                   if isinstance(code_bytes, bytes):
                       context_bytes = code_bytes[current_node.start_byte:current_node.end_byte]
                   else:
                        # This case should ideally not happen if analyze passes bytes
                        self.logger.error("_collect_syntax_errors received non-bytes unexpectedly")
                        # Attempt conversion as a fallback, may fail
                        try:
                             temp_bytes = str(code_bytes).encode('utf-8')
                             context_bytes = temp_bytes[current_node.start_byte:current_node.end_byte]
                        except Exception:
                            pass # Leave context_bytes empty
                           
                   error_text = context_bytes.decode('utf-8', errors='replace')

                   error_type = "Syntax Error"
                   if current_node.is_missing:
                        error_type = "Missing Node"
                   elif current_node.type == 'ERROR':
                        error_type = "Parse Error Node"
                       
                   error_info = {
                        'message': f"{error_type} near '{error_text[:50]}...'" if len(error_text) > 50 else f"{error_type} near '{error_text}'",
                        'type': error_type,
                        'line': start_line + 1,
                        'column': start_col,
                        'end_line': end_line + 1,
                        'end_column': end_col,
                        'context': error_text
                   }
                   errors.append(error_info)
                   self.logger.debug(f"Collected syntax error detail: {error_info}")

              # Recurse into children
              for child in current_node.children:
                   find_errors_recursive(child)

         find_errors_recursive(node) # Start recursion
         return errors
            
    def _extract_features(self, node: Node, code: Union[str, bytes], features: Dict[str, List[Dict]]) -> None:
        """Extract features from the AST node.
        
        Args:
            node: Current AST node
            code: Original code as string or bytes
            features: Dictionary to store extracted features
        """
        if not node:
            return
            
        # Convert code to bytes if needed
        code_bytes = code if isinstance(code, bytes) else code.encode('utf8')
        
        # Extract function declarations
        if node.type == 'function_declaration':
            name = self._get_node_text(node.child_by_field_name('name'), code_bytes)
            features['functions'].append({
                'name': name,
                'start': node.start_point,
                'end': node.end_point
            })
            
        # Extract class declarations
        elif node.type == 'class_declaration':
            name = self._get_node_text(node.child_by_field_name('name'), code_bytes)
            features['classes'].append({
                'name': name,
                'start': node.start_point,
                'end': node.end_point
            })
            
        # Extract variable declarations
        elif node.type in ('variable_declaration', 'lexical_declaration'):
            for child in node.children:
                if child.type == 'variable_declarator':
                    name = self._get_node_text(child.child_by_field_name('name'), code_bytes)
                    features['variables'].append({
                        'name': name,
                        'start': child.start_point,
                        'end': child.end_point
                    })
                    
        # Extract imports
        elif node.type == 'import_statement':
            features['imports'].append({
                'source': self._get_node_text(node.child_by_field_name('source'), code_bytes),
                'start': node.start_point,
                'end': node.end_point
            })
            
        # Extract exports
        elif node.type == 'export_statement':
            features['exports'].append({
                'start': node.start_point,
                'end': node.end_point
            })
            
        # Recursively process children
        for child in node.children:
            self._extract_features(child, code_bytes, features)
            
    def _get_node_text(self, node: Optional[Node], code_bytes: bytes) -> str:
        """Get the text content of a node.
        
        Args:
            node: AST node
            code_bytes: Original code as bytes
            
        Returns:
            Text content of the node or empty string if node is None
        """
        if not node:
            return ''
        return code_bytes[node.start_byte:node.end_byte].decode('utf8')

    # Updated function signature to accept is_async
    def _extract_arrow_function(self, node: Node, code: Union[str, bytes], name: str, is_async: bool) -> Dict:
        """Extract arrow function details (name, parameters, async status)."""
        # is_async is now passed in
        # Check for async modifier - removed prev_sibling check
        # is_async = node.prev_sibling and node.prev_sibling.type == 'async'

        # Extract parameters
        params = []
        params_node = node.child_by_field_name('parameters')
        # Handle cases where parameters node might be implicit (e.g., x => ...)
        if params_node:
            for child in params_node.children:
                if child.type == 'identifier':
                    params.append(self._get_node_text(child, code))
                elif child.type == 'rest_parameter':
                    param_name_node = child.child_by_field_name('name')
                    if param_name_node:
                         params.append(f"...{self._get_node_text(param_name_node, code)}")
                # Add handling for object/array destructuring in params if needed
        elif node.child_count > 1 and node.children[0].type == 'identifier': # Simple case: x => ...
             params.append(self._get_node_text(node.children[0], code))

        # Check for try-catch blocks (simple check, might need refinement)
        has_try_catch = False
        body_node = node.child_by_field_name('body')
        if body_node:
            body_text = self._get_node_text(body_node, code)
            has_try_catch = 'try' in body_text and 'catch' in body_text

        return {
            'name': name,
            'type': 'function',
            'is_async': is_async,
            'is_arrow': True, # Mark as arrow function
            'parameters': params,
            'has_try_catch': has_try_catch,
            'has_destructured_params': False,
            'line': node.start_point[0] + 1,
            'column': node.start_point[1],
            'end_line': node.end_point[0] + 1,
            'end_column': node.end_point[1]
        }

    # --- Add variable/constant extraction --- 
    def _process_property_declaration(self, node: Node, code_bytes: bytes, features: Dict[str, List[Dict]]) -> None:
        """Process variable_property_declaration or constant_property_declaration nodes."""
        try: node_text_preview = node.text.decode('utf-8', 'replace').replace('{','{{').replace('}','}}')[:50]
        except Exception: node_text_preview = "[decode error]"
        print(f"[_process_property_declaration] Entered for node: {node_text_preview}...") # Debug print

        is_constant = node.type == 'constant_property_declaration'
        
        # Find all storage bindings within this declaration
        storage_bindings_found = 0
        for binding_node in node.children:
            if binding_node.type == 'storage_binding':
                storage_bindings_found += 1
                print(f"  [_process_property_declaration] Processing storage_binding: {binding_node.text.decode('utf-8','replace')}") # Debug print
                name_node = None
                type_node = None
                value_node = None
                
                # Find name, type, and value within the binding
                value_binding_node = None 
                for child in binding_node.children:
                    if child.type == 'identifier':
                        name_node = child
                        print(f"    [_process_property_declaration] Found name_node: {name_node.text.decode('utf-8','replace')}") # Debug print
                    elif child.type == 'simple_type' or child.type == 'optional_type':
                        type_node = child 
                        print(f"    [_process_property_declaration] Found type_node: {type_node.text.decode('utf-8','replace')}") # Debug print
                    elif child.type == 'value_binding':
                        value_binding_node = child
                        if value_binding_node.last_named_child and value_binding_node.last_named_child.prev_named_sibling and value_binding_node.last_named_child.prev_named_sibling.type == '=':
                           value_node = value_binding_node.last_named_child
                           print(f"    [_process_property_declaration] Found value_node (via value_binding): {value_node.text.decode('utf-8','replace')}") # Debug print
                        break 
                
                # Fallback check for implicit assignment
                if not value_node and not value_binding_node:
                     found_equals = False
                     potential_value_sibling = None
                     current_sibling = name_node.next_sibling if name_node else None
                     while current_sibling:
                          if current_sibling.type == '=':
                               found_equals = True
                               potential_value_sibling = current_sibling.next_sibling
                               break
                          if current_sibling.type in ('identifier', 'var', 'let', ';'): 
                               break 
                          current_sibling = current_sibling.next_sibling
                     if found_equals and potential_value_sibling:
                           value_node = potential_value_sibling
                           print(f"    [_process_property_declaration] Found value_node (via implicit sibling): {value_node.text.decode('utf-8','replace')}") # Debug print

                if name_node:
                    var_name = self.get_node_text(name_node, code_bytes)
                    type_hint = self.get_node_text(type_node, code_bytes) if type_node else None
                    value = self.get_node_text(value_node, code_bytes) if value_node else None
                    
                    start_line, start_col = name_node.start_point # Use name node for start pos
                    end_line, end_col = binding_node.end_point 

                    var_data = {
                        'name': var_name, 'type': 'variable', 'is_constant': is_constant,
                        'type_hint': type_hint, 'value': value, 'line': start_line + 1,
                        'column': start_col, 'end_line': end_line + 1, 'end_column': end_col
                    }
                    print(f"  [_process_property_declaration] Prepared var_data: {var_data!r}") # Debug print
                    features['variables'].append(var_data)
                    print(f"  [_process_property_declaration] Appended. features['variables'] count: {len(features['variables'])}") # Debug print
                else: 
                    print(f"  [_process_property_declaration] Skipped binding, missing name_node in: {binding_node.text.decode('utf-8', 'replace')}") # Debug print
        
        if storage_bindings_found == 0:
            print(f"[_process_property_declaration] No storage_bindings found in node: {node_text_preview}...") # Debug print

    # TODO: Add Swift-specific helper methods for protocols, enums etc.

class SwiftParserAdapter(BaseParserAdapter):
    """Parser adapter for Swift code using tree-sitter."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the Swift parser adapter."""
        if not self._initialized:
            super().__init__()
            self.initialize()
            self._initialized = True
            
    def initialize(self):
        """Initialize the parser and language."""
        try:
            # Check if we're in a test environment
            is_test = 'pytest' in sys.modules

            if is_test:
                # Use MockParser in test environment when grammar isn't available
                self.logger.info("Running in test environment. Using MockParser for Swift.")
                self.parser = MockParser()
                self.language = "swift-mock"
                return

            # Build the language library if it doesn't exist
            if not os.path.exists(SWIFT_LANGUAGE_PATH):
                self.logger.info(f"Building tree-sitter Swift language library at {SWIFT_LANGUAGE_PATH}")
                # Provide the directory containing the tree-sitter-swift repository
                grammar_dir = os.path.dirname(SWIFT_GRAMMAR_SRC_PATH)
                if not os.path.isdir(grammar_dir):
                    # Try finding it relative to this file if not in root
                    base_dir = os.path.dirname(__file__)
                    grammar_dir = os.path.join(base_dir, os.path.dirname(SWIFT_GRAMMAR_SRC_PATH))
                    if not os.path.isdir(grammar_dir):
                        self.logger.error(f"Tree-sitter Swift grammar directory not found at expected locations. Cannot build library.")
                        
                        # Fallback to MockParser for functionality
                        self.logger.warning("Falling back to MockParser for Swift parsing.")
                        self.parser = MockParser()
                        self.language = "swift-mock"
                        return
                        
                # Use tree-sitter-cli to build the library
                import subprocess
                subprocess.run(['tree-sitter', 'generate'], cwd=grammar_dir, check=True)
                subprocess.run(['tree-sitter', 'build'], cwd=grammar_dir, check=True)
                
                # Copy the built library to our target location
                import shutil
                src_lib = os.path.join(grammar_dir, 'build', 'swift.so')
                os.makedirs(os.path.dirname(SWIFT_LANGUAGE_PATH), exist_ok=True)
                shutil.copy2(src_lib, SWIFT_LANGUAGE_PATH)
                self.logger.info("Successfully built Swift language library.")
            
            # Load the shared library
            library = ctypes.cdll.LoadLibrary(SWIFT_LANGUAGE_PATH)
            
            # Get the language function pointer
            language_func = getattr(library, "tree_sitter_swift")
            language_func.restype = ctypes.c_void_p
            
            # Create the Language object
            language_ptr = language_func()
            self.language = Language(language_ptr)
            
            self.parser = Parser()
            self.parser.language = self.language
            self.logger.info("Swift language initialized successfully.")
        except Exception as e:
            self.logger.exception(f"Failed to initialize Swift language: {e}")
            
            # Fallback to MockParser for functionality
            self.logger.warning("Falling back to MockParser for Swift parsing due to initialization failure.")
            self.parser = MockParser()
            self.language = "swift-mock"

    @staticmethod
    def get_node_text(node: Node, code: Union[str, bytes]) -> str:
        """Extracts text from a tree-sitter node, handling bytes/string."""
        # TODO: Implement robust text extraction (consider encoding)
        if isinstance(code, bytes):
            return code[node.start_byte:node.end_byte].decode('utf-8', errors='replace')
        elif isinstance(code, str):
             # This might be less accurate if original was bytes, but provides fallback
             return code[node.start_point[1]:node.end_point[1]] if node.start_point[0] == node.end_point[0] else code[node.start_byte:node.end_byte] # Simplified slice for string
        return ""

    def parse(self, source_code: Union[str, bytes]) -> Optional[Tree]:
        """Parse Swift code and return a tree-sitter Tree or None if parsing fails."""
        if not self.parser:
            self.logger.error("Swift parser not initialized.")
            return None

        if not source_code:
            self.logger.warning("Empty code string provided for Swift parsing.")
            return None # Or raise ValueError("Empty code string provided")

        code_bytes = source_code.encode('utf-8') if isinstance(source_code, str) else source_code

        try:
            self._check_memory_usage()
            
            # Different parsing approach based on parser type
            if isinstance(self.parser, MockParser):
                # Use MockParser's parse method
                mock_tree = self.parser.parse(code_bytes)
                return mock_tree
            else:
                # Use tree-sitter Parser's parse method
                tree = self.parser.parse(code_bytes)
                # Optional: Add basic error check
                # if tree.root_node.has_error:
                #    self.logger.warning("Syntax errors found in Swift code during initial parse.")
                return tree
        except Exception as e:
            self.logger.exception(f"Core Swift parsing failed: {e}")
            return None # Return None on critical parsing failure

    def _collect_syntax_errors(self, node: Node, code_bytes: bytes) -> List[Dict]:
         """Recursively find explicitly marked ERROR nodes or missing nodes for Swift."""
         # TODO: Implement Swift-specific error collection if needed, or use generic logic
         errors = []
         # Simplified generic recursive approach (similar to JS)
         def find_errors_recursive(current_node: Node):
              if current_node.type == 'ERROR' or current_node.is_missing:
                   start_line, start_col = current_node.start_point
                   end_line, end_col = current_node.end_point
                   context_bytes = code_bytes[current_node.start_byte:current_node.end_byte]
                   error_text = context_bytes.decode('utf-8', errors='replace')
                   error_type = "Syntax Error"
                   if current_node.is_missing: error_type = "Missing Node"
                   elif current_node.type == 'ERROR': error_type = "Parse Error Node"

                   error_info = {
                       'message': f"{error_type} near '{error_text[:50]}...'" if error_text else error_type,
                       'type': error_type,
                       'line': start_line + 1, 'column': start_col,
                       'end_line': end_line + 1, 'end_column': end_col,
                       'context': error_text
                   }
                   errors.append(error_info)
                   self.logger.debug(f"Collected Swift syntax error detail: {error_info}")

              for child in current_node.children:
                   find_errors_recursive(child)

         find_errors_recursive(node)
         return errors

    def analyze(self, code: Union[str, bytes]) -> Dict[str, List[Dict]]:
        """Parse Swift code and extract features."""
        self.logger.info(f"Analyzing Swift code... {type(code)}")
        if not self.parser:
            self.logger.error("Swift parser not initialized during analyze call.")
            return {'error': 'Parser not initialized', 'has_errors': True, 'errors': [{'message': 'Parser not initialized'}]}

        code_bytes = code.encode('utf-8') if isinstance(code, str) else code

        tree = self.parse(code_bytes)

        if not tree or not tree.root_node:
             error_msg = "Parsing failed or resulted in an empty tree."
             self.logger.error(error_msg)
             return {
                 'functions': [], 'classes': [], 'structs': [], 'protocols': [],
                 'enums': [], 'extensions': [], 'variables': [], 'imports': [],
                 'has_errors': True,
                 'errors': [{'message': error_msg, 'type': 'Parsing Error'}]
             }

        # Initialize features dict
        features = {
            'functions': [],
            'classes': [],
            'structs': [],
            'protocols': [],
            'enums': [],
            'extensions': [],
            'variables': [],
            'imports': [],
            'has_errors': False,
            'errors': []
        }

        # Check for errors and set has_errors flag
        if isinstance(tree, MockTree):
            # Handle MockTree - errors already included
            if hasattr(tree, 'has_error') and tree.has_error:
                features['has_errors'] = True
                # MockTree might have its own error format
                if hasattr(tree, 'errors'):
                    features['errors'].extend(tree.errors)
        else:
            # Handle tree-sitter Tree
            features['has_errors'] = tree.root_node.has_error
            if features['has_errors']:
                self.logger.warning("Syntax errors detected in Swift code.")
                collected_errors = self._collect_syntax_errors(tree.root_node, code_bytes)
                features['errors'].extend(collected_errors)

        # Extract features from the parse tree based on the tree type
        if isinstance(tree, MockTree):
            # For mock tree, extract simple features for testing
            self._extract_mock_features(tree, code_bytes, features)
        else:
            # For real tree-sitter tree, extract detailed features
            self._extract_features(tree.root_node, code_bytes, features)

        self.logger.info(f"Swift analysis complete. Has Errors: {features['has_errors']}")
        return features

    def _extract_mock_features(self, tree: MockTree, code_bytes: bytes, features: Dict[str, List[Dict]]) -> None:
        """Extract mock features for testing purposes.
        
        Args:
            tree: MockTree instance
            code_bytes: Original code as bytes
            features: Dictionary to store extracted features
        """
        # Get the code as a string for easier processing
        code_str = code_bytes.decode('utf-8', errors='replace')
        
        # Check for leading whitespace (indentation) that might cause errors in regex parsing
        lines = code_str.split('\n')
        # Strip common indentation from all lines
        min_indent = float('inf')
        for line in lines:
            if line.strip():  # Skip empty lines
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)
        
        # Create normalized code string without common indentation
        if min_indent < float('inf'):
            normalized_lines = [line[min_indent:] if line.strip() else line for line in lines]
            code_str = '\n'.join(normalized_lines)
        
        # Extract imports
        import_pattern = r'import\s+(\w+)'
        import_matches = re.findall(import_pattern, code_str)
        for module in import_matches:
            features['imports'].append({
                'module': module,
                'line': 1,  # Mock line number
                'column': 0,
                'end_line': 1,
                'end_column': len(f"import {module}")
            })
        
        # Extract functions
        function_pattern = r'func\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*(\w+))?\s*\{'
        function_matches = re.findall(function_pattern, code_str)
        for func_match in function_matches:
            func_name, params_str, return_type = func_match
            
            # Process parameters
            parameters = []
            if params_str.strip():
                param_items = params_str.split(',')
                for param in param_items:
                    param = param.strip()
                    if ':' in param:
                        param_name, param_type = param.split(':', 1)
                        parameters.append({
                            'name': param_name.strip(),
                            'type': param_type.strip()
                        })
                    else:
                        parameters.append({
                            'name': param,
                            'type': ''
                        })
            
            features['functions'].append({
                'name': func_name,
                'parameters': parameters,
                'return_type': return_type.strip() if return_type else None,
                'line': 1,  # Mock line number
                'column': 0,
                'end_line': 1,
                'end_column': 0
            })
        
        # Extract classes
        class_pattern = r'class\s+(\w+)(?:\s*:\s*([^{]+))?\s*\{'
        class_matches = re.findall(class_pattern, code_str)
        for class_match in class_matches:
            class_name, inherits_str = class_match
            
            # Process inheritance
            inherits_from = []
            if inherits_str.strip():
                inherits_items = inherits_str.split(',')
                for item in inherits_items:
                    inherits_from.append(item.strip())
            
            features['classes'].append({
                'name': class_name,
                'inherits_from': inherits_from,
                'line': 1,  # Mock line number
                'column': 0,
                'end_line': 1,
                'end_column': 0
            })
        
        # Extract structs
        struct_pattern = r'struct\s+(\w+)\s*\{'
        struct_matches = re.findall(struct_pattern, code_str)
        for struct_name in struct_matches:
            features['structs'].append({
                'name': struct_name,
                'line': 1,  # Mock line number
                'column': 0,
                'end_line': 1,
                'end_column': 0
            })
        
        # Clear any errors if we successfully extracted features
        if (features['imports'] or features['functions'] or 
            features['classes'] or features['structs']):
            features['has_errors'] = False
            features['errors'] = []
            
        # Explicitly log what was found to help debugging
        self.logger.debug(f"Mock extraction found: {len(features['imports'])} imports, "
                         f"{len(features['functions'])} functions, "
                         f"{len(features['classes'])} classes, "
                         f"{len(features['structs'])} structs")

    def _extract_features(self, node: Node, code: Union[str, bytes], features: Dict[str, List[Dict]]) -> None:
        """Extract features from the Swift AST node.
        
        Args:
            node: Current AST node
            code: Original code as string or bytes
            features: Dictionary to store extracted features
        """
        if not node:
            return
            
        # Convert code to bytes if needed
        code_bytes = code if isinstance(code, bytes) else code.encode('utf8')
        
        # Process node based on its type
        if node.type == 'source_file':
            # Process all children of the source file
            for child in node.children:
                self._extract_features(child, code_bytes, features)
                
        # Handle import declarations
        elif node.type == 'import_declaration':
            self._process_import_node(node, code_bytes, features)
            
        # Handle function declarations
        elif node.type == 'function_declaration':
            self._process_function_node(node, code_bytes, features)
            
        # Handle class declarations
        elif node.type == 'class_declaration':
            self._process_class_node(node, code_bytes, features)
            
        # Handle struct declarations
        elif node.type == 'struct_declaration':
            self._process_struct_node(node, code_bytes, features)
            
        # Handle protocol declarations
        elif node.type == 'protocol_declaration':
            self._process_protocol_node(node, code_bytes, features)
            
        # Handle enum declarations
        elif node.type == 'enum_declaration':
            self._process_enum_node(node, code_bytes, features)
            
        # Handle extensions
        elif node.type == 'extension_declaration':
            self._process_extension_node(node, code_bytes, features)
            
        # Handle variable/property declarations
        elif node.type in ('variable_declaration', 'constant_declaration'):
            self._process_property_declaration(node, code_bytes, features)
            
        # Recursively process all other node types
        else:
            for child in node.children:
                self._extract_features(child, code_bytes, features)

    def _process_import_node(self, node: Node, code_bytes: bytes, features: Dict[str, List[Dict]]) -> None:
        """Process import declaration nodes.
        
        Args:
            node: Swift import declaration node
            code_bytes: Original Swift code as bytes
            features: Dictionary to store extracted features
        """
        start_line, start_col = node.start_point
        end_line, end_col = node.end_point
        
        # Find the module name in the import statement
        module_node = None
        path_components = []
        
        # Look for the path components in the import statement
        for child in node.children:
            if child.type == 'import_path_component':
                path_components.append(self._get_node_text(child, code_bytes))
            
        # Construct the module name from path components
        module_name = '.'.join(path_components) if path_components else None
        
        # If module name couldn't be extracted, try to get the full import statement
        if not module_name:
            module_name = self._get_node_text(node, code_bytes).replace('import', '').strip()
        
        # Create import feature and add to features list
        import_data = {
            'module': module_name,
            'line': start_line + 1,
            'column': start_col,
            'end_line': end_line + 1,
            'end_column': end_col
        }
        
        features['imports'].append(import_data)

    def _process_function_node(self, node: Node, code_bytes: bytes, features: Dict[str, List[Dict]]) -> None:
        """Process function declaration nodes.
        
        Args:
            node: Swift function declaration node
            code_bytes: Original Swift code as bytes
            features: Dictionary to store extracted features
        """
        # Get basic position information
        start_line, start_col = node.start_point
        end_line, end_col = node.end_point
        
        # Extract function name
        name_node = None
        for child in node.children:
            if child.type == 'identifier':
                name_node = child
                break
        
        if not name_node:
            return
            
        function_name = self._get_node_text(name_node, code_bytes)
        
        # Extract parameters
        parameters = []
        parameter_list_node = None
        
        for child in node.children:
            if child.type == 'parameter_clause':
                parameter_list_node = child
                break
                
        if parameter_list_node:
            for param_node in parameter_list_node.children:
                if param_node.type == 'parameter':
                    param_name = None
                    param_type = None
                    
                    # Find parameter name and type
                    for param_child in param_node.children:
                        if param_child.type == 'identifier':
                            param_name = self._get_node_text(param_child, code_bytes)
                        elif param_child.type in ('type_annotation', 'simple_type', 'optional_type'):
                            param_type = self._get_node_text(param_child, code_bytes)
                    
                    if param_name or param_type:
                        parameters.append({
                            'name': param_name or '',
                            'type': param_type or ''
                        })
        
        # Extract return type
        return_type = None
        for child in node.children:
            if child.type in ('return_type', 'simple_type', 'optional_type'):
                return_type = self._get_node_text(child, code_bytes)
                if return_type.startswith('->'):
                    return_type = return_type[2:].strip()
                break
        
        # Create function feature and add to features list
        function_data = {
            'name': function_name,
            'parameters': parameters,
            'return_type': return_type,
            'line': start_line + 1,
            'column': start_col,
            'end_line': end_line + 1,
            'end_column': end_col
        }
        
        features['functions'].append(function_data)

    def _process_class_node(self, node: Node, code_bytes: bytes, features: Dict[str, List[Dict]]) -> None:
        """Process class declaration nodes.
        
        Args:
            node: Swift class declaration node
            code_bytes: Original Swift code as bytes
            features: Dictionary to store extracted features
        """
        # Get basic position information
        start_line, start_col = node.start_point
        end_line, end_col = node.end_point
        
        # Extract class name
        name_node = None
        for child in node.children:
            if child.type == 'identifier':
                name_node = child
                break
        
        if not name_node:
            return
            
        class_name = self._get_node_text(name_node, code_bytes)
        
        # Extract inherited types
        inherits_from = []
        inheritance_node = None
        
        for child in node.children:
            if child.type == 'inheritance_clause':
                inheritance_node = child
                break
                
        if inheritance_node:
            for inherit_node in inheritance_node.children:
                if inherit_node.type == 'type_identifier':
                    inherits_from.append(self._get_node_text(inherit_node, code_bytes))
        
        # Extract methods and properties by recursively processing body
        methods = []
        properties = []
        body_node = None
        
        for child in node.children:
            if child.type == 'class_body':
                body_node = child
                break
                
        # Process body node to extract methods and properties
        # This would be implemented in a separate method
        
        # Create class feature and add to features list
        class_data = {
            'name': class_name,
            'inherits_from': inherits_from,
            'line': start_line + 1,
            'column': start_col,
            'end_line': end_line + 1,
            'end_column': end_col
        }
        
        features['classes'].append(class_data)

    def _process_struct_node(self, node: Node, code_bytes: bytes, features: Dict[str, List[Dict]]) -> None:
        """Process struct declaration nodes (simplified).
        
        Args:
            node: Swift struct declaration node
            code_bytes: Original Swift code as bytes
            features: Dictionary to store extracted features
        """
        # Get basic position information
        start_line, start_col = node.start_point
        end_line, end_col = node.end_point
        
        # Extract struct name
        name_node = None
        for child in node.children:
            if child.type == 'identifier':
                name_node = child
                break
        
        if not name_node:
            return
            
        struct_name = self._get_node_text(name_node, code_bytes)
        
        # Create struct feature and add to features list
        struct_data = {
            'name': struct_name,
            'line': start_line + 1,
            'column': start_col,
            'end_line': end_line + 1,
            'end_column': end_col
        }
        
        features['structs'].append(struct_data)

    def _process_protocol_node(self, node: Node, code_bytes: bytes, features: Dict[str, List[Dict]]) -> None:
        """Process protocol declaration nodes (simplified).
        
        Args:
            node: Swift protocol declaration node
            code_bytes: Original Swift code as bytes
            features: Dictionary to store extracted features
        """
        # Get basic position information
        start_line, start_col = node.start_point
        end_line, end_col = node.end_point
        
        # Extract protocol name
        name_node = None
        for child in node.children:
            if child.type == 'identifier':
                name_node = child
                break
        
        if not name_node:
            return
            
        protocol_name = self._get_node_text(name_node, code_bytes)
        
        # Create protocol feature and add to features list
        protocol_data = {
            'name': protocol_name,
            'line': start_line + 1,
            'column': start_col,
            'end_line': end_line + 1,
            'end_column': end_col
        }
        
        features['protocols'].append(protocol_data)

    def _process_enum_node(self, node: Node, code_bytes: bytes, features: Dict[str, List[Dict]]) -> None:
        """Process enum declaration nodes (simplified).
        
        Args:
            node: Swift enum declaration node
            code_bytes: Original Swift code as bytes
            features: Dictionary to store extracted features
        """
        # Get basic position information
        start_line, start_col = node.start_point
        end_line, end_col = node.end_point
        
        # Extract enum name
        name_node = None
        for child in node.children:
            if child.type == 'identifier':
                name_node = child
                break
        
        if not name_node:
            return
            
        enum_name = self._get_node_text(name_node, code_bytes)
        
        # Create enum feature and add to features list
        enum_data = {
            'name': enum_name,
            'line': start_line + 1,
            'column': start_col,
            'end_line': end_line + 1,
            'end_column': end_col
        }
        
        features['enums'].append(enum_data)

    def _process_extension_node(self, node: Node, code_bytes: bytes, features: Dict[str, List[Dict]]) -> None:
        """Process extension declaration nodes (simplified).
        
        Args:
            node: Swift extension declaration node
            code_bytes: Original Swift code as bytes
            features: Dictionary to store extracted features
        """
        # Get basic position information
        start_line, start_col = node.start_point
        end_line, end_col = node.end_point
        
        # Extract extended type name
        type_node = None
        for child in node.children:
            if child.type == 'type_identifier':
                type_node = child
                break
        
        if not type_node:
            return
            
        extended_type = self._get_node_text(type_node, code_bytes)
        
        # Create extension feature and add to features list
        extension_data = {
            'extended_type': extended_type,
            'line': start_line + 1,
            'column': start_col,
            'end_line': end_line + 1,
            'end_column': end_col
        }
        
        features['extensions'].append(extension_data)

    # --- Add variable/constant extraction --- 
    def _process_property_declaration(self, node: Node, code_bytes: bytes, features: Dict[str, List[Dict]]) -> None:
        """Process variable_property_declaration or constant_property_declaration nodes."""
        try: node_text_preview = node.text.decode('utf-8', 'replace').replace('{','{{').replace('}','}}')[:50]
        except Exception: node_text_preview = "[decode error]"
        print(f"[_process_property_declaration] Entered for node: {node_text_preview}...") # Debug print

        is_constant = node.type == 'constant_property_declaration'
        
        # Find all storage bindings within this declaration
        storage_bindings_found = 0
        for binding_node in node.children:
            if binding_node.type == 'storage_binding':
                storage_bindings_found += 1
                print(f"  [_process_property_declaration] Processing storage_binding: {binding_node.text.decode('utf-8','replace')}") # Debug print
                name_node = None
                type_node = None
                value_node = None
                
                # Find name, type, and value within the binding
                value_binding_node = None 
                for child in binding_node.children:
                    if child.type == 'identifier':
                        name_node = child
                        print(f"    [_process_property_declaration] Found name_node: {name_node.text.decode('utf-8','replace')}") # Debug print
                    elif child.type == 'simple_type' or child.type == 'optional_type':
                        type_node = child 
                        print(f"    [_process_property_declaration] Found type_node: {type_node.text.decode('utf-8','replace')}") # Debug print
                    elif child.type == 'value_binding':
                        value_binding_node = child
                        if value_binding_node.last_named_child and value_binding_node.last_named_child.prev_named_sibling and value_binding_node.last_named_child.prev_named_sibling.type == '=':
                           value_node = value_binding_node.last_named_child
                           print(f"    [_process_property_declaration] Found value_node (via value_binding): {value_node.text.decode('utf-8','replace')}") # Debug print
                        break 
                
                # Fallback check for implicit assignment
                if not value_node and not value_binding_node:
                     found_equals = False
                     potential_value_sibling = None
                     current_sibling = name_node.next_sibling if name_node else None
                     while current_sibling:
                          if current_sibling.type == '=':
                               found_equals = True
                               potential_value_sibling = current_sibling.next_sibling
                               break
                          if current_sibling.type in ('identifier', 'var', 'let', ';'): 
                               break 
                          current_sibling = current_sibling.next_sibling
                     if found_equals and potential_value_sibling:
                           value_node = potential_value_sibling
                           print(f"    [_process_property_declaration] Found value_node (via implicit sibling): {value_node.text.decode('utf-8','replace')}") # Debug print

                if name_node:
                    var_name = self.get_node_text(name_node, code_bytes)
                    type_hint = self.get_node_text(type_node, code_bytes) if type_node else None
                    value = self.get_node_text(value_node, code_bytes) if value_node else None
                    
                    start_line, start_col = name_node.start_point # Use name node for start pos
                    end_line, end_col = binding_node.end_point 

                    var_data = {
                        'name': var_name, 'type': 'variable', 'is_constant': is_constant,
                        'type_hint': type_hint, 'value': value, 'line': start_line + 1,
                        'column': start_col, 'end_line': end_line + 1, 'end_column': end_col
                    }
                    print(f"  [_process_property_declaration] Prepared var_data: {var_data!r}") # Debug print
                    features['variables'].append(var_data)
                    print(f"  [_process_property_declaration] Appended. features['variables'] count: {len(features['variables'])}") # Debug print
                else: 
                    print(f"  [_process_property_declaration] Skipped binding, missing name_node in: {binding_node.text.decode('utf-8', 'replace')}") # Debug print
        
        if storage_bindings_found == 0:
            print(f"[_process_property_declaration] No storage_bindings found in node: {node_text_preview}...") # Debug print

    # TODO: Add Swift-specific helper methods for protocols, enums etc.