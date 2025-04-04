import os
import sys
import unittest
import tempfile
import logging
from pathlib import Path

# Add the repository root to Python path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from server.code_understanding.language_adapters import JavaScriptParserAdapter, ParserError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestJavaScriptParserEdgeCases(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.parser = JavaScriptParserAdapter()
        self.temp_files = []
        
    def tearDown(self):
        """Clean up test environment after each test."""
        for file_path in self.temp_files:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def create_temp_file(self, content):
        """Create a temporary file with the provided content."""
        fd, file_path = tempfile.mkstemp(suffix='.js')
        os.close(fd)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.temp_files.append(file_path)
        return file_path
    
    def test_parse_invalid_js(self):
        """Test parsing invalid JavaScript code."""
        invalid_js = """
        function invalid() {
            return
            {
                foo: 'bar'
            }
        }
        """
        file_path = self.create_temp_file(invalid_js)
        result = self.parser.analyze(file_path)
        self.assertTrue(result['has_errors'])
        self.assertIn('error_details', result)
    
    def test_parse_unicode_characters(self):
        """Test parsing JavaScript with Unicode characters."""
        unicode_js = """
        const 你好 = 'world';
        function 测试() {
            return 你好;
        }
        """
        file_path = self.create_temp_file(unicode_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
        self.assertIn('functions', result)
    
    def test_parse_large_file(self):
        """Test parsing a large JavaScript file."""
        large_js = "// Large file test\n" + "function test() {}\n" * 1000
        file_path = self.create_temp_file(large_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['functions']), 1000)
    
    def test_parse_empty_file(self):
        """Test parsing an empty file."""
        file_path = self.create_temp_file("")
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['functions']), 0)
        self.assertEqual(len(result['classes']), 0)
        self.assertEqual(len(result['imports']), 0)
        self.assertEqual(len(result['exports']), 0)
    
    def test_parse_comments_only(self):
        """Test parsing a file with only comments."""
        comments_js = """
        // Single line comment
        /* Multi-line
           comment */
        """
        file_path = self.create_temp_file(comments_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['functions']), 0)
    
    def test_parse_async_functions(self):
        """Test parsing async functions."""
        async_js = """
        async function test1() {}
        const test2 = async () => {};
        class Test {
            async method() {}
        }
        """
        file_path = self.create_temp_file(async_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['functions']), 3)
    
    def test_parse_generator_functions(self):
        """Test parsing generator functions."""
        generator_js = """
        function* test1() {}
        const test2 = function*() {};
        class Test {
            *method() {}
        }
        """
        file_path = self.create_temp_file(generator_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['functions']), 3)
    
    def test_parse_dynamic_imports(self):
        """Test parsing dynamic imports."""
        dynamic_import_js = """
        import('module1');
        const module2 = await import('module2');
        """
        file_path = self.create_temp_file(dynamic_import_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['imports']), 2)
    
    def test_parse_export_all(self):
        """Test parsing export all statements."""
        export_all_js = """
        export * from 'module1';
        export * as ns from 'module2';
        """
        file_path = self.create_temp_file(export_all_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['exports']), 2)
    
    def test_parse_decorators(self):
        """Test parsing decorators."""
        decorator_js = """
        @decorator
        class Test {}
        
        class Test2 {
            @methodDecorator
            method() {}
        }
        """
        file_path = self.create_temp_file(decorator_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['classes']), 2)
    
    def test_parse_private_fields(self):
        """Test parsing private fields."""
        private_fields_js = """
        class Test {
            #privateField = 1;
            #privateMethod() {}
        }
        """
        file_path = self.create_temp_file(private_fields_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['classes']), 1)
    
    def test_parse_static_fields(self):
        """Test parsing static fields."""
        static_fields_js = """
        class Test {
            static field = 1;
            static method() {}
        }
        """
        file_path = self.create_temp_file(static_fields_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['classes']), 1)
    
    def test_parse_nullish_coalescing(self):
        """Test parsing nullish coalescing operator."""
        nullish_js = """
        const test = a ?? b;
        """
        file_path = self.create_temp_file(nullish_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
    
    def test_parse_optional_chaining(self):
        """Test parsing optional chaining operator."""
        optional_js = """
        const test = obj?.prop?.method?.();
        """
        file_path = self.create_temp_file(optional_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
    
    def test_parse_bigint(self):
        """Test parsing BigInt literals."""
        bigint_js = """
        const big = 123n;
        """
        file_path = self.create_temp_file(bigint_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])
    
    def test_parse_import_meta(self):
        """Test parsing import.meta."""
        import_meta_js = """
        const url = import.meta.url;
        """
        file_path = self.create_temp_file(import_meta_js)
        result = self.parser.analyze(file_path)
        self.assertFalse(result['has_errors'])

if __name__ == '__main__':
    unittest.main() 