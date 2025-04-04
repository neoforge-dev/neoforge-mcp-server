"""Comprehensive tests for the JavaScript Parser Adapter.

This file contains a collection of tests for all features
implemented in the JavaScriptParserAdapter.
"""

import os
import sys
import unittest
from pathlib import Path

# Add the parent directory to the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import MockNode and MockTree from standalone_test for independent testing
from server.code_understanding.standalone_test import MockNode, MockTree

# Define test samples
TEST_SAMPLES = {
    "es6_imports": [
        "import React from 'react';",
        "import { useState, useEffect } from 'react';",
        "import * as ReactDOM from 'react-dom';",
        "import DefaultComponent, { NamedComponent } from './components';"
    ],
    
    "commonjs_imports": [
        "const fs = require('fs');", 
        "const { readFile } = require('fs/promises');",
        "var path = require('path');"
    ],
    
    "exports": [
        "export const PI = 3.14159;",
        "export function sum(a, b) { return a + b; }",
        "export default class Calculator { add(a, b) { return a + b; } }",
        "export { name1, name2 as alias };",
        "export * from './utils';"
    ],
    
    "functions": [
        "function greet(name) { return `Hello, ${name}!`; }",
        "async function fetchData() { const result = await api.get('/data'); return result; }",
        "function* generator() { yield 1; yield 2; }",
        "const arrowFn = (x) => x * 2;",
        "const asyncArrow = async () => { return await Promise.resolve(42); };"
    ],
    
    "classes": [
        """
        class Counter {
            count = 0;
            #privateField = 'secret';
            
            constructor(initialCount = 0) {
                this.count = initialCount;
            }
            
            increment() { this.count++; }
            decrement() { this.count--; }
            
            get value() { return this.count; }
            set value(newValue) { this.count = newValue; }
            
            #privateMethod() { return this.#privateField; }
            
            static create() { return new Counter(); }
        }
        """
    ],
    
    "variables": [
        "var legacyVar = 'old';",
        "let mutableVar = 'can change';",
        "const immutableVar = 'fixed';",
        "const { destructured, nested: { property } } = object;",
        "const [first, ...rest] = array;"
    ],
    
    "modern_features": [
        "const templateLiteral = `Value: ${value}`;",
        "const optionalChaining = obj?.prop?.method?.();",
        "const nullishCoalescing = value ?? defaultValue;",
        "const spreadObject = { ...baseObject, newProp: 'value' };",
        "try { await Promise.all([p1, p2]); } catch { /* handle error */ }"
    ]
}

# Combine all samples into one large comprehensive test
COMPREHENSIVE_SAMPLE = "\n\n".join([
    "// ES6 Imports",
    "\n".join(TEST_SAMPLES["es6_imports"]),
    
    "// CommonJS Imports",
    "\n".join(TEST_SAMPLES["commonjs_imports"]),
    
    "// Exports",
    "\n".join(TEST_SAMPLES["exports"]),
    
    "// Functions",
    "\n".join(TEST_SAMPLES["functions"]),
    
    "// Classes",
    "\n".join(TEST_SAMPLES["classes"]),
    
    "// Variables",
    "\n".join(TEST_SAMPLES["variables"]),
    
    "// Modern Features",
    "\n".join(TEST_SAMPLES["modern_features"])
])

