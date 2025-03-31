"""Module for analyzing Python code."""

import ast
import logging
from typing import Dict, List, Optional, Set, Any, Union
import os

from .parser import CodeParser
# Import common types
from .common_types import MockNode, MockTree

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """Analyzer for Python code."""

    def __init__(self):
        """Initialize the analyzer."""
        self.parser = CodeParser()
        self.reset_state()

    def reset_state(self):
        self.imports: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.variables: List[Dict[str, Any]] = []
        # Add other state variables as needed

    def analyze_code(self, code: str, language: str = 'python') -> Dict[str, List[Dict[str, Any]]]:
        """Analyzes code string using the appropriate parser adapter."""
        tree = self.parser.parse(code, language=language)
        
        if not tree or not tree.root_node:
            logger.error(f"Parsing failed for language '{language}'. Cannot analyze.")
            return {'imports': [], 'functions': [], 'classes': [], 'variables': []}

        self.reset_state()
        logger.info(f"Root node type: {tree.type} for language {language}")
        self._analyze_node(tree, language)

        return {
            'imports': self.imports,
            'functions': self.functions,
            'classes': self.classes,
            'variables': self.variables
        }

    def _analyze_node(self, node: Union[MockNode, MockTree], parent_type: str = None, language: str = 'python', parent: Optional[MockNode] = None) -> None:
        """Analyze a single AST node and update the analysis results.

        Args:
            node: The AST node to analyze.
            parent_type: The type of the parent node, if any.
            language: The programming language being analyzed.
            parent: The parent node, if any.
        """
        if not node:
            return

        # If node is a MockTree, use its root_node
        if isinstance(node, MockTree):
            if node.root_node:
                self._analyze_node(node.root_node, parent_type, language, parent)
            return

        # Process imports and requires
        if node.type == 'import_statement':
            logger.debug(f"Processing JS import_statement: {node.text}")
            import_info = self._extract_js_es6_import(node)
            if import_info:
                self.imports.append(import_info)
        elif node.type == 'call_expression':
            # Check for require statements
            require_info = self._extract_js_require(node)
            if require_info:
                self.imports.append(require_info)
        elif node.type == 'variable_declarator':
            # Check for require statements in variable declarations
            require_info = self._extract_js_require(node)
            if require_info:
                self.imports.append(require_info)
                return  # Skip further processing of this node
            
            # Check if it's a function assignment (arrow function)
            name = None
            value = None
            for child in node.children:
                if child.type == 'identifier':
                    name = child.text
                elif child.type == 'arrow_function':
                    value = child
                    break

            if value and name:
                logger.debug(f"Processing arrow function assignment: name='{name}'")
                func_info = self._extract_function(value)
                if func_info['name']:
                    func_info['name'] = name  # Use the variable name as the function name
                    self.functions.append(func_info)
            elif name:  # Only add as variable if it's not a function or require
                logger.debug(f"Processing variable declaration: name='{name}'")
                self.variables.append({
                    'name': name,
                    'type': 'variable',
                    'start_line': node.start_point[0] + 1 if node.start_point else 0,
                    'end_line': node.end_point[0] + 1 if node.end_point else 0
                })
        elif node.type == 'lexical_declaration':
            # Process variable declarations, including requires and arrow functions
            logger.debug(f"Processing lexical_declaration node: {node.text}")
            for child in node.children:
                if child.type == 'variable_declarator':
                    logger.debug(f"Processing variable_declarator child: {child.text}")
                    # First check if it's a require statement
                    require_info = self._extract_js_require(child)
                    if require_info:
                        logger.debug(f"Found require statement: {require_info}")
                        self.imports.append(require_info)
                        continue

                    # Check if it's an arrow function
                    name = None
                    value = None
                    for grandchild in child.children:
                        if grandchild.type == 'arrow_function':
                            value = grandchild
                            logger.debug(f"Found arrow function in variable_declarator: {child.text}")
                            break
                        elif grandchild.type == 'identifier':
                            name = grandchild.text

                    if value and name:
                        func_info = self._extract_function(value)
                        func_info['name'] = name  # Use the variable name as the function name
                        if func_info['name']:
                            self.functions.append(func_info)
                    elif name:  # Only add as variable if it's not a function or require
                        self.variables.append({
                            'name': name,
                            'type': 'variable',
                            'start_line': child.start_point[0] + 1 if child.start_point else 0,
                            'end_line': child.end_point[0] + 1 if child.end_point else 0
                        })

        # Process functions
        if node.type in ('function_declaration', 'function_definition'):
            # Handle function declarations and definitions
            name = ''
            if node.fields.get('name'):
                name = node.fields['name']
            else:
                for child in node.children:
                    if child.type in ('name', 'identifier'):
                        name = child.text
                        break
            effective_top_level = parent is None or parent.type == 'program'
            if parent and parent.type == 'variable_declaration':
                effective_top_level = True
            logger.debug(f"Processing function node: name='{name}', effective_top_level={effective_top_level} (parent_type={parent.type if parent else 'None'})")
            if effective_top_level:
                func_info = self._extract_function(node)
                if func_info['name']:
                    self.functions.append(func_info)
            else:
                logger.debug(f"Skipping function (not top-level, parent={parent.type if parent else 'None'})")

        elif node.type in ('class_declaration', 'class_definition'):
            # Handle class declarations and definitions
            class_info = self._extract_class(node)
            if class_info['name']:
                self.classes.append(class_info)

        # Process children in pre-order traversal
        for child in node.children:
            self._analyze_node(child, node.type, language, node)

    # --- JavaScript Helper Methods ---
    def _extract_js_es6_import(self, node: MockNode):
        """Extracts ES6 import details from an import_statement MockNode."""
        # ---- Add extra logging ----
        logger.debug(f"_extract_js_es6_import called for node: type={node.type}, text='{node.text}'")
        logger.debug(f"Node fields: {node.fields}")
        # ---- End extra logging ----
        
        module = node.fields.get('module')
        default_import = node.fields.get('default_name')
        named_imports = node.fields.get('named_names', [])
        start_line = node.start_point[0] + 1 if node.start_point else 0
        end_line = node.end_point[0] + 1 if node.end_point else 0

        if not module:
            logger.warning(f"JS import statement node missing 'module' field: {node.text}")
            return

        # Add default import if present
        if default_import:
            self.imports.append({
                'type': 'import',
                'name': default_import,
                'module': module,
                'is_default': True,
                'start_line': start_line,
                'end_line': end_line
            })
            logger.debug(f"Extracted JS default import: {default_import} from {module}")

        # Add named imports if present
        for named_import in named_imports:
            self.imports.append({
                'type': 'import',
                'name': named_import,
                'module': module,
                'is_default': False,
                'start_line': start_line,
                'end_line': end_line
            })
            logger.debug(f"Extracted JS named import: {named_import} from {module}")

        # Handle namespace imports if present
        namespace_import = node.fields.get('namespace_name')
        if namespace_import:
            self.imports.append({
                'type': 'import',
                'name': namespace_import,
                'module': module,
                'is_namespace': True,
                'start_line': start_line,
                'end_line': end_line
            })
            logger.debug(f"Extracted JS namespace import: {namespace_import} from {module}")

    def _extract_js_require(self, node: MockNode) -> Optional[Dict[str, Any]]:
        """Extract information about a JavaScript require statement.

        Args:
            node: The AST node representing a require statement.

        Returns:
            A dictionary containing information about the require statement, or None if not a require.
        """
        if not node:
            return None

        logger.debug(f"_extract_js_require called for node: type={node.type}, text='{node.text}'")

        # Handle variable declarator nodes
        if node.type == 'variable_declarator':
            # Check if this is a require statement
            if node.fields.get('type') == 'require':
                return {
                    'type': 'require',
                    'name': node.fields.get('name'),
                    'module': node.fields.get('module'),
                    'start_line': node.start_point[0] + 1 if node.start_point else 0,
                    'end_line': node.end_point[0] + 1 if node.end_point else 0
                }

            # Look for a call_expression child that might be a require
            name = None
            name_node = node.children[0] if node.children else None
            if name_node and name_node.type == 'identifier':
                name = name_node.text
                logger.debug(f"Found variable name: {name}")

            # Look for the require call in the initializer
            for child in node.children:
                if child.type == 'call_expression':
                    logger.debug(f"Found call_expression child: {child.text}")
                    # Check if this is a require call
                    callee = None
                    module = None
                    for call_child in child.children:
                        logger.debug(f"Processing call_child: type={call_child.type}, text='{call_child.text}'")
                        if call_child.type == 'identifier' and call_child.text == 'require':
                            callee = call_child
                        elif call_child.type == 'string':
                            module = call_child.text.strip('"\'')

                    if callee and module:
                        logger.debug(f"Found require call: callee={callee.text}, module={module}")
                        return {
                            'type': 'require',
                            'name': name or module.split('/')[-1],
                            'module': module,
                            'start_line': node.start_point[0] + 1 if node.start_point else 0,
                            'end_line': node.end_point[0] + 1 if node.end_point else 0
                        }
            return None

        # Handle direct call_expression nodes
        if node.type != 'call_expression':
            return None

        logger.debug(f"Processing call_expression node: {node.text}")
        # Check if this is a require call
        callee = None
        module = None
        for child in node.children:
            logger.debug(f"Processing child: type={child.type}, text='{child.text}'")
            if child.type == 'identifier' and child.text == 'require':
                callee = child
            elif child.type == 'string':
                module = child.text.strip('"\'')

        if not callee or not module:
            return None

        # For direct require calls without assignment, use the last part of the path as the name
        name = module.split('/')[-1]

        logger.debug(f"Found require call: callee={callee.text}, module={module}")
        return {
            'type': 'require',
            'name': name,
            'module': module,
            'start_line': node.start_point[0] + 1 if node.start_point else 0,
            'end_line': node.end_point[0] + 1 if node.end_point else 0
        }

    # --- Common Helper Methods (unchanged from previous state) ---

    def _extract_function(self, node: MockNode) -> Dict[str, Any]:
        """Extract information about a function or method definition.

        Args:
            node: The AST node representing the function or method definition.

        Returns:
            dict: A dictionary containing the function name, start and end line numbers,
                  parameters, decorators, and async status.
        """
        if not node:
            return {
                'name': '',
                'start_line': 0,
                'end_line': 0,
                'parameters': [],
                'decorators': [],
                'is_async': False,
                'is_static': False
            }

        # Extract function name
        name = ''
        if node.type == 'method_definition':
            # For method definitions, get name from the name field
            name_node = node.fields.get('name')
            if name_node and hasattr(name_node, 'text'):
                name = name_node.text
            # Check if method is static
            is_static = any(child.type == 'static' for child in node.children)
        elif node.type == 'function_declaration':
            # For function declarations, get name from the name field or first child
            name_node = node.fields.get('name')
            if name_node and hasattr(name_node, 'text'):
                name = name_node.text
            else:
                for child in node.children:
                    if child.type in ('name', 'identifier'):
                        name = child.text
                        break
        else:
            # For regular function definitions and arrow functions, get name from children
            for child in node.children:
                if child.type in ('name', 'identifier'):
                    name = child.text
                    break
            # If no name found in children, check fields
            if not name and node.fields.get('name'):
                name = node.fields['name']

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

        # Log method extraction details
        logger.debug(f"Extracting {'method' if node.type == 'method_definition' else 'function'} '{name}'")
        if node.type == 'method_definition':
            logger.debug(f"  Method is static: {is_static}")

        return {
            'name': name,
            'start_line': start_line,
            'end_line': end_line,
            'parameters': parameters,
            'decorators': decorators,
            'is_async': is_async,
            'is_static': is_static if node.type == 'method_definition' else False
        }

    def _extract_class(self, node: MockNode) -> Dict[str, Any]:
        """Extract information about a class definition.

        Args:
            node: The AST node representing the class definition.

        Returns:
            dict: A dictionary containing the class name, base classes, methods, and attributes.
        """
        if not node:
            return {
                'name': '',
                'base_classes': [],
                'methods': [],
                'attributes': []
            }

        # Extract class name
        name = ''
        for child in node.children:
            if child.type in ('name', 'identifier'):
                name = child.text
                break

        # Extract base classes
        base_classes = []
        for child in node.children:
            if child.type == 'extends_clause':
                for base in child.children:
                    if base.type == 'name':
                        base_classes.append(base.text)

        # Extract methods and attributes
        methods = []
        attributes = []
        
        # Get the class body - check both body and class_body fields
        body_node = node.fields.get('body') or node.fields.get('class_body')
        if body_node:
            for child in body_node.children:
                if child.type in ('function_definition', 'method_definition'):
                    method_info = self._extract_function(child)
                    if method_info['name']:
                        methods.append(method_info)
                elif child.type == 'field_definition':
                    # Handle class fields/attributes
                    for field_child in child.children:
                        if field_child.type == 'name':
                            attributes.append({
                                'name': field_child.text,
                                'is_static': any(c.type == 'static' for c in child.children)
                            })

        # Log class extraction details
        logger.debug(f"Extracting class '{name}'")
        logger.debug(f"  Base classes: {base_classes}")
        logger.debug(f"  Methods: {[m['name'] for m in methods]}")
        logger.debug(f"  Attributes: {[a['name'] for a in attributes]}")

        return {
            'name': name,
            'base_classes': base_classes,
            'methods': methods,
            'attributes': attributes
        }

    def _extract_parameters(self, node: MockNode) -> List[Dict[str, Any]]:
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