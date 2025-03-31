'''Tests for JavaScript parsing support.'''

import unittest
from server.code_understanding.language_adapters import JavaScriptParserAdapter
from server.code_understanding.symbols import SymbolExtractor


class TestJavaScriptParserAdapter(unittest.TestCase):
    def test_parse_valid_js(self):
        adapter = JavaScriptParserAdapter()
        code = "function test() { console.log('Hello'); }"
        tree = adapter.parse(code)
        self.assertIsNotNone(tree)
        self.assertEqual(tree.root_node.type, 'program')

    def test_parse_invalid_js(self):
        adapter = JavaScriptParserAdapter()
        code = ""  # Empty code
        with self.assertRaises(ValueError):
            adapter.parse(code)

    def test_parse_js_class(self):
        adapter = JavaScriptParserAdapter()
        code = "class Test { constructor() { console.log('Test'); } }"
        tree = adapter.parse(code)
        self.assertIsNotNone(tree)
        self.assertEqual(tree.root_node.type, 'program')

    def test_parse_js_variable(self):
        adapter = JavaScriptParserAdapter()
        code = "let x = 42;"
        tree = adapter.parse(code)
        self.assertIsNotNone(tree)
        self.assertEqual(tree.root_node.type, 'program')


class TestJavaScriptSymbolExtraction(unittest.TestCase):
    def test_extract_function(self):
        adapter = JavaScriptParserAdapter()
        code = "function test() { console.log('Hello'); }"
        tree = adapter.parse(code)
        extractor = SymbolExtractor()
        symbols = extractor.extract_symbols(tree)
        self.assertIn('functions', symbols)
        self.assertEqual(len(symbols['functions']), 1)
        self.assertEqual(symbols['functions'][0]['name'], 'test')

    def test_extract_class(self):
        adapter = JavaScriptParserAdapter()
        code = "class Test { constructor() { console.log('Test'); } }"
        tree = adapter.parse(code)
        extractor = SymbolExtractor()
        symbols = extractor.extract_symbols(tree)
        self.assertIn('classes', symbols)
        self.assertEqual(len(symbols['classes']), 1)
        self.assertEqual(symbols['classes'][0]['name'], 'Test')

    def test_extract_variable(self):
        adapter = JavaScriptParserAdapter()
        code = "let x = 42;"
        tree = adapter.parse(code)
        extractor = SymbolExtractor()
        symbols = extractor.extract_symbols(tree)
        self.assertIn('variables', symbols)
        self.assertEqual(len(symbols['variables']), 1)
        self.assertEqual(symbols['variables'][0]['name'], 'x')


if __name__ == '__main__':
    unittest.main() 