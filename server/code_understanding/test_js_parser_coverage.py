import os
import sys
import unittest
import tempfile
import logging
from pathlib import Path

# Add the repository root to Python path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from server.code_understanding.language_adapters import JavaScriptParserAdapter

# Configure logging
logging.basicConfig(level=logging.INFO)

class TestJavaScriptParserCoverage(unittest.TestCase):
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
    
    def test_initialize(self):
        """Test parser initialization and language loading."""
        parser = JavaScriptParserAdapter()
        self.assertIsNotNone(parser.language)
        # The parser doesn't have a query attribute, but it does initialize queries internally
    
    def test_parse_empty_file(self):
        """Test parsing an empty file."""
        file_path = self.create_temp_file("")
        result = self.parser.parse(file_path)
        self.assertIsNotNone(result)
        # Checking parse results directly
        
    def test_parse_simple_js(self):
        """Test parsing simple valid JavaScript."""
        js_code = """
        // A simple function
        function hello() {
            console.log('Hello world');
        }
        """
        file_path = self.create_temp_file(js_code)
        result = self.parser.analyze(file_path)
        # Just verify it doesn't crash
        self.assertFalse(result['has_errors'])
    
    def test_analyze_returns_expected_keys(self):
        """Test that the analyze method returns all expected keys."""
        js_code = """
        // A simple JavaScript file with different features
        function greet(name) {
            return `Hello, ${name}!`;
        }
        
        class Person {
            constructor(name) {
                this.name = name;
            }
        }
        """
        
        file_path = self.create_temp_file(js_code)
        result = self.parser.analyze(file_path)
        
        # Verify that the result contains all expected keys
        self.assertIn('has_errors', result)
        self.assertIn('error_details', result)
        self.assertIn('functions', result)
        self.assertIn('classes', result)
        self.assertIn('imports', result)
        self.assertIn('exports', result)
        self.assertIn('tree', result)  # Parse tree should be included
        
        # Verify no errors
        self.assertFalse(result['has_errors'])
    
    def test_analyzer_doesnt_crash_on_complex_js(self):
        """Test that the analyzer doesn't crash on more complex JavaScript."""
        # A more complex file with imports, exports, classes, functions
        js_code = """
        import React from 'react';
        import { useState, useEffect } from 'react';
        
        export const API_URL = 'https://api.example.com';
        
        export function fetchData() {
            return fetch(API_URL);
        }
        
        export class DataService {
            constructor(baseUrl) {
                this.baseUrl = baseUrl;
            }
            
            async getData() {
                const response = await fetch(this.baseUrl);
                return response.json();
            }
        }
        
        export default function App() {
            const [data, setData] = useState(null);
            
            useEffect(() => {
                fetchData()
                    .then(response => response.json())
                    .then(data => setData(data));
            }, []);
            
            return (
                <div>
                    {data ? (
                        <ul>
                            {data.map(item => (
                                <li key={item.id}>{item.name}</li>
                            ))}
                        </ul>
                    ) : (
                        <p>Loading...</p>
                    )}
                </div>
            );
        }
        """
        
        file_path = self.create_temp_file(js_code)
        result = self.parser.analyze(file_path)
        
        # Just verify it doesn't crash and returns a result
        self.assertIsNotNone(result)
        self.assertFalse(result['has_errors'])

if __name__ == '__main__':
    unittest.main() 