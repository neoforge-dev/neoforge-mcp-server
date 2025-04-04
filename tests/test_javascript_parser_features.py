"""
Tests for specific JavaScript parser features that need better coverage.

This file contains targeted tests for methods in JavaScriptParserAdapter that currently
have low test coverage, including:
- _extract_js_es6_import
- _extract_js_require
- _extract_js_export
- _extract_js_function
- _extract_js_class
- _extract_js_method
- _extract_js_field
"""

import pytest
import logging
from server.code_understanding.analyzer import CodeAnalyzer
from server.code_understanding.language_adapters import JavaScriptParserAdapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def analyzer():
    """Fixture to provide a CodeAnalyzer instance."""
    return CodeAnalyzer()

@pytest.fixture
def js_parser():
    """Fixture to provide a JavaScriptParserAdapter instance."""
    return JavaScriptParserAdapter()

class TestJSImportExtractionFeatures:
    """Tests for JavaScript import extraction features."""
    
    def test_extract_js_es6_import_named(self, analyzer):
        """Test extraction of ES6 named imports."""
        code = "import { useState, useEffect } from 'react';"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify imports
        imports = result.get('imports', [])
        assert len(imports) > 0, "Should find imports"
        
        # Find the react import
        react_import = next((imp for imp in imports if 'react' in str(imp)), None)
        assert react_import is not None, "Should find React import"
        assert 'useState' in str(react_import), "Should extract useState"
        assert 'useEffect' in str(react_import), "Should extract useEffect"
    
    def test_extract_js_es6_import_default(self, analyzer):
        """Test extraction of ES6 default imports."""
        code = "import React from 'react';"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify imports
        imports = result.get('imports', [])
        assert len(imports) > 0, "Should find imports"
        
        # Find the default import
        default_import = next((imp for imp in imports if 'react' in str(imp)), None)
        assert default_import is not None, "Should find default React import"
        assert 'React' in str(default_import), "Should extract React name"
    
    def test_extract_js_es6_import_namespace(self, analyzer):
        """Test extraction of ES6 namespace imports."""
        code = "import * as React from 'react';"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify imports
        imports = result.get('imports', [])
        assert len(imports) > 0, "Should find imports"
        
        # Find the namespace import
        namespace_import = next((imp for imp in imports if 'react' in str(imp)), None)
        assert namespace_import is not None, "Should find namespace React import"
        assert 'React' in str(namespace_import), "Should extract namespace name"
    
    def test_extract_js_es6_import_dynamic(self, analyzer):
        """Test extraction of dynamic imports."""
        code = "const module = import('./dynamic-module.js');"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify imports - dynamic imports may be handled differently
        imports = result.get('imports', [])
        
        # Look for dynamic import - even if not directly captured as an import
        # it should at least not cause errors
        assert 'has_errors' not in result or not result['has_errors'], "Should handle dynamic imports without errors"
    
    def test_extract_js_require_simple(self, analyzer):
        """Test extraction of CommonJS require statements."""
        code = "const fs = require('fs');"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify imports
        imports = result.get('imports', [])
        assert len(imports) > 0, "Should find imports"
        
        # Find the require import
        require_import = next((imp for imp in imports if 'fs' in str(imp)), None)
        assert require_import is not None, "Should find fs require"
    
    def test_extract_js_require_destructuring(self, analyzer):
        """Test extraction of CommonJS require with destructuring."""
        code = "const { readFile, writeFile } = require('fs');"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify imports
        imports = result.get('imports', [])
        assert len(imports) > 0, "Should find imports"
        
        # Find the require import
        require_import = next((imp for imp in imports if 'fs' in str(imp)), None)
        assert require_import is not None, "Should find fs require"
        # May or may not extract destructured names depending on implementation
    
    def test_extract_js_require_in_object(self, analyzer):
        """Test extraction of CommonJS require within object literals."""
        code = "const deps = { fs: require('fs'), path: require('path') };"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify imports
        imports = result.get('imports', [])
        assert len(imports) > 0, "Should find imports"
        
        # Look for at least one of the requires
        found_requires = [imp for imp in imports if 'fs' in str(imp) or 'path' in str(imp)]
        assert len(found_requires) > 0, "Should find at least one require in object"

