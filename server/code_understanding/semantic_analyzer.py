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
            # DEBUG: Inspect the returned AST and its root node
            print(f"DEBUG SEMANTIC_ANALYZER: Parsed AST type: {type(ast)}")
            if hasattr(ast, 'root_node'):
                root = ast.root_node
                print(f"DEBUG SEMANTIC_ANALYZER: Root node type: {type(root)}, Has type attr? {hasattr(root, 'type')}, Type: {getattr(root, 'type', 'N/A')}")
                print(f"DEBUG SEMANTIC_ANALYZER: Root node children count: {len(root.children) if hasattr(root, 'children') else 'N/A'}")
            else:
                print(f"DEBUG SEMANTIC_ANALYZER: AST object has no 'root_node' attribute.")
                # Handle case where parse might return something unexpected
                return {'error': 'Parser returned unexpected object', 'types': {}, 'contexts': {}} 
        except Exception as e:
            print(f"DEBUG SEMANTIC_ANALYZER: Parsing failed with exception: {e}") # ADDED
            return {
                'error': str(e),
                'types': {},
                'contexts': {}
            }
            
        # Create file scope
        file_scope = Scope(self.global_scope)
        
        # Analyze the AST root node
        # Ensure root_node is valid before proceeding
        if not hasattr(ast, 'root_node') or not hasattr(ast.root_node, 'type'):
             print("DEBUG SEMANTIC_ANALYZER: Skipping analysis due to invalid root node.")
             return {'types': {}, 'contexts': {}} # Return empty if root is bad
             
        types = self._analyze_ast(ast.root_node, file_scope)
        
        # Build context map from the root node
        contexts = self._build_context_map(ast.root_node, file_scope)
        
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
            # Access attributes directly instead of using .get()
            node_type = node.type if hasattr(node, 'type') else None 
            
            if node_type == 'variable_declaration':
                # Assuming MockNode structure mirrors TS node structure somewhat
                # Need to adapt based on actual MockNode fields for declarations
                # This part might need further refinement based on MockNode details
                if hasattr(node, 'children'): # Check if children exist
                    for decl_node in node.children: # Iterate through potential declarators
                        if hasattr(decl_node, 'type') and decl_node.type == 'variable_declarator':
                            name_node = decl_node.child_by_field_name('name') if hasattr(decl_node, 'child_by_field_name') else None
                            init_node = decl_node.child_by_field_name('value') if hasattr(decl_node, 'child_by_field_name') else None # Assuming 'value' field for initializer
                            
                            name = name_node.text if hasattr(name_node, 'text') else None
                            if name:
                                type_info = self._infer_type(init_node, scope)
                                scope.variables[name] = type_info
                                types[name] = type_info
                        
            elif node_type == 'function_declaration':
                # Assuming MockNode has child_by_field_name or similar
                name_node = node.child_by_field_name('name') if hasattr(node, 'child_by_field_name') else None
                name_str = None

                if name_node:
                    name_bytes = getattr(name_node, 'text', None)
                    if isinstance(name_bytes, bytes):
                        name_str = name_bytes.decode('utf-8')
                    elif isinstance(name_bytes, str):
                        name_str = name_bytes
                
                if name_str: # Use the decoded string name
                    type_info = self._infer_function_type(node, scope)
                    scope.functions[name_str] = type_info
                    types[name_str] = type_info
                    
            elif node_type == 'class_declaration':
                # Get name node using child_by_field_name for tree-sitter nodes
                name_node = node.child_by_field_name('name') if hasattr(node, 'child_by_field_name') else None
                name_str = None

                if name_node:
                    name_bytes = getattr(name_node, 'text', None)
                    if isinstance(name_bytes, bytes):
                        name_str = name_bytes.decode('utf-8')
                    elif isinstance(name_bytes, str):
                        name_str = name_bytes
                
                if name_str: # Use the decoded string name
                    # --- Correct Logic for _analyze_ast --- 
                    # 1. Add type definition to the types dictionary.
                    # 2. Add type definition to the current scope.
                    # 3. Optionally call _analyze_class (which is currently a placeholder)
                    #    to potentially populate scope.classes for detailed analysis later.
                    # --- DO NOT assign to a 'contexts' variable here --- 
                    class_type = Type(name_str) 
                    types[name_str] = class_type 
                    scope.variables[name_str] = class_type 
                    
                    class_info = self._analyze_class(node, scope) 
                    scope.classes[name_str] = class_info 
            
        return types
        
    def _infer_type(self, node: Any, scope: Scope) -> Type:
        """Infer the type of a MockNode.

        Args:
            node: MockNode instance
            scope: Current scope

        Returns:
            Inferred type
        """
        if not node or not hasattr(node, 'type'):
            return Type('undefined')
            
        node_type = node.type # Direct attribute access
        
        if node_type == 'numeric_literal':
            return Type('number')
        elif node_type == 'string_literal':
            return Type('string')
        elif node_type == 'boolean_literal':
            return Type('boolean')
        elif node_type == 'array_expression':
            element_type = Type('any')
            # Check children for elements
            if hasattr(node, 'children') and node.children:
                # Attempt to infer type from the first element
                first_element = node.children[0]
                if hasattr(first_element, 'type'): # Ensure first element is a valid node
                     element_type = self._infer_type(first_element, scope)
                
            return Type(element_type.name, is_array=True)
            
        elif node_type == 'object_expression':
            return Type('object')
            
        elif node_type == 'identifier':
            # Look up identifier in scope
            name = node.text if hasattr(node, 'text') else None
            if name:
                type_info = scope.lookup(name)
                if type_info:
                    return type_info
            return Type('any') # Unknown identifier
            
        elif node_type == 'call_expression':
            # Infer return type of function call if possible
            callee = node.child_by_field_name('function') if hasattr(node, 'child_by_field_name') else None
            if callee and hasattr(callee, 'text'):
                func_name = callee.text
                func_type = scope.lookup_function(func_name)
                if func_type: # Assuming function type info includes return type somehow
                     # This needs refinement - how is return type stored?
                     # For now, assume function type IS the return type name
                     return Type(func_type.name) 
            return Type('any') # Cannot infer return type
            
        # Add more type inference rules as needed
        
        return Type('any') # Default to 'any' if type cannot be inferred
        
    def _infer_function_type(self, node: Any, scope: Scope) -> Type:
        """Infer the type signature of a function MockNode."""
        # Placeholder: Actual function type inference can be complex
        # Needs to analyze return statements, JSDoc, etc.
        return Type('function') # Simple placeholder
        
    def _analyze_class(self, node: Any, scope: Scope) -> Dict[str, Type]:
        """Analyze a class MockNode."""
        class_info = {'methods': {}, 'properties': {}}
        # TODO: Implement class analysis using MockNode attributes
        # Example: Iterate through node.children or use specific field access 
        # like node.child_by_field_name('body') to find methods/properties
        return class_info
        
    def _build_context_map(self, ast: Any, scope: Scope) -> Dict[str, Any]:
        """Build a map of symbol contexts (functions, classes)."""
        contexts = {}
        
        for node in self._traverse_ast(ast): # node is MockNode
            node_type = node.type if hasattr(node, 'type') else None

            if node_type == 'function_declaration':
                name_node = node.child_by_field_name('name') if hasattr(node, 'child_by_field_name') else None
                name_str = None

                if name_node:
                    name_bytes = getattr(name_node, 'text', None)
                    if isinstance(name_bytes, bytes):
                        name_str = name_bytes.decode('utf-8')
                    elif isinstance(name_bytes, str):
                        name_str = name_bytes
                
                if name_str: # Use the decoded string name
                    contexts[name_str] = {
                        'type': 'function',
                        'parameters': self._get_parameters_info(node),
                        # Placeholder for return type - needs inference
                        'return_type': 'any', 
                        'scope': self._get_scope_info(scope) 
                    }
            elif node_type == 'class_declaration':
                name_node = node.child_by_field_name('name') if hasattr(node, 'child_by_field_name') else None
                name_str = None

                if name_node:
                    name_bytes = getattr(name_node, 'text', None)
                    if isinstance(name_bytes, bytes):
                        name_str = name_bytes.decode('utf-8')
                    elif isinstance(name_bytes, str):
                        name_str = name_bytes
                
                if name_str: # Use the decoded string name
                    contexts[name_str] = {
                        'type': 'class',
                        'methods': self._get_class_methods_info(node),
                        'properties': self._get_class_properties_info(node),
                        'scope': self._get_scope_info(scope)
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
        
    def _get_parameters_info(self, node: Any) -> List[Dict[str, str]]:
        """Extract parameter info from a function or method definition tree-sitter Node."""
        params = []
        # Use child_by_field_name for tree-sitter nodes
        params_node = node.child_by_field_name('parameters') if hasattr(node, 'child_by_field_name') else None
        
        if params_node and hasattr(params_node, 'children'):
            for param_child in params_node.children:
                # The actual identifier might be nested (e.g., inside 'required_parameter')
                identifier_node = None
                if hasattr(param_child, 'type') and param_child.type == 'identifier':
                    identifier_node = param_child
                elif hasattr(param_child, 'children'):
                    # Simple search for the first identifier child if nested
                    for inner_child in param_child.children:
                        if hasattr(inner_child, 'type') and inner_child.type == 'identifier':
                            identifier_node = inner_child
                            break
                            
                if identifier_node:
                     param_name_bytes = getattr(identifier_node, 'text', None)
                     param_name = param_name_bytes.decode('utf-8') if isinstance(param_name_bytes, bytes) else param_name_bytes
                     # Placeholder for type - needs inference
                     if param_name:
                         params.append({'name': param_name, 'type': 'any'})

        return params
        
    def _get_class_methods_info(self, node: Any) -> Dict[str, Any]:
        """Extract method info from a tree-sitter Node."""
        methods = {}
        # Use child_by_field_name for tree-sitter nodes
        class_body = node.child_by_field_name('body') if hasattr(node, 'child_by_field_name') else None
        
        # Find class name (optional, mainly for debug prints)
        class_name_node = node.child_by_field_name('name') if hasattr(node, 'child_by_field_name') else None
        class_name_text = 'UNKNOWN_CLASS'
        if class_name_node:
             name_bytes = getattr(class_name_node, 'text', None)
             class_name_text = name_bytes.decode('utf-8') if isinstance(name_bytes, bytes) else name_bytes
        # print(f"DEBUG: Entered _get_class_methods_info for class: {class_name_text}")

        if class_body and hasattr(class_body, 'children'):
            # print(f"DEBUG: Found class body for {class_name_text} with {len(class_body.children)} children")
            for member in class_body.children:
                # print(f"DEBUG: Processing member type: {member.type if hasattr(member,'type') else 'NO_TYPE'}") 
                if hasattr(member, 'type') and member.type == 'method_definition':
                    # print(f"DEBUG: Found method_definition node in {class_name_text}") 
                    method_name = None
                    # Find the identifier for the method name using child_by_field_name (tree-sitter)
                    name_node = member.child_by_field_name('name') if hasattr(member, 'child_by_field_name') else None 
                    
                    if name_node and hasattr(name_node, 'type') and name_node.type == 'property_identifier':
                         method_name_bytes = getattr(name_node, 'text', None)
                         method_name = method_name_bytes.decode('utf-8') if isinstance(method_name_bytes, bytes) else method_name_bytes
                         # print(f"DEBUG: Extracted method name (from name field): {method_name}") 
                    else:
                         # Fallback: check children if name field didn't work 
                         if hasattr(member, 'children'):
                            # print(f"DEBUG: Checking children of method_definition node for property_identifier.") 
                            for child in member.children:
                                if hasattr(child, 'type') and child.type == 'property_identifier':
                                    method_name_bytes = getattr(child, 'text', None)
                                    method_name = method_name_bytes.decode('utf-8') if isinstance(method_name_bytes, bytes) else method_name_bytes
                                    # print(f"DEBUG: Found method name (property_identifier child): {method_name} in {class_name_text}") 
                                    break
                         # else:
                         #    print(f"DEBUG: Method definition node has no name field or children to check for name.")
                    
                    if method_name:
                        # print(f"DEBUG: Adding method '{method_name}' to {class_name_text}") 
                        methods[method_name] = {
                            'params': self._get_parameters_info(member),
                            'return': 'any' 
                        }
                    # else:
                    #    print(f"DEBUG: Could not extract method name for a method_definition in {class_name_text}")
        # else:
        #     print(f"DEBUG: No class body found or body has no children for {class_name_text}")

        # print(f"DEBUG: Returning methods for {class_name_text}: {methods}") 
        return methods
        
    def _get_class_properties_info(self, node: Any) -> Dict[str, Any]:
        """Extract property info from a class tree-sitter Node."""
        properties = {}
        # Use child_by_field_name for tree-sitter nodes
        class_body = node.child_by_field_name('body') if hasattr(node, 'child_by_field_name') else None
        if class_body and hasattr(class_body, 'children'):
            for member in class_body.children:
                 # Example: Look for field_definition or public_field_definition (JS grammar specific)
                 # Adjust the type check based on the actual tree-sitter grammar for JS class properties
                 # Common types might be 'public_field_definition', 'field_definition'
                 if hasattr(member, 'type') and ('field_definition' in member.type or member.type == 'property_identifier'): # Added check for simple identifiers too
                     prop_name = None
                     prop_type = 'any' # Placeholder
                     
                     # Try finding name via field first (common pattern)
                     name_node = member.child_by_field_name('name') if hasattr(member, 'child_by_field_name') else None
                     if name_node and name_node.type == 'property_identifier':
                         prop_name_bytes = getattr(name_node, 'text', None)
                         prop_name = prop_name_bytes.decode('utf-8') if isinstance(prop_name_bytes, bytes) else prop_name_bytes
                     # Fallback: if the member itself is the identifier (e.g., simple property assignment)
                     elif member.type == 'property_identifier':
                         prop_name_bytes = getattr(member, 'text', None)
                         prop_name = prop_name_bytes.decode('utf-8') if isinstance(prop_name_bytes, bytes) else prop_name_bytes
                     # Fallback: Check children if no name field found
                     elif hasattr(member, 'children'):
                        for name_cand in member.children:
                             if hasattr(name_cand, 'type') and name_cand.type == 'property_identifier':
                                  prop_name_bytes = getattr(name_cand, 'text', None)
                                  prop_name = prop_name_bytes.decode('utf-8') if isinstance(prop_name_bytes, bytes) else prop_name_bytes
                                  break
                                  
                     if prop_name:
                         # Placeholder for type info - needs inference
                         properties[prop_name] = {'type': prop_type}
        return properties
        
    def _traverse_ast(self, node):
        """Traverse the AST recursively."""
        nodes = [node]
        print(f"DEBUG TRAVERSE: Starting traversal from node type: {node.type if hasattr(node, 'type') else 'N/A'}")
        count = 0
        while nodes:
            current_node = nodes.pop(0)
            count += 1
            node_type_str = current_node.type if hasattr(current_node, 'type') else 'N/A'
            print(f"DEBUG TRAVERSE [{count}]: Yielding node type: {node_type_str}")
            yield current_node
            
            # Safely get children - Check if it has 'children' attribute
            children = []
            if hasattr(current_node, 'children'):
                children = current_node.children
            elif isinstance(current_node, dict) and 'children' in current_node:
                children = current_node['children']
                
            if children:
                 # Check if children is iterable and not empty
                try:
                    iter(children)
                    if children: # Ensure it's not an empty list/tuple
                         nodes.extend(children)
                except TypeError:
                     print(f"Warning: Children attribute is not iterable: {type(children)}") 