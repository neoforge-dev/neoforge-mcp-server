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
            
        # --- Ensure we work with bytes consistently ---
        if isinstance(code, str):
             code_bytes = code.encode('utf-8')
        else:
             code_bytes = code
        # --- End Bytes Consistency ---
            
        try:
            # Pass code_bytes to parse
            tree = self.parse(code_bytes) 
            if not tree or not tree.root_node:
                raise ValueError("Parsing resulted in an empty tree.")
                
            # Use the internal feature extraction method, passing code_bytes
            features = self._extract_features(tree.root_node, code_bytes)

            # --- Corrected Syntax Error Handling ---
            errors = []
            if tree.root_node.has_error:
                 self.logger.warning("Syntax errors detected in the tree by tree-sitter.")
                 # --- Set has_errors flag based on the fundamental tree signal ---
                 features['has_errors'] = True 
                 # --- End Flag Setting ---
                 # Call the method to collect specific errors (might return empty list)
                 errors = self._collect_syntax_errors(tree.root_node, code_bytes)
                 # Assign collected errors, even if empty
                 features['errors'] = errors 
                 # Original/Problematic logic:
                 # if errors:
                 #      features['has_errors'] = True # Only set if specific errors found
                 #      features['errors'] = errors
            # --- End Correction ---

            return features
        except ValueError as e:
             # Handle parsing failures specifically raised from self.parse()
             self.logger.error(f"JavaScript analysis could not proceed due to parsing failure: {e}")
             # Return minimal features indicating the error
             return {
                 'functions': [], 'classes': [], 'variables': [], 'imports': [], 'exports': [],
                 'has_errors': True,
                 'errors': [{'message': f"Parsing Failed: {e}"}], 
             }
        except Exception as e:
            self.logger.exception(f"JavaScript analysis failed unexpectedly: {e}")
            # Re-raise to ensure the caller knows analysis failed critically
            raise

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
            elif current_node.type == 'arrow_function':
                parent_node = parent_map.get(current_node)
                is_async_arrow = False
                name = "<anonymous_arrow>"
                if parent_node and parent_node.type == 'variable_declarator':
                    name_node = parent_node.child_by_field_name('name')
                    if name_node: name = self._get_node_text(name_node, code)
                    # CORRECTED: Check children of the arrow function node itself for 'async'
                    is_async_arrow = any(child.type == 'async' for child in current_node.children)

                # --- Integrated Arrow Function Extraction ---
                params = []
                params_node = current_node.child_by_field_name('parameters')
                # Handle cases where parameters might be a single identifier (e.g., x => x * 2)
                if current_node.child_by_field_name('parameter'):
                    param_node = current_node.child_by_field_name('parameter')
                    if param_node.type == 'identifier':
                         params.append(self._get_node_text(param_node, code))
                elif params_node: # Handle formal_parameters node
                     for child in params_node.children:
                         # Extract various parameter types correctly
                         if child.type == 'identifier':
                             params.append(self._get_node_text(child, code))
                         elif child.type == 'rest_pattern':
                              # Find identifier within rest_pattern
                              ident_node = next((sub_child for sub_child in child.children if sub_child.type == 'identifier'), None)
                              if ident_node:
                                   params.append(f"...{self._get_node_text(ident_node, code)}")
                         elif child.type in ('object_pattern', 'array_pattern'):
                              # Represent destructured params textually for now
                              params.append(self._get_node_text(child, code))
                         elif child.type == 'required_parameter': # Handle required_parameter wrapper
                             inner_pattern = child.child_by_field_name('pattern')
                             if inner_pattern:
                                 params.append(self._get_node_text(inner_pattern, code))


                has_try_catch = False
                body_node = current_node.child_by_field_name('body')
                if body_node:
                    # Simple check, might need refinement for nested try-catch
                    body_text = self._get_node_text(body_node, code)
                    has_try_catch = 'try' in body_text and 'catch' in body_text

                func_info = {
                    'name': name,
                    'type': 'function', # Still categorize as 'function' broadly
                    'is_async': is_async_arrow,
                    'is_arrow': True, # Mark specifically as arrow
                    'parameters': params,
                    'has_try_catch': has_try_catch,
                    'has_destructured_params': False,
                    'line': current_node.start_point[0] + 1,
                    'column': current_node.start_point[1],
                    'end_line': current_node.end_point[0] + 1,
                    'end_column': current_node.end_point[1]
                }
                # --- End Integrated Extraction ---

                # func_info = self._extract_arrow_function(current_node, code, name, is_async_arrow) # Removed call to non-existent func
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
        # Initialize func_info dict
        func_info = {
            'name': None,
            'type': 'function',
            'is_async': False,
            'is_arrow': False,
            'parameters': [],
            'has_try_catch': False,
            'has_destructured_params': False,
            'line': node.start_point[0] + 1,
            'column': node.start_point[1],
            'end_line': node.end_point[0] + 1,
            'end_column': node.end_point[1]
        }

        name_node = node.child_by_field_name('name')
        func_info['name'] = self._get_node_text(name_node, code) if name_node else "<anonymous>"
        
        # Check for async modifier
        is_async = any(child.type == 'async' for child in node.children)
        
        # Extract parameters & Check for destructuring
        params = []
        has_destructured = False
        params_node = node.child_by_field_name('parameters')
        if params_node:
            # --- Refined Destructuring Check ---
            for child in params_node.named_children: # Use named_children for more reliability
                param_text = self._get_node_text(child, code)
                # Check the type of the parameter pattern node
                pattern_node = child # Default if no specific pattern wrapper
                if child.type == 'required_parameter':
                     pattern_node = child.child_by_field_name('pattern')
                elif child.type == 'optional_parameter':
                     pattern_node = child.child_by_field_name('pattern')

                if pattern_node:
                    param_text = self._get_node_text(pattern_node, code) # Get text from actual pattern
                    if pattern_node.type in ('object_pattern', 'array_pattern'):
                        has_destructured = True
                    elif pattern_node.type == 'rest_pattern':
                         # Handle rest pattern text representation
                         ident_node = next((sub for sub in pattern_node.children if sub.type == 'identifier'), None)
                         if ident_node:
                              param_text = f"...{self._get_node_text(ident_node, code)}"
                         else:
                              param_text = f"...{param_text}"
                    # Add the potentially refined param_text
                    params.append(param_text)
                else:
                     params.append(self._get_node_text(child, code))
            # --- End Refined Check ---

            # Original loop:
            # for child in params_node.children:
            #     param_text = self._get_node_text(child, code)
            #     params.append(param_text)
            #     if child.type in ('object_pattern', 'array_pattern'):
            #         has_destructured = True
            #     elif child.type == 'rest_parameter':
            #          # Tree-sitter often includes the '...' in the text for rest_parameter
            #          # If not, prepend it.
            #          if not param_text.startswith('...'):
            #               # Find the identifier within the rest_parameter if needed
            #               ident_node = next((sub for sub in child.children if sub.type == 'identifier'), None)
            #               if ident_node:
            #                    params[-1] = f"...{self._get_node_text(ident_node, code)}"
            #               else:
            #                    params[-1] = f"...{param_text}" # Fallback

        func_info['parameters'] = params
        func_info['has_destructured_params'] = has_destructured

        # Check for arrow function
        is_arrow = node.type == 'arrow_function'
        
        # Check for try-catch blocks
        has_try_catch = False
        body_node = node.child_by_field_name('body')
        if body_node:
            body_text = self._get_node_text(body_node, code)
            has_try_catch = 'try' in body_text and 'catch' in body_text
        
        func_info['is_async'] = is_async
        func_info['is_arrow'] = is_arrow
        func_info['has_try_catch'] = has_try_catch

        return func_info
        
    def _extract_class(self, node: Node, code: Union[str, bytes]) -> Dict:
        """Extract class information with support for private fields and methods."""
        class_info = {
            'name': None,
            'type': 'class',
            'is_abstract': False,
            'extends': None,
            'implements': [],
            'methods': [],
            'fields': [],
            'private_fields': [],
            'private_methods': [],
            'line': node.start_point[0] + 1,
            'column': node.start_point[1],
            'end_line': node.end_point[0] + 1,
            'end_column': node.end_point[1]
        }
        
        # Get class name
        name_node = node.child_by_field_name('name')
        if name_node:
            class_info['name'] = self._get_node_text(name_node, code)
        
        # Check for extends clause
        extends_node = node.child_by_field_name('superclass')
        if extends_node:
            class_info['extends'] = self._get_node_text(extends_node, code)
        
        # Check for implements clause
        implements_node = node.child_by_field_name('implements')
        if implements_node:
            for child in implements_node.children:
                if child.type == 'type_identifier':
                    class_info['implements'].append(self._get_node_text(child, code))
        
        # Process class body
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child.type == 'method_definition':
                    # Corrected method name (assuming _extract_method_definition is intended)
                    method_info = self._extract_method_definition(child, code)
                    if method_info:
                        if method_info.get('name', '').startswith('#'):
                            class_info['private_methods'].append(method_info)
                        else:
                            class_info['methods'].append(method_info)
                elif child.type == 'field_definition':
                    field_info = self._extract_field(child, code)
                    if field_info and field_info.get('name'):
                        if field_info['name'].startswith('#'):
                            class_info['private_fields'].append(field_info)
                        else:
                            class_info['fields'].append(field_info)
                    elif field_info:
                        self.logger.warning(f"Field definition at line {field_info.get('line')} is missing a name.")
        
        return class_info

    def _extract_method_definition(self, node: Node, code: Union[str, bytes]) -> Dict:
        """Extract method information (including static, async, generator, name, params)."""
        method_info = {
            'name': None,
            'type': 'method',
            'parameters': [],
            'return_type': None,
            'is_static': False,
            'is_async': False,
            'is_generator': False,
            'is_getter': False,
            'is_setter': False,
            # Known Limitation: super() call detection removed due to instability.
            # 'calls_super': False,
            'line': node.start_point[0] + 1,
            'column': node.start_point[1],
            'end_line': node.end_point[0] + 1,
            'end_column': node.end_point[1],
            'body_start_line': None,
            'body_end_line': None,
            'has_destructured_params': False
        }

        # Check for modifiers like get/set/static/async/* within the method node itself
        # These are often direct children or specific markers
        keywords = {child.type for child in node.children if not child.is_named} # Check unnamed children like keywords
        method_info['is_static'] = 'static' in keywords
        method_info['is_async'] = 'async' in keywords
        method_info['is_generator'] = '*' in keywords
        method_info['is_getter'] = 'get' in keywords
        method_info['is_setter'] = 'set' in keywords

        # Original modifier checks - less reliable as keywords aren't always top-level children
        # for child in node.children:
        #     if child.type == 'static':
        #         method_info['is_static'] = True
        #     elif child.type == 'async':
        #         method_info['is_async'] = True
        #     elif child.type == '*': # Generator indicator
        #         method_info['is_generator'] = True
        #     elif child.type == 'get': # <<< Added Getter Check
        #          method_info['is_getter'] = True
        #     elif child.type == 'set': # <<< Added Setter Check
        #          method_info['is_setter'] = True

        # Get method name (could be identifier or private_property_identifier)
        name_node = node.child_by_field_name('name')
        if name_node:
            name = self._get_node_text(name_node, code)
            method_info['name'] = name
            # Check if name node indicates private
            if name_node.type == 'private_property_identifier': # <<< Check type for private
                 method_info['is_private'] = True
        else:
            self.logger.warning(f"Method definition at line {method_info['line']} is missing a name.")

        # Get parameters & Check destructuring
        params = []
        has_destructured = False
        params_node = node.child_by_field_name('parameters')
        if params_node:
            # --- Refined Destructuring Check ---
            for child in params_node.named_children: # Use named_children
                param_text = self._get_node_text(child, code)
                pattern_node = child
                if child.type == 'required_parameter':
                     pattern_node = child.child_by_field_name('pattern')
                elif child.type == 'optional_parameter':
                     pattern_node = child.child_by_field_name('pattern')
                
                if pattern_node:
                    param_text = self._get_node_text(pattern_node, code)
                    if pattern_node.type in ('object_pattern', 'array_pattern'):
                        has_destructured = True
                    elif pattern_node.type == 'rest_pattern':
                        ident_node = next((sub for sub in pattern_node.children if sub.type == 'identifier'), None)
                        if ident_node:
                             param_text = f"...{self._get_node_text(ident_node, code)}"
                        else:
                             param_text = f"...{param_text}"
                    params.append(param_text)
                else:
                     params.append(self._get_node_text(child, code))
            # --- End Refined Check ---
            
            # Original loop
            # for param in params_node.children:
            #     if param.type in ('identifier', 'object_pattern', 'array_pattern', 'rest_pattern'):
            #         method_info['parameters'].append(self._get_node_text(param, code))
            #         if param.type in ('object_pattern', 'array_pattern'):
            #             method_info['has_destructured_params'] = True
            #     elif child.type == 'rest_parameter': # This was a typo, should be param.type
            #          # ... rest_parameter handling ...

        method_info['parameters'] = params
        method_info['has_destructured_params'] = has_destructured

        # Get body location
        body_node = node.child_by_field_name('body')
        if body_node:
            method_info['body_start_line'] = body_node.start_point[0] + 1
            method_info['body_end_line'] = body_node.end_point[0] + 1

        # Note: Return type extraction might need more logic if types are specified

        # Check for try-catch blocks
        has_try_catch = False
        body_node = node.child_by_field_name('body')
        if body_node:
            body_text = self._get_node_text(body_node, code)
            has_try_catch = 'try' in body_text and 'catch' in body_text
        method_info['has_try_catch'] = has_try_catch

        return method_info

    def _extract_field(self, node: Node, code: Union[str, bytes]) -> Dict:
        """Extract field information with support for private fields."""
        field_info = {
            'name': None,
            'type': 'field',
            'is_static': False,
            'is_private': False,
            'value': None,
            'line': node.start_point[0] + 1,
            'column': node.start_point[1],
            'end_line': node.end_point[0] + 1,
            'end_column': node.end_point[1]
        }
        
        # Check if field is static
        for child in node.children:
            if child.type == 'static':
                field_info['is_static'] = True
                break
        
        # Get field name (could be identifier or private_property_identifier)
        name_node = node.child_by_field_name('name')
        if name_node:
            name = self._get_node_text(name_node, code)
            field_info['name'] = name
            # Check if name node indicates private
            if name_node.type == 'private_property_identifier': # <<< Check type for private
                field_info['is_private'] = True
        else:
            self.logger.warning(f"Field definition at line {field_info['line']} is missing a name node.")
        
        # Get field value if present
        value_node = node.child_by_field_name('value')
        if value_node:
            field_info['value'] = self._get_node_text(value_node, code)
        
        return field_info
        
    def _extract_variables(self, node: Node, code: Union[str, bytes]) -> List[Dict]:
        """Extract variable declarations with support for destructuring and template literals."""
        variables = []
        
        # Get the declaration type (let, const, var)
        declaration_type = node.type.split('_')[0]  # e.g., 'lexical_declaration' -> 'lexical'
        
        # Process each declarator in the declaration
        for child in node.children:
            if child.type == 'variable_declarator':
                name_node = child.child_by_field_name('name')
                value_node = child.child_by_field_name('value')
                
                if name_node:
                    # Handle destructuring patterns
                    if name_node.type in ('object_pattern', 'array_pattern'):
                        self._extract_destructured_variables(name_node, code, variables, declaration_type)
                    else:
                        # Regular variable declaration
                        name = self._get_node_text(name_node, code)
                        var_info = {
                            'name': name,
                            'type': 'variable',
                            'declaration_type': declaration_type,
                            'is_destructured': False,
                            'is_rest': False,
                            'line': name_node.start_point[0] + 1,
                            'column': name_node.start_point[1],
                            'end_line': name_node.end_point[0] + 1,
                            'end_column': name_node.end_point[1],
                            'value_type': None,
                            'is_call_expression': False,
                            'is_new_expression': False,
                            'is_template_literal': False,
                            'is_tagged_template': False,
                            'is_arrow_function': False
                        }

                        if value_node:
                            var_info['value_type'] = value_node.type
                            # Log type for all variables (Removed specific debug logging)
                            # self.logger.debug(f"Variable '{name}' at line {var_info['line']} assigned value of type: {value_node.type}")
                            
                            # --- Refined Tagged Template Check --- 
                            is_tagged = False
                            if child.prev_named_sibling and child.prev_named_sibling.type == 'identifier':
                                # If `tag` immediately precedes `template_string` value, it's tagged
                                is_tagged = True
                                var_info['is_tagged_template'] = True 
                                self.logger.debug(f"Tagged template (sibling check) found for '{name}' at line {var_info['line']}")
                            # --- End Refined Check ---

                            if value_node.type == 'call_expression':
                                var_info['is_call_expression'] = True
                            elif value_node.type == 'new_expression':
                                var_info['is_new_expression'] = True
                            elif value_node.type == 'template_string':
                                var_info['is_template_literal'] = True
                                # Known Limitation: Parsing tagged templates accurately is complex.
                                # The direct 'tagged_template_expression' type is preferred but 
                                # might not always be generated by tree-sitter depending on context.
                            elif value_node.type == 'tagged_template_expression':
                                # This is the ideal case, mark both flags.
                                var_info['is_template_literal'] = True
                                var_info['is_tagged_template'] = True
                                self.logger.debug(f"Tagged template (direct) found for '{name}' at line {var_info['line']}")
                            elif value_node.type == 'arrow_function':
                                var_info['is_arrow_function'] = True

                        variables.append(var_info)
        
        return variables

    def _extract_destructured_variables(self, pattern_node: Node, code: Union[str, bytes], variables: List[Dict], declaration_type: str) -> None:
        """Extract variables from destructuring patterns."""
        for child in pattern_node.children:
            if child.type == 'shorthand_property_identifier_pattern':
                # Object destructuring: { name }
                name = self._get_node_text(child, code)
                variables.append({
                    'name': name,
                    'type': 'variable',
                    'declaration_type': declaration_type,
                    'is_destructured': True,
                    'is_rest': False,
                    'line': child.start_point[0] + 1,
                    'column': child.start_point[1],
                    'end_line': child.end_point[0] + 1,
                    'end_column': child.end_point[1]
                })
            elif child.type == 'rest_pattern':
                # Rest pattern: ...rest
                # CORRECTED: Find the identifier within the rest_pattern's children
                name = "<unknown_rest>"
                ident_node = next((sub_child for sub_child in child.children if sub_child.type == 'identifier'), None)
                if ident_node:
                    name = self._get_node_text(ident_node, code)

                # name_node = child.child(0) # Incorrect assumption
                # if name_node and name_node.type == 'identifier': # Incorrect assumption
                #     name = self._get_node_text(name_node, code)
                variables.append({
                    'name': name,
                    'type': 'variable',
                    'declaration_type': declaration_type,
                    'is_destructured': True,
                    'is_rest': True,
                    'line': child.start_point[0] + 1,
                    'column': child.start_point[1],
                    'end_line': child.end_point[0] + 1,
                    'end_column': child.end_point[1]
                })
            elif child.type == 'identifier':
                # Array destructuring: [name]
                name = self._get_node_text(child, code)
                variables.append({
                    'name': name,
                    'type': 'variable',
                    'declaration_type': declaration_type,
                    'is_destructured': True,
                    'is_rest': False,
                    'line': child.start_point[0] + 1,
                    'column': child.start_point[1],
                    'end_line': child.end_point[0] + 1,
                    'end_column': child.end_point[1]
                })
            elif child.type in ('object_pattern', 'array_pattern'):
                # Nested destructuring
                self._extract_destructured_variables(child, code, variables, declaration_type)
        
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
        """Handle namespace exports and re-exports."""
        base_info['type'] = 're-export'
        base_info['is_namespace'] = True
        
        # Check for namespace alias (export * as ns from ...)
        if namespace_export_node:
            alias_node = namespace_export_node.child_by_field_name('alias')
            if alias_node:
                base_info['namespace'] = {
                    'name': self._get_node_text(alias_node, code),
                    'line': alias_node.start_point[0] + 1,
                    'column': alias_node.start_point[1],
                    'end_line': alias_node.end_point[0] + 1,
                    'end_column': alias_node.end_point[1]
                }
        
        return base_info

    def _handle_named_exports(self, node: Node, code: Union[str, bytes], clause_node: Node, source_node: Optional[Node], base_info: Dict) -> Union[Dict, List[Dict]]:
        """Handle named exports and re-exports."""
        exports_list = []
        current_export_type = 're-export' if source_node else 'named'
        
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
                    single_export['type'] = current_export_type
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
         return None # Corrected indentation