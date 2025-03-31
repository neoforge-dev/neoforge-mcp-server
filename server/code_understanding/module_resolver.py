"""Module for resolving JavaScript module paths and dependencies."""

import os
from pathlib import Path
from typing import Optional, List, Set, Dict, Any
import re

class ModuleResolver:
    """Resolves JavaScript module paths and dependencies."""
    
    def __init__(self, root_dir: str):
        """Initialize the module resolver.
        
        Args:
            root_dir: Root directory of the project
        """
        self.root_dir = Path(root_dir)
        self.module_cache: Dict[str, Dict[str, Any]] = {}
        self.path_cache: Dict[str, Path] = {}
        
    def resolve_import(self, import_path: str, from_file: str) -> Optional[Path]:
        """Resolve an import path to its actual file location.
        
        Args:
            import_path: Import path to resolve
            from_file: File containing the import
            
        Returns:
            Resolved file path or None if not found
        """
        # Handle package imports (e.g., 'react', 'lodash')
        if not import_path.startswith('.'):
            return self._resolve_package_import(import_path)
        
        # Handle relative imports
        from_path = Path(from_file)
        if not from_path.is_absolute():
            from_path = self.root_dir / from_path
            
        # Try different extensions
        extensions = ['.js', '.jsx', '.ts', '.tsx']
        base_path = from_path.parent / import_path
        
        # Try exact path first
        if base_path.exists():
            return base_path
            
        # Try with extensions
        for ext in extensions:
            path = base_path.with_suffix(ext)
            if path.exists():
                return path
                
        # Try index files
        for ext in extensions:
            path = base_path / f'index{ext}'
            if path.exists():
                return path
                
        return None
    
    def _resolve_package_import(self, package_name: str) -> Optional[Path]:
        """Resolve a package import to its location.
        
        Args:
            package_name: Name of the package to resolve
            
        Returns:
            Package location or None if not found
        """
        # Check node_modules in project root
        node_modules = self.root_dir / 'node_modules'
        if node_modules.exists():
            package_dir = node_modules / package_name
            if package_dir.exists():
                return package_dir
                
        # Check package.json for local packages
        package_json = self.root_dir / 'package.json'
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    pkg = json.load(f)
                    if package_name in pkg.get('dependencies', {}):
                        return node_modules / package_name
            except Exception:
                pass
                
        return None
    
    def get_module_dependencies(self, file_path: str) -> Dict[str, List[str]]:
        """Get all dependencies for a module.
        
        Args:
            file_path: Path to the module
            
        Returns:
            Dictionary containing direct and transitive dependencies
        """
        if file_path in self.module_cache:
            return self.module_cache[file_path]
            
        dependencies = {
            'direct': [],
            'transitive': set()
        }
        
        # Read file content
        try:
            with open(file_path) as f:
                content = f.read()
        except Exception:
            return dependencies
            
        # Find all imports
        import_patterns = [
            r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]',  # ES6 imports
            r'require\s*\(\s*[\'"]([^\'"]+)[\'"]',      # CommonJS requires
            r'import\s*\(\s*[\'"]([^\'"]+)[\'"]'        # Dynamic imports
        ]
        
        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                import_path = match.group(1)
                resolved_path = self.resolve_import(import_path, file_path)
                
                if resolved_path:
                    rel_path = str(resolved_path.relative_to(self.root_dir))
                    dependencies['direct'].append(rel_path)
                    
                    # Get transitive dependencies
                    if rel_path not in self.module_cache:
                        trans_deps = self.get_module_dependencies(rel_path)
                        dependencies['transitive'].update(trans_deps['direct'])
                        dependencies['transitive'].update(trans_deps['transitive'])
        
        # Cache the results
        self.module_cache[file_path] = {
            'direct': dependencies['direct'],
            'transitive': list(dependencies['transitive'])
        }
        
        return self.module_cache[file_path]
    
    def get_module_graph(self) -> Dict[str, Any]:
        """Generate a complete module dependency graph.
        
        Returns:
            Dictionary containing nodes and edges of the module graph
        """
        graph = {
            'nodes': [],
            'edges': []
        }
        
        # Find all JavaScript files
        js_files = []
        for ext in ['.js', '.jsx', '.ts', '.tsx']:
            js_files.extend(self.root_dir.rglob(f'*{ext}'))
            
        # Add nodes for all files
        for file_path in js_files:
            rel_path = str(file_path.relative_to(self.root_dir))
            graph['nodes'].append({
                'id': rel_path,
                'type': 'module',
                'dependencies': self.get_module_dependencies(rel_path)
            })
            
        # Add edges for dependencies
        for node in graph['nodes']:
            for dep in node['dependencies']['direct']:
                graph['edges'].append({
                    'from': node['id'],
                    'to': dep,
                    'type': 'import'
                })
                
        return graph
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the module graph.
        
        Returns:
            List of circular dependency chains
        """
        graph = self.get_module_graph()
        cycles = []
        visited = set()
        path = []
        
        def dfs(node: str, current_path: List[str]):
            if node in current_path:
                cycle_start = current_path.index(node)
                cycles.append(current_path[cycle_start:])
                return
                
            if node in visited:
                return
                
            visited.add(node)
            current_path.append(node)
            
            for edge in graph['edges']:
                if edge['from'] == node:
                    dfs(edge['to'], current_path.copy())
                    
        for node in graph['nodes']:
            if node['id'] not in visited:
                dfs(node['id'], [])
                
        return cycles
    
    def get_module_stats(self) -> Dict[str, Any]:
        """Get statistics about the module system.
        
        Returns:
            Dictionary containing various module statistics
        """
        graph = self.get_module_graph()
        stats = {
            'total_modules': len(graph['nodes']),
            'total_dependencies': len(graph['edges']),
            'circular_dependencies': len(self.find_circular_dependencies()),
            'module_types': {},
            'dependency_counts': []
        }
        
        # Count module types
        for node in graph['nodes']:
            ext = Path(node['id']).suffix
            stats['module_types'][ext] = stats['module_types'].get(ext, 0) + 1
            
        # Calculate dependency counts
        dep_counts = {}
        for node in graph['nodes']:
            count = len(node['dependencies']['direct'])
            dep_counts[count] = dep_counts.get(count, 0) + 1
            
        stats['dependency_counts'] = [
            {'dependencies': count, 'modules': num}
            for count, num in sorted(dep_counts.items())
        ]
        
        return stats 