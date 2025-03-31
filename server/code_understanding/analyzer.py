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
        self.exports: List[Dict[str, Any]] = []  # Add exports list
        # Add other state variables as needed

    def analyze_code(self, code: str, language: str = 'python') -> Dict[str, List[Dict[str, Any]]]:
        """Analyzes code string using the appropriate parser adapter.
        
        Args:
            code: Source code string to analyze.
            language: Programming language of the code.
            
        Returns:
            Dict containing analysis results with the following structure:
            {
                'has_errors': bool,
                'error_details': List[Dict[str, str]],
                'imports': List[Dict],
                'functions': List[Dict],
                'classes': List[Dict],
                'variables': List[Dict],
                'exports': List[Dict]
            }
        """
        # Input validation
        if code is None:
            return {
                'has_errors': True,
                'error_details': [{"message": "Input code cannot be None"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        
        if not isinstance(code, (str, bytes)):
            return {
                'has_errors': True,
                'error_details': [{"message": f"Input code must be string or bytes, got {type(code)}"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        
        # Convert bytes to string if needed
        if isinstance(code, bytes):
            try:
                code = code.decode('utf-8')
            except UnicodeDecodeError:
                return {
                    'has_errors': True,
                    'error_details': [{"message": "Invalid UTF-8 encoding in input code"}],
                    'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
                }
        
        # Parse code
        try:
            tree = self.parser.parse(code, language=language)
        except Exception as e:
            return {
                'has_errors': True,
                'error_details': [{"message": f"Parser error: {str(e)}"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        
        # Handle parsing failures
        if not tree:
            return {
                'has_errors': True,
                'error_details': [{"message": f"Parsing failed for language '{language}'. Cannot analyze."}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        
        if tree.has_errors:
            return {
                'has_errors': True,
                'error_details': tree.error_details,
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        
        # Reset state and analyze
        try:
            self.reset_state()
            logger.info(f"Root node type: {tree.type} for language {language}")
            self._analyze_node(tree, language)
            
            return {
                'has_errors': False,
                'error_details': [],
                'imports': self.imports,
                'functions': self.functions,
                'classes': self.classes,
                'variables': self.variables,
                'exports': self.exports
            }
        except Exception as e:
            return {
                'has_errors': True,
                'error_details': [{"message": f"Analysis error: {str(e)}"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
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

        # Process exports
        if node.type == 'export_statement':
            logger.debug(f"Processing export statement: {node.text}")
            export_info = self._extract_js_export(node)
            if export_info:
                self.exports.append(export_info)
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
        if node.type in ('function_declaration', 'function_definition', 'arrow_function'):
            # Handle function declarations and definitions
            name = ''
            if node.fields.get('name'):
                name = node.fields['name']
            else:
                for child in node.children:
                    if child.type in ('name', 'identifier'):
                        name = child.text
                        break

            # Check if it's a top-level function
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
        """Extracts ES6 import details from an import_statement MockNode.
        
        Handles various import types:
        - Default imports: import name from './module'
        - Named imports: import { name1, name2 } from './module'
        - Namespace imports: import * as name from './module'
        - Dynamic imports: import('./module')
        - Import assertions: import json from './data.json' assert { type: 'json' }
        """
        logger.debug(f"_extract_js_es6_import called for node: type={node.type}, text='{node.text}'")
        
        # Initialize import info with common fields
        import_info = {
            'type': 'import',
            'start_line': node.start_point[0] + 1 if node.start_point else 0,
            'end_line': node.end_point[0] + 1 if node.end_point else 0
        }
        
        # Get source module
        source = None
        is_dynamic = False
        is_namespace = False
        assertions = {}
        
        for child in node.children:
            if child.type == 'string':
                source = child.text.strip('"\'')
            elif child.type == 'import_specifier':
                # Handle named imports
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        import_info['names'] = import_info.get('names', []) + [grandchild.text]
                        import_info['is_default'] = False
                        break
            elif child.type == 'namespace_import':
                # Handle namespace imports (import * as name)
                is_namespace = True
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        import_info['name'] = grandchild.text
                        break
            elif child.type == 'identifier':
                # Handle default imports
                import_info['name'] = child.text
                import_info['is_default'] = True
            elif child.type == 'import_assertion':
                # Handle import assertions
                for grandchild in child.children:
                    if grandchild.type == 'object':
                        for prop in grandchild.children:
                            if prop.type == 'property':
                                key = None
                                value = None
                                for prop_child in prop.children:
                                    if prop_child.type == 'property_identifier':
                                        key = prop_child.text
                                    elif prop_child.type == 'string':
                                        value = prop_child.text.strip('"\'')
                                if key and value:
                                    assertions[key] = value
        
        if not source:
            logger.warning(f"JS import statement node missing source: {node.text}")
            return None
        
        import_info.update({
            'module': source,
            'is_dynamic': is_dynamic,
            'is_namespace': is_namespace
        })
        
        if assertions:
            import_info['assertions'] = assertions
        
        # Add default import if present
        if import_info.get('name'):
            logger.debug(f"Extracted JS default import: {import_info['name']} from {source}")
        
        # Add named imports if present
        if import_info.get('names'):
            logger.debug(f"Extracted JS named imports: {import_info['names']} from {source}")
        
        return import_info

    def _extract_js_require(self, node: MockNode) -> Optional[Dict[str, Any]]:
        """Extracts require statement details from a call_expression MockNode."""
        logger.debug(f"_extract_js_require called for node: type={node.type}, text='{node.text}'")
        
        # Check if it's a require call
        is_require = False
        source = None
        
        for child in node.children:
            if child.type == 'identifier' and child.text == 'require':
                is_require = True
            elif child.type == 'arguments':
                for arg in child.children:
                    if arg.type == 'string':
                        source = arg.text.strip('"\'')
                        break

        if not is_require or not source:
            return None

        return {
            'type': 'require',
            'name': source,  # Use source as name for require statements
            'module': source,
            'is_default': True,
            'start_line': node.start_point[0] + 1 if node.start_point else 0,
            'end_line': node.end_point[0] + 1 if node.end_point else 0
        }

    def _extract_js_export(self, node: MockNode) -> Optional[Dict[str, Any]]:
        """Extracts export statement details from an export_statement MockNode.
        
        Handles various export types:
        - Named exports: export { name1, name2 }
        - Default exports: export default value
        - Re-exports: export { name as renamed } from './module'
        - Namespace exports: export * from './module'
        """
        logger.debug(f"_extract_js_export called for node: type={node.type}, text='{node.text}'")
        
        # Initialize export info with common fields
        export_info = {
            'type': 'export',
            'start_line': node.start_point[0] + 1 if node.start_point else 0,
            'end_line': node.end_point[0] + 1 if node.end_point else 0
        }
        
        # Check for default export
        is_default = False
        name = None
        source = None
        is_namespace = False
        
        for child in node.children:
            if child.type == 'export_clause':
                is_default = True
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        name = grandchild.text
                        break
            elif child.type == 'identifier':
                name = child.text
                is_default = True
            elif child.type == 'namespace_export':
                is_namespace = True
                # Look for source module
                for grandchild in child.children:
                    if grandchild.type == 'string':
                        source = grandchild.text.strip('"\'')
                        break
            elif child.type == 'export_specifier':
                # Handle named exports and re-exports
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        name = grandchild.text
                        break
                    elif grandchild.type == 'string':
                        source = grandchild.text.strip('"\'')
                        break
            elif child.type == 'string':
                source = child.text.strip('"\'')
        
        if is_namespace:
            export_info.update({
                'is_namespace': True,
                'source': source
            })
            return export_info
        
        if not name:
            logger.warning(f"Could not extract export name from node: {node.text}")
            return None
        
        export_info.update({
            'name': name,
            'is_default': is_default,
            'source': source
        })
        
        # Handle re-exports
        if source and not is_default:
            export_info['is_re_export'] = True
        
        return export_info

    # --- Common Helper Methods (unchanged from previous state) ---

    def _extract_function(self, node: MockNode) -> Dict[str, Any]:
        """Extracts function details from a function node.
        
        Handles various function types:
        - Regular functions
        - Arrow functions
        - Async functions
        - Generator functions
        - Decorated functions
        - Class methods
        """
        logger.debug(f"_extract_function called for node: type={node.type}, text='{node.text}'")
        
        # Initialize function info with common fields
        func_info = {
            'type': 'function',
            'start_line': node.start_point[0] + 1 if node.start_point else 0,
            'end_line': node.end_point[0] + 1 if node.end_point else 0,
            'is_async': False,
            'is_generator': False,
            'is_arrow': node.type == 'arrow_function',
            'is_method': False,
            'is_static': False,
            'is_private': False,
            'decorators': [],
            'parameters': [],
            'return_type': None
        }
        
        # Extract name
        name = ''
        if node.fields.get('name'):
            name = node.fields['name']
        else:
            for child in node.children:
                if child.type in ('name', 'identifier'):
                    name = child.text
                    break
        
        func_info['name'] = name
        
        # Check for decorators
        if node.fields.get('decorators'):
            for decorator in node.fields['decorators']:
                if decorator.type == 'decorator':
                    decorator_name = ''
                    for child in decorator.children:
                        if child.type == 'identifier':
                            decorator_name = child.text
                            break
                    if decorator_name:
                        func_info['decorators'].append(decorator_name)
        
        # Check for async/await
        if node.fields.get('async'):
            func_info['is_async'] = True
        
        # Check for generator
        if node.fields.get('generator'):
            func_info['is_generator'] = True
        
        # Check for static method
        if node.fields.get('static'):
            func_info['is_static'] = True
        
        # Check for private method
        if name.startswith('#'):
            func_info['is_private'] = True
            func_info['name'] = name[1:]  # Remove # prefix
        
        # Extract parameters
        if node.fields.get('parameters'):
            for param in node.fields['parameters']:
                param_info = {
                    'name': '',
                    'type': None,
                    'default': None,
                    'is_rest': False,
                    'is_optional': False
                }
                
                for child in param.children:
                    if child.type == 'identifier':
                        param_info['name'] = child.text
                    elif child.type == 'type_annotation':
                        param_info['type'] = child.text
                    elif child.type == 'default_value':
                        param_info['default'] = child.text
                    elif child.type == 'rest_parameter':
                        param_info['is_rest'] = True
                
                if param_info['name']:
                    func_info['parameters'].append(param_info)
        
        # Extract return type if present
        if node.fields.get('return_type'):
            func_info['return_type'] = node.fields['return_type'].text
        
        # Extract body if needed (for future use)
        if node.fields.get('body'):
            func_info['has_body'] = True
        
        logger.debug(f"Extracted function info: {func_info}")
        return func_info

    def _extract_class(self, node: MockNode) -> Dict[str, Any]:
        """Extracts class details from a class node.
        
        Handles various class features:
        - Class fields (public, private, static)
        - Class methods (public, private, static)
        - Class decorators
        - Class inheritance
        - Class expressions
        """
        logger.debug(f"_extract_class called for node: type={node.type}, text='{node.text}'")
        
        # Initialize class info with common fields
        class_info = {
            'type': 'class',
            'start_line': node.start_point[0] + 1 if node.start_point else 0,
            'end_line': node.end_point[0] + 1 if node.end_point else 0,
            'name': '',
            'is_expression': False,
            'decorators': [],
            'extends': None,
            'implements': [],
            'fields': [],
            'methods': [],
            'constructors': []
        }
        
        # Extract class name
        name = ''
        if node.fields.get('name'):
            name = node.fields['name']
        else:
            for child in node.children:
                if child.type == 'identifier':
                    name = child.text
                    break
        
        class_info['name'] = name
        
        # Check for class expression
        if node.type == 'class_expression':
            class_info['is_expression'] = True
        
        # Extract decorators
        if node.fields.get('decorators'):
            for decorator in node.fields['decorators']:
                if decorator.type == 'decorator':
                    decorator_name = ''
                    for child in decorator.children:
                        if child.type == 'identifier':
                            decorator_name = child.text
                            break
                    if decorator_name:
                        class_info['decorators'].append(decorator_name)
        
        # Extract class body
        body = None
        for child in node.children:
            if child.type == 'class_body':
                body = child
                break
        
        if body:
            for child in body.children:
                if child.type == 'field_definition':
                    # Handle class fields
                    field_info = {
                        'name': '',
                        'type': None,
                        'is_static': False,
                        'is_private': False,
                        'is_readonly': False,
                        'initializer': None
                    }
                    
                    for field_child in child.children:
                        if field_child.type == 'property_identifier':
                            field_info['name'] = field_child.text
                            if field_info['name'].startswith('#'):
                                field_info['is_private'] = True
                                field_info['name'] = field_info['name'][1:]
                        elif field_child.type == 'static':
                            field_info['is_static'] = True
                        elif field_child.type == 'readonly':
                            field_info['is_readonly'] = True
                        elif field_child.type == 'type_annotation':
                            field_info['type'] = field_child.text
                        elif field_child.type == 'initializer':
                            field_info['initializer'] = field_child.text
                    
                    if field_info['name']:
                        class_info['fields'].append(field_info)
                
                elif child.type == 'method_definition':
                    # Handle class methods
                    method_info = self._extract_function(child)
                    method_info['is_method'] = True
                    
                    if method_info['name'] == 'constructor':
                        class_info['constructors'].append(method_info)
                    else:
                        class_info['methods'].append(method_info)
        
        # Extract inheritance
        if node.fields.get('extends'):
            class_info['extends'] = node.fields['extends'].text
        
        # Extract interfaces (if TypeScript)
        if node.fields.get('implements'):
            for interface in node.fields['implements']:
                if interface.type == 'identifier':
                    class_info['implements'].append(interface.text)
        
        logger.debug(f"Extracted class info: {class_info}")
        return class_info

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

    def analyze_file(self, file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Analyze a source code file.
        
        Args:
            file_path: Path to the source code file.
            language: Optional language override. If not provided, inferred from file extension.
            
        Returns:
            Dict containing analysis results with the following structure:
            {
                'has_errors': bool,
                'error_details': List[Dict[str, str]],
                'imports': List[Dict],
                'functions': List[Dict],
                'classes': List[Dict],
                'variables': List[Dict],
                'exports': List[Dict]
            }
        """
        # Input validation
        if not file_path:
            return {
                'has_errors': True,
                'error_details': [{"message": "File path cannot be empty"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        
        # Check file existence
        if not os.path.exists(file_path):
            return {
                'has_errors': True,
                'error_details': [{"message": f"File not found: {file_path}"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        
        # Infer language from file extension if not provided
        if not language:
            ext = os.path.splitext(file_path)[1].lower()
            language = {
                '.py': 'python',
                '.js': 'javascript',
                '.swift': 'swift'
            }.get(ext)
            if not language:
                return {
                    'has_errors': True,
                    'error_details': [{"message": f"Could not determine language for file: {file_path}"}],
                    'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
                }
        
        # Read and analyze file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            return self.analyze_code(code, language)
        except UnicodeDecodeError:
            return {
                'has_errors': True,
                'error_details': [{"message": f"File {file_path} is not valid UTF-8"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        except IOError as e:
            return {
                'has_errors': True,
                'error_details': [{"message": f"Error reading file {file_path}: {str(e)}"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        except Exception as e:
            return {
                'has_errors': True,
                'error_details': [{"message": f"Unexpected error analyzing file {file_path}: {str(e)}"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }

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