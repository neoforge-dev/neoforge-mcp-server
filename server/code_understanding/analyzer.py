"""Module for analyzing Python code."""

import ast
import logging
from typing import Dict, List, Optional, Set, Any, Union
import os

from .parser import CodeParser, MockNode, MockTree

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """Analyzer for Python code."""

    def __init__(self):
        """Initialize the analyzer."""
        self.parser = CodeParser()

    def analyze_code(self, code: str) -> Dict[str, Any]:
        """Analyze Python code and extract information about imports, functions, classes, and variables.

        Args:
            code (str): The Python code to analyze.

        Returns:
            dict: A dictionary containing lists of imports, functions, classes, and variables.
        """
        tree = self.parser.parse(code)
        root = tree.root_node

        result = {
            'imports': [],
            'functions': [],
            'classes': [],
            'variables': []
        }

        logger.info(f"Root node type: {root.type}")
        for child in root.children:
            logger.info(f"Child node type: {child.type}")
            # Check for the correct node types produced by MockParser
            if child.type == 'import_statement': 
                logger.info("Found import_statement")
                # Handle simple imports like 'import os'
                for import_child in child.children:
                    logger.info(f"Import child type: {import_child.type}")
                    # The direct children should be identifiers for simple imports
                    if import_child.type == 'identifier': 
                        result['imports'].append({
                            'type': 'import',
                            'name': import_child.text,
                            'start_line': child.start_point[0] + 1,
                            'end_line': child.end_point[0] + 1
                        })
            # Check for the correct node types produced by MockParser
            elif child.type == 'import_from_statement': 
                logger.info("Found import_from_statement")
                # Handle from imports like 'from sys import path'
                module_name = ''
                imported_names = []
                for import_child in child.children:
                    logger.info(f"Import from child type: {import_child.type}")
                    # First child is module name (dotted_name), rest are identifiers
                    if import_child.type == 'dotted_name': 
                        module_name = import_child.text
                    elif import_child.type == 'identifier': 
                        imported_names.append(import_child.text)
                
                # Ensure we captured module and names before adding
                if module_name and imported_names: 
                    for name in imported_names:
                        result['imports'].append({
                            'type': 'from_import',
                            'name': name,
                            'module': module_name,
                            'start_line': child.start_point[0] + 1,
                            'end_line': child.end_point[0] + 1
                        })
                elif not module_name and imported_names: # Handle 'from . import foo'
                     # Attempt to reconstruct relative import path if possible, or mark as relative
                     # For now, let's just record the names found
                     logger.warning(f"Found 'from .' style import, module name missing in mock node.")
                     for name in imported_names:
                        result['imports'].append({
                            'type': 'from_import',
                            'name': name,
                            'module': '.', # Indicate relative import
                            'start_line': child.start_point[0] + 1,
                            'end_line': child.end_point[0] + 1
                        })
            elif child.type == 'function_definition':
                result['functions'].append(self._extract_function(child))
            elif child.type == 'class_definition':
                result['classes'].append(self._extract_class(child))
            elif child.type == 'assignment':
                # Handle variable assignments
                for assign_child in child.children:
                    if assign_child.type == 'identifier':
                        result['variables'].append({
                            'name': assign_child.text,
                            'start_line': child.start_point[0] + 1,
                            'end_line': child.end_point[0] + 1
                        })

        return result

    def analyze_tree(self, tree):
        result = {'imports': [], 'functions': [], 'classes': [], 'variables': []}
        for node in tree.root_node.children:
            if node.type == 'import_statement':
                # Handle simple imports like 'import os'
                for import_child in node.children:
                    if import_child.type == 'identifier':
                        result['imports'].append({
                            'type': 'import',
                            'name': import_child.text,
                            'start_line': node.start_point[0] + 1,
                            'end_line': node.end_point[0] + 1
                        })
            elif node.type == 'import_from_statement':
                # Handle from imports like 'from sys import path'
                module_name = ''
                imported_names = []
                for import_child in node.children:
                    if import_child.type == 'dotted_name':
                        module_name = import_child.text
                    elif import_child.type == 'identifier':
                        imported_names.append(import_child.text)
                if module_name and imported_names:
                    for name in imported_names:
                        result['imports'].append({
                            'type': 'from_import',
                            'name': name,
                            'module': module_name,
                            'start_line': node.start_point[0] + 1,
                            'end_line': node.end_point[0] + 1
                        })
            elif node.type == 'function_definition':
                result['functions'].append({
                    'name': node.fields["name"].text if "name" in node.fields else node.text,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'parameters': []
                })
            elif node.type == 'class_definition':
                result['classes'].append({
                    'name': node.fields["name"].text if "name" in node.fields else node.text,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'methods': [],
                    'bases': []
                })
            elif node.type == 'assignment':
                if 'right' in node.fields and 'left' in node.fields:
                    right_text = node.fields["right"].text
                    left_text = node.fields["left"].text
                    inferred_type = "str" if ((right_text.startswith("'") and right_text.endswith("'")) or (right_text.startswith('"') and right_text.endswith('"'))) else "unknown"
                    result['variables'].append({
                        'name': left_text,
                        'start_line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1,
                        'type': inferred_type
                    })
        return result

    def _extract_function(self, node) -> Dict[str, Any]:
        """Extract information about a function definition.

        Args:
            node: The function definition node.

        Returns:
            Dictionary containing function information.
        """
        if not node:
            return {
                'name': '',
                'start_line': 0,
                'end_line': 0,
                'parameters': [],
                'decorators': [],
                'is_async': False
            }

        # Extract function name
        name = node.text if hasattr(node, 'text') else ''
        if not name:
            for child in node.children:
                if child.type == 'name':
                    name = child.text
                    break

        # Extract decorators
        decorators = []
        for child in node.children:
            if child.type == 'decorator':
                decorators.append(child.text)

        # Extract parameters
        params_node = None
        for child in node.children:
            if child.type == 'parameters':
                params_node = child
                break
        parameters = self._extract_parameters(params_node) if params_node else []

        # Check if function is async
        is_async = any(child.type == 'async' for child in node.children)

        # Get line numbers - end_point[0] is already 0-based
        start_line = node.start_point[0] + 1 if node.start_point else 0
        end_line = node.end_point[0] if node.end_point else 0

        return {
            'name': name,
            'start_line': start_line,
            'end_line': end_line,
            'parameters': parameters,
            'decorators': decorators,
            'is_async': is_async
        }

    def _extract_class(self, node: Any) -> Dict[str, Any]:
        """Extract information about a class definition.

        Args:
            node: The AST node representing the class definition.

        Returns:
            dict: A dictionary containing the class name, start and end line numbers,
                  methods, and base classes.
        """
        if not node:
            return {
                'name': '',
                'start_line': 0,
                'end_line': 0,
                'methods': [],
                'bases': [],
                'attributes': []
            }

        # Extract class name
        name = node.text if hasattr(node, 'text') else ''
        if not name:
            for child in node.children:
                if child.type == 'name':
                    name = child.text
                    break

        # Extract base classes
        bases = []
        for child in node.children:
            if child.type == 'bases':
                for base in child.children:
                    if base.type == 'identifier':
                        bases.append(base.text)
                    elif base.type == 'keyword_argument':
                        name_node = next((c for c in base.children if c.type == 'name'), None)
                        value_node = next((c for c in base.children if c.type == 'value'), None)
                        if name_node and value_node:
                            bases.append(f"{name_node.text}={value_node.text}")

        # Extract methods
        methods = []
        body_node = next((child for child in node.children if child.type == 'body'), None)
        if body_node:
            for method_node in body_node.children:
                # Check if the child of the body is indeed a function
                if method_node.type == 'function_definition': 
                    # Reuse the existing _extract_function logic
                    method_info = self._extract_function(method_node) 
                    # We might only need name/lines, but let's keep it detailed for now
                    methods.append(method_info) 
                    
        # Extract attributes (simple assignments)
        attributes = []
        if body_node: # Check body_node again
            for attr_node in body_node.children:
                 if attr_node.type == 'attribute': # Assuming mock parser creates 'attribute' for class vars
                     attributes.append({
                         'name': attr_node.text,
                         'start_line': attr_node.start_point[0] + 1,
                         'end_line': attr_node.end_point[0] + 1 # Adjust if needed
                     })

        # Get line numbers - end_point[0] is already 0-based
        start_line = node.start_point[0] + 1 if node.start_point else 0
        end_line = node.end_point[0] if node.end_point else 0 # End line of class def

        return {
            'name': name,
            'start_line': start_line,
            'end_line': end_line,
            'methods': methods,
            'bases': bases,
            'attributes': attributes # Add attributes if needed by tests later
        }

    def _extract_parameters(self, node) -> List[Dict[str, Any]]:
        """Extract information about function parameters.

        Args:
            node: The parameters node.

        Returns:
            List of dictionaries containing parameter information.
        """
        if not node:
            return []

        parameters = []
        for child in node.children:
            param_info = {
                'name': '',
                'type': None,
                'default': None,
                'start_line': child.start_point[0] + 1 if child.start_point else 0,
                'end_line': child.end_point[0] + 1 if child.end_point else 0
            }

            if child.type == 'identifier':
                param_info['name'] = child.text
                param_info['type'] = 'parameter'
            elif child.type == 'typed_parameter':
                name_node = next((c for c in child.children if c.type == 'name'), None)
                type_node = next((c for c in child.children if c.type == 'type'), None)
                if name_node:
                    param_info['name'] = name_node.text
                if type_node:
                    param_info['type'] = type_node.text
            elif child.type == 'list_splat_pattern':
                name_node = next((c for c in child.children if c.type == 'name'), None)
                if name_node:
                    param_info['name'] = f"*{name_node.text}"
                    param_info['type'] = 'parameter'

            if param_info['name']:
                parameters.append(param_info)

        return parameters

    def _extract_functions(self, root):
        """Extract function definitions from a node.
        
        Args:
            root: Root node to extract functions from
            
        Returns:
            List of dictionaries containing function information
        """
        functions = []
        for node in root.children:
            if node.type == 'function_definition':
                functions.append({
                    'name': node.fields["name"].text,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'parameters': []
                })
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

    def analyze_file(self, file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze a Python file and extract information about its contents.

        Args:
            file_path: Path to the Python file to analyze.

        Returns:
            Dictionary containing analysis results.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r') as f:
                code = f.read()
            return self.analyze_code(code)
        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")
            raise

    def analyze_directory(self, directory_path):
        """Analyze all Python files in a directory.

        Args:
            directory_path (str): Path to the directory to analyze.

        Returns:
            list: A list of dictionaries, each containing analysis results for a file:
                - file (str): The file path
                - imports (list): List of import information
                - functions (list): List of function information
                - classes (list): List of class information
                - variables (list): List of variable information

        Raises:
            FileNotFoundError: If the directory does not exist.
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not os.path.isdir(directory_path):
            raise NotADirectoryError(f"Path is not a directory: {directory_path}")

        results = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        analysis = self.analyze_file(file_path)
                        analysis['file'] = file_path
                        results.append(analysis)
                    except Exception as e:
                        logger.error(f"Error analyzing file {file_path}: {str(e)}")

        return results

    def _extract_imports(self, root):
        """Extract import statements from a node.
        
        Args:
            root: Root node to extract imports from
            
        Returns:
            List of dictionaries containing import information
        """
        imports = []
        for node in root.children:
            if node.type == 'import':
                imports.append({
                    'type': 'import',
                    'name': node.text,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        return imports

    def _extract_classes(self, root):
        """Extract class definitions from a node.
        
        Args:
            root: Root node to extract classes from
            
        Returns:
            List of dictionaries containing class information
        """
        classes = []
        for node in root.children:
            if node.type == 'class_definition':
                classes.append({
                    'name': node.fields["name"].text,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'methods': [],
                    'bases': []
                })
        return classes

    def _extract_variables(self, root):
        """Extract variable assignments from a node.
        
        Args:
            root: Root node to extract variables from
            
        Returns:
            List of dictionaries containing variable information
        """
        variables = []
        for node in root.children:
            if node.type == 'assignment':
                right_text = node.fields["right"].text
                inferred_type = "str" if ((right_text.startswith("'") and right_text.endswith("'")) or (right_text.startswith('"') and right_text.endswith('"'))) else "unknown"
                variables.append({
                    'name': node.fields["left"].text,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'type': inferred_type
                })
        return variables 