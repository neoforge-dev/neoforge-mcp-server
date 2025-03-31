"""Module for semantic analysis of JavaScript code."""

from typing import Dict, List, Set, Any, Optional, Union
from pathlib import Path
import re
from .language_adapters import JavaScriptParserAdapter

class Type:
    """Represents a JavaScript type."""
    
    def __init__(self, name: str, is_array: bool = False, is_optional: bool = False):
        self.name = name
        self.is_array = is_array
        self.is_optional = is_optional
        
    def __str__(self) -> str:
        result = self.name
        if self.is_array:
            result += '[]'
        if self.is_optional:
            result += '?'
        return result

class Scope:
    """Represents a lexical scope in JavaScript."""
    
    def __init__(self, parent: Optional['Scope'] = None):
        self.parent = parent
        self.variables: Dict[str, Type] = {}
        self.functions: Dict[str, Type] = {}
        self.classes: Dict[str, Dict[str, Type]] = {}
        
    def lookup(self, name: str) -> Optional[Type]:
        """Look up a variable in the current scope and parent scopes."""
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup(name)
        return None
        
    def lookup_function(self, name: str) -> Optional[Type]:
        """Look up a function in the current scope and parent scopes."""
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.lookup_function(name)
        return None
        
    def lookup_class(self, name: str) -> Optional[Dict[str, Type]]:
        """Look up a class in the current scope and parent scopes."""
        if name in self.classes:
            return self.classes[name]
        if self.parent:
            return self.parent.lookup_class(name)
        return None