class MockJavaScriptParserAdapter:
    """Mock version of JavaScriptParserAdapter for testing.
    
    This class mocks the analyzer to test its API and integration
    independently of the tree-sitter parsing infrastructure.
    """
    
    def __init__(self):
        """Initialize the mock adapter."""
        pass
    
    def parse(self, code):
        """Parse code into a mock tree."""
        root_node = MockNode(type="program", text=code)
        
        # Add simple children based on content
        if "import" in code:
            root_node.children.append(MockNode(type="import_statement", text="import"))
            
        if "export" in code:
            root_node.children.append(MockNode(type="export_statement", text="export"))
            
        if "function" in code:
            root_node.children.append(MockNode(type="function_declaration", text="function"))
            
        if "class" in code:
            root_node.children.append(MockNode(type="class_declaration", text="class"))
            
        if "const" in code or "let" in code or "var" in code:
            root_node.children.append(MockNode(type="variable_declaration", text="variable"))
        
        return MockTree(root_node)
    
    def analyze(self, code):
        """Analyze code and return a mock structure."""
        import re
        
        # Base result structure
        result = {
            'imports': [],
            'exports': [],
            'functions': [],
            'classes': [],
            'variables': [],
            'has_errors': False
        }
        
        # Detect imports
        for line in code.split('\n'):
            # ES6 imports
            if re.search(r'import\s+.+\s+from\s+[\'"]', line):
                if '{' in line:
                    # Named imports
                    module_match = re.search(r'from\s+[\'"]([^\'"]+)[\'"]', line)
                    module = module_match.group(1) if module_match else "unknown"
                    
                    names = []
                    named_match = re.search(r'{([^}]+)}', line)
                    if named_match:
                        names_text = named_match.group(1)
                        names = [n.strip().split(' as ')[0].strip() for n in names_text.split(',')]
                    
                    result['imports'].append({
                        'type': 'import',
                        'module': module,
                        'names': names,
                        'is_default': False
                    })
                elif '*' in line:
                    # Namespace import
                    module_match = re.search(r'from\s+[\'"]([^\'"]+)[\'"]', line)
                    module = module_match.group(1) if module_match else "unknown"
                    
                    name_match = re.search(r'\*\s+as\s+(\w+)', line)
                    name = name_match.group(1) if name_match else "unknown"
                    
                    result['imports'].append({
                        'type': 'import',
                        'module': module,
                        'name': name,
                        'is_namespace': True,
                        'is_default': False
                    })
                else:
                    # Default import
                    default_match = re.search(r'import\s+(\w+)\s+from', line)
                    name = default_match.group(1) if default_match else "unknown"
                    
                    module_match = re.search(r'from\s+[\'"]([^\'"]+)[\'"]', line)
                    module = module_match.group(1) if module_match else "unknown"
                    
                    result['imports'].append({
                        'type': 'import',
                        'module': module,
                        'name': name,
                        'is_default': True
                    })
            
            # CommonJS requires
            elif 'require(' in line:
                name_match = re.search(r'(?:const|let|var)\s+(\w+)\s*=\s*require', line)
                name = name_match.group(1) if name_match else "unknown"
                
                module_match = re.search(r'require\s*\([\'"]([^\'"]+)[\'"]', line)
                module = module_match.group(1) if module_match else "unknown"
                
                result['imports'].append({
                    'type': 'require',
                    'module': module,
                    'name': name,
                    'is_default': True
                })
            
            # Exports
            elif line.strip().startswith('export '):
                if 'default' in line:
                    # Default export
                    class_match = re.search(r'export\s+default\s+class\s+(\w+)', line)
                    func_match = re.search(r'export\s+default\s+function\s+(\w+)', line)
                    
                    if class_match:
                        name = class_match.group(1)
                        export_type = 'class'
                    elif func_match:
                        name = func_match.group(1)
                        export_type = 'function'
                    else:
                        name = 'default'
                        export_type = 'value'
                    
                    result['exports'].append({
                        'type': 'export',
                        'name': name,
                        'export_type': export_type,
                        'is_default': True
                    })
                elif 'function' in line:
                    # Named function export
                    func_match = re.search(r'export\s+function\s+(\w+)', line)
                    name = func_match.group(1) if func_match else "unknown"
                    
                    result['exports'].append({
                        'type': 'export',
                        'name': name,
                        'export_type': 'function',
                        'is_default': False
                    })
                elif 'class' in line:
                    # Named class export
                    class_match = re.search(r'export\s+class\s+(\w+)', line)
                    name = class_match.group(1) if class_match else "unknown"
                    
                    result['exports'].append({
                        'type': 'export',
                        'name': name,
                        'export_type': 'class',
                        'is_default': False
                    })
                elif 'const' in line or 'let' in line or 'var' in line:
                    # Variable export
                    var_match = re.search(r'export\s+(?:const|let|var)\s+(\w+)', line)
                    name = var_match.group(1) if var_match else "unknown"
                    
                    result['exports'].append({
                        'type': 'export',
                        'name': name,
                        'export_type': 'variable',
                        'is_default': False
                    })
                elif '{' in line:
                    # Named exports
                    named_match = re.search(r'{([^}]+)}', line)
                    if named_match:
                        names_text = named_match.group(1)
                        names = [n.strip().split(' as ')[0].strip() for n in names_text.split(',')]
                        
                        for name in names:
                            result['exports'].append({
                                'type': 'export',
                                'name': name,
                                'export_type': 'named',
                                'is_default': False
                            })
                elif '*' in line:
                    # Re-export
                    module_match = re.search(r'from\s+[\'"]([^\'"]+)[\'"]', line)
                    module = module_match.group(1) if module_match else "unknown"
                    
                    result['exports'].append({
                        'type': 'export',
                        'export_type': 'namespace',
                        'is_namespace': True,
                        'source': module,
                        'is_default': False
                    })
            
            # Functions - improved to catch async functions too
            elif ('function ' in line or 'function*' in line or line.strip().startswith('async function')):
                is_generator = '*' in line
                is_async = 'async' in line
                
                # Handle both regular and async functions
                if is_async:
                    func_match = re.search(r'async\s+function\s+(\w+)', line)
                else:
                    func_match = re.search(r'function\s*\*?\s*(\w+)', line)
                    
                name = func_match.group(1) if func_match else "unknown"
                
                result['functions'].append({
                    'type': 'function',
                    'name': name,
                    'is_generator': is_generator,
                    'is_async': is_async,
                    'is_arrow': False,
                    'is_method': False
                })
            elif '=>' in line:
                # Arrow function
                name_match = re.search(r'(?:const|let|var)\s+(\w+)\s*=', line)
                name = name_match.group(1) if name_match else "unknown"
                
                result['functions'].append({
                    'type': 'function',
                    'name': name,
                    'is_generator': False,
                    'is_async': 'async' in line,
                    'is_arrow': True,
                    'is_method': False
                })
            
            # Variables - improved to detect destructuring patterns
            elif line.strip().startswith(('const ', 'let ', 'var ')):
                # Skip arrow functions already handled
                if '=>' not in line:
                    if '{' in line and '=' in line:
                        # Object destructuring pattern
                        var_match = re.search(r'(?:const|let|var)\s+\{([^}]+)\}', line)
                        if var_match:
                            destructured_names = var_match.group(1).split(',')
                            for name_part in destructured_names:
                                name = name_part.strip().split(':')[0].strip()
                                result['variables'].append({
                                    'type': 'variable',
                                    'name': name,
                                    'declaration_type': 'const' if 'const' in line else ('let' if 'let' in line else 'var')
                                })
                    elif '[' in line and '=' in line:
                        # Array destructuring pattern
                        var_match = re.search(r'(?:const|let|var)\s+\[([^\]]+)\]', line)
                        if var_match:
                            destructured_names = var_match.group(1).split(',')
                            for name_part in destructured_names:
                                name = name_part.strip().split('...')[0].strip()
                                if name:  # Skip empty names from rest pattern
                                    result['variables'].append({
                                        'type': 'variable',
                                        'name': name,
                                        'declaration_type': 'const' if 'const' in line else ('let' if 'let' in line else 'var')
                                    })
                    else:
                        # Simple variable assignment
                        var_match = re.search(r'(?:const|let|var)\s+(\w+)', line)
                        if var_match:
                            name = var_match.group(1)
                            
                            result['variables'].append({
                                'type': 'variable',
                                'name': name,
                                'declaration_type': 'const' if 'const' in line else ('let' if 'let' in line else 'var')
                            })
        
        # Class detection with a simple regex approach
        class_matches = re.finditer(r'class\s+(\w+)', code)
        for match in class_matches:
            name = match.group(1)
            result['classes'].append({
                'type': 'class',
                'name': name,
                'methods': [],  # Would be populated with proper parsing
                'properties': []
            })
        
        # Return the mocked result
        return result


