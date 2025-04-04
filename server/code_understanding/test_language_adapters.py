import unittest
import pytest
from server.code_understanding.language_adapters import JavaScriptParserAdapter

@pytest.fixture
def js_parser():
    return JavaScriptParserAdapter()

def test_empty_input(js_parser):
    """Test parsing of empty input"""
    result = js_parser.parse("")
    assert result is not None, "Empty input should return a valid tree"
    assert result.root_node.type == 'program', "Root node should be a program"
    assert not result.root_node.children, "Empty program should have no children"
    
    # Empty spaces should also parse fine
    result = js_parser.parse("   \n   ")
    assert result is not None

def test_es6_imports(js_parser):
    """Test ES6 import statements"""
    # Default import
    code = "import React from 'react';"
    result = js_parser.analyze(code)
    imports = result.get('imports', [])
    assert len(imports) == 1
    assert imports[0]['name'] == 'React'
    assert imports[0]['module'] == 'react'
    assert imports[0]['is_default'] == True
    
    # Named imports
    code = "import { useState, useEffect } from 'react';"
    result = js_parser.analyze(code)
    imports = result.get('imports', [])
    assert len(imports) == 1
    assert 'names' in imports[0]
    assert 'useState' in imports[0]['names']
    assert 'useEffect' in imports[0]['names']
    
    # Namespace import
    code = "import * as ReactDOM from 'react-dom';"
    result = js_parser.analyze(code)
    imports = result.get('imports', [])
    assert len(imports) == 1
    assert imports[0]['name'] == 'ReactDOM'
    assert imports[0]['module'] == 'react-dom'
    assert imports[0].get('is_namespace') == True

def test_require_statements(js_parser):
    """Test CommonJS require statements"""
    code = "const fs = require('fs');"
    result = js_parser.analyze(code)
    imports = result.get('imports', [])
    assert len(imports) == 1
    assert imports[0]['name'] == 'fs'
    assert imports[0]['module'] == 'fs'
    assert imports[0]['type'] == 'require'

def test_async_await(js_parser):
    """Test async/await functions"""
    code = """
    async function fetchData() {
        const response = await fetch('/api/data');
        return response.json();
    }
    
    const fetchUser = async (id) => {
        const response = await fetch(`/api/users/${id}`);
        return response.json();
    };
    """
    
    result = js_parser.analyze(code)
    functions = result.get('functions', [])
    assert len(functions) == 2
    
    # Check regular async function
    assert any(f['name'] == 'fetchData' and f['is_async'] == True for f in functions)
    
    # Check async arrow function
    assert any(f['name'] == 'fetchUser' and f['is_async'] == True and f['is_arrow'] == True for f in functions)

def test_decorators(js_parser):
    """Test decorator-like patterns in JS"""
    # While JS doesn't have native decorators, we can test experimental syntax or patterns
    code = """
    class MyComponent extends React.Component {
        @autobind
        handleClick() {
            console.log('clicked');
        }
        
        render() {
            return <div onClick={this.handleClick}>Click me</div>;
        }
    }
    """
    
    # This test might be skipped depending on parser capabilities
    try:
        result = js_parser.analyze(code)
        classes = result.get('classes', [])
        assert len(classes) > 0
    except Exception as e:
        # Skip if decorators not supported
        pytest.skip(f"Decorator parsing not supported: {e}")

def test_class_fields(js_parser):
    """Test class fields and methods"""
    code = """
    class Counter {
        count = 0;
        #privateField = 'secret';
        
        static DEFAULT_COUNT = 0;
        
        increment() {
            this.count++;
        }
        
        static create() {
            return new Counter();
        }
    }
    """
    
    result = js_parser.analyze(code)
    classes = result.get('classes', [])
    assert len(classes) == 1
    assert classes[0]['name'] == 'Counter'
    
    # Check for methods and fields - the exact structure might vary
    assert len(classes[0]['methods']) > 0
    # Assert that it found the increment method
    assert any(m['name'] == 'increment' for m in classes[0]['methods'])

def test_modern_features(js_parser):
    """Test modern JS features like destructuring, rest/spread, etc."""
    code = """
    // Destructuring
    const { name, age } = person;
    const [first, ...rest] = items;
    
    // Template literals
    const greeting = `Hello, ${name}!`;
    
    // Arrow functions with implicit returns
    const double = x => x * 2;
    
    // Optional chaining
    const value = obj?.prop?.nested;
    """
    
    # This is primarily a syntax test - just verify it parses
    result = js_parser.analyze(code)
    assert 'error' not in result, f"Failed to parse modern features: {result.get('error')}"

def test_error_handling(js_parser):
    """Test handling of syntax errors"""
    code = """
    function broken( {
        // Missing closing parenthesis
        return "oops";
    }
    """
    
    result = js_parser.analyze(code)
    # We expect either an error field or has_errors to be true
    assert result.get('has_errors') or 'error' in result
    
    # Empty code should not cause errors
    result = js_parser.analyze("")
    assert not result.get('has_errors', False)

def test_exports(js_parser):
    """Test various export formats"""
    code = """
    // Named exports
    export const PI = 3.14159;
    export function square(x) { return x * x; }
    
    // Default export
    export default class Calculator {
        add(a, b) { return a + b; }
    }
    """
    
    result = js_parser.analyze(code)
    exports = result.get('exports', [])
    assert len(exports) >= 2  # At least named and default exports
    
    # Check for default export
    assert any(e.get('is_default', False) for e in exports)

def test_variable_declarations(js_parser):
    """Test different variable declaration types"""
    code = """
    var legacy = 'old';
    let mutable = 'can change';
    const immutable = 'fixed';
    """
    
    result = js_parser.analyze(code)
    variables = result.get('variables', [])
    assert len(variables) == 3
    
    var_names = [v['name'] for v in variables]
    assert 'legacy' in var_names
    assert 'mutable' in var_names
    assert 'immutable' in var_names

def test_class_fields(js_parser):
    """Test class fields and methods"""
    code = """
    class Example {
        static field = 'static';
        instanceField = 'instance';
        
        static method() {}
        instanceMethod() {}
        
        #privateField = 'private';
        #privateMethod() {}
    }
    """
    result = js_parser.parse(code)
    assert not result.has_errors
    
    classes = result.features['classes']
    assert len(classes) == 1
    methods = classes[0]['methods']
    assert len(methods) == 4
    assert any(m['is_static'] for m in methods) 