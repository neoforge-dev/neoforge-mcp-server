"""Module for extracting relationships between JavaScript code elements."""

from typing import Dict, List, Set, Any, Optional
from pathlib import Path
from .language_adapters import JavaScriptParserAdapter
from .module_resolver import ModuleResolver

class JavaScriptRelationshipExtractor:
    """Extracts relationships between JavaScript code elements."""
    
    def __init__(self, root_dir: str):
        """Initialize the relationship extractor.
        
        Args:
            root_dir: Root directory of the project
        """
        self.root_dir = Path(root_dir)
        self.parser = JavaScriptParserAdapter()
        self.module_resolver = ModuleResolver(root_dir)
        self.import_mapping: Dict[str, Dict[str, str]] = {}
        self.export_mapping: Dict[str, Dict[str, str]] = {}
        self.symbol_table: Dict[str, Dict[str, Any]] = {}
        
    def analyze_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Analyze a JavaScript file and extract relationships.
        
        Args:
            file_path: Path to the file
            content: File contents
            
        Returns:
            Dictionary containing analysis results
        """
        # Parse the file
        tree = self.parser.parse(content)
        if not tree:
            return {
                'error': 'Failed to parse file',
                'imports': {},
                'exports': {},
                'symbols': {},
                'relationships': []
            }
            
        # Extract imports and exports
        imports = self.parser.get_imports(tree)
        exports = self.parser.get_exports(tree)
        requires = self.parser.get_requires(tree)
        
        # Process imports and exports
        self._process_imports_exports(file_path, imports, exports, requires)
        
        # Extract symbols
        symbols = self.parser.get_symbols(tree)
        self.symbol_table[file_path] = {
            s['name']: s['type'] for s in symbols
        }
        
        # Build relationships
        relationships = self._build_relationships(tree, file_path)
        
        return {
            'imports': self.import_mapping.get(file_path, {}),
            'exports': self.export_mapping.get(file_path, {}),
            'symbols': self.symbol_table.get(file_path, {}),
            'relationships': relationships
        }
        
    def _process_imports_exports(self, file_path: str, imports: List[Dict[str, Any]],
                               exports: List[Dict[str, Any]], requires: List[Dict[str, Any]]):
        """Process imports and exports in the file.
        
        Args:
            file_path: Path to the file
            imports: List of import information
            exports: List of export information
            requires: List of require information
        """
        # Process imports
        self.import_mapping[file_path] = {}
        for imp in imports:
            source = imp.get('source')
            if source:
                resolved_path = self.module_resolver.resolve_import(source, file_path)
                if resolved_path:
                    self.import_mapping[file_path][source] = str(resolved_path)
                    
        # Process exports
        self.export_mapping[file_path] = {}
        for exp in exports:
            if 'source' in exp:
                source = exp['source']
                resolved_path = self.module_resolver.resolve_import(source, file_path)
                if resolved_path:
                    self.export_mapping[file_path][source] = str(resolved_path)
            elif 'name' in exp:
                self.export_mapping[file_path][exp['name']] = file_path
                
        # Process requires
        for req in requires:
            source = req.get('source')
            if source:
                resolved_path = self.module_resolver.resolve_import(source, file_path)
                if resolved_path:
                    self.import_mapping[file_path][source] = str(resolved_path)
                    
    def _build_relationships(self, tree: Any, file_path: str) -> List[Dict[str, Any]]:
        """Build relationships between code elements.
        
        Args:
            tree: AST root node
            file_path: Path to the file
            
        Returns:
            List of relationships
        """
        relationships = []
        
        # Add import relationships
        for source, resolved_path in self.import_mapping.get(file_path, {}).items():
            relationships.append({
                'type': 'import',
                'from': file_path,
                'to': resolved_path,
                'source': source
            })
            
        # Add export relationships
        for name, resolved_path in self.export_mapping.get(file_path, {}).items():
            relationships.append({
                'type': 'export',
                'from': file_path,
                'to': resolved_path,
                'name': name
            })
            
        # Add symbol relationships
        for name, type_info in self.symbol_table.get(file_path, {}).items():
            relationships.append({
                'type': 'symbol',
                'from': file_path,
                'to': name,
                'symbol_type': type_info
            })
            
        return relationships
        
    def get_cross_file_references(self, file_path: str) -> Dict[str, List[str]]:
        """Get cross-file references for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing outgoing and incoming references
        """
        return {
            'outgoing': list(self.import_mapping.get(file_path, {}).values()),
            'incoming': [
                f for f, imports in self.import_mapping.items()
                if file_path in imports.values()
            ]
        }
        
    def get_module_graph(self) -> Dict[str, Any]:
        """Get the module dependency graph.
        
        Returns:
            Dictionary containing nodes and edges of the graph
        """
        graph = {
            'nodes': [],
            'edges': []
        }
        
        # Add nodes
        for file_path in set(self.import_mapping.keys()) | set(self.export_mapping.keys()):
            graph['nodes'].append({
                'id': file_path,
                'type': 'module'
            })
            
        # Add edges
        for file_path, imports in self.import_mapping.items():
            for source, resolved_path in imports.items():
                graph['edges'].append({
                    'from': file_path,
                    'to': resolved_path,
                    'type': 'import'
                })
                
        return graph 