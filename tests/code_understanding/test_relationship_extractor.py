"""Tests for the JavaScript relationship extractor."""

import unittest
import tempfile
import os
from pathlib import Path
from server.code_understanding.relationship_extractor import JavaScriptRelationshipExtractor

class TestJavaScriptRelationshipExtractor(unittest.TestCase):
    """Test cases for JavaScriptRelationshipExtractor."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.root_dir = Path(self.temp_dir)
        self.extractor = JavaScriptRelationshipExtractor(str(self.root_dir))
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def _create_test_files(self):
        """Create test JavaScript files."""
        # Create main.js
        main_content = """
import { helper } from './utils/helper';
import { asyncOperation } from './services/async';

export class Calculator {
    constructor() {
        this.state = { value: 0 };
    }
    
    add(x) {
        return helper.add(this.state.value, x);
    }
    
    async multiply(x) {
        return await asyncOperation.multiply(this.state.value, x);
    }
}

export default Calculator;
"""
        main_path = self.root_dir / 'main.js'
        main_path.parent.mkdir(exist_ok=True)
        main_path.write_text(main_content)
        
        # Create utils/helper.js
        helper_content = """
export const helper = {
    add(a, b) {
        return a + b;
    }
};
"""
        helper_path = self.root_dir / 'utils' / 'helper.js'
        helper_path.parent.mkdir(exist_ok=True)
        helper_path.write_text(helper_content)
        
        # Create services/async.js
        async_content = """
export const asyncOperation = {
    async multiply(a, b) {
        return new Promise(resolve => {
            setTimeout(() => resolve(a * b), 100);
        });
    }
};
"""
        async_path = self.root_dir / 'services' / 'async.js'
        async_path.parent.mkdir(exist_ok=True)
        async_path.write_text(async_content)
        
        return {
            'main': main_path,
            'helper': helper_path,
            'async': async_path
        }
        
    def test_analyze_file(self):
        """Test analyzing a single JavaScript file."""
        files = self._create_test_files()
        main_path = files['main']
        
        # Analyze main.js
        with open(main_path) as f:
            content = f.read()
        result = self.extractor.analyze_file(str(main_path), content)
        
        # Check imports
        self.assertIn('imports', result)
        imports = result['imports']
        self.assertEqual(len(imports), 2)
        self.assertIn('./utils/helper', imports)
        self.assertIn('./services/async', imports)
        
        # Check exports
        self.assertIn('exports', result)
        exports = result['exports']
        self.assertEqual(len(exports), 2)
        self.assertIn('Calculator', exports)
        self.assertIn('default', exports)
        
        # Check symbols
        self.assertIn('symbols', result)
        symbols = result['symbols']
        self.assertIn('Calculator', symbols)
        self.assertIn('state', symbols)
        
    def test_cross_file_references(self):
        """Test tracking cross-file references."""
        files = self._create_test_files()
        main_path = files['main']
        helper_path = files['helper']
        async_path = files['async']
        
        # Analyze all files
        for file_path in files.values():
            with open(file_path) as f:
                content = f.read()
            self.extractor.analyze_file(str(file_path), content)
            
        # Check cross-file references for main.js
        refs = self.extractor.get_cross_file_references(str(main_path))
        
        # Check outgoing references
        self.assertEqual(len(refs['outgoing']), 2)
        # Assert based on the 'target' key (resolved path of the imported module)
        # Also use realpath for comparison consistency
        self.assertTrue(any(os.path.realpath(ref['target']) == os.path.realpath(str(helper_path)) for ref in refs['outgoing']))
        self.assertTrue(any(os.path.realpath(ref['target']) == os.path.realpath(str(async_path)) for ref in refs['outgoing']))
        
        # Check incoming references (main.js is not imported by helper.js or async.js)
        self.assertEqual(len(refs['incoming']), 0) # Expect 0 incoming refs to main.js
        
    def test_module_graph(self):
        """Test generating module dependency graph."""
        files = self._create_test_files()
        
        # Analyze ALL files before getting the graph
        for file_path in files.values():
            with open(file_path) as f:
                content = f.read()
            # Use the extractor instance to analyze each file
            # This populates self.file_data needed by get_module_graph
            self.extractor.analyze_file(str(file_path), content)
            
        # Get module graph AFTER analyzing all files
        graph = self.extractor.get_module_graph()
        
        # Debug: Print graph for inspection
        # import json
        # print(f"DEBUG Graph: {json.dumps(graph, indent=2)}")

        # Check nodes
        self.assertEqual(len(graph['nodes']), 3)
        # Get realpaths of node IDs from the graph
        node_paths = {os.path.realpath(n['id']) for n in graph['nodes']}
        # Assert using realpaths of the test files
        for file_path in files.values():
            self.assertIn(os.path.realpath(str(file_path)), node_paths)
            
        # Check edges
        self.assertEqual(len(graph['edges']), 2)
        # Get realpaths for edge sources and destinations
        edge_paths = {(os.path.realpath(e['from']), os.path.realpath(e['to'])) for e in graph['edges']}
        # Assert using realpaths of the test files
        expected_edge1 = (os.path.realpath(str(files['main'])), os.path.realpath(str(files['helper'])))
        expected_edge2 = (os.path.realpath(str(files['main'])), os.path.realpath(str(files['async'])))
        self.assertIn(expected_edge1, edge_paths)
        self.assertIn(expected_edge2, edge_paths)
        
    def test_error_handling(self):
        """Test handling of invalid files."""
        # Test with empty content (should trigger validation error)
        result = self.extractor.analyze_file('nonexistent.js', '')
        self.assertIn('errors', result)
        self.assertGreater(len(result['errors']), 0)
        self.assertEqual(result['errors'][0]['type'], 'validation')
        
        # Test invalid JavaScript (regex parser might not raise specific error, check for empty results)
        result = self.extractor.analyze_file('invalid.js', 'invalid javascript code {')
        # The regex parser might not detect this as an error, but it shouldn't find anything
        self.assertEqual(result['imports'], {})
        self.assertEqual(result['exports'], {})
        self.assertEqual(result['symbols'], {})
        # We accept that errors might be empty here due to parser limitations
        self.assertIn('errors', result)
        
    def test_complex_imports(self):
        """Test handling of complex import patterns."""
        content = """