class TestJSExportExtractionFeatures:
    """Tests for JavaScript export extraction features."""
    
    def test_extract_js_export_named(self, analyzer):
        """Test extraction of named exports."""
        code = "export const API_URL = 'https://api.example.com';"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify exports
        exports = result.get('exports', [])
        assert len(exports) > 0, "Should find exports"
        
        # Find the named export
        named_export = next((exp for exp in exports if 'API_URL' in str(exp)), None)
        assert named_export is not None, "Should find API_URL export"
    
    def test_extract_js_export_function(self, analyzer):
        """Test extraction of function exports."""
        code = "export function fetchData() { return fetch('/api'); }"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify exports
        exports = result.get('exports', [])
        assert len(exports) > 0, "Should find exports"
        
        # Find the function export
        function_export = next((exp for exp in exports if 'fetchData' in str(exp)), None)
        assert function_export is not None, "Should find fetchData export"
    
    def test_extract_js_export_default(self, analyzer):
        """Test extraction of default exports."""
        code = "export default class App { render() {} }"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify exports
        exports = result.get('exports', [])
        assert len(exports) > 0, "Should find exports"
        
        # Find the default export
        default_export = next((exp for exp in exports if 'default' in str(exp)), None)
        assert default_export is not None, "Should find default export"
        assert 'App' in str(default_export), "Should identify App in default export"
    
    def test_extract_js_export_named_from(self, analyzer):
        """Test extraction of named exports from another module."""
        code = "export { useState, useEffect } from 'react';"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify exports
        exports = result.get('exports', [])
        assert len(exports) > 0, "Should find exports"
        
        # Find a re-export 
        re_export = next((exp for exp in exports if 'react' in str(exp) or 'useState' in str(exp)), None)
        assert re_export is not None, "Should find re-export"
    
    def test_extract_js_export_namespace(self, analyzer):
        """Test extraction of namespace exports."""
        code = "export * from './utils';"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify exports
        exports = result.get('exports', [])
        assert len(exports) > 0, "Should find exports"
        
        # Find namespace export
        namespace_export = next((exp for exp in exports if './utils' in str(exp)), None)
        assert namespace_export is not None, "Should find namespace export"
    
    def test_extract_js_export_alias(self, analyzer):
        """Test extraction of exports with aliases."""
        code = "export { default as React } from 'react';"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify exports
        exports = result.get('exports', [])
        assert len(exports) > 0, "Should find exports"
        
        # Find alias export
        alias_export = next((exp for exp in exports if 'React' in str(exp)), None)
        assert alias_export is not None, "Should find export with alias"

