"""Module for mapping and tracking code contexts and relationships."""

from typing import Dict, List, Set, Any, Optional, Tuple
from pathlib import Path
from .semantic_analyzer import SemanticAnalyzer, Type, Scope
from .module_resolver import ModuleResolver

class ContextMapper:
    """Maps and tracks relationships between code contexts."""
    
    def __init__(self, root_dir: str):
        """Initialize the context mapper.
        
        Args:
            root_dir: Root directory of the project
        """
        self.root_dir = Path(root_dir)
        self.semantic_analyzer = SemanticAnalyzer()
        self.module_resolver = ModuleResolver(root_dir)
        self.context_map: Dict[str, Dict[str, Any]] = {}
        self.relationship_map: Dict[str, List[Dict[str, Any]]] = {}
        
    def analyze_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Analyze a file and build its context map.
        
        Args:
            file_path: Path to the file (can be relative to root_dir)
            content: File contents
            
        Returns:
            Dictionary containing analysis results
        """
        # Ensure file_path is absolute for consistent resolution
        abs_file_path_obj = self.root_dir / file_path
        abs_file_path = str(abs_file_path_obj.resolve()) # Resolve symlinks and get absolute path string

        # Get semantic analysis (using original file_path key? TBD, using abs path for now)
        semantic_result = self.semantic_analyzer.analyze_file(abs_file_path, content)
        
        # Get module dependencies using the absolute path
        module_deps = self.module_resolver.get_module_dependencies(abs_file_path)
        
        # Build context map using absolute path
        context_info = self._build_context_info(abs_file_path, semantic_result, module_deps)
        
        # Store results using the original file_path as the key for consistency? Or abs path?
        # Using original relative path as key seems more user-friendly if root_dir is known.
        self.context_map[file_path] = context_info
        
        # Update relationships using original file_path key
        self._update_relationships(file_path, context_info)
        
        return context_info
        
    def _build_context_info(self, file_path: str, semantic_result: Dict[str, Any],
                          module_deps: Dict[str, List[str]]) -> Dict[str, Any]:
        """Build context information for a file.
        
        Args:
            file_path: Path to the file
            semantic_result: Results from semantic analysis
            module_deps: Module dependencies
            
        Returns:
            Dictionary containing context information
        """
        return {
            'file_path': file_path,
            'types': semantic_result['types'],
            'contexts': semantic_result['contexts'],
            'dependencies': module_deps,
            'relationships': self._build_relationships(semantic_result, module_deps)
        }
        
    def _build_relationships(self, semantic_result: Dict[str, Any],
                           module_deps: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Build relationships between code elements.
        
        Args:
            semantic_result: Results from semantic analysis
            module_deps: Module dependencies
            
        Returns:
            List of relationships
        """
        relationships = []
        
        # Add type relationships
        for name, type_info in semantic_result['types'].items():
            relationships.append({
                'type': 'type_definition',
                'from': name,
                'to': str(type_info),
                'context': 'type'
            })
            
        # Add function relationships
        for name, context in semantic_result['contexts'].items():
            if context['type'] == 'function':
                relationships.append({
                    'type': 'function_definition',
                    'from': name,
                    'to': str(context['return_type']),
                    'context': 'function'
                })
                
                # Add parameter relationships
                for param in context['parameters']:
                    relationships.append({
                        'type': 'parameter',
                        'from': name,
                        'to': param['name'],
                        'context': 'function'
                    })
                    
        # Add class relationships
        for name, context in semantic_result['contexts'].items():
            if context['type'] == 'class':
                relationships.append({
                    'type': 'class_definition',
                    'from': name,
                    'to': 'object',
                    'context': 'class'
                })
                
                # Add method relationships
                for method_name, method_info in context['methods'].items():
                    relationships.append({
                        'type': 'method',
                        'from': name,
                        'to': method_name,
                        'context': 'class'
                    })
                    
                # Add property relationships
                for prop_name, prop_info in context['properties'].items():
                    relationships.append({
                        'type': 'property',
                        'from': name,
                        'to': prop_name,
                        'context': 'class'
                    })
                    
        # Add module relationships
        for dep in module_deps['direct']:
            relationships.append({
                'type': 'module_dependency',
                'from': 'current',
                'to': dep,
                'context': 'module'
            })
            
        return relationships
        
    def _update_relationships(self, file_path: str, context_info: Dict[str, Any]):
        """Update the relationship map with new relationships.
        
        Args:
            file_path: Path to the file
            context_info: Context information
        """
        self.relationship_map[file_path] = context_info['relationships']
        
    def get_context(self, file_path: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Get context information for a symbol.
        
        Args:
            file_path: Path to the file
            symbol: Symbol to look up
            
        Returns:
            Context information or None if not found
        """
        if file_path in self.context_map:
            context_info = self.context_map[file_path]
            
            # Check contexts FIRST (function, class, etc.)
            if symbol in context_info['contexts']:
                return {
                    'type': context_info['contexts'][symbol]['type'],
                    'symbol': symbol,
                    'context': context_info['contexts'][symbol]
                }
                
            # Check types SECOND (variable, general type definition)
            if symbol in context_info['types']:
                return {
                    'type': 'type',
                    'symbol': symbol,
                    'type_info': str(context_info['types'][symbol])
                }
                
        return None
        
    def get_relationships(self, file_path: str, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get relationships for a file or symbol.
        
        Args:
            file_path: Path to the file
            symbol: Optional symbol to filter relationships
            
        Returns:
            List of relationships
        """
        if file_path not in self.relationship_map:
            return []
            
        relationships = self.relationship_map[file_path]
        
        if symbol:
            return [r for r in relationships if r['from'] == symbol or r['to'] == symbol]
            
        return relationships
        
    def get_symbol_usage(self, file_path: str, symbol: str) -> List[Dict[str, Any]]:
        """Get usage information for a symbol.
        
        Args:
            file_path: Path to the file
            symbol: Symbol to look up
            
        Returns:
            List of usage information
        """
        if file_path not in self.context_map:
            # print(f"DEBUG USAGE: File path '{file_path}' not found in context_map keys: {list(self.context_map.keys())}") # DEBUG
            return []
            
        context_info = self.context_map[file_path]
        usages = []
        
        # DEBUG: Print relevant context info
        # print(f"DEBUG USAGE ({symbol} in {file_path}):") # DEBUG
        # print(f"  Types: {context_info.get('types', 'MISSING')}") # DEBUG
        # print(f"  Contexts: {context_info.get('contexts', 'MISSING')}") # DEBUG

        # Check type usage
        # print(f"  Checking if '{symbol}' in types...") # DEBUG
        if symbol in context_info.get('types', {}):
            # print(f"    Found '{symbol}' in types.") # DEBUG
            usages.append({
                'type': 'type_usage',
                'symbol': symbol,
                'context': 'type'
            })
            
        # Check function/class usage
        # print(f"  Checking if '{symbol}' in contexts...") # DEBUG
        found_in_top_level_context = False
        if symbol in context_info.get('contexts', {}):
            found_in_top_level_context = True # Mark that we found it directly
            # print(f"    Found '{symbol}' in contexts.") # DEBUG
            context = context_info['contexts'][symbol]
            # print(f"    Context type: {context.get('type')}") # DEBUG
            if context.get('type') == 'function':
                # print(f"      Adding function_usage.") # DEBUG
                usages.append({
                    'type': 'function_usage',
                    'symbol': symbol,
                    'context': 'function'
                })
            elif context.get('type') == 'class':
                # print(f"      Adding class_usage.") # DEBUG
                usages.append({
                    'type': 'class_usage',
                    'symbol': symbol,
                    'context': 'class'
                })
                
        # Check method usage (if not found as top-level context)
        if not found_in_top_level_context:
             # print(f"  Checking if '{symbol}' is a method...") # DEBUG
             for class_name, class_context in context_info.get('contexts', {}).items():
                 if class_context.get('type') == 'class' and symbol in class_context.get('methods', {}):
                     # print(f"    Found method '{symbol}' in class '{class_name}'.") # DEBUG
                     usages.append({
                         'type': 'method_usage', # Use specific type
                         'symbol': symbol,
                         'context': 'method',
                         'class': class_name # Add class context
                     })
                     break # Assume method names are unique across classes in a file for now
        
        # Check property usage (similar logic could be added here if needed)
        # ...

        # Check variable usage (where variable's type is the symbol)
        # print(f"  Checking variable usage...") # DEBUG
        # for name, type_info in context_info.get('types', {}).items():
        #     if str(type_info) == symbol:
        #         print(f"    Found variable '{name}' with type '{symbol}'") # DEBUG
        #         usages.append({
        #             'type': 'variable_usage',
        #             'symbol': name,
        #             'context': 'variable'
        #         })
                
        # print(f"  Final usages for '{symbol}': {usages}") # DEBUG
        return usages
        
    def get_dependency_graph(self) -> Dict[str, Any]:
        """Get the complete dependency graph.
        
        Returns:
            Dictionary containing nodes and edges of the dependency graph
        """
        graph = {
            'nodes': [],
            'edges': []
        }
        
        # Add nodes for all files
        for file_path, context_info in self.context_map.items():
            graph['nodes'].append({
                'id': file_path,
                'type': 'file',
                'symbols': list(context_info['types'].keys()) + list(context_info['contexts'].keys())
            })
            
        # Add edges for dependencies
        for file_path, context_info in self.context_map.items():
            for dep in context_info['dependencies']['direct']:
                graph['edges'].append({
                    'from': file_path,
                    'to': dep,
                    'type': 'module_dependency'
                })
                
        return graph
        
    def get_symbol_graph(self, file_path: str) -> Dict[str, Any]:
        """Get the symbol relationship graph for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing nodes and edges of the symbol graph
        """
        if file_path not in self.context_map:
            return {'nodes': [], 'edges': []}
            
        context_info = self.context_map[file_path]
        graph = {
            'nodes': [],
            'edges': []
        }
        
        # Add nodes for all top-level types (variables, etc.)
        for name, type_info in context_info['types'].items():
            graph['nodes'].append({
                'id': name,
                'type': 'type', # Generic type node
                'type_info': str(type_info)
            })
            
        # Add nodes for top-level contexts (functions, classes) AND their members (methods, properties)
        for name, context in context_info['contexts'].items():
            # Add node for the main context (function or class)
            graph['nodes'].append({
                'id': name,
                'type': context['type'], # 'function' or 'class'
                'context': context
            })
            
            # If it's a class, also add nodes for its methods and properties
            if context['type'] == 'class':
                # Add method nodes
                for method_name, method_info in context.get('methods', {}).items():
                    graph['nodes'].append({
                        'id': method_name,
                        'type': 'method', 
                        'context': method_info # Store params, etc.
                    })
                    
                # Add property nodes
                for prop_name, prop_info in context.get('properties', {}).items():
                    graph['nodes'].append({
                        'id': prop_name,
                        'type': 'property', 
                        'context': prop_info # Store type info if available
                    })
            
        # Add edges for relationships (these should already use string IDs)
        for rel in context_info.get('relationships', []):
            # Ensure 'from' and 'to' exist before adding edge
            if 'from' in rel and 'to' in rel:
                 graph['edges'].append({
                     'from': rel['from'],
                     'to': rel['to'],
                     'type': rel.get('type', 'unknown') # Use get for safety
                 })
            
        return graph 