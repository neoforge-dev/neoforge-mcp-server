'''Tests for JavaScript and Swift parsing adapters.'''

import unittest
from server.code_understanding.language_adapters import JavaScriptParserAdapter, SwiftParserAdapter


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


class TestSwiftParserAdapter(unittest.TestCase):
    def test_parse_valid_swift(self):
        adapter = SwiftParserAdapter()
        code = "func test() { print(\"Hello\") }"
        tree = adapter.parse(code)
        self.assertIsNotNone(tree)
        self.assertEqual(tree.root_node.type, 'source_file')

    def test_parse_invalid_swift(self):
        adapter = SwiftParserAdapter()
        code = ""  # Empty code
        with self.assertRaises(ValueError):
            adapter.parse(code)

    def test_parse_swift_class(self):
        adapter = SwiftParserAdapter()
        code = "class Test { init() { print(\"Test\") } }"
        tree = adapter.parse(code)
        self.assertIsNotNone(tree)
        self.assertEqual(tree.root_node.type, 'source_file')

    def test_parse_swift_variable(self):
        adapter = SwiftParserAdapter()
        code = "var x: Int = 42"
        tree = adapter.parse(code)
        self.assertIsNotNone(tree)
        self.assertEqual(tree.root_node.type, 'source_file')


if __name__ == '__main__':
    unittest.main() 