class TestJSFunctionExtractionFeatures:
    """Tests for JavaScript function extraction features."""
    
    def test_extract_js_function_declaration(self, analyzer):
        """Test extraction of function declarations."""
        code = "function greet(name) { return `Hello, ${name}!`; }"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify functions
        functions = result.get('functions', [])
        assert len(functions) > 0, "Should find functions"
        
        # Find the function
        greet_func = next((func for func in functions if func['name'] == 'greet'), None)
        assert greet_func is not None, "Should find greet function"
    
    def test_extract_js_function_expression(self, analyzer):
        """Test extraction of function expressions."""
        code = "const greet = function(name) { return `Hello, ${name}!`; };"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify functions
        functions = result.get('functions', [])
        assert len(functions) > 0, "Should find functions"
        
        # Find the function
        greet_func = next((func for func in functions if func['name'] == 'greet'), None)
        assert greet_func is not None, "Should find greet function expression"
    
    def test_extract_js_arrow_function(self, analyzer):
        """Test extraction of arrow functions."""
        code = "const greet = (name) => `Hello, ${name}!`;"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify functions
        functions = result.get('functions', [])
        assert len(functions) > 0, "Should find functions"
        
        # Find the arrow function
        greet_func = next((func for func in functions if func['name'] == 'greet'), None)
        assert greet_func is not None, "Should find greet arrow function"
    
    def test_extract_js_async_function(self, analyzer):
        """Test extraction of async functions."""
        code = "async function fetchData() { const response = await fetch('/api'); return response.json(); }"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify functions
        functions = result.get('functions', [])
        assert len(functions) > 0, "Should find functions"
        
        # Find the async function
        async_func = next((func for func in functions if func['name'] == 'fetchData'), None)
        assert async_func is not None, "Should find fetchData async function"
        assert async_func.get('is_async', False), "Should identify function as async"
    
    def test_extract_js_generator_function(self, analyzer):
        """Test extraction of generator functions."""
        code = "function* generator() { yield 1; yield 2; }"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify functions
        functions = result.get('functions', [])
        assert len(functions) > 0, "Should find functions"
        
        # Find the generator function
        generator_func = next((func for func in functions if func['name'] == 'generator'), None)
        assert generator_func is not None, "Should find generator function"
        assert generator_func.get('is_generator', False) or '*' in generator_func.get('text', ''), "Should identify as generator"
    
    def test_extract_js_async_generator_function(self, analyzer):
        """Test extraction of async generator functions."""
        code = "async function* asyncGenerator() { for await (const x of items) { yield x; } }"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify functions
        functions = result.get('functions', [])
        assert len(functions) > 0, "Should find functions"
        
        # Find the async generator function
        async_gen_func = next((func for func in functions if func['name'] == 'asyncGenerator'), None)
        assert async_gen_func is not None, "Should find asyncGenerator function"
        
        # Check if it's identified as both async and generator
        is_async = async_gen_func.get('is_async', False)
        is_generator = async_gen_func.get('is_generator', False)
        contains_async = 'async' in async_gen_func.get('text', '')
        contains_generator = '*' in async_gen_func.get('text', '')
        
        assert is_async or contains_async, "Should identify as async"
        assert is_generator or contains_generator, "Should identify as generator"

