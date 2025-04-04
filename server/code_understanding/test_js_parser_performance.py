import os
import sys
import unittest
import tempfile
import logging
import time
import psutil
from pathlib import Path

# Add the repository root to Python path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from server.code_understanding.language_adapters import JavaScriptParserAdapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestJavaScriptParserPerformance(unittest.TestCase):
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
    
    def test_performance_large_file(self):
        """Test performance with a large JavaScript file."""
        # Create a large file with various JavaScript features
        large_js = []
        
        # Add imports
        large_js.append("import React from 'react';")
        large_js.append("import { useState, useEffect } from 'react';")
        
        # Add classes
        for i in range(100):
            large_js.append(f"""
            class Component{i} {{
                constructor(props) {{
                    this.props = props;
                }}
                
                render() {{
                    return <div>Component {i}</div>;
                }}
            }}
            """)
        
        # Add functions
        for i in range(1000):
            large_js.append(f"""
            function function{i}() {{
                return {i} * {i};
            }}
            """)
        
        # Add async functions
        for i in range(100):
            large_js.append(f"""
            async function asyncFunction{i}() {{
                await new Promise(resolve => setTimeout(resolve, 100));
                return {i};
            }}
            """)
        
        # Add generator functions
        for i in range(100):
            large_js.append(f"""
            function* generator{i}() {{
                yield {i};
                yield {i * 2};
                yield {i * 3};
            }}
            """)
        
        # Combine all code
        js_code = "\n".join(large_js)
        file_path = self.create_temp_file(js_code)
        
        # Measure memory before parsing
        memory_before = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        
        # Parse the file and measure time
        start_time = time.time()
        result = self.parser.analyze(file_path)
        end_time = time.time()
        
        # Measure memory after parsing
        memory_after = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        memory_used = memory_after - memory_before
        
        # Log performance metrics
        logger.info(f"Parsing time: {end_time - start_time:.2f}s")
        logger.info(f"Memory used: {memory_used:.2f}MB")
        logger.info(f"Functions found: {len(result['functions'])}")
        logger.info(f"Classes found: {len(result['classes'])}")
        
        # Verify results
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['functions']), 1200)  # 1000 functions + 100 async + 100 generators
        self.assertEqual(len(result['classes']), 100)
        
        # Performance requirements
        self.assertLess(end_time - start_time, 5.0)  # Should parse in under 5 seconds
        self.assertLess(memory_used, 500.0)  # Should use less than 500MB of memory
    
    def test_performance_memory_pressure(self):
        """Test performance under memory pressure."""
        # Create a very large file to test memory handling
        large_js = []
        
        # Add a large number of functions with complex bodies
        for i in range(5000):
            large_js.append(f"""
            function complexFunction{i}() {{
                const data = new Array(1000).fill(0).map((_, j) => ({{
                    id: j,
                    value: Math.random(),
                    nested: {{
                        a: Math.random(),
                        b: Math.random(),
                        c: Math.random()
                    }}
                }}));
                
                return data.filter(item => item.value > 0.5)
                    .map(item => ({{
                        ...item,
                        processed: true,
                        timestamp: Date.now()
                    }}));
            }}
            """)
        
        # Combine all code
        js_code = "\n".join(large_js)
        file_path = self.create_temp_file(js_code)
        
        # Measure memory before parsing
        memory_before = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        
        # Parse the file and measure time
        start_time = time.time()
        result = self.parser.analyze(file_path)
        end_time = time.time()
        
        # Measure memory after parsing
        memory_after = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        memory_used = memory_after - memory_before
        
        # Log performance metrics
        logger.info(f"Parsing time under memory pressure: {end_time - start_time:.2f}s")
        logger.info(f"Memory used under pressure: {memory_used:.2f}MB")
        logger.info(f"Functions found: {len(result['functions'])}")
        
        # Verify results
        self.assertFalse(result['has_errors'])
        self.assertEqual(len(result['functions']), 5000)
        
        # Performance requirements under memory pressure
        self.assertLess(end_time - start_time, 10.0)  # Should parse in under 10 seconds
        self.assertLess(memory_used, 1000.0)  # Should use less than 1GB of memory
    
    def test_performance_concurrent_parsing(self):
        """Test performance with concurrent parsing of multiple files."""
        # Create multiple medium-sized files
        file_paths = []
        for i in range(5):
            js_code = f"""
            // File {i}
            import React from 'react';
            
            class Component{i} {{
                constructor(props) {{
                    this.props = props;
                }}
                
                render() {{
                    return <div>Component {i}</div>;
                }}
            }}
            
            function function{i}() {{
                return {i} * {i};
            }}
            
            async function asyncFunction{i}() {{
                await new Promise(resolve => setTimeout(resolve, 100));
                return {i};
            }}
            """
            file_paths.append(self.create_temp_file(js_code))
        
        # Measure memory before parsing
        memory_before = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        
        # Parse all files concurrently and measure time
        start_time = time.time()
        results = []
        for file_path in file_paths:
            result = self.parser.analyze(file_path)
            results.append(result)
        end_time = time.time()
        
        # Measure memory after parsing
        memory_after = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        memory_used = memory_after - memory_before
        
        # Log performance metrics
        logger.info(f"Concurrent parsing time: {end_time - start_time:.2f}s")
        logger.info(f"Memory used for concurrent parsing: {memory_used:.2f}MB")
        
        # Verify results
        for i, result in enumerate(results):
            self.assertFalse(result['has_errors'])
            self.assertEqual(len(result['functions']), 2)  # function and asyncFunction
            self.assertEqual(len(result['classes']), 1)  # Component
        
        # Performance requirements for concurrent parsing
        self.assertLess(end_time - start_time, 3.0)  # Should parse all files in under 3 seconds
        self.assertLess(memory_used, 300.0)  # Should use less than 300MB of memory

if __name__ == '__main__':
    unittest.main() 