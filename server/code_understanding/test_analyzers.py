import pytest
import os
import json
from .package_analyzer import PackageAnalyzer
from .dependency_analyzer import DependencyAnalyzer

@pytest.fixture
def test_project_root(tmp_path):
    """Create a temporary test project with package.json and test files."""
    # Create package.json
    package_json = {
        'name': 'test-project',
        'version': '1.0.0',
        'description': 'Test project',
        'main': 'src/index.js',
        'type': 'module',
        'scripts': {
            'start': 'node src/index.js',
            'test': 'jest'
        },
        'dependencies': {
            'react': '^18.2.0',
            'lodash': '^4.17.21'
        },
        'devDependencies': {
            'jest': '^29.0.0',
            'typescript': '^4.9.0'
        },
        'peerDependencies': {
            'react-dom': '^18.2.0'
        }
    }
    
    with open(tmp_path / 'package.json', 'w') as f:
        json.dump(package_json, f)
    
    # Create test files
    os.makedirs(tmp_path / 'src', exist_ok=True)
    
    # Create index.js
    with open(tmp_path / 'src/index.js', 'w') as f:
        f.write("""
        import { useState } from 'react';
        import { debounce } from 'lodash';
        import { helper } from './utils';
        
        export default function App() {
            const [count, setCount] = useState(0);
            return <div>{count}</div>;
        }
        """)
    
    # Create utils.js
    with open(tmp_path / 'src/utils.js', 'w') as f:
        f.write("""
        export const helper = () => {
            console.log('Helper function');
        };
        
        export const unused = () => {
            console.log('Unused function');
        };
        """)
    
    # Create circular dependency
    with open(tmp_path / 'src/circular1.js', 'w') as f:
        f.write("""
        import { helper } from './circular2';
        export const func1 = () => helper();
        """)
    
    with open(tmp_path / 'src/circular2.js', 'w') as f:
        f.write("""
        import { func1 } from './circular1';
        export const helper = () => func1();
        """)
    
    return tmp_path

def test_package_analyzer(test_project_root):
    """Test PackageAnalyzer functionality."""
    analyzer = PackageAnalyzer(test_project_root)
    result = analyzer.analyze()
    
    assert not result['has_errors']
    assert result['dependencies'] == {
        'react': '^18.2.0',
        'lodash': '^4.17.21'
    }
    assert result['devDependencies'] == {
        'jest': '^29.0.0',
        'typescript': '^4.9.0'
    }
    assert result['peerDependencies'] == {
        'react-dom': '^18.2.0'
    }
    assert result['scripts'] == {
        'start': 'node src/index.js',
        'test': 'jest'
    }
    assert result['metadata']['name'] == 'test-project'
    assert result['metadata']['version'] == '1.0.0'
    assert result['package_manager'] in ['npm', 'yarn', 'pnpm']

def test_dependency_analyzer(test_project_root):
    """Test DependencyAnalyzer functionality."""
    analyzer = DependencyAnalyzer(test_project_root)
    
    # Test single file analysis
    index_result = analyzer.analyze_dependencies(os.path.join(test_project_root, 'src/index.js'))
    assert not index_result['has_errors']
    assert len(index_result['imports']) == 3
    assert len(index_result['exports']) == 1
    assert len(index_result['dependencies']) == 3
    
    # Test dependency graph
    graph = analyzer.build_dependency_graph([
        os.path.join(test_project_root, 'src/index.js')
    ])
    assert not graph['has_errors']
    assert len(graph['nodes']) > 0
    assert len(graph['edges']) > 0
    
    # Test circular dependencies
    circular_deps = analyzer.find_circular_dependencies()
    assert len(circular_deps) > 0
    assert any('circular1.js' in cycle and 'circular2.js' in cycle for cycle in circular_deps)
    
    # Test unused exports
    unused_exports = analyzer.find_unused_exports()
    assert len(unused_exports) > 0
    assert any(exp['name'] == 'unused' for exp in unused_exports)

def test_module_resolution(test_project_root):
    """Test module resolution functionality."""
    analyzer = DependencyAnalyzer(test_project_root)
    
    # Test relative imports
    index_path = os.path.join(test_project_root, 'src/index.js')
    utils_path = os.path.join(test_project_root, 'src/utils.js')
    
    resolved = analyzer._resolve_module_path('./utils', index_path)
    assert resolved == utils_path
    
    # Test node_modules resolution
    resolved = analyzer._resolve_module_path('react', index_path)
    assert resolved is not None
    assert 'node_modules/react' in resolved

def test_error_handling(test_project_root):
    """Test error handling in analyzers."""
    # Test non-existent file
    analyzer = DependencyAnalyzer(test_project_root)
    result = analyzer.analyze_dependencies('nonexistent.js')
    assert result['has_errors']
    assert len(result['error_details']) > 0
    
    # Test invalid package.json
    with open(os.path.join(test_project_root, 'package.json'), 'w') as f:
        f.write('invalid json')
    
    package_analyzer = PackageAnalyzer(test_project_root)
    result = package_analyzer.analyze()
    assert result['has_errors']
    assert len(result['error_details']) > 0

def test_cache_mechanism(test_project_root):
    """Test module resolution caching."""
    analyzer = DependencyAnalyzer(test_project_root)
    index_path = os.path.join(test_project_root, 'src/index.js')
    
    # First resolution
    resolved1 = analyzer._resolve_module_path('./utils', index_path)
    
    # Second resolution should use cache
    resolved2 = analyzer._resolve_module_path('./utils', index_path)
    assert resolved1 == resolved2
    assert (('./utils', index_path) in analyzer._module_cache) 