class TestJSClassExtractionFeatures:
    """Tests for JavaScript class extraction features."""
    
    def test_extract_js_class_basic(self, analyzer):
        """Test extraction of basic classes."""
        code = """
        class Counter {
            constructor() {
                this.count = 0;
            }
            
            increment() {
                this.count++;
            }
        }
        """
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify classes
        classes = result.get('classes', [])
        assert len(classes) > 0, "Should find classes"
        
        # Find the class
        counter_class = next((cls for cls in classes if cls['name'] == 'Counter'), None)
        assert counter_class is not None, "Should find Counter class"
    
    def test_extract_js_class_inheritance(self, analyzer):
        """Test extraction of class inheritance."""
        code = """
        class Component {}
        class App extends Component {
            render() {
                return 'Hello';
            }
        }
        """
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify classes
        classes = result.get('classes', [])
        assert len(classes) == 2, "Should find both classes"
        
        # Find the App class
        app_class = next((cls for cls in classes if cls['name'] == 'App'), None)
        assert app_class is not None, "Should find App class"
        
        # Inheritance might be captured in the text or a specific field
        assert 'extends' in app_class.get('text', '') or app_class.get('extends') == 'Component', "Should capture inheritance"
    
    def test_extract_js_class_methods(self, analyzer):
        """Test extraction of class methods."""
        code = """
        class Service {
            constructor() {}
            
            getData() {}
            
            async fetchData() {}
            
            static create() {}
            
            get count() {}
            
            set count(value) {}
        }
        """
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify classes
        classes = result.get('classes', [])
        assert len(classes) > 0, "Should find classes"
        
        # Find the Service class
        service_class = next((cls for cls in classes if cls['name'] == 'Service'), None)
        assert service_class is not None, "Should find Service class"
        
        # Class methods might be captured as functions or as methods in the class
        methods = service_class.get('methods', [])
        if methods:
            assert len(methods) >= 5, "Should find all methods"
            method_names = [m.get('name') for m in methods]
            assert 'constructor' in method_names, "Should find constructor"
            assert 'getData' in method_names, "Should find getData method"
            assert 'fetchData' in method_names, "Should find fetchData method"
            assert 'create' in method_names, "Should find static create method"
            assert 'count' in method_names, "Should find getter/setter methods"
    
    def test_extract_js_class_fields(self, analyzer):
        """Test extraction of class fields."""
        code = """
        class User {
            name = '';
            #age = 0;
            static MAX_USERS = 100;
            
            constructor(name) {
                this.name = name;
            }
        }
        """
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify classes
        classes = result.get('classes', [])
        assert len(classes) > 0, "Should find classes"
        
        # Find the User class
        user_class = next((cls for cls in classes if cls['name'] == 'User'), None)
        assert user_class is not None, "Should find User class"
        
        # Fields might be captured directly or in the text
        class_text = user_class.get('text', '')
        assert 'name = ' in class_text, "Should find name field"
        assert '#age' in class_text, "Should find private age field"
        assert 'MAX_USERS' in class_text, "Should find static MAX_USERS field"
    
    def test_extract_js_class_private_members(self, analyzer):
        """Test extraction of private class members."""
        code = """
        class Test {
            #privateField = 'secret';
            
            #privateMethod() {
                return this.#privateField;
            }
            
            access() {
                return this.#privateMethod();
            }
        }
        """
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify classes
        classes = result.get('classes', [])
        assert len(classes) > 0, "Should find classes"
        
        # Find the Test class
        test_class = next((cls for cls in classes if cls['name'] == 'Test'), None)
        assert test_class is not None, "Should find Test class"
        
        # Private members might be captured directly or in the text
        class_text = test_class.get('text', '')
        assert '#privateField' in class_text, "Should find private field"
        assert '#privateMethod' in class_text, "Should find private method"

class TestJSVariableExtractionFeatures:
    """Tests for JavaScript variable extraction features."""
    
    def test_extract_js_variable_declaration(self, analyzer):
        """Test extraction of variable declarations with var, let, and const."""
        code = """
        var oldVar = 'old';
        let mutableVar = 'mutable';
        const immutableVar = 'immutable';
        """
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify variables
        variables = result.get('variables', [])
        assert len(variables) >= 3, "Should find all variables"
        
        # Find each variable type
        var_names = [v['name'] for v in variables]
        assert 'oldVar' in var_names, "Should find var variable"
        assert 'mutableVar' in var_names, "Should find let variable"
        assert 'immutableVar' in var_names, "Should find const variable"
    
    def test_extract_js_destructuring_assignment(self, analyzer):
        """Test extraction of variables using destructuring assignment."""
        code = """
        const { name, age } = person;
        const [first, second] = items;
        """
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify variables
        variables = result.get('variables', [])
        assert len(variables) >= 4, "Should find all destructured variables"
        
        # Find destructured variables
        var_names = [v['name'] for v in variables]
        assert 'name' in var_names, "Should find destructured name"
        assert 'age' in var_names, "Should find destructured age"
        assert 'first' in var_names, "Should find destructured first"
        assert 'second' in var_names, "Should find destructured second"
    
    def test_extract_js_complex_assignment(self, analyzer):
        """Test extraction of variables with complex assignments."""
        code = """
        const result = (() => {
            return { value: 42 };
        })();
        
        const calculated = 10 * 20 + (30 / 5);
        """
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify variables
        variables = result.get('variables', [])
        assert len(variables) >= 2, "Should find all variables"
        
        # Find the variables
        var_names = [v['name'] for v in variables]
        assert 'result' in var_names, "Should find result variable"
        assert 'calculated' in var_names, "Should find calculated variable"

