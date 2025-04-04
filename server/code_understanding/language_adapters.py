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

class JavaScriptParserAdapter:
    """Adapter for JavaScript language support."""

    def __init__(self):
        """Initialize the JavaScript parser adapter."""
        self.parser = Parser()
        self.language = None
        self._init_language()

    def _init_language(self):
        """Initialize the JavaScript language."""
        try:
            if os.path.exists(JAVASCRIPT_LANGUAGE_PATH):
                self.language = Language(JAVASCRIPT_LANGUAGE_PATH, 'javascript')
                self.parser.set_language(self.language)
                logger.info("JavaScript language initialized successfully")
            else:
                logger.error(f"JavaScript language file not found at {JAVASCRIPT_LANGUAGE_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize JavaScript language: {e}")

    def parse(self, code: str) -> MockTree:
        """Parse JavaScript code and return a MockTree.

        Args:
            code: JavaScript source code

        Returns:
            MockTree: A unified abstract syntax tree representation
        """
        if not code.strip():
            raise ValueError("Empty code string")

        try:
            # Parse with tree-sitter
            tree = self.parser.parse(bytes(code, 'utf8'))
            
            # Convert to MockTree
            mock_root = self._tree_sitter_to_mock_node(tree.root_node)
            mock_tree = MockTree(root_node=mock_root)

            # Extract features
            self._extract_features(mock_tree, code)

            return mock_tree
        except Exception as e:
            logger.error(f"Failed to parse JavaScript code: {e}")
            raise

    def _tree_sitter_to_mock_node(self, node: Node) -> MockNode:
        """Convert a tree-sitter node to a MockNode.

        Args:
            node: Tree-sitter Node

        Returns:
            MockNode: Converted node
        """
        if not node:
            return None

        # Get text, handling bytes vs string
        text = node.text.decode('utf8') if isinstance(node.text, bytes) else str(node.text)

        # Create MockNode
        mock_node = MockNode(
            type=node.type,
            text=text,
            start_point=node.start_point,
            end_point=node.end_point,
            children=[],
            fields={}
        )

        # Convert children
        for child in node.children:
            child_mock = self._tree_sitter_to_mock_node(child)
            if child_mock:
                mock_node.children.append(child_mock)
                child_mock.parent = mock_node

        # Convert named fields
        for field_name, field_value in node.children_by_field_name().items():
            if isinstance(field_value, list):
                mock_node.fields[field_name] = [
                    self._tree_sitter_to_mock_node(v) for v in field_value
                ]
            else:
                mock_node.fields[field_name] = self._tree_sitter_to_mock_node(field_value)

        return mock_node

    def _extract_features(self, tree: MockTree, code: str) -> None:
        """Extract features from the tree.

        Args:
            tree: MockTree to extract features from
            code: Original source code
        """
        # Initialize feature lists
        tree.features = {
            'functions': [],
            'classes': [],
            'variables': [],
            'imports': [],
            'exports': []
        }

        # Process each node type
        for node in tree.walk():
            if node.type == 'function_declaration':
                name_node = node.child_by_field_name('name')
                if name_node:
                    tree.add_feature('functions', {
                        'name': name_node.text,
                        'start_line': node.start_point[0],
                        'end_line': node.end_point[0]
                    })
            elif node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                if name_node:
                    tree.add_feature('classes', {
                        'name': name_node.text,
                        'start_line': node.start_point[0],
                        'end_line': node.end_point[0]
                    })
            elif node.type == 'variable_declaration':
                for child in node.children:
                    if child.type == 'variable_declarator':
                        name_node = child.child_by_field_name('name')
                        if name_node:
                            tree.add_feature('variables', {
                                'name': name_node.text,
                                'start_line': node.start_point[0],
                                'end_line': node.end_point[0]
                            })
            elif node.type == 'import_statement':
                tree.add_feature('imports', {
                    'source': node.text,
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0]
                })
            elif node.type == 'export_statement':
                tree.add_feature('exports', {
                    'source': node.text,
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0]
                })

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