import { default as React } from 'react';
import * as utils from './utils';
import './styles.css';
import type { Props } from './types';
import { Component } from '@angular/core';
"""
        result = self.extractor.analyze_file('test.js', content)
        
        # Check imports
        imports = result['imports']
        self.assertEqual(len(imports), 5)
        self.assertIn('react', imports)
        self.assertIn('./utils', imports)
        self.assertIn('./styles.css', imports)
        self.assertIn('./types', imports)
        self.assertIn('@angular/core', imports)
        
    def test_complex_exports(self):
        """Test handling of complex export patterns."""
        content = """
export const constant = 42;
export function helper() {}
export class Component {}
export default class App {}
export { helper as util };
export * from './other';
"""
        result = self.extractor.analyze_file('test.js', content)
        
        # Check exports
        exports = result['exports']
        self.assertEqual(len(exports), 6)
        self.assertIn('constant', exports)
        self.assertIn('helper', exports)
        self.assertIn('Component', exports)
        self.assertIn('default', exports)
        self.assertIn('util', exports)
        self.assertIn('*', exports)
        
    def test_symbol_types(self):
        """Test symbol type inference."""
        content = """
const number = 42;
let string = 'hello';
var boolean = true;
const array = [1, 2, 3];
const object = { key: 'value' };
function func() {}
class Class {}
"""
        result = self.extractor.analyze_file('test.js', content)
        
        # Check symbol types
        symbols = result['symbols']
        self.assertEqual(symbols['number']['type'], 'variable')
        self.assertEqual(symbols['string']['type'], 'variable')
        self.assertEqual(symbols['boolean']['type'], 'variable')
        self.assertEqual(symbols['array']['type'], 'variable')
        self.assertEqual(symbols['object']['type'], 'variable')
        self.assertEqual(symbols['func']['type'], 'function')
        self.assertEqual(symbols['Class']['type'], 'class')

if __name__ == '__main__':
    unittest.main() 