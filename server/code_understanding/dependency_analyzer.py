import os
import json
from typing import Dict, List, Set, Optional
import logging
from .package_analyzer import PackageAnalyzer
from .language_adapters import JavaScriptParserAdapter

logger = logging.getLogger(__name__)

class DependencyAnalyzer:
    """Analyzes JavaScript/TypeScript dependencies and module resolution."""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.package_analyzer = PackageAnalyzer(project_root)
        self.js_parser = JavaScriptParserAdapter()
        self._module_cache = {}
        self._dependency_graph = {}
        self._circular_dependencies = set()
    
    def analyze_dependencies(self, file_path: str) -> Dict:
        """Analyze dependencies for a specific file."""
        try:
            if not os.path.exists(file_path):
                return {
                    'imports': [],
                    'exports': [],
                    'dependencies': [],
                    'has_errors': True,
                    'error_details': [{'message': f'File not found: {file_path}'}]
                }
            
            # Read file content
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse file
            parse_result = self.js_parser.parse(content)
            if parse_result.has_errors:
                return {
                    'imports': [],
                    'exports': [],
                    'dependencies': [],
                    'has_errors': True,
                    'error_details': parse_result.error_details
                }
            
            # Get imports and exports
            imports = parse_result.features['imports']
            exports = parse_result.features['exports']
            
            # Resolve dependencies
            dependencies = []
            for imp in imports:
                module_path = self._resolve_module_path(imp['module'], file_path)
                if module_path:
                    dependencies.append({
                        'name': imp['name'],
                        'module': imp['module'],
                        'resolved_path': module_path,
                        'type': imp['type'],
                        'is_default': imp['is_default']
                    })
            
            return {
                'imports': imports,
                'exports': exports,
                'dependencies': dependencies,
                'has_errors': False,
                'error_details': []
            }
            
        except Exception as e:
            logger.error(f"Error analyzing dependencies for {file_path}: {e}")
            return {
                'imports': [],
                'exports': [],
                'dependencies': [],
                'has_errors': True,
                'error_details': [{'message': str(e)}]
            }
    
    def build_dependency_graph(self, entry_points: List[str]) -> Dict:
        """Build a complete dependency graph starting from entry points."""
        try:
            graph = {
                'nodes': [],
                'edges': [],
                'circular_dependencies': [],
                'unresolved_dependencies': [],
                'has_errors': False,
                'error_details': []
            }
            
            # Add entry points
            for entry_point in entry_points:
                if os.path.exists(entry_point):
                    self._add_file_to_graph(entry_point, graph)
            
            return graph
            
        except Exception as e:
            logger.error(f"Error building dependency graph: {e}")
            return {
                'nodes': [],
                'edges': [],
                'circular_dependencies': [],
                'unresolved_dependencies': [],
                'has_errors': True,
                'error_details': [{'message': str(e)}]
            }
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the project."""
        try:
            circular_deps = []
            visited = set()
            path = []
            
            def dfs(node: str, current_path: List[str]):
                if node in current_path:
                    # Found a cycle
                    cycle_start = current_path.index(node)
                    cycle = current_path[cycle_start:]
                    if cycle not in circular_deps:
                        circular_deps.append(cycle)
                    return
                
                if node in visited:
                    return
                
                visited.add(node)
                current_path.append(node)
                
                # Get dependencies for this node
                deps = self._dependency_graph.get(node, [])
                for dep in deps:
                    dfs(dep, current_path.copy())
                
                current_path.pop()
            
            # Start DFS from each node
            for node in self._dependency_graph:
                if node not in visited:
                    dfs(node, [])
            
            return circular_deps
            
        except Exception as e:
            logger.error(f"Error finding circular dependencies: {e}")
            return []
    
    def find_unused_exports(self) -> List[Dict]:
        """Find unused exports in the project."""
        try:
            unused_exports = []
            
            # Get all exports
            for file_path, deps in self._dependency_graph.items():
                if not os.path.exists(file_path):
                    continue
                
                with open(file_path, 'r') as f:
                    content = f.read()
                
                parse_result = self.js_parser.parse(content)
                if parse_result.has_errors:
                    continue
                
                exports = parse_result.features['exports']
                for export in exports:
                    if not self._is_export_used(export['name'], file_path):
                        unused_exports.append({
                            'file': file_path,
                            'name': export['name'],
                            'is_default': export['is_default']
                        })
            
            return unused_exports
            
        except Exception as e:
            logger.error(f"Error finding unused exports: {e}")
            return []
    
    def _resolve_module_path(self, module: str, source_file: str) -> Optional[str]:
        """Resolve a module path to an absolute file path."""
        try:
            # Check cache
            cache_key = (module, source_file)
            if cache_key in self._module_cache:
                return self._module_cache[cache_key]
            
            # Handle different module formats
            if module.startswith('.'):
                # Relative path
                base_dir = os.path.dirname(source_file)
                possible_paths = [
                    os.path.join(base_dir, module),
                    os.path.join(base_dir, f"{module}.js"),
                    os.path.join(base_dir, f"{module}/index.js")
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        self._module_cache[cache_key] = path
                        return path
            else:
                # Node module
                package_data = self.package_analyzer.analyze()
                if package_data['has_errors']:
                    return None
                
                # Check node_modules
                node_modules_path = os.path.join(self.project_root, 'node_modules')
                if os.path.exists(node_modules_path):
                    module_path = os.path.join(node_modules_path, module)
                    if os.path.exists(module_path):
                        # Find main entry point
                        package_json = os.path.join(module_path, 'package.json')
                        if os.path.exists(package_json):
                            with open(package_json, 'r') as f:
                                pkg_data = json.load(f)
                                main = pkg_data.get('main', 'index.js')
                                entry_point = os.path.join(module_path, main)
                                if os.path.exists(entry_point):
                                    self._module_cache[cache_key] = entry_point
                                    return entry_point
            
            return None
            
        except Exception as e:
            logger.error(f"Error resolving module path: {e}")
            return None
    
    def _add_file_to_graph(self, file_path: str, graph: Dict, visited: Set[str] = None):
        """Add a file and its dependencies to the graph."""
        if visited is None:
            visited = set()
        
        if file_path in visited:
            return
        
        visited.add(file_path)
        
        # Add node
        graph['nodes'].append({
            'id': file_path,
            'type': 'file'
        })
        
        # Get dependencies
        deps = self.analyze_dependencies(file_path)
        if deps['has_errors']:
            graph['unresolved_dependencies'].append({
                'file': file_path,
                'errors': deps['error_details']
            })
            return
        
        # Add edges
        for dep in deps['dependencies']:
            if dep['resolved_path']:
                graph['edges'].append({
                    'from': file_path,
                    'to': dep['resolved_path'],
                    'type': dep['type'],
                    'name': dep['name']
                })
                self._add_file_to_graph(dep['resolved_path'], graph, visited)
            else:
                graph['unresolved_dependencies'].append({
                    'file': file_path,
                    'module': dep['module'],
                    'name': dep['name']
                })
    
    def _is_export_used(self, export_name: str, source_file: str) -> bool:
        """Check if an export is used anywhere in the project."""
        try:
            # Check if it's a default export
            is_default = export_name == 'default'
            
            # Search through all files
            for file_path, deps in self._dependency_graph.items():
                if file_path == source_file:
                    continue
                
                if not os.path.exists(file_path):
                    continue
                
                with open(file_path, 'r') as f:
                    content = f.read()
                
                parse_result = self.js_parser.parse(content)
                if parse_result.has_errors:
                    continue
                
                # Check imports
                for imp in parse_result.features['imports']:
                    if imp['name'] == export_name or (is_default and imp['is_default']):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking export usage: {e}")
            return False 