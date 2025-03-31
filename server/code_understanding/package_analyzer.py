import json
import os
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class PackageAnalyzer:
    """Analyzes package.json files to extract dependency information."""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        
    def analyze(self) -> Dict:
        """Analyze package.json and return dependency information."""
        try:
            package_json_path = os.path.join(self.project_root, 'package.json')
            if not os.path.exists(package_json_path):
                logger.warning(f"No package.json found at {package_json_path}")
                return {
                    'dependencies': {},
                    'devDependencies': {},
                    'peerDependencies': {},
                    'scripts': {},
                    'engines': {},
                    'has_errors': True,
                    'error_details': [{'message': 'package.json not found'}]
                }
            
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            # Extract dependencies
            dependencies = package_data.get('dependencies', {})
            dev_dependencies = package_data.get('devDependencies', {})
            peer_dependencies = package_data.get('peerDependencies', {})
            
            # Extract scripts
            scripts = package_data.get('scripts', {})
            
            # Extract engines
            engines = package_data.get('engines', {})
            
            # Extract other metadata
            metadata = {
                'name': package_data.get('name'),
                'version': package_data.get('version'),
                'description': package_data.get('description'),
                'main': package_data.get('main'),
                'module': package_data.get('module'),
                'types': package_data.get('types'),
                'type': package_data.get('type', 'commonjs'),
                'private': package_data.get('private', False),
                'workspaces': package_data.get('workspaces', []),
                'license': package_data.get('license'),
                'author': package_data.get('author'),
                'repository': package_data.get('repository'),
                'bugs': package_data.get('bugs'),
                'homepage': package_data.get('homepage'),
                'keywords': package_data.get('keywords', []),
                'publishConfig': package_data.get('publishConfig'),
                'files': package_data.get('files', []),
                'sideEffects': package_data.get('sideEffects'),
                'exports': package_data.get('exports'),
                'imports': package_data.get('imports'),
                'resolutions': package_data.get('resolutions'),
                'overrides': package_data.get('overrides'),
                'packageManager': package_data.get('packageManager')
            }
            
            # Check for lock files
            lock_files = {
                'yarn.lock': os.path.exists(os.path.join(self.project_root, 'yarn.lock')),
                'package-lock.json': os.path.exists(os.path.join(self.project_root, 'package-lock.json')),
                'pnpm-lock.yaml': os.path.exists(os.path.join(self.project_root, 'pnpm-lock.yaml'))
            }
            
            # Determine package manager
            package_manager = None
            if lock_files['yarn.lock']:
                package_manager = 'yarn'
            elif lock_files['package-lock.json']:
                package_manager = 'npm'
            elif lock_files['pnpm-lock.yaml']:
                package_manager = 'pnpm'
            elif metadata['packageManager']:
                package_manager = metadata['packageManager'].split('@')[0]
            
            return {
                'dependencies': dependencies,
                'devDependencies': dev_dependencies,
                'peerDependencies': peer_dependencies,
                'scripts': scripts,
                'engines': engines,
                'metadata': metadata,
                'lock_files': lock_files,
                'package_manager': package_manager,
                'has_errors': False,
                'error_details': []
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing package.json: {e}")
            return {
                'dependencies': {},
                'devDependencies': {},
                'peerDependencies': {},
                'scripts': {},
                'engines': {},
                'has_errors': True,
                'error_details': [{'message': f'Invalid JSON in package.json: {str(e)}'}]
            }
        except Exception as e:
            logger.error(f"Error analyzing package.json: {e}")
            return {
                'dependencies': {},
                'devDependencies': {},
                'peerDependencies': {},
                'scripts': {},
                'engines': {},
                'has_errors': True,
                'error_details': [{'message': str(e)}]
            }
    
    def get_dependency_graph(self) -> Dict:
        """Generate a dependency graph from package.json."""
        try:
            package_data = self.analyze()
            if package_data['has_errors']:
                return {
                    'nodes': [],
                    'edges': [],
                    'has_errors': True,
                    'error_details': package_data['error_details']
                }
            
            nodes = []
            edges = []
            
            # Add root package
            root_package = package_data['metadata']['name'] or 'root'
            nodes.append({
                'id': root_package,
                'type': 'root',
                'version': package_data['metadata']['version'] or 'unknown'
            })
            
            # Add dependencies
            for dep_type, deps in [
                ('dependencies', package_data['dependencies']),
                ('devDependencies', package_data['devDependencies']),
                ('peerDependencies', package_data['peerDependencies'])
            ]:
                for name, version in deps.items():
                    # Add dependency node
                    nodes.append({
                        'id': name,
                        'type': dep_type,
                        'version': version
                    })
                    
                    # Add edge from root to dependency
                    edges.append({
                        'from': root_package,
                        'to': name,
                        'type': dep_type
                    })
            
            return {
                'nodes': nodes,
                'edges': edges,
                'has_errors': False,
                'error_details': []
            }
            
        except Exception as e:
            logger.error(f"Error generating dependency graph: {e}")
            return {
                'nodes': [],
                'edges': [],
                'has_errors': True,
                'error_details': [{'message': str(e)}]
            }
    
    def get_scripts(self) -> Dict[str, str]:
        """Get available npm/yarn scripts."""
        package_data = self.analyze()
        return package_data['scripts']
    
    def get_engines(self) -> Dict[str, str]:
        """Get required Node.js and npm versions."""
        package_data = self.analyze()
        return package_data['engines']
    
    def get_metadata(self) -> Dict:
        """Get package metadata."""
        package_data = self.analyze()
        return package_data['metadata']
    
    def get_package_manager(self) -> Optional[str]:
        """Determine the package manager being used."""
        package_data = self.analyze()
        return package_data['package_manager'] 