"""Module for building code relationships."""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import ast

from .parser import CodeParser
from .extractor import SymbolExtractor
from .graph import Graph, Node, NodeType, RelationType

logger = logging.getLogger(__name__)

# Constants
IGNORED_NAMES = {'self', 'cls'}

@dataclass
class FileContext:
    """Context for a file being analyzed."""

    def __init__(self, path: str, code: Optional[str] = None, tree: Optional[Any] = None, symbols: Optional[Dict[str, Any]] = None, references: Optional[Dict[str, Any]] = None) -> None:
        """Initialize file context.

        Args:
            path: Path to the file
            code: Original code string
            tree: AST tree
            symbols: Dictionary of symbols extracted from the file
            references: Dictionary of references extracted from the file
        """
        self.path = path
        self.code = code
        self.tree = tree
        self.symbols = symbols or {
            'imports': [],
            'functions': [],
            'classes': [],
            'variables': []
        }
        self.references = references or {
            'imports': [],
            'calls': [],
            'attributes': [],
            'variables': []
        }

class RelationshipBuilder:
    """Builder for creating relationship graphs from code."""

    def __init__(self):
        """Initialize the relationship builder."""
        self.graph = Graph()
        self.file_contexts = {}
        self.ignored_names = {'self', 'cls', 'super', 'object', 'type', 'None', 'True', 'False'}
        self.extractor = SymbolExtractor()
        self.parser = CodeParser()

    def analyze_file(self, file_path: str, code: Optional[str] = None) -> FileContext:
        """Analyze a file and extract relationships.

        Args:
            file_path: Path to the file to analyze
            code: Optional code string. If not provided, will read from file_path

        Returns:
            FileContext containing the analysis results

        Raises:
            ValueError: If file_path is empty or code cannot be parsed
            FileNotFoundError: If file does not exist and no code is provided
            Exception: For any other errors during analysis
        """
        if not file_path:
            raise ValueError("file_path cannot be empty")

        try:
            if code is None:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")
                with open(file_path, 'r') as f:
                    code = f.read()

            if not code:
                raise ValueError("Code cannot be empty")

            tree = ast.parse(code)
            context = FileContext(path=file_path, code=code, tree=tree)
            
            # Create a node for the current file
            self.current_file_node = self.graph.find_or_create_node(
                name=file_path,
                type=NodeType.MODULE,
                properties={
                    'file_path': file_path
                }
            )

            # Extract symbols and references
            extractor = SymbolExtractor()
            symbols, _ = extractor.extract_symbols(tree)
            context.symbols = symbols
            context.references = extractor.extract_references(tree)

            # Process the extracted information
            self._process_imports(context.symbols.get('imports', []))
            self._process_functions(context)
            self._process_classes(context)
            self._process_references(context)

            return context

        except (SyntaxError, IndentationError) as e:
            raise ValueError(f"Failed to parse code: {str(e)}")
        except Exception as e:
            raise Exception(f"Error analyzing file {file_path}: {str(e)}")

    def analyze_directory(self, directory: str) -> None:
        """Analyze all Python files in a directory.

        Args:
            directory: Directory path

        Raises:
            FileNotFoundError: If the directory doesn't exist
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory not found: {directory}")

        try:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        self.analyze_file(file_path)
        except Exception as e:
            logger.error(f"Failed to analyze directory {directory}: {str(e)}")
            raise

    def get_relationships(self) -> Graph:
        """Get the relationship graph.

        Returns:
            Graph object containing relationships
        """
        return self.graph

    def clear(self) -> None:
        """Clear all analysis data."""
        self.graph.clear()
        self.file_contexts.clear()

    def _build_file_relationships(self, context: FileContext) -> None:
        """Build relationships for a file.

        Args:
            context: The file context to process
        """
        try:
            # Process imports
            self._process_imports(context.symbols.get('imports', []))

            # Process classes
            self._process_classes(context)

            # Process functions
            self._process_functions(context)

            # Process references
            self._process_references(context)
        except Exception as e:
            logger.error(f"Failed to build relationships for {context}: {str(e)}")
            raise

    def _process_imports(self, imports: List[dict]) -> None:
        """Process imports and create corresponding nodes and edges.

        Args:
            imports: List of import dictionaries, each containing 'module' and optionally 'symbol' keys
        """
        if not isinstance(imports, list):
            raise ValueError("imports must be a list")

        for import_info in imports:
            if not isinstance(import_info, dict) or 'module' not in import_info:
                raise ValueError("Each import must be a dictionary with a 'module' key")

            module_name = import_info['module']
            module_node = self.graph.find_or_create_node(
                name=module_name,
                type=NodeType.MODULE,
                properties={
                    'start_line': import_info.get('start_line'),
                    'end_line': import_info.get('end_line')
                }
            )

            # Always create an edge from the current file to the module
            self.graph.create_edge(
                from_node=self.current_file_node,
                to_node=module_node,
                type=RelationType.IMPORTS,
                properties={
                    'line': import_info.get('start_line')
                }
            )

            # If a symbol is specified, create a symbol node and edges
            if 'symbol' in import_info and import_info['symbol']:
                symbol_name = import_info['symbol']
                symbol_node = self.graph.find_or_create_node(
                    name=symbol_name,
                    type=NodeType.SYMBOL,
                    properties={
                        'start_line': import_info.get('start_line'),
                        'end_line': import_info.get('end_line')
                    }
                )

                # Create an edge from the module to the symbol
                self.graph.create_edge(
                    from_node=module_node,
                    to_node=symbol_node,
                    type=RelationType.CONTAINS,
                    properties={
                        'line': import_info.get('start_line')
                    }
                )

                # Create an edge from the current file to the symbol
                self.graph.create_edge(
                    from_node=self.current_file_node,
                    to_node=symbol_node,
                    type=RelationType.IMPORTS,
                    properties={
                        'line': import_info.get('start_line')
                    }
                )

    def _process_classes(self, context: FileContext) -> None:
        """Process class definitions and create nodes and edges.

        Args:
            context: FileContext containing the class definitions to process.

        Raises:
            ValueError: If context is not a FileContext or if classes are invalid.
        """
        if not isinstance(context, FileContext):
            raise ValueError("Context must be a FileContext")

        classes = context.symbols.get('classes', [])
        if not isinstance(classes, list):
            raise ValueError("Classes must be a list")

        for class_info in classes:
            if not isinstance(class_info, dict) or 'name' not in class_info:
                raise ValueError("Each class must be a dictionary with a 'name' key")

            class_name = class_info['name']
            class_node = self.graph.find_or_create_node(
                name=class_name,
                type=NodeType.CLASS,
                properties={
                    'file_path': context.path,
                    'start_line': class_info.get('start_line'),
                    'end_line': class_info.get('end_line')
                }
            )

            # Create edge from file to class
            self.graph.create_edge(
                from_node=self.current_file_node,
                to_node=class_node,
                type=RelationType.CONTAINS,
                properties={
                    'line': class_info.get('start_line')
                }
            )

            # Process inheritance
            bases = class_info.get('bases', [])
            for base_name in bases:
                base_node = self.graph.find_or_create_node(
                    name=base_name,
                    type=NodeType.CLASS,
                    properties={
                        'file_path': context.path
                    }
                )
                self.graph.create_edge(
                    from_node=class_node,
                    to_node=base_node,
                    type=RelationType.INHERITS,
                    properties={
                        'line': class_info.get('start_line')
                    }
                )

            # Process methods
            methods = class_info.get('methods', [])
            for method_info in methods:
                if not isinstance(method_info, dict) or 'name' not in method_info:
                    raise ValueError("Each method must be a dictionary with a 'name' key")

                method_name = method_info['name']
                method_node = self.graph.find_or_create_node(
                    name=method_name,
                    type=NodeType.METHOD,
                    properties={
                        'file_path': context.path,
                        'start_line': method_info.get('start_line'),
                        'end_line': method_info.get('end_line')
                    }
                )

                # Create edge from class to method
                self.graph.create_edge(
                    from_node=class_node,
                    to_node=method_node,
                    type=RelationType.CONTAINS,
                    properties={
                        'line': method_info.get('start_line')
                    }
                )

    def _process_functions(self, context: FileContext) -> None:
        """Process functions in a file.

        Args:
            context: FileContext containing the functions to process
        """
        if not isinstance(context, FileContext):
            raise ValueError("context must be a FileContext instance")

        functions = context.symbols.get('functions', [])
        if not isinstance(functions, list):
            raise ValueError("functions must be a list")

        for func in functions:
            if not isinstance(func, dict) or 'name' not in func:
                raise ValueError("Each function must be a dictionary with a 'name' key")

            # Create function node
            func_node = self.graph.find_or_create_node(
                name=func['name'],
                type=NodeType.FUNCTION,
                properties={
                    'file_path': context.path,
                    'start_line': func.get('start_line'),
                    'end_line': func.get('end_line')
                }
            )

            # Process parameters
            for param in func.get('parameters', []):
                if not isinstance(param, dict) or 'name' not in param:
                    continue

                # Create parameter node
                param_node = self.graph.find_or_create_node(
                    name=param['name'],
                    type=NodeType.PARAMETER,
                    properties={
                        'file_path': context.path,
                        'start_line': param.get('start_line'),
                        'end_line': param.get('end_line')
                    }
                )

                # Create edge from function to parameter
                self.graph.create_edge(
                    from_node=func_node,
                    to_node=param_node,
                    type=RelationType.CONTAINS,
                    properties={
                        'line': param.get('start_line')
                    }
                )

    def _process_references(self, context: FileContext) -> None:
        """Process references in a file.

        Args:
            context: FileContext containing the references to process
        """
        if not isinstance(context, FileContext):
            raise ValueError("context must be a FileContext instance")

        if not context.references:
            return

        # Process function calls
        for call in context.references.get('calls', []):
            if not isinstance(call, dict) or 'name' not in call or 'scope' not in call:
                raise ValueError("Invalid function call format")

            # Find or create caller node (scope)
            caller_node = self.graph.find_or_create_node(
                name=call['scope'],
                type=NodeType.FUNCTION,
                properties={
                    'file_path': context.path,
                    'start_line': call.get('start_line'),
                    'end_line': call.get('end_line')
                }
            )

            # Find or create called function node
            called_node = self.graph.find_or_create_node(
                name=call['name'],
                type=NodeType.FUNCTION,
                properties={
                    'file_path': call.get('file_path', context.path),
                    'start_line': call.get('start_line'),
                    'end_line': call.get('end_line')
                }
            )

            # Create edge for the function call
            self.graph.create_edge(
                from_node=caller_node,
                to_node=called_node,
                type=RelationType.CALLS,
                properties={
                    'line': call.get('start_line')
                }
            )

        # Process attribute references
        for attr in context.references.get('attributes', []):
            if not isinstance(attr, dict) or 'name' not in attr or 'scope' not in attr:
                raise ValueError("Invalid attribute reference format")

            # Find or create scope node
            scope_node = self.graph.find_or_create_node(
                name=attr['scope'],
                type=NodeType.CLASS if attr.get('is_class', False) else NodeType.FUNCTION,
                properties={
                    'file_path': context.path,
                    'start_line': attr.get('start_line'),
                    'end_line': attr.get('end_line')
                }
            )

            # Find or create attribute node
            attr_node = self.graph.find_or_create_node(
                name=attr['name'],
                type=NodeType.ATTRIBUTE,
                properties={
                    'file_path': attr.get('file_path', context.path),
                    'start_line': attr.get('start_line'),
                    'end_line': attr.get('end_line')
                }
            )

            # Create edge for the attribute reference
            self.graph.create_edge(
                from_node=scope_node,
                to_node=attr_node,
                type=RelationType.REFERENCES,
                properties={
                    'line': attr.get('start_line')
                }
            )