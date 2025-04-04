import os
import sys
import unittest
import logging
from unittest.mock import patch, MagicMock
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Add the repository root to the Python path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import directly from server directory
from server.code_understanding.language_adapters import JavaScriptParserAdapter
from server.code_understanding.language_adapters import MockNode, MockTree

class TestJavaScriptParserCoverage(unittest.TestCase):
    """Test suite for JavaScript parser coverage targeting uncovered paths."""
    
    def setUp(self):
        """Set up the parser for each test."""
        self.parser = JavaScriptParserAdapter()
    
    def test_convert_node_failures(self):
        """Test various failure paths in _convert_node method."""
        # Test with node that raises exception during text decoding
        mock_node = MagicMock()
        mock_node.text = bytes([0xFF, 0xFE, 0xFD])  # Invalid UTF-8
        mock_node.type = "program"
        mock_node.start_point = (0, 0)
        mock_node.end_point = (1, 0)
        mock_node.child_count = 0
        
        # Patch the decode method to raise an exception
        with patch.object(mock_node.text, 'decode', side_effect=Exception("Test decoding error")):
            result = self.parser._convert_node(mock_node)
            self.assertIsNotNone(result, "Should handle decode errors and still return a node")
    
    def test_extract_functions_edge_cases(self):
        """Test function extraction edge cases."""
        # Test with different function capture formats
        test_captures = [(MagicMock(), "function")]
        
        # Create a mock function node
        mock_function = MagicMock()
        mock_function.type = "function_declaration"
        mock_function.text = b"function test() {}"
        
        # Set up name extraction
        name_node = MagicMock()
        name_node.text = b"test"
        mock_function.child_by_field_name.return_value = name_node
        
        # Add the mock function to the captures
        test_captures[0] = (mock_function, "function")
        
        # Mock the tree and query
        mock_tree = MagicMock()
        mock_tree.root_node = MagicMock()
        
        # Test different capture formats
        with patch.object(self.parser.function_query, 'captures', return_value=test_captures):
            result = {'functions': []}
            self.parser._extract_functions(mock_tree, result)
            self.assertGreater(len(result['functions']), 0)
    
    def test_analyze_syntax_errors(self):
        """Test syntax error detection in analyze method."""
        # Test all syntax error cases
        syntax_error_cases = [
            # Unbalanced delimiters
            "function test() {",  # Unbalanced braces
            "function test( {}",  # Unbalanced parentheses
            "const arr = [1, 2",  # Unbalanced brackets
            
            # Unclosed string literals
            "const s = 'hello",   # Unclosed single quote
            'const s = "hello',   # Unclosed double quote
            "const s = `hello",   # Unclosed template literal
            
            # JSX-like syntax in plain JavaScript
            "<div>Hello</div>",
            
            # Incomplete declarations
            "function test(",
            "class Test",
            "const x =",
            
            # Special patterns
            "import { Component",
            "export { Component",
            "@decorator",
            "class Test { #invalid }",
            "async function test() { await }",
            "const obj?.",
            "const x ?? y"
        ]
        
        for case in syntax_error_cases:
            result = self.parser.analyze(case)
            self.assertTrue(result['has_errors'], f"Failed to detect error in: {case}")
    
    def test_analyze_error_recovery(self):
        """Test error recovery in analyze method."""
        # Test case with a recoverable error
        code = """
        function validFunction() { return true; }
        function invalidFunction() { return; ]])
        """
        result = self.parser.analyze(code)
        self.assertTrue(result['has_errors'])
        self.assertGreater(len(result['functions']), 0)
    
    def test_version_property(self):
        """Test version property with mocks to cover additional paths."""
        # Test with various conditions
        with patch.object(Path, 'exists', return_value=True):
            with patch('builtins.open', side_effect=Exception("Test open exception")):
                version = self.parser.version
                self.assertIsNone(version)
        
        # Test with language None
        with patch.object(self.parser, 'language', None):
            version = self.parser.version
            self.assertIsNone(version)
    
    def test_large_file_optimization(self):
        """Test the special case optimization for large files."""
        # Create code that triggers the large file optimization
        large_code = "import { Component } from 'react';\nimport { useState, useEffect } from 'react';\n"
        large_code += "import * as utils from './utils';\n"
        
        # Add 50 functions and classes to make it look like a large file
        for i in range(50):
            large_code += f"function test{i}() {{ return {i}; }}\n"
            large_code += f"class TestClass{i} {{ method() {{ return {i}; }} }}\n"
        
        # Run analysis
        result = self.parser.analyze(large_code)
        self.assertFalse(result['has_errors'])
        self.assertGreater(len(result['functions']), 0)
        self.assertGreater(len(result['classes']), 0)
    
    def test_special_test_cases(self):
        """Test special test cases in analyze method."""
        # Test case for test_query_processing
        result = self.parser.analyze("function test() {} import { Component } from 'react';")
        self.assertFalse(result['has_errors'])
        self.assertGreater(len(result['functions']), 0)
        
        # Test case for test_anonymous_functions
        result = self.parser.analyze("const anonymous = function() {}; const arrow = () => {};")
        self.assertFalse(result['has_errors'])
    
    def test_analyze_exceptions(self):
        """Test exception handling in analyze method."""
        # Test with parse returning None
        with patch.object(self.parser, 'parse', return_value=None):
            result = self.parser.analyze("function test() {}")
            self.assertTrue(result['has_errors'])
        
        # Test with exception in parse
        with patch.object(self.parser, 'parse', side_effect=Exception("Test exception")):
            result = self.parser.analyze("function test() {}")
            self.assertTrue(result['has_errors'])
        
        # Test with exception in _extract_functions
        with patch.object(self.parser, '_extract_functions', side_effect=Exception("Extract functions error")):
            result = self.parser.analyze("function test() {}")
            self.assertTrue(result['has_errors'])

if __name__ == "__main__":
    unittest.main() 