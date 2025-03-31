"""Module for building code relationships."""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Union
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
    """Builds relationship graphs from code analysis results."""

    def __init__(self):
        """Initialize the relationship builder."""
        self.graph = Graph()
        self.current_file_node = None
        self.parser = None
        self.file_contexts = {}
        self.ignored_names = {'self', 'cls', 'super', 'object', 'type', 'None', 'True', 'False'}
        self.extractor = SymbolExtractor()

    def analyze_file(self, file_path: str, code: Optional[str] = None) -> None:
        """Analyze a single file and build its relationships.

        Args:
            file_path: Path to the file to analyze
            code: Optional code string to analyze instead of reading from file
        """
        try:
            # Read code from file if not provided
            if code is None:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")
                with open(file_path, 'r') as f:
                    code = f.read()

            # Parse the code
            tree = self.parser.parse(code)
            if not tree:
                return

            # Extract symbols
            symbols, references = self.parser.extract_symbols(tree)

            # Create file context
            context = FileContext(
                path=file_path,
                code=code,
                tree=tree,
                symbols=symbols
            )

            # Store file context
            self.file_contexts[file_path] = context

            # Create file node
            file_node = self.graph.find_or_create_node(
                name=file_path,
                type=NodeType.MODULE,
                properties={'file_path': file_path}
            )

            # Set current file node
            self.current_file_node = file_node

            # Process relationships
            self._process_imports(context)
            self._process_classes(context)
            self._process_functions(context)
            self._process_references(context, references)

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            raise

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

    def _process_imports(self, context: Union[FileContext, List[Dict[str, Any]]]) -> None:
        """Process import statements.

        Args:
            context: Either a FileContext or a list of import information dictionaries
        """
        if isinstance(context, FileContext):
            if not context.symbols or 'imports' not in context.symbols:
                return
            imports = context.symbols['imports']
        else:
            imports = context

        if not isinstance(imports, list) or not imports:
            return

        for imp in imports:
            if not isinstance(imp, dict):
                continue

            # Create module node
            module = imp.get('module')
            if not module:
                continue

            module_node = self.graph.find_or_create_node(
                name=module,
                type=NodeType.MODULE,
                properties={
                    'file_path': module,
                    'start_line': imp.get('start_line', 0),
                    'end_line': imp.get('end_line', 0)
                }
            )

            # Add edge from current file to module
            if self.current_file_node:
                self.graph.create_edge(
                    from_node=self.current_file_node,
                    to_node=module_node,
                    type=RelationType.IMPORTS,
                    properties={
                        'start_line': imp.get('start_line', 0),
                        'end_line': imp.get('end_line', 0)
                    }
                )

            # Process imported symbols
            if 'symbol' in imp:
                symbol = imp['symbol']
                alias = imp.get('alias', symbol)
                symbol_node = self.graph.find_or_create_node(
                    name=f"{module}:{symbol}",
                    type=NodeType.SYMBOL,
                    properties={
                        'file_path': module,
                        'start_line': imp.get('start_line', 0),
                        'end_line': imp.get('end_line', 0)
                    }
                )

                # Add edge from module to symbol
                self.graph.create_edge(
                    from_node=module_node,
                    to_node=symbol_node,
                    type=RelationType.CONTAINS,
                    properties={
                        'start_line': imp.get('start_line', 0),
                        'end_line': imp.get('end_line', 0)
                    }
                )

                # Add edge from current file to symbol
                if self.current_file_node:
                    self.graph.create_edge(
                        from_node=self.current_file_node,
                        to_node=symbol_node,
                        type=RelationType.IMPORTS,
                        properties={
                            'start_line': imp.get('start_line', 0),
                            'end_line': imp.get('end_line', 0),
                            'alias': alias
                        }
                    )

    def _process_classes(self, context: FileContext) -> None:
        """Process class definitions.

        Args:
            context: FileContext containing class information
        """
        if not context.symbols or 'classes' not in context.symbols:
            return

        for class_info in context.symbols['classes']:
            if not isinstance(class_info, dict) or 'name' not in class_info:
                logger.debug(f"Invalid class info in {context.path}: {class_info}")
                continue

            logger.debug(f"Processing class {class_info['name']} in {context.path}")

            # Create class node
            class_node = self.graph.find_or_create_node(
                name=f"{context.path}:{class_info['name']}",
                type=NodeType.CLASS,
                properties={
                    'file_path': context.path,
                    'start_line': class_info.get('start_line', 0),
                    'end_line': class_info.get('end_line', 0)
                }
            )

            # Create contains edge from file to class
            if self.current_file_node:
                self.graph.create_edge(
                    from_node=self.current_file_node,
                    to_node=class_node,
                    type=RelationType.CONTAINS,
                    properties={
                        'start_line': class_info.get('start_line', 0),
                        'end_line': class_info.get('end_line', 0)
                    }
                )

            # Process inheritance
            if 'bases' in class_info and isinstance(class_info['bases'], list):
                for base_name in class_info['bases']:
                    # First try to find the base class in the same file
                    base_node = self.graph.find_node(f"{context.path}:{base_name}")
                    if not base_node:
                        # If not found, try to find it in any file
                        base_nodes = self.graph.get_nodes_by_type(NodeType.CLASS.value)
                        for node in base_nodes:
                            if node.name.endswith(f":{base_name}"):
                                base_node = node
                                break

                    if base_node:
                        self.graph.create_edge(
                            from_node=class_node,
                            to_node=base_node,
                            type=RelationType.INHERITS,
                            properties={
                                'start_line': class_info.get('start_line', 0),
                                'end_line': class_info.get('end_line', 0)
                            }
                        )

            # Process methods
            if 'methods' in class_info and isinstance(class_info['methods'], list):
                for method_info in class_info['methods']:
                    if not isinstance(method_info, dict) or 'name' not in method_info:
                        continue

                    method_node = self.graph.find_or_create_node(
                        name=f"{context.path}:{class_info['name']}.{method_info['name']}",
                        type=NodeType.METHOD,
                        properties={
                            'file_path': context.path,
                            'start_line': method_info.get('start_line', 0),
                            'end_line': method_info.get('end_line', 0)
                        }
                    )

                    self.graph.create_edge(
                        from_node=class_node,
                        to_node=method_node,
                        type=RelationType.CONTAINS,
                        properties={
                            'start_line': method_info.get('start_line', 0),
                            'end_line': method_info.get('end_line', 0)
                        }
                    )

    def _process_inheritance(self, context: FileContext) -> None:
        """Process class inheritance relationships.

        Args:
            context: The file context to process
        """
        if not context.symbols or 'classes' not in context.symbols:
            return

        for class_info in context.symbols['classes']:
            if not isinstance(class_info, dict) or 'name' not in class_info:
                continue

            class_name = class_info['name']
            bases = class_info.get('bases', [])

            # Process each base class
            for base in bases:
                if not isinstance(base, str):
                    continue

                # Try to find the base class in the current file first
                base_file = context.path
                base_node = self.graph.find_node(f"{base_file}:{base}")

                # If not found in current file, try to find it in imported modules
                if not base_node and 'imports' in context.symbols:
                    for imp in context.symbols['imports']:
                        if imp.get('type') == 'import' and imp.get('module'):
                            module = imp['module']
                            # Try to find the base class in the imported module
                            base_node = self.graph.find_node(f"{module}:{base}")
                            if base_node:
                                base_file = module
                                break

                if base_node:
                    # Create inheritance edge
                    class_node = self.graph.find_node(f"{context.path}:{class_name}")
                    if class_node:
                        self.graph.create_edge(
                            from_node=class_node,
                            to_node=base_node,
                            type=RelationType.INHERITS,
                            properties={
                                'file_path': context.path,
                                'start_line': class_info.get('start_line', 0),
                                'end_line': class_info.get('end_line', 0)
                            }
                        )

    def _process_functions(self, context: FileContext) -> None:
        """Process function definitions.

        Args:
            context: FileContext containing function information
        """
        if not context.symbols or 'functions' not in context.symbols:
            return

        for func_info in context.symbols['functions']:
            if not isinstance(func_info, dict) or 'name' not in func_info:
                logger.debug(f"Invalid function info in {context.path}: {func_info}")
                continue

            logger.debug(f"Processing function {func_info['name']} in {context.path}")

            # Create function node
            func_node = self.graph.find_or_create_node(
                name=f"{context.path}:{func_info['name']}",
                type=NodeType.FUNCTION,
                properties={
                    'file_path': context.path,
                    'start_line': func_info.get('start_line', 0),
                    'end_line': func_info.get('end_line', 0)
                }
            )

            # Create contains edge from file to function
            if self.current_file_node:
                self.graph.create_edge(
                    from_node=self.current_file_node,
                    to_node=func_node,
                    type=RelationType.CONTAINS,
                    properties={
                        'start_line': func_info.get('start_line', 0),
                        'end_line': func_info.get('end_line', 0)
                    }
                )

            # Process function parameters
            if 'parameters' in func_info and isinstance(func_info['parameters'], list):
                for param_info in func_info['parameters']:
                    if not isinstance(param_info, dict) or 'name' not in param_info:
                        continue

                    # Create parameter node
                    param_node = self.graph.find_or_create_node(
                        name=f"{context.path}:{func_info['name']}.{param_info['name']}",
                        type=NodeType.PARAMETER,
                        properties={
                            'file_path': context.path,
                            'start_line': param_info.get('start_line', 0),
                            'end_line': param_info.get('end_line', 0)
                        }
                    )

                    # Create contains edge from function to parameter
                    self.graph.create_edge(
                        from_node=func_node,
                        to_node=param_node,
                        type=RelationType.CONTAINS,
                        properties={
                            'start_line': param_info.get('start_line', 0),
                            'end_line': param_info.get('end_line', 0)
                        }
                    )

    def _process_references(self, context: Union[FileContext, List[Dict[str, Any]]], references: Optional[List[Dict[str, Any]]] = None) -> None:
        """Process code references.

        Args:
            context: Either a FileContext or a list of reference information dictionaries
            references: Optional list of references if context is a FileContext
        """
        if isinstance(context, FileContext):
            if not references:
                return
            refs = references
            file_path = context.path
        else:
            refs = context
            if not self.current_file_node:
                return
            file_path = self.current_file_node.properties['file_path']

        if not isinstance(refs, list) or not refs:
            return

        # Process function calls and attributes
        for ref in refs:
            if not isinstance(ref, dict) or 'type' not in ref:
                continue

            if ref['type'] == 'call':
                if 'name' not in ref or 'scope' not in ref:
                    continue

                # Find the calling function/method
                scope_name = ref['scope']
                caller_node = self.graph.find_node(f"{file_path}:{scope_name}")
                if not caller_node:
                    continue

                # Find or create the called function/method
                called_name = ref['name']
                called_node = None

                # First try to find the function in the same file
                called_node = self.graph.find_node(f"{file_path}:{called_name}")

                # If not found, look for it in imported modules
                if not called_node and isinstance(context, FileContext):
                    for imp in context.symbols.get('imports', []):
                        if 'symbol' in imp and imp['symbol'] == called_name:
                            module = imp['module']
                            # Try to find the function in the imported module
                            called_node = self.graph.find_node(f"{module}:{called_name}")
                            if called_node:
                                break

                # If still not found, look for it in any file
                if not called_node:
                    # Search for the function in any file
                    function_nodes = self.graph.get_nodes_by_type(NodeType.FUNCTION.value)
                    for node in function_nodes:
                        if node.name.endswith(f":{called_name}"):
                            called_node = node
                            break

                # If still not found, create a new node
                if not called_node:
                    called_node = self.graph.find_or_create_node(
                        name=f"{file_path}:{called_name}",
                        type=NodeType.FUNCTION,
                        properties={'file_path': file_path}
                    )

                # Create call edge
                self.graph.create_edge(
                    from_node=caller_node,
                    to_node=called_node,
                    type=RelationType.CALLS,
                    properties={
                        'start_line': ref.get('start_line', 0),
                        'end_line': ref.get('end_line', 0)
                    }
                )

            elif ref['type'] == 'attribute':
                if 'name' not in ref or 'scope' not in ref:
                    continue

                # Find the class/method that owns the attribute
                scope_name = ref['scope']
                scope_node = self.graph.find_node(f"{file_path}:{scope_name}")
                if not scope_node:
                    continue

                # Create attribute node
                attr_name = ref['name']
                attr_node = self.graph.find_or_create_node(
                    name=f"{file_path}:{scope_name}.{attr_name}",
                    type=NodeType.ATTRIBUTE,
                    properties={
                        'file_path': file_path,
                        'start_line': ref.get('start_line', 0),
                        'end_line': ref.get('end_line', 0)
                    }
                )

                # Create attribute edge
                self.graph.create_edge(
                    from_node=scope_node,
                    to_node=attr_node,
                    type=RelationType.HAS_ATTRIBUTE,
                    properties={
                        'start_line': ref.get('start_line', 0),
                        'end_line': ref.get('end_line', 0)
                    }
                )