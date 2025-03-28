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
        """Analyze a syntax tree and return a structured dictionary."""
        try:
            root = tree.root_node
            imports = self._extract_imports(root)
            functions = self._extract_functions(root)
            classes = self._extract_classes(root)
            variables = self._extract_variables(root)

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

    def _extract_imports(self, node: Any) -> List[Dict[str, Any]]:
        """Extract import statements.

        Args:
            node: AST node

        Returns:
            List of import information
        """
        imports = []
        for child in node.children_by_field_name('body'):
            if child.type == 'import':
                text = child.text.decode('utf-8') if isinstance(child.text, bytes) else child.text
                if text.startswith('from '):
                    # Handle from imports
                    parts = text.split(' import ')
                    if len(parts) == 2:
                        module = parts[0][5:].strip()  # Remove 'from '
                        names = [n.strip() for n in parts[1].split(',')]
                        for name in names:
                            if name:
                                imports.append({
                                    'type': 'import',
                                    'name': f'from {module} import {name}',
                                    'start_line': child.start_point[0] + 1,
                                    'end_line': child.end_point[0] + 1
                                })
                else:
                    # Handle regular imports
                    imports.append({
                        'type': 'import',
                        'name': text,
                        'start_line': child.start_point[0] + 1,
                        'end_line': child.end_point[0] + 1
                    })
        return imports

    def _extract_functions(self, node: Any) -> List[Dict[str, Any]]:
        """Extract function definitions.

        Args:
            node: AST node

        Returns:
            List of function information
        """
        functions = []
        for child in node.children_by_field_name('body'):
            if child.type == 'function_definition':
                name_node = child.child_by_field_name('name')
                functions.append({
                    'name': name_node.text.decode('utf-8') if isinstance(name_node.text, bytes) else name_node.text,
                    'start_line': child.start_point[0] + 1,
                    'end_line': child.end_point[0] + 1,
                    'parameters': self._extract_parameters(child)
                })
        return functions

    def _extract_parameters(self, node: Any) -> List[Dict[str, Any]]:
        """Extract function parameters.

        Args:
            node: AST node

        Returns:
            List of parameter information
        """
        params = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for param in params_node.children:
                if param.type == 'identifier':
                    params.append({
                        'name': param.text.decode('utf-8') if isinstance(param.text, bytes) else param.text,
                        'start_line': param.start_point[0] + 1,
                        'end_line': param.end_point[0] + 1
                    })
        return params

    def _extract_classes(self, node: Any) -> List[Dict[str, Any]]:
        """Extract class definitions.

        Args:
            node: AST node

        Returns:
            List of class information
        """
        classes = []
        for child in node.children_by_field_name('body'):
            if child.type == 'class_definition':
                name_node = child.child_by_field_name('name')
                classes.append({
                    'name': name_node.text.decode('utf-8') if isinstance(name_node.text, bytes) else name_node.text,
                    'start_line': child.start_point[0] + 1,
                    'end_line': child.end_point[0] + 1,
                    'methods': self._extract_functions(child),
                    'bases': self._extract_base_classes(child)
                })
        return classes

    def _extract_base_classes(self, node: Any) -> List[str]:
        """Extract base classes.

        Args:
            node: AST node

        Returns:
            List of base class names
        """
        bases = []
        bases_node = node.child_by_field_name('bases')
        if bases_node:
            for base in bases_node.children:
                if base.type == 'identifier':
                    bases.append(base.text.decode('utf-8') if isinstance(base.text, bytes) else base.text)
        return bases

    def _extract_variables(self, node: Any) -> List[Dict[str, Any]]:
        """Extract variable assignments.

        Args:
            node: AST node

        Returns:
            List of variable information
        """
        variables = []
        for child in node.children_by_field_name('body'):
            if child.type == 'assignment':
                left = child.child_by_field_name('left')
                right = child.child_by_field_name('right')
                if left and right:
                    variables.append({
                        'name': left.text.decode('utf-8') if isinstance(left.text, bytes) else left.text,
                        'start_line': child.start_point[0] + 1,
                        'end_line': child.end_point[0] + 1,
                        'type': self._infer_type(right)
                    })
        return variables

    def _infer_type(self, node: Any) -> str:
        """Infer type from value node.

        Args:
            node: AST node

        Returns:
            Type string
        """
        type_map = {
            'string': 'str',
            'integer': 'int',
            'float': 'float',
            'true': 'bool',
            'false': 'bool',
            'none': 'None',
            'list': 'list',
            'dictionary': 'dict'
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