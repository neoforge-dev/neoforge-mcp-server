"""Symbol extractor for code understanding."""

from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class SymbolExtractor:
    """Extracts symbols from syntax trees."""
    
    def __init__(self):
        """Initialize the symbol extractor."""
        self.symbols = {
            'imports': [],
            'functions': [],
            'classes': [],
            'variables': []
        }
        self.references = {
            'calls': [],
            'attributes': [],
            'variables': []
        }
        self.current_scope = None
        self.current_file = None
        self.file_contexts = {}
        
    def extract_symbols(self, tree: Any, file_path: str = None, file_contexts: Dict[str, Any] = None) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
        """Extract symbols from a syntax tree.
        
        Args:
            tree: Syntax tree to analyze
            file_path: Path to the current file
            file_contexts: Dictionary of file contexts
            
        Returns:
            Tuple of (symbols, references)
        """
        try:
            self.symbols = {
                'imports': [],
                'functions': [],
                'classes': [],
                'variables': []
            }
            self.references = {
                'calls': [],
                'attributes': [],
                'variables': []
            }
            self.current_scope = 'global'
            self.current_file = file_path
            self.file_contexts = file_contexts or {}
            
            # Process root node if it exists
            if hasattr(tree, 'root_node') and tree.root_node:
                self._process_node(tree.root_node)
            elif hasattr(tree, 'type'):
                self._process_node(tree)
            
            return self.symbols, self.references
            
        except Exception as e:
            logger.error(f"Failed to extract symbols: {e}")
            return {}, {}
            
    def extract_references(self, tree: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Extract references from a syntax tree.
        
        Args:
            tree: Syntax tree to analyze
            
        Returns:
            Dictionary of references
        """
        try:
            self.references = {
                'calls': [],
                'attributes': [],
                'variables': []
            }
            self.current_scope = 'global'
            
            self._process_node(tree)
            return self.references
            
        except Exception as e:
            logger.error(f"Failed to extract references: {e}")
            return {}
            
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
            if hasattr(node, 'type'):
                if node.type == 'import':
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
            if hasattr(node, 'children'):
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
                        self.symbols['imports'].append({
                            'module': module,
                            'alias': alias,
                            'start_line': node.start_point[0],
                            'end_line': node.end_point[0]
                        })
                    else:
                        self.symbols['imports'].append({
                            'module': module,
                            'start_line': node.start_point[0],
                            'end_line': node.end_point[0]
                        })
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
                            self.symbols['imports'].append({
                                'module': module,
                                'symbol': name,
                                'alias': alias,
                                'start_line': node.start_point[0],
                                'end_line': node.end_point[0]
                            })
                        else:
                            self.symbols['imports'].append({
                                'module': module,
                                'symbol': name.strip(),
                                'start_line': node.start_point[0],
                                'end_line': node.end_point[0]
                            })
                        
        except Exception as e:
            logger.error(f"Failed to process import: {e}")
            
    def _process_function(self, node: Any):
        """Process a function definition node.
        
        Args:
            node: Function definition node
        """
        try:
            name_node = node.child_by_field_name('name')
            if name_node:
                func_info = {
                    'name': name_node.text,
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0],
                    'parameters': []
                }
                
                # Process parameters
                params_node = node.child_by_field_name('parameters')
                if params_node:
                    for param in params_node.children:
                        if param.type == 'identifier':
                            func_info['parameters'].append({
                                'name': param.text,
                                'start_line': param.start_point[0],
                                'end_line': param.end_point[0]
                            })
                
                self.symbols['functions'].append(func_info)
                
        except Exception as e:
            logger.error(f"Failed to process function: {e}")
            
    def _process_class(self, node: Any):
        """Process a class definition node.
        
        Args:
            node: Class definition node
        """
        try:
            name_node = node.child_by_field_name('name')
            if name_node:
                class_info = {
                    'name': name_node.text,
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0],
                    'bases': [],
                    'methods': []
                }
                
                # Process base classes
                bases_node = node.child_by_field_name('bases')
                if bases_node:
                    for base in bases_node.children:
                        if base.type == 'identifier':
                            # Check if base class is imported
                            base_name = base.text
                            base_file = None
                            # First check if it's an imported symbol
                            for imp in self.symbols['imports']:
                                if imp.get('symbol') == base_name:
                                    # Found direct symbol import
                                    module_name = imp.get('module')
                                    # Try to find the actual file path for the imported module
                                    for file_path in self.file_contexts:
                                        if file_path.endswith(module_name + '.py'):
                                            # Check if the base class exists in this file
                                            for other_class in self.file_contexts[file_path].symbols.get('classes', []):
                                                if other_class.get('name') == base_name:
                                                    base_file = file_path
                                                    break
                                            if base_file:
                                                break
                                    if not base_file:
                                        base_file = module_name  # If not found, use module name
                                    break
                                elif imp.get('module') == base_name:
                                    # Found module import
                                    base_file = imp.get('module')
                                    break
                            # If not found in imports, look in other files
                            if not base_file:
                                for file_path, file_context in self.file_contexts.items():
                                    if file_path != self.current_file:  # Don't look in current file
                                        for other_class in file_context.symbols.get('classes', []):
                                            if other_class.get('name') == base_name:
                                                base_file = file_path
                                                break
                                        if base_file:
                                            break
                            # If still not found, assume it's in current file
                            if not base_file:
                                base_file = self.current_file
                            class_info['bases'].append({
                                'name': base_name,
                                'file_path': base_file,
                                'start_line': base.start_point[0],
                                'end_line': base.end_point[0]
                            })
                
                # Process methods
                body_node = node.child_by_field_name('body')
                if body_node:
                    for child in body_node.children:
                        if child.type == 'function_definition':
                            name_node = child.child_by_field_name('name')
                            if name_node:
                                class_info['methods'].append({
                                    'name': name_node.text,
                                    'start_line': child.start_point[0],
                                    'end_line': child.end_point[0]
                                })
                
                self.symbols['classes'].append(class_info)
                
        except Exception as e:
            logger.error(f"Failed to process class: {e}")
            
    def _process_identifier(self, node: Any):
        """Process an identifier node.
        
        Args:
            node: Identifier node
        """
        try:
            # Add to references if in a function or method scope
            if self.current_scope != 'global':
                self.references['variables'].append({
                    'name': node.text,
                    'scope': self.current_scope,
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0]
                })
                
        except Exception as e:
            logger.error(f"Failed to process identifier: {e}")
            
    def _process_assignment(self, node: Any):
        """Process an assignment node.
        
        Args:
            node: Assignment node
        """
        try:
            left_node = node.child_by_field_name('left')
            if left_node:
                self.symbols['variables'].append({
                    'name': left_node.text,
                    'scope': self.current_scope,
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0]
                })
                
        except Exception as e:
            logger.error(f"Failed to process assignment: {e}")
            
    def get_symbols(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get the extracted symbols.
        
        Returns:
            Dictionary of symbols
        """
        return self.symbols
        
    def get_references(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get the extracted references.
        
        Returns:
            Dictionary of references
        """
        return self.references 