class SemanticAnalyzer:
    """Performs semantic analysis on JavaScript code."""
    
    def __init__(self):
        """Initialize the semantic analyzer."""
        self.parser = JavaScriptParserAdapter()
        self.global_scope = Scope()
        self.context_map: Dict[str, Dict[str, Any]] = {}
        
        # Initialize built-in types
        self._init_builtin_types()
        
    def _init_builtin_types(self):
        """Initialize built-in JavaScript types."""
        builtin_types = {
            'number': Type('number'),
            'string': Type('string'),
            'boolean': Type('boolean'),
            'object': Type('object'),
            'array': Type('array', is_array=True),
            'function': Type('function'),
            'undefined': Type('undefined'),
            'null': Type('null'),
            'symbol': Type('symbol'),
            'bigint': Type('bigint'),
            'Promise': Type('Promise'),
            'Date': Type('Date'),
            'RegExp': Type('RegExp'),
            'Error': Type('Error'),
            'Map': Type('Map'),
            'Set': Type('Set'),
            'WeakMap': Type('WeakMap'),
            'WeakSet': Type('WeakSet')
        }
        
        for name, type_info in builtin_types.items():
            self.global_scope.variables[name] = type_info
            
    def analyze_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Analyze a JavaScript file for semantic information.
        
        Args:
            file_path: Path to the JavaScript file
            content: File contents
            
        Returns:
            Dictionary containing semantic analysis results
        """
        # Parse the file
        try:
            ast = self.parser.parse(content)
        except Exception as e:
            return {
                'error': str(e),
                'types': {},
                'contexts': {}
            }
            
        # Create file scope
        file_scope = Scope(self.global_scope)
        
        # Analyze the AST
        types = self._analyze_ast(ast, file_scope)
        
        # Build context map
        contexts = self._build_context_map(ast, file_scope)
        
        # Store results
        self.context_map[file_path] = {
            'types': types,
            'contexts': contexts,
            'scope': file_scope
        }
        
        return {
            'types': types,
            'contexts': contexts
        }
        
    def _analyze_ast(self, ast: Any, scope: Scope) -> Dict[str, Type]:
        """Analyze the AST and infer types.
        
        Args:
            ast: Abstract syntax tree
            scope: Current scope
            
        Returns:
            Dictionary of variable names to their inferred types
        """
        types = {}
        
        for node in self._traverse_ast(ast):
            if node.get('type') == 'variable_declaration':
                # Handle variable declarations
                for decl in node.get('declarations', []):
                    name = decl.get('id', {}).get('name')
                    if name:
                        type_info = self._infer_type(decl.get('init'), scope)
                        scope.variables[name] = type_info
                        types[name] = type_info
                        
            elif node.get('type') == 'function_declaration':
                # Handle function declarations
                name = node.get('id', {}).get('name')
                if name:
                    type_info = self._infer_function_type(node, scope)
                    scope.functions[name] = type_info
                    types[name] = type_info
                    
            elif node.get('type') == 'class_declaration':
                # Handle class declarations
                name = node.get('id', {}).get('name')
                if name:
                    class_info = self._analyze_class(node, scope)
                    scope.classes[name] = class_info
                    types[name] = Type(name)  # Class type
                    
        return types
        
    def _infer_type(self, node: Any, scope: Scope) -> Type:
        """Infer the type of a node.
        
        Args:
            node: AST node
            scope: Current scope
            
        Returns:
            Inferred type
        """
        if not node:
            return Type('undefined')
            
        node_type = node.get('type')
        
        if node_type == 'numeric_literal':
            return Type('number')
        elif node_type == 'string_literal':
            return Type('string')
        elif node_type == 'boolean_literal':
            return Type('boolean')
        elif node_type == 'array_expression':
            element_type = Type('any')
            if node.get('elements'):
                element_type = self._infer_type(node['elements'][0], scope)
            return Type(element_type.name, is_array=True)
        elif node_type == 'object_expression':
            return Type('object')
        elif node_type == 'identifier':
            # Look up variable type
            var_type = scope.lookup(node.get('name'))
            return var_type or Type('any')
        elif node_type == 'call_expression':
            # Infer type from function call
            func_type = self._infer_type(node.get('callee'), scope)
            return func_type
        elif node_type == 'member_expression':
            # Handle property access
            obj_type = self._infer_type(node.get('object'), scope)
            prop_name = node.get('property', {}).get('name')
            if prop_name and obj_type.name in scope.classes:
                class_info = scope.classes[obj_type.name]
                return class_info.get(prop_name, Type('any'))
            return Type('any')
            
        return Type('any')
        
    def _infer_function_type(self, node: Any, scope: Scope) -> Type:
        """Infer the type of a function.
        
        Args:
            node: Function declaration node
            scope: Current scope
            
        Returns:
            Function type
        """
        # Create new scope for function parameters
        func_scope = Scope(scope)
        
        # Analyze parameters
        params = node.get('params', [])
        param_types = []
        for param in params:
            if param.get('type') == 'identifier':
                name = param.get('name')
                type_info = Type('any')  # Default to any
                func_scope.variables[name] = type_info
                param_types.append(type_info)
                
        # Analyze return type
        body = node.get('body', {})
        return_type = Type('void')
        if body.get('type') == 'block_statement':
            for stmt in body.get('body', []):
                if stmt.get('type') == 'return_statement':
                    return_type = self._infer_type(stmt.get('argument'), func_scope)
                    break
                    
        return Type('function', is_array=False)
        
    def _analyze_class(self, node: Any, scope: Scope) -> Dict[str, Type]:
        """Analyze a class declaration.
        
        Args:
            node: Class declaration node
            scope: Current scope
            
        Returns:
            Dictionary of class members to their types
        """
        class_info = {}
        
        # Analyze class body
        body = node.get('body', {})
        if body.get('type') == 'class_body':
            for member in body.get('body', []):
                if member.get('type') == 'method_definition':
                    name = member.get('key', {}).get('name')
                    if name:
                        class_info[name] = self._infer_function_type(member, scope)
                elif member.get('type') == 'property_definition':
                    name = member.get('key', {}).get('name')
                    if name:
                        class_info[name] = self._infer_type(member.get('value'), scope)
                        
        return class_info
        
    def _build_context_map(self, ast: Any, scope: Scope) -> Dict[str, Any]:
        """Build a map of code contexts.
        
        Args:
            ast: Abstract syntax tree
            scope: Current scope
            
        Returns:
            Dictionary mapping contexts to their information
        """
        contexts = {}
        
        for node in self._traverse_ast(ast):
            if node.get('type') == 'function_declaration':
                # Function context
                name = node.get('id', {}).get('name')
                if name:
                    contexts[name] = {
                        'type': 'function',
                        'scope': self._get_scope_info(scope),
                        'parameters': self._get_parameters_info(node),
                        'return_type': self._infer_function_type(node, scope)
                    }
            elif node.get('type') == 'class_declaration':
                # Class context
                name = node.get('id', {}).get('name')
                if name:
                    contexts[name] = {
                        'type': 'class',
                        'scope': self._get_scope_info(scope),
                        'methods': self._get_class_methods_info(node),
                        'properties': self._get_class_properties_info(node)
                    }
            elif node.get('type') == 'variable_declaration':
                # Variable context
                for decl in node.get('declarations', []):
                    name = decl.get('id', {}).get('name')
                    if name:
                        contexts[name] = {
                            'type': 'variable',
                            'scope': self._get_scope_info(scope),
                            'value_type': self._infer_type(decl.get('init'), scope)
                        }
                        
        return contexts
        
    def _get_scope_info(self, scope: Scope) -> Dict[str, Any]:
        """Get information about a scope.
        
        Args:
            scope: Scope to analyze
            
        Returns:
            Dictionary containing scope information
        """
        return {
            'variables': {name: str(type_info) for name, type_info in scope.variables.items()},
            'functions': {name: str(type_info) for name, type_info in scope.functions.items()},
            'classes': {name: {prop: str(type_info) for prop, type_info in class_info.items()}
                      for name, class_info in scope.classes.items()}
        }
        
    def _get_parameters_info(self, node: Any) -> List[Dict[str, Any]]:
        """Get information about function parameters.
        
        Args:
            node: Function declaration node
            
        Returns:
            List of parameter information dictionaries
        """
        params = []
        for param in node.get('params', []):
            if param.get('type') == 'identifier':
                params.append({
                    'name': param.get('name'),
                    'type': str(Type('any'))  # Default to any
                })
        return params
        
    def _get_class_methods_info(self, node: Any) -> Dict[str, Any]:
        """Get information about class methods.
        
        Args:
            node: Class declaration node
            
        Returns:
            Dictionary mapping method names to their information
        """
        methods = {}
        body = node.get('body', {})
        if body.get('type') == 'class_body':
            for member in body.get('body', []):
                if member.get('type') == 'method_definition':
                    name = member.get('key', {}).get('name')
                    if name:
                        methods[name] = {
                            'type': 'method',
                            'return_type': str(Type('any'))  # Default to any
                        }
        return methods
        
    def _get_class_properties_info(self, node: Any) -> Dict[str, Any]:
        """Get information about class properties.
        
        Args:
            node: Class declaration node
            
        Returns:
            Dictionary mapping property names to their information
        """
        properties = {}
        body = node.get('body', {})
        if body.get('type') == 'class_body':
            for member in body.get('body', []):
                if member.get('type') == 'property_definition':
                    name = member.get('key', {}).get('name')
                    if name:
                        properties[name] = {
                            'type': 'property',
                            'value_type': str(Type('any'))  # Default to any
                        }
        return properties
        
    def _traverse_ast(self, node: Any) -> List[Any]:
        """Traverse the AST and yield nodes.
        
        Args:
            node: AST node
            
        Returns:
            List of nodes
        """
        nodes = [node]
        for child in node.get('children', []):
            nodes.extend(self._traverse_ast(child))
        return nodes 