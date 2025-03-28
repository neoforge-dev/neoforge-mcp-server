"""Module for building code relationships."""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

from .parser import CodeParser
from .graph import Graph, Node, Edge, RelationType

logger = logging.getLogger(__name__)

# Constants
IGNORED_NAMES = {'self', 'cls'}

@dataclass
class FileContext:
    """Context for a file being analyzed."""
    path: str
    code: str
    tree: object
    symbols: Dict[str, List[dict]] = field(default_factory=lambda: {
        'imports': [],
        'functions': [],
        'classes': [],
        'variables': []
    })
    references: Dict[str, List[dict]] = field(default_factory=lambda: {
        'imports': [],
        'calls': [],
        'attributes': [],
        'variables': []
    })

class RelationshipBuilder:
    """Builds relationships between code elements."""

    def __init__(self):
        """Initialize the relationship builder."""
        self.parser = CodeParser()
        self.graph = Graph()
        self.file_contexts: Dict[str, FileContext] = {}

    def analyze_file(self, file_path: str, code: Optional[str] = None) -> None:
        """Analyze a file and build relationships.

        Args:
            file_path: Path to the file
            code: Optional code string. If not provided, reads from file_path.
        """
        try:
            if code is None:
                with open(file_path, 'r') as f:
                    code = f.read()

            tree = self.parser.parse(code)
            symbols, references = self.parser.extract_symbols(tree)
            context = FileContext(
                path=file_path,
                code=code,
                tree=tree,
                symbols=symbols,
                references=references
            )
            self.file_contexts[file_path] = context
            self._build_file_relationships(file_path)
        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {str(e)}")
            raise

    def analyze_directory(self, directory: str) -> None:
        """Analyze all Python files in a directory.

        Args:
            directory: Directory path
        """
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

    def _build_file_relationships(self, file_path: str) -> None:
        """Build relationships for a file.

        Args:
            file_path: Path to the file
        """
        try:
            context = self.file_contexts[file_path]
            self._process_imports(context.symbols.get('imports', []))
            self._process_classes(context)
            self._process_functions(context)
            self._process_references(context)
        except Exception as e:
            logger.error(f"Failed to build relationships for {file_path}: {str(e)}")
            raise

    def _process_imports(self, imports: List[Dict[str, Any]]) -> None:
        """Process import statements and create corresponding nodes and edges.
        
        Args:
            imports: List of import information dictionaries
        """
        try:
            # Track modules to avoid duplicates
            processed_modules = set()
            
            for imp in imports:
                module = imp.get('module', '')
                symbol = imp.get('symbol', '')
                
                if not module:
                    continue
                    
                # Create module node if not already processed
                if module not in processed_modules:
                    module_node = self.graph.add_node(
                        name=module,
                        type='module',
                        file_path='',  # External module
                        start_line=imp.get('start_line', 0),
                        end_line=imp.get('end_line', 0)
                    )
                    processed_modules.add(module)
                else:
                    # Find existing module node
                    module_node = None
                    for node in self.graph.nodes.values():
                        if node.name == module and node.type == 'module':
                            module_node = node
                            break
                
                if symbol:
                    # For 'from' imports, create a node for the imported symbol
                    symbol_node = self.graph.add_node(
                        name=symbol,
                        type='import',
                        file_path='',  # External symbol
                        start_line=imp.get('start_line', 0),
                        end_line=imp.get('end_line', 0)
                    )
                    # Create edge from symbol to its module
                    self.graph.add_edge(symbol_node, module_node, type=RelationType.IMPORTS)
                else:
                    # For direct module imports, just create an import edge
                    self.graph.add_edge(module_node, module_node, type=RelationType.IMPORTS)
                    
        except Exception as e:
            logger.error(f"Failed to process imports: {str(e)}")
            raise

    def _process_classes(self, context: FileContext) -> None:
        """Process class definitions and create nodes and edges.
        
        Args:
            context: The context containing class information
        """
        try:
            for class_info in context.symbols.get('classes', []):
                class_name = class_info.get('name', '')
                if not class_name:
                    continue
                    
                # Create class node
                class_node = self.graph.add_node(
                    name=class_name,
                    type='class',
                    file_path=context.path,
                    start_line=class_info.get('start_line', 0),
                    end_line=class_info.get('end_line', 0)
                )
                
                # Process base classes
                for base in class_info.get('bases', []):
                    # Find or create base class node
                    base_node = None
                    for node in self.graph.nodes.values():
                        if node.name == base and node.type == 'class':
                            base_node = node
                            break
                            
                    if not base_node:
                        base_node = self.graph.add_node(
                            name=base,
                            type='class',
                            file_path='',  # External class
                            start_line=0,
                            end_line=0
                        )
                        
                    # Create inheritance edge
                    self.graph.add_edge(class_node, base_node, type=RelationType.INHERITS)
                
                # Process methods
                for method in class_info.get('methods', []):
                    method_name = method.get('name', '')
                    if not method_name:
                        continue
                        
                    # Create method node
                    method_node = self.graph.add_node(
                        name=method_name,
                        type='method',
                        file_path=context.path,
                        start_line=method.get('start_line', 0),
                        end_line=method.get('end_line', 0)
                    )
                    
                    # Create edge from class to method
                    self.graph.add_edge(class_node, method_node, type=RelationType.CONTAINS)
                    
        except Exception as e:
            logger.error(f"Failed to process classes: {str(e)}")
            raise

    def _process_functions(self, context: FileContext) -> None:
        """Process functions and create nodes."""
        for func in context.symbols.get('functions', []):
            name = func.get('name', '')
            if not name:
                continue

            # Create function node
            func_node = self.graph.add_node(
                name=name,
                type='function',
                file_path=context.path,
                start_line=func.get('start_line', 0),
                end_line=func.get('end_line', 0)
            )

            # Process parameters
            for param in func.get('parameters', []):
                param_name = param.get('name', '')
                if not param_name or param_name in ('self', 'cls'):
                    continue

                # Skip type hints
                if param_name.startswith('str') or param_name.startswith('int') or param_name.startswith('float') or param_name.startswith('bool'):
                    continue

                # Remove type hints from parameter names
                if ':' in param_name:
                    param_name = param_name.split(':')[0].strip()

                # Create parameter node
                param_node = self.graph.add_node(
                    name=param_name,
                    type='variable',
                    file_path=context.path,
                    start_line=param.get('start_line', 0),
                    end_line=param.get('end_line', 0)
                )

                # Add edge from function to parameter
                self.graph.add_edge(
                    source=func_node,
                    target=param_node,
                    type=RelationType.CONTAINS
                )

    def _process_references(self, context: FileContext) -> None:
        """Process references and create nodes and edges.
        
        Args:
            context: The context containing reference information
        """
        try:
            # Track processed references to avoid duplicates
            processed_refs = set()
            
            # Process function calls
            for call in context.references.get('calls', []):
                callee_name = call.get('name', '')
                if not callee_name or callee_name in processed_refs:
                    continue
                    
                processed_refs.add(callee_name)
                
                # Find or create callee node
                callee_node = None
                for node in self.graph.nodes.values():
                    if node.name == callee_name and node.type in ('function', 'method', 'import'):
                        callee_node = node
                        break
                        
                if not callee_node:
                    # Check if it's an imported function
                    for imp in context.symbols.get('imports', []):
                        if imp.get('symbol') == callee_name:
                            callee_node = self.graph.add_node(
                                name=callee_name,
                                type='import',
                                file_path=context.path,
                                start_line=call.get('start_line', 0),
                                end_line=call.get('end_line', 0)
                            )
                            break
                            
                    if not callee_node:
                        callee_node = self.graph.add_node(
                            name=callee_name,
                            type='function',
                            file_path=context.path,
                            start_line=call.get('start_line', 0),
                            end_line=call.get('end_line', 0)
                        )
                
                # Find caller node (function or method containing this call)
                caller_node = None
                for node in self.graph.nodes.values():
                    if (node.type in ('function', 'method') and
                        node.file_path == context.path and
                        node.start_line <= call.get('start_line', 0) <= node.end_line):
                        caller_node = node
                        break
                        
                if caller_node:
                    # Add call edge
                    self.graph.add_edge(caller_node, callee_node, type=RelationType.CALLS)
            
            # Process variable references
            for ref in context.references.get('variables', []):
                var_name = ref.get('name', '')
                if not var_name or var_name in processed_refs:
                    continue
                    
                processed_refs.add(var_name)
                
                # Skip if this is a function or import
                is_special = False
                for node in self.graph.nodes.values():
                    if node.name == var_name and node.type in ('function', 'method', 'import', 'class'):
                        is_special = True
                        break
                        
                if is_special:
                    continue
                
                # Find scope node (function or method containing this reference)
                scope_node = None
                for node in self.graph.nodes.values():
                    if (node.type in ('function', 'method') and
                        node.file_path == context.path and
                        node.start_line <= ref.get('start_line', 0) <= node.end_line):
                        scope_node = node
                        break
                        
                if scope_node:
                    # Find or create variable node
                    var_node = None
                    for node in self.graph.nodes.values():
                        if node.name == var_name and node.type == 'variable':
                            var_node = node
                            break
                            
                    if not var_node:
                        var_node = self.graph.add_node(
                            name=var_name,
                            type='variable',
                            file_path=context.path,
                            start_line=ref.get('start_line', 0),
                            end_line=ref.get('end_line', 0)
                        )
                    
                    # Add reference edge
                    self.graph.add_edge(scope_node, var_node, type=RelationType.REFERENCES)
                    
        except Exception as e:
            logger.error(f"Failed to process references: {str(e)}")
            raise