class TestJSErrorHandlingFeatures:
    """Tests for JavaScript parser error handling features."""
    
    def test_syntax_error_handling(self, analyzer):
        """Test handling of syntax errors."""
        code = "function test() { console.log('missing closing brace';"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify errors are detected
        assert result.get('has_errors', False), "Should detect syntax error"
        assert len(result.get('error_details', [])) > 0, "Should provide error details"
    
    def test_unclosed_string_handling(self, analyzer):
        """Test handling of unclosed strings."""
        code = "const message = 'This string is not closed;"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify errors are detected
        assert result.get('has_errors', False), "Should detect unclosed string"
        assert len(result.get('error_details', [])) > 0, "Should provide error details"
    
    def test_unclosed_template_literal(self, analyzer):
        """Test handling of unclosed template literals."""
        code = "const template = `This template is not closed;"
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify errors are detected
        assert result.get('has_errors', False), "Should detect unclosed template literal"
        assert len(result.get('error_details', [])) > 0, "Should provide error details"
    
    def test_invalid_jsx_like_syntax(self, analyzer):
        """Test handling of JSX-like syntax in plain JS."""
        code = "const element = <div>Hello</div>;"
        result = analyzer.analyze_code(code, language='javascript')
        
        # JSX is not valid in plain JS, should detect error
        assert result.get('has_errors', False), "Should detect invalid JSX syntax"
        assert len(result.get('error_details', [])) > 0, "Should provide error details"
    
    def test_recovery_from_partial_errors(self, analyzer):
        """Test recovery from partial errors."""
        code = """
        // Valid function
        function validFunction() {
            return true;
        }
        
        // Invalid function with syntax error
        function invalidFunction() {
            return true
        
        // Another valid function
        function anotherValidFunction() {
            return false;
        }
        """
        result = analyzer.analyze_code(code, language='javascript')
        
        # Should detect errors
        assert result.get('has_errors', False), "Should detect syntax error"
        
        # But should still extract valid parts
        functions = result.get('functions', [])
        assert len(functions) >= 1, "Should extract at least one valid function"
        
        # Check if validFunction was extracted
        valid_func = next((f for f in functions if f['name'] == 'validFunction'), None)
        assert valid_func is not None, "Should extract validFunction despite errors elsewhere"

class TestJSDeduplicationFeatures:
    """Tests for JavaScript parser deduplication features."""
    
    def test_deduplicate_functions(self, analyzer):
        """Test deduplication of functions with the same name."""
        code = """
        // These functions have the same name but are at different positions
        function test() { return 1; }
        
        if (condition) {
            function test() { return 2; }
        }
        """
        result = analyzer.analyze_code(code, language='javascript')
        
        # Should deduplicate functions by name
        functions = result.get('functions', [])
        test_functions = [f for f in functions if f['name'] == 'test']
        
        # This might return 1 or 2 functions depending on deduplication strategy
        # The important part is that the code doesn't crash with duplicates
        assert len(test_functions) > 0, "Should extract test function"
    
    def test_deduplicate_imports(self, analyzer):
        """Test deduplication of imports from the same module."""
        code = """
        import React from 'react';
        import { useState } from 'react';
        import * as ReactDOM from 'react-dom';
        import { render } from 'react-dom';
        """
        result = analyzer.analyze_code(code, language='javascript')
        
        # Verify imports (may be deduplicated by source or not, depending on implementation)
        imports = result.get('imports', [])
        assert len(imports) > 0, "Should extract imports"
        
        # Check for 'react' import
        react_imports = [i for i in imports if 'react' in str(i) and 'react-dom' not in str(i)]
        assert len(react_imports) > 0, "Should extract react imports"
        
        # Check for 'react-dom' import
        react_dom_imports = [i for i in imports if 'react-dom' in str(i)]
        assert len(react_dom_imports) > 0, "Should extract react-dom imports" 