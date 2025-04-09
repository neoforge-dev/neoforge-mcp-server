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
            root_dir: Root directory of the project (should be realpath)
        """
        # Store the realpath of the root directory
        self.root_dir = Path(os.path.realpath(root_dir))
        self.module_cache: Dict[str, Dict[str, Any]] = {}
        # Cache resolved realpaths
        self.path_cache: Dict[str, Optional[Path]] = {}
        
    def resolve_import(self, import_path: str, from_file: str) -> Optional[Path]:
        """Resolve an import path to its actual file location (realpath).
        
        Args:
            import_path: Import path to resolve
            from_file: File containing the import (should be realpath)
            
        Returns:
            Resolved real file path (Path object) or None if not found
        """
        # Use realpath for the importing file
        from_file_real = os.path.realpath(from_file)
        cache_key = (import_path, from_file_real)
        if cache_key in self.path_cache:
            return self.path_cache[cache_key]

        try:
            # Handle package imports (e.g., 'react', 'lodash') - these won't be realpaths
            if not import_path.startswith('.'):
                return self._resolve_package_import(import_path)
            
            # Handle relative imports
            from_path = Path(from_file_real)
            if not from_path.is_absolute():
                # This case might occur if from_file is relative itself, resolve against root_dir
                # Ensure root_dir is Path
                from_path = self.root_dir / from_file_real
                
            # Use realpath to handle potential symlinks in the path itself
            from_path_real = Path(os.path.realpath(str(from_path)))

            # Defensive check: Ensure from_path_real exists and is a file before getting parent
            if not from_path_real.is_file():
                print(f"[ModuleResolver] Warning: from_file real path is not a valid file: {from_path_real}")
                self.path_cache[cache_key] = None
                return None

            from_dir = from_path_real.parent
            if not from_dir.is_dir():
                print(f"[ModuleResolver] Warning: Parent directory not found for: {from_path_real}")
                self.path_cache[cache_key] = None
                return None
                
            # Try different extensions
            extensions = ['.js', '.jsx', '.ts', '.tsx']
            # Resolve the base path using the validated from_dir and normalize immediately
            # No need for .resolve() here as from_dir is already realpath'd parent
            base_path = from_dir / import_path
            # Get the realpath before checking existence/suffixes
            base_path_real_str = os.path.realpath(str(base_path))
            base_path_real = Path(base_path_real_str)

            # Try exact path (already realpath)
            if base_path_real.is_file():
                self.path_cache[cache_key] = base_path_real
                return base_path_real

            # Try with extensions (checking realpath)
            for ext in extensions:
                # Construct path with suffix, then get realpath
                path_with_ext_str = str(base_path) + ext # Use original base for suffix logic
                path_real_str = os.path.realpath(path_with_ext_str)
                path_real = Path(path_real_str)
                if path_real.is_file():
                    self.path_cache[cache_key] = path_real
                    return path_real

            # Try index files (checking realpath)
            for ext in extensions:
                # Construct path with index/suffix, then get realpath
                index_path_str = str(base_path / f'index{ext}')
                path_real_str = os.path.realpath(index_path_str)
                path_real = Path(path_real_str)
                if path_real.is_file():
                    self.path_cache[cache_key] = path_real
                    return path_real

            # No match found
            self.path_cache[cache_key] = None
            return None
        except Exception as e:
            print(f"[ModuleResolver] Error resolving import '{import_path}' from '{from_file}': {e}")
            self.path_cache[cache_key] = None
            return None
    
    def _resolve_package_import(self, package_name: str) -> Optional[Path]:
        """Resolve a package import to its location.
        
        Args:
            package_name: Name of the package to resolve
            
        Returns:
            Package location (Path object) or None if not found
        """
        # Check node_modules in project root (root_dir is already realpath)
        node_modules = self.root_dir / 'node_modules'
        if node_modules.exists():
            package_dir = node_modules / package_name
            if package_dir.exists():
                return package_dir # Return the Path object
                
        # Check package.json for local packages (root_dir is already realpath)
        package_json = self.root_dir / 'package.json'
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    pkg = json.load(f)
                    if package_name in pkg.get('dependencies', {}):
                        # Assuming standard node_modules structure
                        pkg_loc = node_modules / package_name
                        if pkg_loc.exists():
                            return pkg_loc # Return the Path object
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