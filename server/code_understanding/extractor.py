"""Symbol extractor for code understanding."""

from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class SymbolExtractor:
    """Extracts symbols from syntax trees."""
    
    def __init__(self):
        """Initialize the symbol extractor."""
        self.symbols: Dict[str, Dict[str, Any]] = {}
        self.references: Dict[str, List[Dict[str, Any]]] = {
            'imports': [],
            'calls': [],
            'attributes': [],
            'variables': []
        }
        self.current_scope: Optional[str] = None
        
    def extract_symbols(self, tree: Any) -> tuple[Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """Extract symbols from a syntax tree.
        
        Args:
            tree: Syntax tree to analyze
            
        Returns:
            Tuple of (symbols dict, references dict)
        """
        try:
            self.symbols.clear()
            self.references.clear()
            self.current_scope = 'global'
            
            self._process_node(tree)
            return self.symbols, self.references
            
        except Exception as e:
            logger.error(f"Failed to extract symbols: {e}")
            return {}, {'imports': [], 'calls': [], 'attributes': [], 'variables': []}
            
    def extract_references(self, tree: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Extract references from a syntax tree.
        
        Args:
            tree: Syntax tree to analyze
            
        Returns:
            Dictionary of references
        """
        try:
            self.references.clear()
            self.current_scope = 'global'
            
            self._process_node(tree)
            return self.references
            
        except Exception as e:
            logger.error(f"Failed to extract references: {e}")
            return {'imports': [], 'calls': [], 'attributes': [], 'variables': []}
            
    def _process_node(self, node: Any, parent_scope: Optional[str] = None):
        """Process a syntax tree node and extract symbols.
        
        Args:
            node: Syntax tree node
            parent_scope: Parent scope name
        """
        try:
            if not node:
                return
                
            # Store old scope to restore later
            old_scope = self.current_scope
            
            # Update current scope if parent_scope is provided
            if parent_scope:
                self.current_scope = parent_scope
            elif not self.current_scope:
                self.current_scope = 'global'
                
            # Process node based on type
            if node.type == 'import_statement' or node.type == 'import':
                self._process_import(node)
            elif node.type == 'function_definition':
                self._process_function(node)
                # Process function body with function name as scope
                body_node = node.child_by_field_name('body')
                if body_node:
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        self._process_node(body_node, name_node.text)
            elif node.type == 'class_definition':
                self._process_class(node)
                # Process class body with class name as scope
                body_node = node.child_by_field_name('body')
                if body_node:
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        self._process_node(body_node, name_node.text)
            elif node.type == 'identifier':
                self._process_identifier(node)
            elif node.type == 'assignment':
                self._process_assignment(node)
                
            # Process children if not already processed
            if hasattr(node, 'children') and node.type not in ['function_definition', 'class_definition']:
                for child in node.children:
                    self._process_node(child, self.current_scope)
                    
            # Restore old scope
            self.current_scope = old_scope
                    
        except Exception as e:
            logger.error(f"Failed to process node: {e}")
            
    def _process_import(self, node: Any):
        """Process an import statement node.
        
        Args:
            node: Import statement node
        """
        try:
            text = node.text.strip()
            if text.startswith('import '):
                # Simple import
                modules = text[7:].split(',')  # Skip 'import ' and split on comma
                for module in modules:
                    module = module.strip()
                    # Handle aliases
                    if ' as ' in module:
                        module, alias = module.split(' as ')
                        module = module.strip()
                        alias = alias.strip()
                        self.symbols[alias] = {
                            'type': 'import',
                            'scope': self.current_scope,
                            'start': node.start_point,
                            'end': node.end_point,
                            'module': module,
                            'alias': alias
                        }
                    else:
                        self.symbols[module] = {
                            'type': 'import',
                            'scope': self.current_scope,
                            'start': node.start_point,
                            'end': node.end_point,
                            'module': module
                        }
            elif text.startswith('from '):
                # From import
                parts = text.split(' import ')
                if len(parts) == 2:
                    module = parts[0][5:].strip()  # Skip 'from '
                    names = [n.strip() for n in parts[1].split(',')]
                    for name in names:
                        # Handle aliases
                        if ' as ' in name:
                            name, alias = name.split(' as ')
                            name = name.strip()
                            alias = alias.strip()
                            self.symbols[alias] = {
                                'type': 'import',
                                'scope': self.current_scope,
                                'start': node.start_point,
                                'end': node.end_point,
                                'module': module,
                                'symbol': name,
                                'alias': alias
                            }
                        else:
                            self.symbols[name] = {
                                'type': 'import',
                                'scope': self.current_scope,
                                'start': node.start_point,
                                'end': node.end_point,
                                'module': module,
                                'symbol': name
                            }
                        
        except Exception as e:
            logger.error(f"Failed to process import: {e}")
            
    def _process_function(self, node: Any):
        """Process a function definition node.
        
        Args:
            node: Function definition node
        """
        try:
            # Get function name
            name_node = node.child_by_field_name('name')
            if not name_node:
                return
                
            # Add function symbol
            symbol_name = name_node.text
            self.symbols[symbol_name] = {
                'type': 'function',
                'scope': self.current_scope,
                'start': node.start_point,
                'end': node.end_point,
                'params': []
            }
            
            # Process parameters
            params_node = node.child_by_field_name('parameters')
            if params_node:
                for param in params_node.children:
                    if param.type == 'identifier':
                        param_text = param.text
                        param_name = param_text.split(':')[0].strip()
                        self.symbols[symbol_name]['params'].append(param_name)
                        
                        # Add parameter as a symbol in function scope
                        self.symbols[param_name] = {
                            'type': 'parameter',
                            'scope': symbol_name,
                            'start': param.start_point,
                            'end': param.end_point
                        }
                        
        except Exception as e:
            logger.error(f"Failed to process function: {e}")
            
    def _process_class(self, node: Any):
        """Process a class definition node.
        
        Args:
            node: Class definition node
        """
        try:
            # Get class name
            name_node = node.child_by_field_name('name')
            if not name_node:
                return
                
            # Add class symbol
            symbol_name = name_node.text
            self.symbols[symbol_name] = {
                'type': 'class',
                'scope': self.current_scope,
                'start': node.start_point,
                'end': node.end_point,
                'bases': []
            }
            
            # Process base classes
            bases_node = node.child_by_field_name('bases')
            if bases_node:
                for base in bases_node.children:
                    if base.type == 'identifier':
                        self.symbols[symbol_name]['bases'].append(base.text)
                        
        except Exception as e:
            logger.error(f"Failed to process class: {e}")
            
    def _process_identifier(self, node: Any):
        """Process an identifier node.
        
        Args:
            node: Identifier node
        """
        try:
            # Add reference
            symbol_name = node.text
            if symbol_name not in self.references['attributes']:
                self.references['attributes'].append({
                    'scope': self.current_scope,
                    'start': node.start_point,
                    'end': node.end_point
                })
                
            # Add symbol if not already present and not a parameter
            if (symbol_name not in self.symbols and 
                not any(s.get('type') == 'parameter' and s.get('scope') == self.current_scope 
                       for s in self.symbols.values())):
                self.symbols[symbol_name] = {
                    'type': 'identifier',
                    'scope': self.current_scope,
                    'start': node.start_point,
                    'end': node.end_point
                }
                
        except Exception as e:
            logger.error(f"Failed to process identifier: {e}")
            
    def _process_assignment(self, node: Any):
        """Process an assignment node.
        
        Args:
            node: Assignment node
        """
        try:
            # Get left side (target) of assignment
            left_node = node.child_by_field_name('left')
            if not left_node or left_node.type != 'identifier':
                return
                
            # Get right side (value) of assignment
            right_node = node.child_by_field_name('right')
            
            # Add or update symbol
            symbol_name = left_node.text
            self.symbols[symbol_name] = {
                'type': 'variable',
                'scope': self.current_scope,
                'start': node.start_point,
                'end': node.end_point
            }
            
            # Process right side for references
            if right_node:
                self._process_node(right_node, self.current_scope)
                
        except Exception as e:
            logger.error(f"Failed to process assignment: {e}")
            
    def get_symbols(self) -> Dict[str, Any]:
        """Get extracted symbols.
        
        Returns:
            Dict containing extracted symbols
        """
        return self.symbols
        
    def get_references(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get extracted references.
        
        Returns:
            Dict containing extracted references
        """
        return self.references 