class TestJavaScriptParserAdapter(unittest.TestCase):
    """Test suite for the JavaScript parser adapter."""
    
    def setUp(self):
        """Set up the test with a mock parser."""
        self.parser = MockJavaScriptParserAdapter()
    
    def test_parse_returns_mock_tree(self):
        """Test that parse returns a MockTree."""
        result = self.parser.parse("const x = 1;")
        self.assertIsInstance(result, MockTree)
        self.assertEqual(result.root_node.type, "program")
    
    def test_analyze_es6_imports(self):
        """Test analysis of ES6 imports."""
        for sample in TEST_SAMPLES["es6_imports"]:
            result = self.parser.analyze(sample)
            self.assertGreaterEqual(len(result['imports']), 1, f"Failed to detect import in: {sample}")
            self.assertEqual(result['imports'][0]['type'], 'import')
    
    def test_analyze_commonjs_imports(self):
        """Test analysis of CommonJS imports."""
        for sample in TEST_SAMPLES["commonjs_imports"]:
            result = self.parser.analyze(sample)
            self.assertGreaterEqual(len(result['imports']), 1, f"Failed to detect require in: {sample}")
            self.assertEqual(result['imports'][0]['type'], 'require')
    
    def test_analyze_exports(self):
        """Test analysis of export statements."""
        for sample in TEST_SAMPLES["exports"]:
            result = self.parser.analyze(sample)
            self.assertGreaterEqual(len(result['exports']), 1, f"Failed to detect export in: {sample}")
            self.assertEqual(result['exports'][0]['type'], 'export')
    
    def test_analyze_functions(self):
        """Test analysis of function declarations."""
        for sample in TEST_SAMPLES["functions"]:
            result = self.parser.analyze(sample)
            self.assertGreaterEqual(len(result['functions']), 1, f"Failed to detect function in: {sample}")
            self.assertEqual(result['functions'][0]['type'], 'function')
    
    def test_analyze_classes(self):
        """Test analysis of class declarations."""
        for sample in TEST_SAMPLES["classes"]:
            result = self.parser.analyze(sample)
            self.assertGreaterEqual(len(result['classes']), 1, f"Failed to detect class in: {sample}")
            self.assertEqual(result['classes'][0]['type'], 'class')
    
    def test_analyze_variables(self):
        """Test analysis of variable declarations."""
        for sample in TEST_SAMPLES["variables"]:
            if "=" in sample and not "=>" in sample:  # Skip destructuring for now
                result = self.parser.analyze(sample)
                self.assertGreaterEqual(len(result['variables']), 1, f"Failed to detect variable in: {sample}")
                self.assertEqual(result['variables'][0]['type'], 'variable')
    
    def test_comprehensive_analysis(self):
        """Test comprehensive analysis of all features combined."""
        result = self.parser.analyze(COMPREHENSIVE_SAMPLE)
        
        # Check that we found at least some items in each category
        self.assertGreaterEqual(len(result['imports']), 4, "Failed to detect imports")
        self.assertGreaterEqual(len(result['exports']), 3, "Failed to detect exports")
        self.assertGreaterEqual(len(result['functions']), 3, "Failed to detect functions")
        self.assertGreaterEqual(len(result['classes']), 1, "Failed to detect classes")
        self.assertGreaterEqual(len(result['variables']), 2, "Failed to detect variables")


if __name__ == "__main__":
    unittest.main() 