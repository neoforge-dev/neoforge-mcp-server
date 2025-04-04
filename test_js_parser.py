"""Simple tests for the JavaScriptParserAdapter."""

import unittest
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from server.code_understanding.language_adapters import JavaScriptParserAdapter
except ImportError:
    from language_adapters import JavaScriptParserAdapter

class TestJavaScriptParser(unittest.TestCase):
    """Test the JavaScript parser adapter."""
    
    def setUp(self):
        """Set up the test."""
        self.parser = JavaScriptParserAdapter()
    
    def test_parse_simple_function(self):
        """Test parsing a simple function."""
        code = """
        function greet(name) {
            return `Hello, ${name}!`;
        }
        """
        
        result = self.parser.analyze(code)
        
        # Check that the parse worked
        self.assertIn('functions', result)
        self.assertGreaterEqual(len(result['functions']), 1)
        
        # Check the function details
        func = next((f for f in result['functions'] if f['name'] == 'greet'), None)
        self.assertIsNotNone(func, "Function 'greet' not found")
        self.assertEqual(func['name'], 'greet')
        self.assertFalse(func['is_async'])
        self.assertEqual(func['parameters'], ['name'])
    
    def test_parse_es6_import(self):
        """Test parsing ES6 imports."""
        code = "import React from 'react';"
        
        result = self.parser.analyze(code)
        
        # Check the imports
        self.assertIn('imports', result)
        self.assertEqual(len(result['imports']), 1)
        
        # Check import details
        imp = result['imports'][0]
        self.assertEqual(imp['name'], 'React')
        self.assertEqual(imp['module'], 'react')
        self.assertTrue(imp['is_default'])
    
    def test_parse_export(self):
        """Test parsing exports."""
        code = "export default function App() { return null; }"
        
        result = self.parser.analyze(code)
        
        # Check the exports
        self.assertIn('exports', result)
        self.assertGreaterEqual(len(result['exports']), 1)
        
        # Check export details
        exp = next((e for e in result['exports'] if e.get('is_default')), None)
        self.assertIsNotNone(exp, "Default export not found")
        self.assertTrue(exp['is_default'])
    
    def test_parse_class(self):
        """Test parsing a class."""
        code = """
        class Counter {
            count = 0;
            
            increment() {
                this.count++;
            }
            
            decrement() {
                this.count--;
            }
        }
        """
        
        result = self.parser.analyze(code)
        
        # Check the classes
        self.assertIn('classes', result)
        self.assertEqual(len(result['classes']), 1)
        
        # Check class details
        cls = result['classes'][0]
        self.assertEqual(cls['name'], 'Counter')
        self.assertGreaterEqual(len(cls['methods']), 2)

if __name__ == '__main__':
    unittest.main() 