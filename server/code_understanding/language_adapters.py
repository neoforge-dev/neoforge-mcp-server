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
        for child in node.children:
            if child.has_error:
                errors.append({
                    'type': child.type,
                    'start_point': child.start_point,
                    'end_point': child.end_point
                })
            if child.children:
                self._handle_tree_errors(child, mock_tree)
        if errors:
            mock_tree.errors = errors

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
            return features
        except Exception as e:
            self.logger.exception(f"JavaScript analysis failed: {e}")
            # Re-raise to ensure the caller knows analysis failed
            raise
            
    def _extract_features(self, node: Node, code: Union[str, bytes]) -> Dict[str, List[Dict]]:
        """Extract features from the parse tree recursively.

        Args:
            node: The current tree-sitter node to process.
            code: Original code.

        Returns:
            Dict: Features organized by type (functions, classes, etc.).
        """
        features = {
            'functions': [],
            'classes': [],
            'variables': [],
            'imports': [],
            'exports': []
        }

        def traverse(current_node: Node):
            # Process the current node based on its type
            if current_node.type == 'function_declaration':
                features['functions'].append(self._extract_function(current_node, code))
            elif current_node.type == 'class_declaration':
                features['classes'].append(self._extract_class(current_node, code))
            elif current_node.type in ('variable_declaration', 'lexical_declaration'):
                vars = self._extract_variables(current_node, code)
                features['variables'].extend(vars)
            elif current_node.type == 'import_statement':
                features['imports'].append(self._extract_import(current_node, code))
            elif current_node.type == 'export_statement':
                 # Process exports, but also recurse into its children 
                 # (e.g., to find class/func defined within the export)
                features['exports'].append(self._extract_export(current_node, code))
            
            # Recursively process children
            for child in current_node.children:
                traverse(child)

        # Start traversal from the provided node (usually the root)
        traverse(node)

        return features
        
    def _extract_function(self, node: Node, code: Union[str, bytes]) -> Dict:
        """Extract function information from a node.
        
        Args:
            node: Function declaration node
            code: Original code
            
        Returns:
            Dict: Function information
        """
        name_node = node.child_by_field_name('name')
        name = self._get_node_text(name_node, code) if name_node else "<anonymous>"
        
        # Get function signature
        params_node = node.child_by_field_name('parameters')
        params = []
        if params_node:
            for param in params_node.children:
                if param.type != ',' and param.type != '(' and param.type != ')':
                    params.append(self._get_node_text(param, code))
                    
        return {
            'name': name,
            'type': 'function',
            'line': node.start_point[0] + 1,
            'column': node.start_point[1],
            'end_line': node.end_point[0] + 1,
            'end_column': node.end_point[1],
            'params': params
        }
        
    def _extract_class(self, node: Node, code: Union[str, bytes]) -> Dict:
        """Extract class information from a node.
        
        Args:
            node: Class declaration node
            code: Original code
            
        Returns:
            Dict: Class information
        """
        name_node = node.child_by_field_name('name')
        name = self._get_node_text(name_node, code) if name_node else "<anonymous>"
        
        # Get parent class if it exists
        heritage_node = node.child_by_field_name('heritage')
        parent = None
        if heritage_node:
            parent = self._get_node_text(heritage_node, code)
            
        return {
            'name': name,
            'type': 'class',
            'line': node.start_point[0] + 1,
            'column': node.start_point[1],
            'end_line': node.end_point[0] + 1,
            'end_column': node.end_point[1],
            'parent': parent
        }
        
    def _extract_variables(self, node: Node, code: Union[str, bytes]) -> List[Dict]:
        """Extract variable information from a node.
        
        Args:
            node: Variable declaration node
            code: Original code
            
        Returns:
            List[Dict]: Variable information
        """
        variables = []
        
        # Process each declarator in the declaration
        declaration_node = node.child_by_field_name('declaration')
        if declaration_node:
            for child in declaration_node.children:
                if child.type == 'variable_declarator':
                    name_node = child.child_by_field_name('name')
                    if name_node:
                        name = self._get_node_text(name_node, code)
                        variables.append({
                            'name': name,
                            'type': 'variable',
                            'line': child.start_point[0] + 1,
                            'column': child.start_point[1],
                            'end_line': child.end_point[0] + 1,
                            'end_column': child.end_point[1]
                        })
                        
        return variables
        
    def _extract_import(self, node: Node, code: Union[str, bytes]) -> Dict:
        """Extract import information from a node.
        
        Args:
            node: Import statement node
            code: Original code
            
        Returns:
            Dict: Import information
        """
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
        
    def _extract_export(self, node: Node, code: Union[str, bytes]) -> Dict:
        """Extract export information from a node.
        
        Args:
            node: Export statement node
            code: Original code
            
        Returns:
            Dict: Export information
        """
        name = None # Initialize name to None
        is_default = False
        value_node = None # Node representing the exported value (identifier, class, func)
        
        declaration_node = node.child_by_field_name('declaration')
        
        if declaration_node:
            value_node = declaration_node # Exporting a definition
            if declaration_node.type == 'function_declaration':
                name_node = declaration_node.child_by_field_name('name')
                name = self._get_node_text(name_node, code) if name_node else None
            elif declaration_node.type == 'class_declaration':
                name_node = declaration_node.child_by_field_name('name')
                name = self._get_node_text(name_node, code) if name_node else None
        else:
            # Check for direct identifier export (e.g., export default MyVar; export { MyVar };)
            # Iterate children to find 'default' keyword or 'identifier' for default export
            for child in node.children:
                if child.type == 'default':
                    is_default = True
                elif child.type == 'identifier' and is_default:
                     # Found 'export default Identifier'
                     value_node = child
                     name = self._get_node_text(child, code)
                     break # Found the default export identifier
                # Handle export specifiers later if needed (export { name1, name2 })

        # Handle export from source
        source_node = node.child_by_field_name('source')
        source = self._get_node_text(source_node, code) if source_node else None
        
        # Remove quotes from source
        if source and (source.startswith('"') and source.endswith('"') or 
                      source.startswith("'") and source.endswith("'")):
            source = source[1:-1]
            
        # Get export specifiers
        specifiers = []
        clause_node = node.child_by_field_name('clause')
        if clause_node:
            for child in clause_node.children:
                if child.type == 'export_specifier':
                    local_node = child.child_by_field_name('local')
                    exported_node = child.child_by_field_name('exported')
                    
                    local = self._get_node_text(local_node, code) if local_node else ""
                    exported = self._get_node_text(exported_node, code) if exported_node else local
                    
                    specifiers.append({
                        'local': local,
                        'exported': exported
                    })
                    
        return {
            'type': 'export',
            'name': name, # The name of the exported item, if directly available
            'source': source,
            'specifiers': specifiers, # For named exports like export { a, b }
            'isDefault': is_default, # Explicitly tracked
            'line': node.start_point[0] + 1,
            'column': node.start_point[1]
        }
        
    def _get_node_text(self, node: Node, code: Union[str, bytes]) -> str:
        """Get the text of a node from the original code.
        
        Args:
            node: Node to get text for
            code: Original code
            
        Returns:
            str: Text of the node
        """
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
        super().__init__()
        self.initialize()
        
    def initialize(self):
        """Initialize the parser and language."""
        try:
            # Get the Swift language
            language_path = str(tree_sitter_swift.__path__[0])
            
            # Using tree-sitter 0.24.0, we need to load the language differently
            language_capsule = tree_sitter_swift.language()
            self.language = Language(language_capsule)
            
            # Initialize the parser with the language
            self.parser = Parser(self.language)
            
            self.logger.info("Swift parser initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Swift parser: {e}")
            raise
            
    def parse(self, source_code: Union[str, bytes]) -> Optional[MockTree]:
        """Parse Swift code and return a mock tree."""
        attempts = 0
        last_error = None
        
        while attempts < self._error_recovery_attempts:
            try:
                # Check memory usage before parsing
                self._check_memory_usage()
                
                # Convert string to bytes if needed
                if isinstance(source_code, str):
                    source_code = source_code.encode('utf-8')
                    
                # Parse the code
                tree = self.parser.parse(source_code)
                if not tree:
                    raise ParserError("Failed to parse source code", "parse_error")
                    
                # Create mock tree
                mock_tree = MockTree()
                
                # Extract features with caching
                self._extract_features(tree.root_node, mock_tree)
                
                # Check for errors in the tree
                if tree.root_node.has_error:
                    self._handle_tree_errors(tree.root_node, mock_tree)
                
                return mock_tree
                
            except ParserError as e:
                last_error = e
                attempts += 1
                self._handle_parser_error(e, attempts)
                
            except Exception as e:
                last_error = ParserError(str(e), "unexpected_error")
                attempts += 1
                self._handle_parser_error(last_error, attempts)
        
        # If all recovery attempts failed, log the error and return None
        self.logger.error(f"Failed to parse Swift code after {attempts} attempts: {last_error}")
        return None
        
    def _extract_features(self, node: Node, mock_tree: MockTree) -> None:
        """Extract features with memory optimization and error handling."""
        try:
            # Generate feature key for caching
            feature_key = f"{node.type}_{node.start_point}_{node.end_point}"
            
            # Check cache first
            cached_feature = self._get_cached_feature(feature_key)
            if cached_feature:
                feature_type, feature = cached_feature
                mock_tree.add_feature(feature_type, feature)
                return
                
            # Extract features based on node type
            if node.type == 'source_file':
                for child in node.children:
                    self._extract_features(child, mock_tree)
                    
            elif node.type == 'import_declaration':
                import_info = self._extract_import_info(node)
                if import_info:
                    self._cache_feature(feature_key, 'import', import_info)
                    mock_tree.add_feature('import', import_info)
                    
            elif node.type == 'function_declaration':
                func_info = self._extract_function_info(node)
                if func_info:
                    self._cache_feature(feature_key, 'function', func_info)
                    mock_tree.add_feature('function', func_info)
                    
            elif node.type == 'class_declaration':
                class_info = self._extract_class_info(node)
                if class_info:
                    self._cache_feature(feature_key, 'class', class_info)
                    mock_tree.add_feature('class', class_info)
                    
            # Process child nodes
            for child in node.children:
                self._extract_features(child, mock_tree)
                
        except Exception as e:
            error = ParserError(str(e), "feature_extraction_error", node)
            self._handle_parser_error(error, 1)
            raise
            
    def _extract_import_info(self, node: Node) -> Optional[Dict[str, Any]]:
        """Extract import information with caching."""
        node_id = f"import_{node.start_point}_{node.end_point}"
        cached_node = self._get_cached_node(node_id)
        if cached_node:
            return self._process_import_node(cached_node)
            
        import_info = self._process_import_node(node)
        if import_info:
            self._cache_node(node_id, node)
        return import_info
        
    def _extract_function_info(self, node: Node) -> Optional[Dict[str, Any]]:
        """Extract function information with caching."""
        node_id = f"function_{node.start_point}_{node.end_point}"
        cached_node = self._get_cached_node(node_id)
        if cached_node:
            return self._process_function_node(cached_node)
            
        func_info = self._process_function_node(node)
        if func_info:
            self._cache_node(node_id, node)
        return func_info
        
    def _extract_class_info(self, node: Node) -> Optional[Dict[str, Any]]:
        """Extract class information with caching."""
        node_id = f"class_{node.start_point}_{node.end_point}"
        cached_node = self._get_cached_node(node_id)
        if cached_node:
            return self._process_class_node(cached_node)
            
        class_info = self._process_class_node(node)
        if class_info:
            self._cache_node(node_id, node)
        return class_info
        
    def _process_import_node(self, node: Node) -> Optional[Dict[str, Any]]:
        """Process an import node and return import information."""
        path = self._get_field_value(node, 'path')
        if not path:
            return None
            
        return {
            'type': 'import',
            'path': path
        }
        
    def _process_function_node(self, node: Node) -> Optional[Dict[str, Any]]:
        """Process a function node and return function information."""
        name = self._get_field_value(node, 'name')
        if not name:
            name = 'anonymous'
            
        # Check for async modifier
        async_node = self._find_child_by_type(node, 'async')
        
        return {
            'name': name,
            'type': 'function',
            'async': bool(async_node)
        }
        
    def _process_class_node(self, node: Node) -> Optional[Dict[str, Any]]:
        """Process a class node and return class information."""
        name = self._get_field_value(node, 'name')
        if not name:
            return None
            
        return {
            'name': name,
            'type': 'class'
        } 