"""Module for analyzing Python code."""

import ast
import logging
from typing import Dict, List, Optional, Set, Any, Union

from .parser import CodeParser, MockNode, MockTree

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """Analyzer for Python code."""

    def __init__(self):
        """Initialize the analyzer."""
        self.parser = CodeParser()

    def analyze_code(self, code: str) -> Dict[str, Any]:
        """Analyze Python code.

        Args:
            code: Python source code

        Returns:
            Dictionary with analysis results
        """
        try:
            tree = self.parser.parse(code)
            return self.analyze_tree(tree)
        except Exception as e:
            logger.error(f"Failed to analyze code: {e}")
            return {
                'imports': [],
                'functions': [],
                'classes': [],
                'variables': []
            }

    def analyze_tree(self, tree: Union[Any, MockTree]) -> Dict[str, Any]:
        """Analyze a syntax tree and return a structured dictionary.
        
        Args:
            tree: Syntax tree to analyze
            
        Returns:
            Dict containing analysis results
        """
        try:
            root = tree.root_node
            imports = []
            functions = []
            classes = []
            variables = []
            
            def process_node(node):
                """Process a single node."""
                if not node:
                    return
                    
                if node.type == 'import_statement' or node.type == 'import':
                    # Handle simple imports
                    if node.text.startswith('import '):
                        modules = node.text[7:].split(',')  # Skip 'import ' and split on comma
                        for module in modules:
                            module = module.strip()
                            # Handle aliases
                            if ' as ' in module:
                                module, alias = module.split(' as ')
                                module = module.strip()
                                alias = alias.strip()
                                imports.append({
                                    'module': module,
                                    'alias': alias,
                                    'start_line': node.start_point[0] + 1,
                                    'end_line': node.end_point[0] + 1
                                })
                            else:
                                imports.append({
                                    'module': module,
                                    'start_line': node.start_point[0] + 1,
                                    'end_line': node.end_point[0] + 1
                                })
                    # Handle from imports
                    elif node.text.startswith('from '):
                        parts = node.text.split(' import ')
                        if len(parts) == 2:
                            module = parts[0][5:].strip()  # Skip 'from '
                            names = [n.strip() for n in parts[1].split(',')]
                            for name in names:
                                # Handle aliases
                                if ' as ' in name:
                                    name, alias = name.split(' as ')
                                    name = name.strip()
                                    alias = alias.strip()
                                    imports.append({
                                        'module': module,
                                        'symbol': name,
                                        'alias': alias,
                                        'start_line': node.start_point[0] + 1,
                                        'end_line': node.end_point[0] + 1
                                    })
                                else:
                                    imports.append({
                                        'module': module,
                                        'symbol': name,
                                        'start_line': node.start_point[0] + 1,
                                        'end_line': node.end_point[0] + 1
                                    })
                                    
                elif node.type == 'function_definition':
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        function_info = {
                            'name': name_node.text,
                            'start_line': node.start_point[0] + 1,
                            'end_line': node.end_point[0] + 1,
                            'parameters': []
                        }
                        
                        # Process parameters
                        params_node = node.child_by_field_name('parameters')
                        if params_node:
                            for param in params_node.children:
                                if param.type == 'identifier':
                                    function_info['parameters'].append({
                                        'name': param.text,
                                        'start_line': param.start_point[0] + 1,
                                        'end_line': param.end_point[0] + 1
                                    })
                                    
                        functions.append(function_info)
                        
                elif node.type == 'class_definition':
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        class_info = {
                            'name': name_node.text,
                            'start_line': node.start_point[0] + 1,
                            'end_line': node.end_point[0] + 1,
                            'bases': [],
                            'methods': []
                        }
                        
                        # Process base classes
                        bases_node = node.child_by_field_name('bases')
                        if bases_node:
                            for base in bases_node.children:
                                if base.type == 'identifier':
                                    class_info['bases'].append(base.text)
                                    
                        # Process methods
                        body_node = node.child_by_field_name('body')
                        if body_node:
                            for method in body_node.children:
                                if method.type == 'function_definition':
                                    method_name = method.child_by_field_name('name')
                                    if method_name:
                                        class_info['methods'].append({
                                            'name': method_name.text,
                                            'start_line': method.start_point[0] + 1,
                                            'end_line': method.end_point[0] + 1
                                        })
                                        
                        classes.append(class_info)
                        
                elif node.type == 'assignment':
                    # Handle chained assignments
                    left = node.child_by_field_name('left')
                    right = node.child_by_field_name('right')
                    if left and right:
                        if isinstance(left, list):
                            # Handle tuple unpacking
                            for l in left:
                                if l.type == 'identifier':
                                    variables.append({
                                        'name': l.text,
                                        'start_line': node.start_point[0] + 1,
                                        'end_line': node.end_point[0] + 1,
                                        'type': self._infer_type(right)
                                    })
                        else:
                            variables.append({
                                'name': left.text,
                                'start_line': node.start_point[0] + 1,
                                'end_line': node.end_point[0] + 1,
                                'type': self._infer_type(right)
                            })

            for node in root.children_by_field_name('body'):
                if isinstance(node, list):
                    # Handle lists of nodes (e.g., multiple imports from one line)
                    for n in node:
                        process_node(n)
                else:
                    process_node(node)

            return {
                'imports': imports,
                'functions': functions,
                'classes': classes,
                'variables': variables
            }
        except Exception as e:
            logger.error(f"Failed to analyze tree: {e}")
            return {
                'imports': [],
                'functions': [],
                'classes': [],
                'variables': []
            }

    def _extract_function(self, node: Any) -> Dict[str, Any]:
        """Extract function information from a node."""
        if node is None:
            return {
                'name': '',
                'start_line': 0,
                'end_line': 0,
                'parameters': [],
                'decorators': [],
                'is_async': False
            }

        # Check for decorators
        decorators = []
        for child in node.children:
            if child and child.type == 'decorator':
                decorators.append(child.text)

        # Get function name and parameters
        name = node.text if node and node.text else ''
        parameters = self._extract_parameters(node)

        # Check if it's an async function
        is_async = any(child and child.type == 'async' for child in node.children)

        return {
            'name': name,
            'start_line': node.start_point[0] + 1 if node else 0,
            'end_line': node.end_point[0] + 1 if node else 0,
            'parameters': parameters,
            'decorators': decorators,
            'is_async': is_async
        }

    def _extract_class(self, node: Any) -> Dict[str, Any]:
        """Extract class information from a node."""
        if node is None:
            return {
                'name': '',
                'start_line': 0,
                'end_line': 0,
                'methods': [],
                'bases': []
            }

        # Get class name
        name_node = node.child_by_field_name('name')
        name = name_node.text if name_node else ''

        # Get base classes
        bases = []
        bases_node = node.child_by_field_name('bases')
        if bases_node:
            for base in bases_node.children:
                if base is None:
                    continue

                if base.type == 'identifier':
                    # Simple base class
                    bases.append(base.text)
                elif base.type == 'keyword_argument':
                    # Handle metaclass argument
                    name_node = base.child_by_field_name('name')
                    value_node = base.child_by_field_name('value')
                    if name_node and name_node.text == 'metaclass' and value_node:
                        bases.append(f'metaclass={value_node.text}')
                elif base.type == 'attribute':
                    # Handle qualified names (e.g., module.Class)
                    bases.append(base.text)

        # Get methods
        methods = []
        body_node = node.child_by_field_name('body')
        if body_node:
            for child in body_node.children:
                if child and child.type == 'function_definition':
                    methods.append(self._extract_function(child))

        return {
            'name': name,
            'start_line': node.start_point[0] + 1 if node else 0,
            'end_line': node.end_point[0] + 1 if node else 0,
            'methods': methods,
            'bases': bases
        }

    def _extract_parameters(self, node: Any) -> List[Dict[str, Any]]:
        """Extract function parameters."""
        if node is None:
            return []

        parameters = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for param in params_node.children:
                if param is None:
                    continue

                if param.type == 'identifier':
                    # Regular parameter
                    parameters.append({
                        'name': param.text,
                        'start_line': param.start_point[0] + 1,
                        'end_line': param.end_point[0] + 1,
                        'type': 'parameter'
                    })
                elif param.type == 'typed_parameter':
                    # Type-annotated parameter
                    name_node = param.child_by_field_name('name')
                    type_node = param.child_by_field_name('type')
                    if name_node:
                        parameters.append({
                            'name': name_node.text,
                            'start_line': param.start_point[0] + 1,
                            'end_line': param.end_point[0] + 1,
                            'type': type_node.text if type_node else 'unknown'
                        })
                elif param.type == 'list_splat_pattern':
                    # *args parameter
                    name_node = param.child_by_field_name('name')
                    if name_node:
                        parameters.append({
                            'name': f'*{name_node.text}',
                            'start_line': param.start_point[0] + 1,
                            'end_line': param.end_point[0] + 1,
                            'type': 'args'
                        })
                elif param.type == 'dictionary_splat_pattern':
                    # **kwargs parameter
                    name_node = param.child_by_field_name('name')
                    if name_node:
                        parameters.append({
                            'name': f'**{name_node.text}',
                            'start_line': param.start_point[0] + 1,
                            'end_line': param.end_point[0] + 1,
                            'type': 'kwargs'
                        })
                elif param.type == 'default_parameter':
                    # Parameter with default value
                    name_node = param.child_by_field_name('name')
                    value_node = param.child_by_field_name('value')
                    if name_node:
                        parameters.append({
                            'name': name_node.text,
                            'start_line': param.start_point[0] + 1,
                            'end_line': param.end_point[0] + 1,
                            'type': 'parameter',
                            'has_default': True
                        })
        return parameters

    def _extract_functions(self, node: Any) -> List[Dict[str, Any]]:
        """Extract functions from a node."""
        if node is None:
            return []

        functions = []
        for child in node.children_by_field_name('body'):
            if child and child.type == 'function_definition':
                functions.append(self._extract_function(child))
        return functions

    def _infer_type(self, node: Any) -> str:
        """Infer type from value node."""
        if node is None:
            return 'unknown'

        type_map = {
            'string': 'str',
            'integer': 'int',
            'float': 'float',
            'true': 'bool',
            'false': 'bool',
            'none': 'None',
            'list': 'list',
            'dictionary': 'dict',
            'tuple': 'tuple'
        }
        return type_map.get(node.type, 'unknown')

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a Python file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary containing analysis results
        """
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            return self.analyze_code(code)
        except FileNotFoundError as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")
            return {
                'imports': [],
                'functions': [],
                'classes': [],
                'variables': []
            }
        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")
            return {
                'imports': [],
                'functions': [],
                'classes': [],
                'variables': []
            }

    def analyze_directory(self, directory: str) -> Dict[str, Dict[str, Any]]:
        """Analyze all Python files in a directory.

        Args:
            directory: Directory path

        Returns:
            Dictionary mapping file paths to analysis results
        """
        try:
            import os
            results = {}
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        results[file_path] = self.analyze_file(file_path)
            return results
        except Exception as e:
            logger.error(f"Failed to analyze directory {directory}: {e}")
            raise 