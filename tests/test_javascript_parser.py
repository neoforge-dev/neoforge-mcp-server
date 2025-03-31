"""Tests for the JavaScript parser."""

import unittest
from server.code_understanding.javascript_parser import JavaScriptParser

class TestJavaScriptParser(unittest.TestCase):
    """Test cases for JavaScriptParser."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = JavaScriptParser()
        
    def test_parse_empty_code(self):
        """Test parsing empty code."""
        tree = self.parser.parse("")
        self.assertIsNone(tree)
        
    def test_parse_basic_function(self):
        """Test parsing basic function declaration."""
        code = "function test() { console.log('Hello'); }"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.assertEqual(tree.type, 'program')
        
        # Extract symbols
        symbols = self.parser.get_symbols(tree)
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0]['name'], 'test')
        self.assertEqual(symbols[0]['type'], 'function')
        
    def test_parse_async_function(self):
        """Test parsing async function declaration."""
        code = "async function fetchData() { return await api.get(); }"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        
        # Extract symbols
        symbols = self.parser.get_symbols(tree)
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0]['name'], 'fetchData')
        self.assertEqual(symbols[0]['type'], 'function')
        
    def test_parse_class(self):
        """Test parsing class declaration."""
        code = "class Test { constructor() { console.log('Test'); } }"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        
        # Extract symbols
        symbols = self.parser.get_symbols(tree)
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0]['name'], 'Test')
        self.assertEqual(symbols[0]['type'], 'class')
        
    def test_parse_imports(self):
        """Test parsing import statements."""
        code = "import { process } from './utils.js';"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        
        # Extract imports
        imports = self.parser.get_imports(tree)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0]['source'], './utils.js')
        self.assertEqual(imports[0]['specifier'], 'process')
        
    def test_parse_exports(self):
        """Test parsing export statements."""
        code = "export const PI = 3.14;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        
        # Extract exports
        exports = self.parser.get_exports(tree)
        self.assertEqual(len(exports), 1)
        self.assertEqual(exports[0]['name'], 'PI')
        
    def test_parse_requires(self):
        """Test parsing require statements."""
        code = "const fs = require('fs');"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        
        # Extract requires
        requires = self.parser.get_requires(tree)
        self.assertEqual(len(requires), 1)
        self.assertEqual(requires[0]['source'], 'fs')
        
    def test_parse_complex_module(self):
        """Test parsing a complex JavaScript module."""
        code = """
        import { process } from './utils.js';
        
        class DataProcessor {
            constructor(config) {
                this.config = config;
                this.data = [];
            }
            
            async process(inputData) {
                const result = [];
                for (const item of inputData) {
                    if (item > 0) {
                        result.push(await process(item));
                    }
                }
                return result;
            }
        }
        
        export const main = async () => {
            const processor = new DataProcessor({ threshold: 0 });
            const data = [1, 2, 3, -1, -2];
            const result = await processor.process(data);
            console.log(result);
        };
        """
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        
        # Extract imports
        imports = self.parser.get_imports(tree)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0]['source'], './utils.js')
        self.assertEqual(imports[0]['specifier'], 'process')
        
        # Extract exports
        exports = self.parser.get_exports(tree)
        self.assertEqual(len(exports), 1)
        self.assertEqual(exports[0]['name'], 'main')
        
        # Extract symbols
        symbols = self.parser.get_symbols(tree)
        self.assertEqual(len(symbols), 2)  # DataProcessor and main
        self.assertEqual(symbols[0]['name'], 'DataProcessor')
        self.assertEqual(symbols[0]['type'], 'class')
        self.assertEqual(symbols[1]['name'], 'main')
        self.assertEqual(symbols[1]['type'], 'variable')
        
    def test_error_handling(self):
        """Test handling of invalid JavaScript code."""
        # Test invalid syntax
        tree = self.parser.parse("invalid javascript code")
        self.assertIsNone(tree)
        
        # Test malformed imports
        tree = self.parser.parse("import { from './test';")
        self.assertIsNotNone(tree)
        imports = self.parser.get_imports(tree)
        self.assertEqual(len(imports), 0)
        
        # Test malformed exports
        tree = self.parser.parse("export { from './test';")
        self.assertIsNotNone(tree)
        exports = self.parser.get_exports(tree)
        self.assertEqual(len(exports), 0)
        
    def test_symbol_types(self):
        """Test symbol type inference."""
        code = """
        const number = 42;
        let string = 'hello';
        var boolean = true;
        const array = [1, 2, 3];
        const object = { key: 'value' };
        function func() {}
        class Class {}
        """
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        
        # Extract symbols
        symbols = self.parser.get_symbols(tree)
        self.assertEqual(len(symbols), 7)
        
        # Check types
        symbol_types = {s['name']: s['type'] for s in symbols}
        self.assertEqual(symbol_types['number'], 'variable')
        self.assertEqual(symbol_types['string'], 'variable')
        self.assertEqual(symbol_types['boolean'], 'variable')
        self.assertEqual(symbol_types['array'], 'variable')
        self.assertEqual(symbol_types['object'], 'variable')
        self.assertEqual(symbol_types['func'], 'function')
        self.assertEqual(symbol_types['Class'], 'class')

if __name__ == '__main__':
    unittest.main() 