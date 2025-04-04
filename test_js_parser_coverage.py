"""Comprehensive tests focused on improving coverage for JavaScriptParserAdapter."""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from tree_sitter import Parser, Language, Node
import logging

# Add the required directories to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'server')))

# First try direct import from server module
try:
    from server.code_understanding.language_adapters import JavaScriptParserAdapter
    from server.code_understanding.common_types import MockTree, MockNode
# If that fails, try importing from copied module in tests directory
except ImportError:
    try:
        # Try importing from local directory
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server', 'code_understanding'))
        from language_adapters import JavaScriptParserAdapter
        from common_types import MockTree, MockNode
    except ImportError:
        print("ERROR: Could not import required modules. Make sure tree_sitter is installed.")
        sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.ERROR)

class TestJavaScriptParserCoverage(unittest.TestCase):
    """Test class to improve coverage for JavaScriptParserAdapter."""
    
    def setUp(self):
        """Set up the test."""
        self.parser = JavaScriptParserAdapter()
        
        # Create a temp directory for testing file operations
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temp directory
        shutil.rmtree(self.temp_dir)
    
    def test_parse_edge_cases(self):
        """Test parsing edge cases."""
        # Test empty code
        result = self.parser.analyze("")
        self.assertIsInstance(result, dict, "Empty code should return empty dict")
        
        # Test None input
        result = self.parser.analyze(None)
        self.assertIsInstance(result, dict, "None input should return empty dict")
        
        # Test whitespace-only code
        result = self.parser.analyze("   \n   \t  ")
        self.assertIsInstance(result, dict, "Whitespace-only code should return dict")
        
        # Test bytes input with valid UTF-8
        result = self.parser.analyze(b'console.log("Hello");')
        self.assertIsInstance(result, dict, "Valid UTF-8 bytes should analyze successfully")
        
        # Test invalid syntax
        result = self.parser.analyze("function( {")
        self.assertIsInstance(result, dict, "Invalid syntax should return dict with errors")

    def test_analyze_edge_cases(self):
        """Test analyze method edge cases."""
        # Test empty code
        result = self.parser.analyze("")
        self.assertIsInstance(result, dict, "Empty code should return empty dict")
        self.assertEqual(len(result.get('imports', [])), 0, "Empty code should have no imports")
        
        # Test None input
        result = self.parser.analyze(None)
        self.assertIsInstance(result, dict, "None input should return empty dict")
        
        # Test invalid syntax
        result = self.parser.analyze("function( {")
        self.assertIsInstance(result, dict, "Invalid syntax should return dict with errors")
        
        # Test with complex code with errors
        complex_code = """
        import React from 'react';
        function Component() {
            return <div>
                {/* Missing closing tag */}
        """
        result = self.parser.analyze(complex_code)
        self.assertIsInstance(result, dict, "Complex code with errors should return dict")
    
    def test_analyze_javascript_features(self):
        """Test analyze with different JavaScript features."""
        # Test ES6 imports
        code = """
        import React from 'react';
        import { useState, useEffect } from 'react';
        import * as ReactDOM from 'react-dom';
        import DefaultExport, { NamedExport } from './module';
        """
        result = self.parser.analyze(code)
        self.assertIsInstance(result, dict, "Should return a dictionary result")
        self.assertIn('imports', result, "Result should include imports key")
        
        # Test CommonJS imports
        code = """
        const fs = require('fs');
        const { join } = require('path');
        const module = require('./local-module');
        """
        result = self.parser.analyze(code)
        self.assertIsInstance(result, dict, "Should return a dictionary result")
        self.assertIn('imports', result, "Result should include imports key")
        
        # Test function declarations and arrow functions
        code = """
        function regularFunction(a, b) {
            return a + b;
        }
        
        const arrowFunction = (a, b) => a + b;
        
        const obj = {
            method() {
                return true;
            }
        };
        """
        result = self.parser.analyze(code)
        self.assertIsInstance(result, dict, "Should return a dictionary result")
        self.assertIn('functions', result, "Result should include functions key")
        
        # Test class declarations
        code = """
        class MyClass {
            constructor(value) {
                this.value = value;
            }
            
            getValue() {
                return this.value;
            }
            
            static create(value) {
                return new MyClass(value);
            }
        }
        """
        result = self.parser.analyze(code)
        self.assertIsInstance(result, dict, "Should return a dictionary result")
        self.assertIn('classes', result, "Result should include classes key")
    
    def test_analyze_exports(self):
        """Test analysis of export statements."""
        # Test various export types
        code = """
        export const value = 42;
        export function func() { return true; }
        export class MyClass {}
        export default { value, func, MyClass };
        export { value as default, func as namedFunc };
        """
        result = self.parser.analyze(code)
        self.assertIsInstance(result, dict, "Should return a dictionary result")
        self.assertIn('exports', result, "Result should include exports key")
    
    def test_version_property(self):
        """Test version property."""
        version = self.parser.version
        self.assertIsNotNone(version, "Version should not be None")
        self.assertIsInstance(version, str, "Version should be a string")

    def test_parse_empty_string(self):
        """Test parsing an empty string."""
        with self.assertRaises(ValueError):
            self.parser.parse("")
    
    def test_parse_empty_bytes(self):
        """Test parsing empty bytes."""
        with self.assertRaises(ValueError):
            self.parser.parse(b"")
    
    def test_parse_invalid_utf8(self):
        """Test parsing invalid UTF-8."""
        result = self.parser.parse(b"\xff\xfe\xfd")
        self.assertIsNone(result)
    
    def test_convert_tree(self):
        """Test converting a tree-sitter Tree to MockTree."""
        source_code = "function test() {}"
        tree = self.parser.parser.parse(bytes(source_code, 'utf-8'))
        mock_tree = self.parser._convert_tree(tree)
        self.assertIsNotNone(mock_tree)
        self.assertEqual(mock_tree.root_node.type, "program")
    
    def test_convert_node(self):
        """Test converting a tree-sitter Node to MockNode."""
        source_code = "function test() {}"
        tree = self.parser.parser.parse(bytes(source_code, 'utf-8'))
        mock_node = self.parser._convert_node(tree.root_node)
        self.assertIsNotNone(mock_node)
        self.assertEqual(mock_node.type, "program")
        self.assertTrue(len(mock_node.children) > 0)
    
    def test_analyze_empty_string(self):
        """Test analyzing an empty string."""
        result = self.parser.analyze("")
        self.assertTrue(result['has_errors'])
        self.assertEqual(result['error_details'][0]['message'], "Empty code")
    
    def test_analyze_empty_bytes(self):
        """Test analyzing empty bytes."""
        result = self.parser.analyze(b"")
        self.assertTrue(result['has_errors'])
        self.assertEqual(result['error_details'][0]['message'], "Empty code")
    
    def test_analyze_invalid_utf8(self):
        """Test analyzing invalid UTF-8."""
        result = self.parser.analyze(b"\xff\xfe\xfd")
        self.assertTrue(result['has_errors'])
        self.assertEqual(result['error_details'][0]['message'], "Invalid UTF-8 encoding")
    
    def test_analyze_syntax_errors(self):
        """Test analyzing code with syntax errors."""
        # Unbalanced braces
        result = self.parser.analyze("function test() {")
        self.assertTrue(result['has_errors'])
        
        # Unbalanced parentheses
        result = self.parser.analyze("function test( {}")
        self.assertTrue(result['has_errors'])
        
        # Unbalanced brackets
        result = self.parser.analyze("const arr = [1, 2, 3;")
        self.assertTrue(result['has_errors'])
        
        # Unclosed strings
        result = self.parser.analyze("const str = 'hello;")
        self.assertTrue(result['has_errors'])
        
        # Unclosed template literals
        result = self.parser.analyze("const tpl = `hello;")
        self.assertTrue(result['has_errors'])
    
    def test_analyze_special_test_cases(self):
        """Test analyzing special test cases."""
        # Test case for test_query_processing
        result = self.parser.analyze("function test() {} import { Component } from 'react';")
        self.assertFalse(result['has_errors'])
        self.assertGreater(len(result['functions']), 0)
        self.assertGreater(len(result['imports']), 0)
        
        # Test case for test_anonymous_functions
        result = self.parser.analyze("const anonymous = function() {}; const arrow = () => {};")
        self.assertFalse(result['has_errors'])
        self.assertGreater(len(result['functions']), 0)
    
    def test_analyze_large_file_performance(self):
        """Test analyzing a large file for performance."""
        # Generate a large JavaScript file with many functions and classes
        large_code = "import { Component } from 'react';\nimport { useState, useEffect } from 'react';\n"
        large_code += "import * as utils from './utils';\n"
        
        # Add 100 functions and classes
        for i in range(100):
            large_code += f"function test{i}() {{ return {i}; }}\n"
            large_code += f"class TestClass{i} {{ method() {{ return {i}; }} }}\n"
        
        result = self.parser.analyze(large_code)
        self.assertFalse(result['has_errors'])
        self.assertGreater(len(result['functions']), 0)
        self.assertGreater(len(result['classes']), 0)
        self.assertGreater(len(result['imports']), 0)
    
    def test_analyze_error_recovery(self):
        """Test error recovery in analysis."""
        code = """
        function validFunction() { return true; }
        function invalidFunction() { return; ]])
        """
        result = self.parser.analyze(code)
        self.assertTrue(result['has_errors'])
        self.assertGreater(len(result['functions']), 0)
    
    def test_error_test_cases(self):
        """Test specific error test cases."""
        error_test_cases = [
            "function test() {",
            "const str = `Hello ${name",
            "class Test {",
            "import { from 'module'",
            "export { from 'module'",
            "@invalidDecorator",
            "class Test { #invalid }",
            "async function test() { await }",
            "const value = obj?.",
            "const value = ?? defaultValue"
        ]
        
        for case in error_test_cases:
            result = self.parser.analyze(case)
            self.assertTrue(result['has_errors'])
    
    def test_get_function_name(self):
        """Test function name extraction."""
        # Function declaration
        code = "function testFunc() {}"
        tree = self.parser.parser.parse(bytes(code, 'utf-8'))
        func_node = None
        for node in tree.root_node.children:
            if node.type == "function_declaration":
                func_node = node
                break
        
        if func_node:
            name = self.parser._get_function_name(func_node)
            self.assertEqual(name, "testFunc")
        
        # Arrow function
        code = "const arrowFunc = () => {};"
        tree = self.parser.parser.parse(bytes(code, 'utf-8'))
        arrow_node = None
        for node in tree.root_node.children:
            if node.type == "lexical_declaration":
                for child in node.children:
                    if child.type == "variable_declarator":
                        for subchild in child.children:
                            if subchild.type == "arrow_function":
                                arrow_node = subchild
                                break
        
        if arrow_node:
            name = self.parser._get_function_name(arrow_node)
            self.assertEqual(name, "arrowFunc")
    
    def test_cleanup_temp_files(self):
        """Test cleanup of temporary files."""
        import tempfile
        from pathlib import Path
        
        # Create a temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create some files
        (temp_dir / "test.txt").write_text("test")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "test2.txt").write_text("test2")
        
        # Call cleanup
        self.parser._cleanup_temp_files(temp_dir)
        
        # Check directory no longer exists
        self.assertFalse(temp_dir.exists())
    
    def test_extract_functions(self):
        """Test function extraction."""
        code = """
        function regular() { return true; }
        async function asyncFunc() { await fetch('/api'); }
        function* generator() { yield 1; }
        const arrow = () => false;
        """
        
        result = self.parser.analyze(code)
        self.assertFalse(result['has_errors'])
        # Validate specifically for function extraction
        functions = result['functions']
        function_names = [f['name'] for f in functions]
        self.assertIn('regular', function_names)
        self.assertIn('asyncFunc', function_names)
        self.assertIn('generator', function_names)
        
        # Check async flag for asyncFunc
        async_funcs = [f for f in functions if f['name'] == 'asyncFunc']
        if async_funcs:
            self.assertTrue(async_funcs[0]['is_async'])
    
    def test_extract_classes(self):
        """Test class extraction."""
        code = """
        class TestClass {
            constructor() {
                this.prop = 1;
            }
            
            method() {
                return this.prop;
            }
            
            get propValue() {
                return this.prop;
            }
            
            static staticMethod() {
                return 'static';
            }
        }
        """
        
        result = self.parser.analyze(code)
        self.assertFalse(result['has_errors'])
        # Validate specifically for class extraction
        classes = result['classes']
        self.assertEqual(len(classes), 1)
        
        # Check for the class by name
        test_class = classes[0]
        self.assertEqual(test_class['name'], 'TestClass')
        
        # Check for methods
        methods = test_class['methods']
        method_names = [m['name'] for m in methods]
        self.assertIn('constructor', method_names)
        self.assertIn('method', method_names)
        self.assertIn('propValue', method_names)
        self.assertIn('staticMethod', method_names)
    
    def test_extract_imports(self):
        """Test import extraction."""
        code = """
        import defaultImport from 'module';
        import { namedImport1, namedImport2 } from 'module2';
        import * as namespace from 'module3';
        import defaultAndNamed, { named1, named2 } from 'module4';
        """
        
        result = self.parser.analyze(code)
        self.assertFalse(result['has_errors'])
        # Validate specifically for import extraction
        imports = result['imports']
        self.assertEqual(len(imports), 4)
        
        # Check for imports by module
        import_modules = [i['module'] for i in imports if 'module' in i]
        self.assertIn('module', import_modules)
        self.assertIn('module2', import_modules)
        self.assertIn('module3', import_modules)
        self.assertIn('module4', import_modules)
        
        # Check default imports
        default_imports = [i for i in imports if i.get('is_default', False) and 'name' in i]
        default_import_names = [i['name'] for i in default_imports]
        self.assertIn('defaultImport', default_import_names)
    
    def test_extract_exports(self):
        """Test export extraction."""
        code = """
        export const constantVar = 42;
        export let mutableVar = 'mutable';
        export function exportedFunction() { return true; }
        export class ExportedClass {}
        export default function defaultExport() {}
        export { thing1, thing2 };
        export * from './module';
        """
        
        result = self.parser.analyze(code)
        self.assertFalse(result['has_errors'])
        # Validate specifically for export extraction
        exports = result['exports']
        self.assertGreaterEqual(len(exports), 5)
        
        # Check for specific exports
        export_names = [e.get('name', '') for e in exports]
        self.assertIn('constantVar', export_names)
        self.assertIn('mutableVar', export_names)
        self.assertIn('exportedFunction', export_names)
        self.assertIn('ExportedClass', export_names)
        
        # Check for default exports
        default_exports = [e for e in exports if e.get('is_default', False)]
        self.assertGreaterEqual(len(default_exports), 1)
        
        # Check export types
        export_types = [e.get('export_type', '') for e in exports]
        self.assertIn('function', export_types)
        self.assertIn('variable', export_types)
        self.assertIn('class', export_types)

if __name__ == '__main__':
    unittest.main() 