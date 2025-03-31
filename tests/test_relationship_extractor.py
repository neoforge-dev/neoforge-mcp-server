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
        
        # Check relationships
        self.assertIn('relationships', result)
        relationships = result['relationships']
        self.assertTrue(any(r['type'] == 'import' for r in relationships))
        self.assertTrue(any(r['type'] == 'export' for r in relationships))
        self.assertTrue(any(r['type'] == 'symbol' for r in relationships))
        
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
        self.assertIn(str(helper_path), refs['outgoing'])
        self.assertIn(str(async_path), refs['outgoing'])
        
        # Check incoming references
        self.assertEqual(len(refs['incoming']), 0)
        
        # Check cross-file references for helper.js
        refs = self.extractor.get_cross_file_references(str(helper_path))
        self.assertEqual(len(refs['outgoing']), 0)
        self.assertEqual(len(refs['incoming']), 1)
        self.assertIn(str(main_path), refs['incoming'])
        
    def test_module_graph(self):
        """Test generating module dependency graph."""
        files = self._create_test_files()
        
        # Analyze all files
        for file_path in files.values():
            with open(file_path) as f:
                content = f.read()
            self.extractor.analyze_file(str(file_path), content)
            
        # Get module graph
        graph = self.extractor.get_module_graph()
        
        # Check nodes
        self.assertEqual(len(graph['nodes']), 3)
        node_paths = {n['id'] for n in graph['nodes']}
        for file_path in files.values():
            self.assertIn(str(file_path), node_paths)
            
        # Check edges
        self.assertEqual(len(graph['edges']), 2)
        edge_paths = {(e['from'], e['to']) for e in graph['edges']}
        self.assertIn((str(files['main']), str(files['helper'])), edge_paths)
        self.assertIn((str(files['main']), str(files['async'])), edge_paths)
        
    def test_error_handling(self):
        """Test handling of invalid files."""
        # Test non-existent file
        result = self.extractor.analyze_file('nonexistent.js', '')
        self.assertIn('error', result)
        
        # Test invalid JavaScript
        result = self.extractor.analyze_file('invalid.js', 'invalid javascript code')
        self.assertIn('error', result)
        
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
        self.assertEqual(symbols['number'], 'number')
        self.assertEqual(symbols['string'], 'string')
        self.assertEqual(symbols['boolean'], 'boolean')
        self.assertEqual(symbols['array'], 'array')
        self.assertEqual(symbols['object'], 'object')
        self.assertEqual(symbols['func'], 'function')
        self.assertEqual(symbols['Class'], 'class')

if __name__ == '__main__':
    unittest.main() 