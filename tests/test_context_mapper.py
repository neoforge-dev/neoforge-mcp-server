"""Tests for the JavaScript context mapper."""

import unittest
import tempfile
import os
from pathlib import Path
from server.code_understanding.context_mapper import ContextMapper

class TestContextMapper(unittest.TestCase):
    """Test cases for the ContextMapper class."""
    
    def setUp(self):
        """Set up a temporary directory with mock files."""
        self.temp_dir = tempfile.mkdtemp()
        self.root_dir_path = Path(self.temp_dir)
        
        # Create dummy files and directories
        (self.root_dir_path / 'utils').mkdir()
        (self.root_dir_path / 'services').mkdir()
        
        with open(self.root_dir_path / 'utils' / 'helper.js', 'w') as f:
            f.write("export function helper(arg) { console.log('Helper:', arg); }")
            
        # Use triple quotes for the multiline string, ensure internal quotes are handled
        async_js_content = """
        import { fetch } from 'node-fetch'; // Example external dep

        export async function asyncOperation() {
            // Dummy implementation for testing resolver
            const response = await new Promise(resolve => setTimeout(() => resolve({{json: () => ({{ data: 'mock' }})}}), 10));
            return response.json();
        }
        """
        with open(self.root_dir_path / 'services' / 'async.js', 'w') as f:
            f.write(async_js_content)
        
        # Initialize ContextMapper with the temporary directory as the root
        self.mapper = ContextMapper(self.temp_dir)
        
        # Create test files
        self._create_test_files()
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def _create_test_files(self):
        """Create test JavaScript files with various relationships."""
        # Create main.js
        main_content = """
        import { helper } from './utils/helper';
        import { Component } from 'react';
        import { asyncOperation } from './services/async';
        
        class MainComponent extends Component {
            constructor() {
                super();
                this.state = {};
            }
            
            async componentDidMount() {
                const result = await asyncOperation();
                helper(result);
            }
        }
        
        export default MainComponent;
        """
        self._write_file('main.js', main_content)
        
        # Create utils/helper.js
        helper_content = """
        import { format } from 'date-fns';
        
        export function helper(data) {
            return format(new Date(), 'yyyy-MM-dd');
        }
        """
        self._write_file('utils/helper.js', helper_content)
        
        # Create services/async.js
        async_content = """
        import { fetch } from 'node-fetch';
        
        export async function asyncOperation() {
            const response = await fetch('https://api.example.com');
            return response.json();
        }
        """
        self._write_file('services/async.js', async_content)
        
        # Create package.json
        package_json = {
            'dependencies': {
                'react': '^17.0.0',
                'date-fns': '^2.29.0',
                'node-fetch': '^2.6.0'
            }
        }
        self._write_file('package.json', str(package_json))
        
    def _write_file(self, rel_path: str, content: str):
        """Helper to write test files."""
        full_path = Path(self.temp_dir) / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        
    def test_analyze_file(self):
        """Test analyzing a single JavaScript file."""
        with open(Path(self.temp_dir) / 'main.js') as f:
            content = f.read()
            
        result = self.mapper.analyze_file('main.js', content)
        
        # Check basic structure
        self.assertIn('file_path', result)
        self.assertIn('types', result)
        self.assertIn('contexts', result)
        self.assertIn('dependencies', result)
        self.assertIn('relationships', result)
        
        # Check types
        self.assertIn('MainComponent', result['types'])
        
        # Check contexts
        self.assertIn('MainComponent', result['contexts'])
        self.assertEqual(result['contexts']['MainComponent']['type'], 'class')
        
        # Check dependencies
        self.assertIn('direct', result['dependencies'])
        self.assertIn('transitive', result['dependencies'])
        
    def test_get_context(self):
        """Test getting context for symbols."""
        with open(Path(self.temp_dir) / 'main.js') as f:
            content = f.read()
            
        self.mapper.analyze_file('main.js', content)
        
        # Test class context
        context = self.mapper.get_context('main.js', 'MainComponent')
        self.assertIsNotNone(context)
        self.assertEqual(context['type'], 'class')
        
        # Test non-existent symbol
        context = self.mapper.get_context('main.js', 'NonExistent')
        self.assertIsNone(context)
        
    def test_get_relationships(self):
        """Test getting relationships between code elements."""
        with open(Path(self.temp_dir) / 'main.js') as f:
            content = f.read()
            
        self.mapper.analyze_file('main.js', content)
        
        # Get all relationships
        relationships = self.mapper.get_relationships('main.js')
        self.assertGreater(len(relationships), 0)
        
        # Check relationship types
        relationship_types = {r['type'] for r in relationships}
        self.assertIn('class_definition', relationship_types)
        self.assertIn('method', relationship_types)
        self.assertIn('module_dependency', relationship_types)
        
        # Get relationships for specific symbol
        main_relationships = self.mapper.get_relationships('main.js', 'MainComponent')
        self.assertGreater(len(main_relationships), 0)
        self.assertTrue(all(r['from'] == 'MainComponent' or r['to'] == 'MainComponent'
                          for r in main_relationships))
        
    def test_get_symbol_usage(self):
        """Test getting usage information for symbols."""
        with open(Path(self.temp_dir) / 'main.js') as f:
            content = f.read()
            
        self.mapper.analyze_file('main.js', content)
        
        # Test class usage
        usages = self.mapper.get_symbol_usage('main.js', 'MainComponent')
        self.assertGreater(len(usages), 0)
        self.assertTrue(any(u['type'] == 'class_usage' for u in usages))
        
        # Test method usage
        usages = self.mapper.get_symbol_usage('main.js', 'componentDidMount')
        self.assertGreater(len(usages), 0)
        self.assertTrue(any(u['type'] == 'method_usage' for u in usages))
        
    def test_get_dependency_graph(self):
        """Test generating the dependency graph."""
        # Analyze all files
        for file_path in ['main.js', 'utils/helper.js', 'services/async.js']:
            with open(Path(self.temp_dir) / file_path) as f:
                content = f.read()
            self.mapper.analyze_file(file_path, content)
            
        graph = self.mapper.get_dependency_graph()
        
        # Check nodes
        self.assertEqual(len(graph['nodes']), 3)  # main.js, helper.js, async.js
        
        # Check edges
        self.assertGreater(len(graph['edges']), 0)
        self.assertTrue(any(e['type'] == 'module_dependency' for e in graph['edges']))
        
    def test_get_symbol_graph(self):
        """Test getting the symbol graph for a file."""
        content = """
        import { helper } from './utils/helper';
        import { Component } from 'react';
        import { asyncOperation } from './services/async';

        class MainComponent extends Component {
            constructor() {
                super();
                this.state = { data: null };
            }

            async componentDidMount() {
                const result = await asyncOperation();
                this.setState({ data: result });
                helper(result);
            }
        }
        
        export default MainComponent;
        """
        file_path = 'main.js' # Relative path within temp_dir context
        with open(self.root_dir_path / file_path, 'w') as f:
            f.write(content)
            
        self.mapper.analyze_file(file_path, content)
        graph = self.mapper.get_symbol_graph(file_path)
        
        # Verify graph structure (basic checks)
        self.assertIsInstance(graph, dict)
        self.assertIn('nodes', graph)
        self.assertIn('edges', graph)
        
        # Check for specific nodes (e.g., the class)
        self.assertTrue(any(n['id'] == 'MainComponent' and n['type'] == 'class' for n in graph['nodes']))
        # Check for method node (as part of class context)
        # Note: The graph structure might place methods as top-level nodes or nested. Adjust assertion based on implementation.
        # Assuming methods are added as nodes linked by edges:
        self.assertTrue(any(n['id'] == 'constructor' for n in graph['nodes']), "Constructor node not found")
        self.assertTrue(any(n['id'] == 'componentDidMount' for n in graph['nodes']), "componentDidMount node not found")
        
        # Check for specific edges (e.g., method definitions)
        self.assertTrue(any(e['from'] == 'MainComponent' and e['to'] == 'constructor' and e['type'] == 'method' for e in graph['edges']))
        self.assertTrue(any(e['from'] == 'MainComponent' and e['to'] == 'componentDidMount' and e['type'] == 'method' for e in graph['edges']))
        
    def test_error_handling(self):
        """Test handling of invalid files and symbols."""
        # Test non-existent file
        result = self.mapper.analyze_file('nonexistent.js', '')
        self.assertEqual(result['types'], {})
        self.assertEqual(result['contexts'], {})
        
        # Test invalid JavaScript
        result = self.mapper.analyze_file('invalid.js', 'invalid javascript code')
        self.assertEqual(result['types'], {})
        self.assertEqual(result['contexts'], {})
        
        # Test getting context for non-existent file
        context = self.mapper.get_context('nonexistent.js', 'symbol')
        self.assertIsNone(context)
        
        # Test getting relationships for non-existent file
        relationships = self.mapper.get_relationships('nonexistent.js')
        self.assertEqual(relationships, [])
        
    def test_complex_relationships(self):
        """Test handling of complex code relationships."""
        complex_content = """
        class Base {
            constructor() {
                this.baseProp = 'base';
            }
            
            baseMethod() {
                return this.baseProp;
            }
        }
        
        class Derived extends Base {
            constructor() {
                super();
                this.derivedProp = 'derived';
            }
            
            derivedMethod() {
                return this.baseMethod() + this.derivedProp;
            }
        }
        
        const instance = new Derived();
        const result = instance.derivedMethod();
        """
        
        self._write_file('complex.js', complex_content)
        with open(Path(self.temp_dir) / 'complex.js') as f:
            content = f.read()
            
        result = self.mapper.analyze_file('complex.js', content)
        
        # Check class relationships
        self.assertIn('Base', result['contexts'])
        self.assertIn('Derived', result['contexts'])
        
        # Check inheritance
        relationships = self.mapper.get_relationships('complex.js')
        self.assertTrue(any(r['type'] == 'class_definition' and r['from'] == 'Derived'
                          for r in relationships))
        
        # Check method relationships
        self.assertTrue(any(r['type'] == 'method' and r['from'] == 'Derived'
                          for r in relationships), "Should find method relationship for Derived class")
        
        # Check property relationships
        # self.assertTrue(any(r['type'] == 'property' and r['from'] == 'Derived'
        #                   for r in relationships), "Should find property relationship for Derived class")

if __name__ == '__main__':
    unittest.main() 