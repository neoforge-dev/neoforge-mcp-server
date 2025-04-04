"""Symbol extractor module for extracting symbols from syntax trees."""

from typing import Dict, List, Any, Optional, Set
import logging
from .parser import MockNode as Node, MockTree as Tree

logger = logging.getLogger(__name__)

class SymbolExtractor:
    """Extractor class that extracts symbols from syntax trees."""
    
    def __init__(self):
        """Initialize the symbol extractor."""
        self.current_scope = None
        self.symbols = {}
        self.references = {}
        
    def extract_symbols(self, tree: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Extract symbols from the tree.

        Args:
            tree: Syntax tree

        Returns:
            Dictionary of symbols
        """
        symbols = {
            'functions': [],
            'classes': [],
            'variables': []
        }

        if tree.root_node.type == 'program':
            for node in tree.root_node.children:
                if node.type == 'function_declaration':
                    name_node = node.fields.get('name')
                    if name_node:
                        symbols['functions'].append({
                            'name': name_node.text,
                            'start_line': node.start_point[0],
                            'end_line': node.end_point[0]
                        })
                elif node.type == 'class_declaration':
                    name_node = node.fields.get('name')
                    if name_node:
                        symbols['classes'].append({
                            'name': name_node.text,
                            'start_line': node.start_point[0],
                            'end_line': node.end_point[0]
                        })
                elif node.type in ('variable_declaration', 'lexical_declaration'):
                    # Handle both var and let/const declarations
                    for child in node.children:
                        if child.type == 'variable_declarator':
                            name_node = child.fields.get('name')
                            if name_node:
                                symbols['variables'].append({
                                    'name': name_node.text,
                                    'start_line': node.start_point[0],
                                    'end_line': node.end_point[0]
                                })

        return symbols
    
    def _process_node(self, node: Node) -> None:
        """Process a node in the syntax tree.
        
        Args:
            node: Node to process
        """
        try:
            if not node:
                return
                
            # Update current scope
            if node.type in ('function_definition', 'class_definition'):
                name_node = node.child_by_field_name('name')
                if name_node:
                    scope_name = self._get_node_text(name_node)
                    old_scope = self.current_scope
                    self.current_scope = f"{old_scope}.{scope_name}" if old_scope else scope_name
                    
                    # Process the node
                    if node.type == 'function_definition':
                        self._process_function(node)
                    else:
                        self._process_class(node)
                        
                    # Process body with updated scope
                    for child in node.children_by_field_name('body'):
                        self._process_node(child)
                        
                    self.current_scope = old_scope
                    return
            
            # Process other node types
            if node.type == 'import':
                self._process_import(node)
            elif node.type == 'identifier':
                self._process_identifier(node)
            elif node.type == 'assignment':
                self._process_assignment(node)
                
            # Process children
            for child in node.children:
                self._process_node(child)
        except Exception as e:
            logger.error(f"Failed to process node: {e}")
    
    def _process_identifier(self, node: Node) -> None:
        """Process an identifier node.
        
        Args:
            node: Identifier node
        """
        try:
            name = self._get_node_text(node)
            if name:
                # Add reference with current scope
                self._add_reference(name, {
                    'scope': self.current_scope or 'global',
                    'start': node.start_point,
                    'end': node.end_point
                })
                
                # If not already a symbol and not a parameter, add it as a variable
                if name not in self.symbols and not self._is_parameter(name):
                    self.symbols[name] = {
                        'type': 'variable',
                        'scope': self.current_scope or 'global',
                        'start': node.start_point,
                        'end': node.end_point
                    }
        except Exception as e:
            logger.error(f"Failed to process identifier: {e}")
    
    def _process_import(self, node: Node) -> None:
        """Process an import statement node.
        
        Args:
            node: Import statement node
        """
        try:
            # Extract imported names from the text
            text = self._get_node_text(node)
            
            if text.startswith('import '):
                # Simple import: "import os, sys"
                module_names = [name.strip() for name in text[7:].split(',')]
                for module_name in module_names:
                    module_name = module_name.strip()
                    if module_name:
                        # Extract just the module name without any 'as' alias
                        if ' as ' in module_name:
                            module_name = module_name.split(' as ')[0].strip()
                        self.symbols[module_name] = {
                            'type': 'import',
                            'scope': self.current_scope or 'global',
                            'start': node.start_point,
                            'end': node.end_point
                        }
            elif text.startswith('from '):
                # From import: "from typing import List, Optional"
                parts = text.split(' import ')
                if len(parts) == 2:
                    module = parts[0].replace('from ', '').strip()
                    # Split by comma and handle each import
                    imported_names = [name.strip() for name in parts[1].split(',')]
                    for name in imported_names:
                        name = name.strip()
                        if name:
                            # Extract just the name without any 'as' alias
                            if ' as ' in name:
                                name = name.split(' as ')[0].strip()
                            self.symbols[name] = {
                                'type': 'import',
                                'scope': self.current_scope or 'global',
                                'start': node.start_point,
                                'end': node.end_point,
                                'module': module
                            }
                            # Add the module itself as a symbol
                            if module not in self.symbols:
                                self.symbols[module] = {
                                    'type': 'import',
                                    'scope': self.current_scope or 'global',
                                    'start': node.start_point,
                                    'end': node.end_point
                                }
        except Exception as e:
            logger.error(f"Failed to process import: {e}")
    
    def _process_function(self, node: Node) -> None:
        """Process a function definition node.
        
        Args:
            node: Function definition node
        """
        try:
            name_node = node.child_by_field_name('name')
            if name_node:
                func_name = self._get_node_text(name_node)
                params = []
                
                # Process parameters
                params_node = node.child_by_field_name('parameters')
                if params_node:
                    for param in params_node.children:
                        if param.type == 'identifier':
                            param_text = self._get_node_text(param)
                            if ':' in param_text:
                                param_name = param_text.split(':')[0].strip()
                                param_type = param_text.split(':')[1].strip()
                            else:
                                param_name = param_text
                                param_type = 'Any'
                            params.append(param_name)
                            # Add parameter as a symbol in function scope
                            self.symbols[param_name] = {
                                'type': param_type,
                                'scope': f"{self.current_scope}.{func_name}" if self.current_scope else func_name,
                                'start': param.start_point,
                                'end': param.end_point
                            }
                
                # Add function to symbols
                self.symbols[func_name] = {
                    'type': 'function',
                    'scope': self.current_scope or 'global',
                    'start': node.start_point,
                    'end': node.end_point,
                    'params': params
                }
                
                # Process function body with updated scope
                old_scope = self.current_scope
                self.current_scope = f"{old_scope}.{func_name}" if old_scope else func_name
                
                for child in node.children_by_field_name('body'):
                    self._process_node(child)
                    
                self.current_scope = old_scope
        except Exception as e:
            logger.error(f"Failed to process function: {e}")
    
    def _process_class(self, node: Node) -> None:
        """Process a class definition node.
        
        Args:
            node: Class definition node
        """
        try:
            name_node = node.child_by_field_name('name')
            if name_node:
                class_name = self._get_node_text(name_node)
                bases = self._get_class_bases(node)
                self._add_symbol(class_name, {
                    'type': 'class',
                    'scope': self.current_scope,
                    'bases': bases,
                    'start': node.start_point,
                    'end': node.end_point
                })
        except Exception as e:
            logger.error(f"Failed to process class: {e}")
    
    def _process_assignment(self, node: Node) -> None:
        """Process an assignment node.
        
        Args:
            node: Assignment node
        """
        try:
            left = node.child_by_field_name('left')
            right = node.child_by_field_name('right')
            
            if left and left.type == 'identifier':
                name = self._get_node_text(left)
                if name:
                    # Get type from right side if available
                    type_info = 'Any'
                    if right:
                        type_info = self._get_type_info(right)
                    
                    # Add or update symbol
                    self.symbols[name] = {
                        'type': type_info,
                        'scope': self.current_scope or 'global',
                        'start': node.start_point,
                        'end': node.end_point
                    }
                    
                    # Process right side for references
                    if right:
                        self._process_node(right)
        except Exception as e:
            logger.error(f"Failed to process assignment: {e}")
    
    def _add_symbol(self, name: str, info: Dict[str, Any]) -> None:
        """Add a symbol to the symbols dictionary.
        
        Args:
            name: Symbol name
            info: Symbol information
        """
        self.symbols[name] = info
    
    def _add_reference(self, name: str, ref: Dict[str, Any]) -> None:
        """Add a reference to a name.
        
        Args:
            name: Name being referenced
            ref: Reference information
        """
        try:
            if name not in self.references:
                self.references[name] = []
            self.references[name].append(ref)
        except Exception as e:
            logger.error(f"Failed to add reference: {e}")
    
    def _find_child(self, node: Node, child_type: str) -> Optional[Node]:
        """Find a child node of a specific type.
        
        Args:
            node: Parent node
            child_type: Type of child to find
            
        Returns:
            Node: Found child node or None
        """
        try:
            for child in node.children:
                if child.type == child_type:
                    return child
            return None
        except Exception as e:
            logger.error(f"Failed to find child: {e}")
            return None
    
    def _get_node_text(self, node: Node) -> str:
        """Get text from a node.
        
        Args:
            node: Node to get text from
            
        Returns:
            Text from the node
        """
        try:
            if not node or not node.text:
                return ""
            
            # Handle bytes
            if isinstance(node.text, bytes):
                return node.text.decode('utf-8').strip()
            
            # Handle non-string types
            if not isinstance(node.text, str):
                return ""
            
            return node.text.strip()
        except Exception as e:
            logger.error(f"Failed to get node text: {e}")
            return ""
    
    def _get_function_params(self, node: Node) -> List[str]:
        """Get function parameters.
        
        Args:
            node: Function definition node
            
        Returns:
            List of parameter strings
        """
        params = []
        try:
            params_node = node.child_by_field_name('parameters')
            if params_node:
                for param in params_node.children:
                    param_text = self._get_node_text(param)
                    if param_text and param_text not in ('self', 'cls'):
                        if ':' in param_text:
                            name = param_text.split(':')[0].strip()
                            params.append(name)
                        else:
                            params.append(param_text)
        except Exception as e:
            logger.error(f"Failed to get function parameters: {e}")
        return params
    
    def _get_class_bases(self, node: Node) -> List[str]:
        """Get class base classes.
        
        Args:
            node: Class definition node
            
        Returns:
            List[str]: List of base class names
        """
        try:
            bases = []
            bases_node = node.child_by_field_name('bases')
            if bases_node:
                for base in bases_node.children:
                    if base.type == 'identifier':
                        bases.append(self._get_node_text(base))
            return bases
        except Exception as e:
            logger.error(f"Failed to get class bases: {e}")
            return []

    def _get_type_info(self, node: Optional[Node]) -> str:
        """Get type information from a node.
        
        Args:
            node: Node to get type info from
            
        Returns:
            Type string
        """
        if not node:
            return 'Any'
            
        try:
            text = self._get_node_text(node)
            if ':' in text:
                _, type_hint = text.split(':', 1)
                return type_hint.strip()
                
            if node.type == 'string':
                return 'str'
            elif node.type == 'integer':
                return 'int'
            elif node.type == 'float':
                return 'float'
            elif node.type == 'true' or node.type == 'false':
                return 'bool'
            elif node.type == 'list':
                return 'List'
            elif node.type == 'dict':
                return 'Dict'
            elif node.type == 'call':
                return self._get_node_text(node)
            elif node.type == 'identifier':
                return self._get_node_text(node)
            else:
                return 'Any'
        except Exception as e:
            logger.error(f"Failed to get type info: {e}")
            return 'Any'

    def _is_parameter(self, name: str) -> bool:
        """Check if a name is a parameter in the current scope.
        
        Args:
            name: Name to check
            
        Returns:
            True if the name is a parameter, False otherwise
        """
        try:
            if not self.current_scope:
                return False
                
            # Check if the name is a parameter in any parent scope
            scope = self.current_scope
            while scope:
                for symbol in self.symbols.values():
                    if (symbol.get('scope') == scope and 
                        symbol.get('type') == 'function' and 
                        name in symbol.get('params', [])):
                        return True
                # Move up to parent scope
                scope = scope.rsplit('.', 1)[0] if '.' in scope else None
            return False
        except Exception as e:
            logger.error(f"Failed to check if name is parameter: {e}")
            return False